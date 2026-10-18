import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.JsonAsset;
import com.hypixel.hytale.assetstore.RawAsset;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.ExtraInfo;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.builder.BuilderField;
import com.hypixel.hytale.codec.util.RawJsonReader;
import com.hypixel.hytale.codec.validation.ValidationResults;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;

import org.bson.BsonDocument;
import org.bson.BsonValue;

import java.lang.classfile.ClassFile;
import java.lang.classfile.ClassModel;
import java.lang.classfile.CodeElement;
import java.lang.classfile.Instruction;
import java.lang.classfile.MethodModel;
import java.lang.classfile.instruction.ConstantInstruction;
import java.lang.classfile.instruction.FieldInstruction;
import java.lang.classfile.instruction.InvokeInstruction;
import java.lang.constant.ClassDesc;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Décode les assets JSON du pack avec les codecs du serveur Hytale pour détecter
 * les clés inconnues et les valeurs invalides sans lancer le jeu.
 *
 * Usage : java -cp Server-0.7.2.jar ValidateAssets.java <dossier pack/Server>
 */
public class ValidateAssets {
    private static final Map<String, String> CODECS = new LinkedHashMap<>();

    private static final List<String> STORES = List.of(
            "com.hypixel.hytale.server.core.asset.AssetRegistryLoader"
    );

    private static final List<String> EMPTY_STORES = List.of(
            "com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction",
            "com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction",
            "com.hypixel.hytale.server.core.modules.entitystats.asset.EntityStatType"
    );

    /** Méthodes qui enregistrent des types de codecs ("Classe" = initialiseur statique, "Classe#méthode" sinon). */
    private static final List<String> BOOTSTRAP = List.of(
            "com.hypixel.hytale.builtin.hytalegenerator.assets.AssetManager",
            // Types d'interactions (Simple, Serial, Parallel, DamageEntity...) : setup() du module et des plugins.
            "com.hypixel.hytale.server.core.modules.interaction.InteractionModule#setup",
            "com.hypixel.hytale.server.core.modules.projectile.ProjectileModule#setup",
            "com.hypixel.hytale.builtin.abilities.AbilitiesPlugin#setup",
            "com.hypixel.hytale.builtin.beam.BeamPlugin#setup",
            "com.hypixel.hytale.builtin.deployables.DeployablesPlugin#setup",
            "com.hypixel.hytale.builtin.crafting.CraftingPlugin#setup",
            "com.hypixel.hytale.server.npc.NPCPlugin#setup",
            "com.hypixel.hytale.server.spawning.SpawningPlugin#setup",
            "com.hypixel.hytale.builtin.mounts.MountPlugin#setup",
            // Types d'établis (Crafting, Processing...).
            "com.hypixel.hytale.server.core.blocktype.BlockTypeModule#setup"
    );

    static {
        CODECS.put("HytaleGenerator/Biomes/", "com.hypixel.hytale.builtin.hytalegenerator.assets.biomes.BiomeAsset");
        CODECS.put("HytaleGenerator/WorldStructures/", "com.hypixel.hytale.builtin.hytalegenerator.assets.worldstructures.WorldStructureAsset");
        CODECS.put("PortalTypes/", "com.hypixel.hytale.server.core.asset.type.portalworld.PortalType");
        CODECS.put("Environments/", "com.hypixel.hytale.server.core.asset.type.environment.config.Environment");
        CODECS.put("Weathers/", "com.hypixel.hytale.server.core.asset.type.weather.config.Weather");
        CODECS.put("NPC/Spawn/World/", "com.hypixel.hytale.server.spawning.assets.spawns.config.WorldNPCSpawn");
        CODECS.put("Item/Items/", "com.hypixel.hytale.server.core.asset.type.item.config.Item");
        CODECS.put("Instances/", "com.hypixel.hytale.server.core.universe.world.WorldConfig");
        CODECS.put("NPC/Spawn/Markers/", "com.hypixel.hytale.server.spawning.assets.spawnmarker.config.SpawnMarker");
        CODECS.put("NPC/Groups/", "com.hypixel.hytale.builtin.tagset.config.NPCGroup");
        CODECS.put("Models/", "com.hypixel.hytale.server.core.asset.type.model.config.ModelAsset");
        CODECS.put("Entity/Effects/", "com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect");
        CODECS.put("Drops/", "com.hypixel.hytale.server.core.asset.type.item.config.ItemDropList");
        CODECS.put("Item/RootInteractions/", "com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction");
        CODECS.put("Item/Interactions/", "com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction");
    }

    private static int replayCodecRegistrations(String entry) throws Exception {
        String className = entry.contains("#") ? entry.substring(0, entry.indexOf('#')) : entry;
        String methodName = entry.contains("#") ? entry.substring(entry.indexOf('#') + 1) : "<clinit>";
        byte[] bytes;
        try (var in = ClassLoader.getSystemResourceAsStream(className.replace('.', '/') + ".class")) {
            bytes = in.readAllBytes();
        }
        ClassModel model = ClassFile.of().parse(bytes);
        int count = 0;
        for (MethodModel method : model.methods()) {
            if (!method.methodName().equalsString(methodName) || method.code().isEmpty()) {
                continue;
            }
            List<Instruction> window = new ArrayList<>();
            for (CodeElement element : method.code().get()) {
                if (!(element instanceof Instruction instruction)) {
                    continue;
                }
                if (instruction instanceof InvokeInstruction invoke
                        && invoke.name().equalsString("register")
                        && invoke.typeSymbol().parameterCount() == 3
                        && window.size() >= 4) {
                    List<Instruction> args = window.subList(window.size() - 4, window.size());
                    // CODEC.register(...) ou, dans un plugin, getCodecRegistry(CODEC).register(...).
                    Instruction map = args.get(0);
                    if (map instanceof InvokeInstruction registry && registry.name().equalsString("getCodecRegistry")
                            && window.size() >= 5) {
                        map = window.get(window.size() - 5);
                    }
                    // La clé du type est une chaîne ("Simple") ou une constante d'enum (BenchType.Crafting).
                    if (map instanceof FieldInstruction mapField
                            && (args.get(1) instanceof ConstantInstruction || args.get(1) instanceof FieldInstruction)
                            && args.get(2) instanceof ConstantInstruction typeClass
                            && args.get(3) instanceof FieldInstruction typeCodec
                            && typeClass.constantValue() instanceof ClassDesc classDesc) {
                        Object name = null;
                        try {
                            name = args.get(1) instanceof ConstantInstruction constant
                                    ? constant.constantValue() : staticField((FieldInstruction) args.get(1));
                            Object mapCodec = staticField(mapField);
                            Class<?> type = Class.forName(binaryName(classDesc));
                            Object codec = staticField(typeCodec);
                            for (Method register : mapCodec.getClass().getMethods()) {
                                if (register.getName().equals("register") && register.getParameterCount() == 3
                                        && register.getParameterTypes()[0].isInstance(name)
                                        && register.getParameterTypes()[2].isInstance(codec)) {
                                    register.invoke(mapCodec, name, type, codec);
                                    count++;
                                    break;
                                }
                            }
                        } catch (Throwable t) {
                            System.out.println("WARN  type " + name + " non enregistré : " + rootCause(t));
                        }
                    }
                }
                window.add(instruction);
            }
        }
        return count;
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static ExtraInfo newExtraInfo(Class<?> assetClass, Path file) {
        if (!JsonAsset.class.isAssignableFrom(assetClass)) {
            return new ExtraInfo();
        }
        String key = file.getFileName().toString().replaceFirst("\\.json$", "");
        return new AssetExtraInfo(file, new AssetExtraInfo.Data((Class) assetClass, key, null));
    }

    private static final Pattern STEREO_WORLD_SOUND = Pattern.compile("\"WorldSoundEventId\"\\s*:\\s*\"([^\"]*_Local)\"");

    private static void decodeAsset(Class<?> assetClass, Path file, List<String> problems, List<String> notes) throws Exception {
        Codec<?> codec = (Codec<?>) assetClass.getField("CODEC").get(null);
        ExtraInfo extraInfo = newExtraInfo(assetClass, file);
        String json = Files.readString(file);
        try {
            decode(codec, RawJsonReader.fromJsonString(json), extraInfo, "", problems, notes);
        } catch (Throwable t) {
            // Deux cas que seul le serveur peut décoder : un type d'interaction écrit en Java par nos plugins, et un
            // asset qui hérite (Parent) d'un asset vanilla absent hors jeu.
            String message = String.valueOf(rootCause(t).getMessage());
            if (rootCause(t) instanceof com.hypixel.hytale.codec.lookup.ACodecMapCodec.UnknownIdException
                    && (message.contains("'Type': Nakasar_") || message.contains("'Type': null") && json.contains("\"Parent\""))) {
                notes.add("non vérifiable hors jeu : " + message);
                return;
            }
            throw t;
        }
        // Les sons vanilla ne sont pas chargés hors jeu, donc le validateur MONO de WorldSoundEventId ne tourne pas.
        // Les variantes "_Local" sont stéréo : en jeu, l'interaction entière est rejetée.
        Matcher stereo = STEREO_WORLD_SOUND.matcher(json);
        while (stereo.find()) {
            problems.add("WorldSoundEventId " + stereo.group(1) + " : son « _Local » (stéréo), refusé par le validateur MONO du serveur ; utiliser la variante sans _Local");
        }
        if (json.contains("\"Parent\"")) {
            // Les champs obligatoires viennent du parent vanilla.
            problems.removeIf(p -> p.contains("Can't be null"));
        }
    }


    /**
     * Décode un asset (les validateurs des champs tournent pendant le décodage), puis les assets écrits en ligne
     * dedans (ex. une interaction dans "Next"), que le serveur valide comme des assets à part entière.
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    private static void decode(Codec<?> codec, RawJsonReader reader, ExtraInfo extraInfo, String label,
                               List<String> problems, List<String> notes) throws Exception {
        try {
            // decodeJsonAsset (comme AssetStore) rattache les données de l'asset (tags...) avant les champs.
            if (codec instanceof com.hypixel.hytale.assetstore.codec.AssetCodec assetCodec && extraInfo instanceof AssetExtraInfo assetInfo) {
                assetCodec.decodeJsonAsset(reader, assetInfo);
            } else {
                codec.decodeJson(reader, extraInfo);
            }
        } catch (Throwable t) {
            if (!isAfterDecode(t)) {
                throw t;
            }
            // Le JSON est décodé ; seul le post-traitement (qui lit les assets vanilla chargés) a échoué.
            notes.add(label + "post-traitement ignoré hors serveur : " + rootCause(t).getMessage());
        }
        for (String key : extraInfo.getUnknownKeys()) {
            problems.add(label + "clé inconnue : " + key);
        }
        List<String> found = new ArrayList<>();
        collectResults(extraInfo.getValidationResults(), found, notes);
        found.stream().distinct().forEach(r -> problems.add(label + r));
        if (!(extraInfo instanceof AssetExtraInfo<?> assetInfo)) {
            return;
        }
        Map<Class<? extends JsonAssetWithMap>, Map<Object, List<RawAsset<Object>>>> contained = new HashMap<>();
        assetInfo.getData().fetchContainedRawAssets(assetInfo.getData().getKey(), contained);
        for (var byClass : contained.entrySet()) {
            Codec<?> childCodec = (Codec<?>) byClass.getKey().getField("CODEC").get(null);
            for (List<RawAsset<Object>> children : byClass.getValue().values()) {
                for (RawAsset<Object> child : children) {
                    AssetExtraInfo.Data data = child.makeData((Class) byClass.getKey(), child.getKey(), child.getParentKey());
                    AssetExtraInfo<?> childInfo = new AssetExtraInfo<>(child.getPath(), data);
                    decode(childCodec, child.toRawJsonReader(() -> new char[4096]), childInfo,
                            label + child.getKey() + " > ", problems, notes);
                }
            }
        }
    }

    /**
     * Chaque validateur de champ termine par _processValidationResults(), qui déplace les avertissements et
     * les échecs de getResults() vers le champ protégé validatorExceptions : on lit les deux.
     */
    private static void collectResults(ValidationResults results, List<String> problems, List<String> notes) throws Exception {
        List<Object> all = new ArrayList<>();
        if (results.getResults() != null) {
            all.addAll(results.getResults());
        }
        Field held = ValidationResults.class.getDeclaredField("validatorExceptions");
        held.setAccessible(true);
        List<?> holders = (List<?>) held.get(results);
        if (holders != null) {
            for (Object holder : holders) {
                // Record protégé : on passe par ses composants.
                var components = holder.getClass().getRecordComponents();
                String key = null;
                List<?> list = List.of();
                for (var component : components) {
                    Method accessor = component.getAccessor();
                    accessor.setAccessible(true);
                    if (component.getName().equals("key")) {
                        key = (String) accessor.invoke(holder);
                    } else if (component.getName().equals("results")) {
                        list = (List<?>) accessor.invoke(holder);
                    }
                }
                for (Object r : list) {
                    all.add(key + " : " + r);
                }
            }
        }
        for (Object r : all) {
            String text = String.valueOf(r).replace("\n", " ").replace("\t", " ").trim();
            // Les magasins d'assets sont vides hors serveur : une référence vers un autre asset (son, stat, interaction
            // vanilla) ne peut pas y être trouvée. Elle est notée, pas comptée.
            boolean reference = text.contains("doesn't exist") || text.contains("does not exist");
            if (text.contains("FAIL") && !reference) {
                problems.add(text);
            } else {
                notes.add(text);
            }
        }
    }

    private static final Pattern PREFAB_BLOCK = Pattern.compile("\"name\":\"(?:\\d+%)?([^\"]+)\"");
    private static final Pattern WORLDGEN_BLOCK = Pattern.compile("\"Solid\"\\s*:\\s*\"([^\"]+)\"");

    /**
     * Un id de bloc inconnu dans un prefab ou un matériau du générateur ne fait aucune erreur au
     * chargement : le serveur pose le bloc « Unknown » (damier rose et noir). On compare donc chaque
     * id à la liste des blocs vanilla (-Dblocks=fichier, une ligne par id, états compris sous la forme
     * « *Bloc_State_Definitions_État ») ; nos propres blocs commencent par Nakasar_.
     */
    private static int checkBlockIds(Path root, Path idsFile) throws Exception {
        java.util.Set<String> known = new java.util.HashSet<>();
        for (String line : Files.readAllLines(idsFile)) {
            line = line.strip();
            if (!line.isEmpty() && !line.startsWith("#")) {
                known.add(line);
            }
        }
        known.add("Empty");
        List<Path> files;
        try (Stream<Path> walk = Files.walk(root)) {
            files = walk.filter(p -> p.toString().endsWith(".prefab.json")
                            || p.toString().endsWith(".json") && root.relativize(p).toString().replace('\\', '/').startsWith("HytaleGenerator/"))
                    .sorted()
                    .toList();
        }
        int errors = 0;
        for (Path file : files) {
            Pattern pattern = file.toString().endsWith(".prefab.json") ? PREFAB_BLOCK : WORLDGEN_BLOCK;
            Matcher matcher = pattern.matcher(Files.readString(file));
            java.util.Set<String> unknown = new java.util.TreeSet<>();
            while (matcher.find()) {
                String id = matcher.group(1);
                if (!known.contains(id) && !id.startsWith("Nakasar_")) {
                    unknown.add(id);
                }
            }
            if (!unknown.isEmpty()) {
                errors++;
                System.out.println("ERROR " + root.relativize(file).toString().replace('\\', '/'));
                unknown.forEach(id -> System.out.println("      bloc inconnu (damier rose en jeu) : " + id));
            }
        }
        System.out.println(files.size() + " prefabs et fichiers du générateur vérifiés (ids de blocs), " + errors + " en erreur");
        return errors;
    }

    private static final Pattern PREFAB_PATH = Pattern.compile("\"Path\"\\s*:\\s*\"([^\"]+)\"");

    /**
     * Les props Prefab référencent un fichier (avec son extension) ou un dossier relatif à Server/Prefabs/,
     * comme PrefabPropAsset.loadPrefabBuffersFrom : il doit exister dans le pack. Le serveur ignore sans
     * rien dire un chemin introuvable, d'où cette vérification.
     */
    private static void checkPrefabPaths(Path root, Path file, List<String> problems) throws Exception {
        Matcher matcher = PREFAB_PATH.matcher(Files.readString(file));
        while (matcher.find()) {
            String path = matcher.group(1);
            Path target = root.resolve("Prefabs").resolve(path);
            boolean found = Files.isRegularFile(target) && path.endsWith(".json");
            if (!found && Files.isDirectory(target)) {
                try (Stream<Path> walk = Files.walk(target)) {
                    found = walk.anyMatch(p -> p.toString().endsWith(".prefab.json"));
                }
            }
            if (!found) {
                problems.add("prefab introuvable dans le pack : " + path);
            }
        }
    }

    /**
     * Vrai seulement si le post-traitement a échoué parce qu'un magasin d'assets n'existe pas hors
     * serveur (il est rempli par les plugins au démarrage) ; toute autre erreur reste une erreur.
     */
    private static boolean isAfterDecode(Throwable t) {
        Throwable cause = rootCause(t);
        if (!(cause instanceof NullPointerException) || cause.getMessage() == null
                || !cause.getMessage().contains("getAssetStore(")) {
            return false;
        }
        for (StackTraceElement frame : cause.getStackTrace()) {
            if (frame.getMethodName().equals("afterDecodeAndValidate")) {
                return true;
            }
        }
        return false;
    }

    /**
     * WorldConfig ne se construit pas hors serveur (configs de plugins) : on décode chaque champ
     * séparément, et on vérifie que le générateur HytaleGenerator pointe sur une WorldStructure du pack.
     */
    private static void checkWorldConfig(Path root, Path file, BuilderCodec<?> codec, List<String> problems) throws Exception {
        BsonDocument document = BsonDocument.parse(Files.readString(file));
        Map<String, ? extends List<? extends BuilderField<?, ?>>> entries = codec.getEntries();
        for (String key : document.keySet()) {
            BsonValue value = document.get(key);
            if (key.equals("WorldGen")) {
                BsonDocument worldGen = value.asDocument();
                if (!worldGen.getString("Type").getValue().equals("HytaleGenerator")) {
                    continue;
                }
                for (String genKey : worldGen.keySet()) {
                    if (!List.of("Type", "WorldStructure", "SeedOverride").contains(genKey)) {
                        problems.add("clé inconnue : WorldGen." + genKey);
                    }
                }
                String structure = worldGen.getString("WorldStructure").getValue();
                if (!Files.exists(root.resolve("HytaleGenerator/WorldStructures/" + structure + ".json"))) {
                    problems.add("WorldStructure introuvable dans le pack : " + structure);
                }
                continue;
            }
            var fields = entries.get(key);
            if (fields == null) {
                problems.add("clé inconnue : " + key);
                continue;
            }
            try {
                fields.get(0).getCodec().getChildCodec().decode(value, new ExtraInfo());
            } catch (Throwable t) {
                problems.add(key + " : " + describe(t));
            }
        }
    }

    private static String describe(Throwable t) {
        Throwable cause = rootCause(t);
        return t + (cause != t ? " / cause : " + cause : "");
    }

    /** Les magasins d'assets publient leurs événements sur le bus du serveur : on en fournit un sans démarrer le serveur. */
    private static void fakeServer() throws Exception {
        Field unsafeField = Class.forName("sun.misc.Unsafe").getDeclaredField("theUnsafe");
        unsafeField.setAccessible(true);
        Object unsafe = unsafeField.get(null);
        Class<?> serverClass = Class.forName("com.hypixel.hytale.server.core.HytaleServer");
        Object server = unsafe.getClass().getMethod("allocateInstance", Class.class).invoke(unsafe, serverClass);
        Field eventBus = serverClass.getDeclaredField("eventBus");
        eventBus.setAccessible(true);
        Object bus = Class.forName("com.hypixel.hytale.event.EventBus").getConstructor(boolean.class).newInstance(false);
        Method objectFieldOffset = unsafe.getClass().getMethod("objectFieldOffset", Field.class);
        long offset = (long) objectFieldOffset.invoke(unsafe, eventBus);
        unsafe.getClass().getMethod("putObject", Object.class, long.class, Object.class).invoke(unsafe, server, offset, bus);
        Field instance = serverClass.getDeclaredField("instance");
        instance.setAccessible(true);
        instance.set(null, server);
    }

    /**
     * Magasins d'assets créés par des modules (interactions, stats) au démarrage du serveur : on en crée des
     * vides, pour que le décodage puisse y chercher les références et y valider les ids.
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    private static void emptyStore(String className) throws Exception {
        Class c = Class.forName(className);
        if (com.hypixel.hytale.assetstore.AssetRegistry.getAssetStore(c) != null) {
            return;
        }
        var map = new com.hypixel.hytale.assetstore.map.IndexedLookupTableAssetMap(n -> java.lang.reflect.Array.newInstance(c, n));
        var builder = com.hypixel.hytale.server.core.asset.HytaleAssetStore.builder(c, map);
        builder.setPath("X/" + c.getSimpleName());
        builder.setCodec((com.hypixel.hytale.assetstore.codec.AssetCodec) c.getField("CODEC").get(null));
        Method getId = c.getMethod("getId");
        builder.setKeyFunction(o -> {
            try {
                return getId.invoke(o);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });
        builder.setReplaceOnRemove(k -> null);
        com.hypixel.hytale.assetstore.AssetRegistry.register(builder.build());
    }

    private static Throwable rootCause(Throwable t) {
        while (t.getCause() != null) {
            t = t.getCause();
        }
        return t;
    }

    private static Object staticField(FieldInstruction field) throws Exception {
        String owner = field.owner().asInternalName().replace('/', '.');
        return Class.forName(owner).getField(field.name().stringValue()).get(null);
    }

    private static String binaryName(ClassDesc desc) {
        String descriptor = desc.descriptorString();
        return descriptor.substring(1, descriptor.length() - 1).replace('/', '.');
    }

    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]);
        // Les magasins d'assets lisent les options de ligne de commande du serveur.
        com.hypixel.hytale.server.core.Options.parse(new String[0]);
        fakeServer();
        for (String store : STORES) {
            try {
                Class.forName(store);
            } catch (Throwable t) {
                System.out.println("WARN  initialisation de " + store + " : " + rootCause(t));
            }
        }
        for (String store : EMPTY_STORES) {
            emptyStore(store);
        }
        // Les types du générateur (Density, Props...) sont enregistrés dans l'initialiseur statique
        // d'AssetManager, qui a besoin d'un serveur démarré. On rejoue seulement ses appels
        // CODEC.register("Type", Classe.class, Classe.CODEC) en lisant son bytecode.
        for (String bootstrap : BOOTSTRAP) {
            int count = replayCodecRegistrations(bootstrap);
            System.out.println("INFO  " + count + " types enregistrés depuis " + bootstrap);
        }
        List<Path> files;
        try (Stream<Path> walk = Files.walk(root)) {
            files = walk.filter(Files::isRegularFile)
                    .filter(p -> p.toString().endsWith(".json") || p.toString().endsWith(".bson"))
                    .filter(p -> !p.toString().endsWith(".prefab.json"))
                    .sorted()
                    .toList();
        }
        int errors = 0;
        int checked = 0;
        for (Path file : files) {
            String rel = root.relativize(file).toString().replace('\\', '/');
            String className = CODECS.entrySet().stream()
                    .filter(e -> rel.startsWith(e.getKey()))
                    .map(Map.Entry::getValue)
                    .findFirst()
                    .orElse(null);
            if (className == null) {
                continue;
            }
            checked++;
            List<String> problems = new ArrayList<>();
            List<String> notes = new ArrayList<>();
            try {
                Class<?> assetClass = Class.forName(className);
                if (rel.startsWith("Instances/")) {
                    checkWorldConfig(root, file, (BuilderCodec<?>) assetClass.getField("CODEC").get(null), problems);
                } else {
                    decodeAsset(assetClass, file, problems, notes);
                }
                if (rel.startsWith("HytaleGenerator/")) {
                    checkPrefabPaths(root, file, problems);
                }
            } catch (Throwable t) {
                problems.add(describe(t));
                if (System.getenv("VALIDATE_TRACE") != null) {
                    rootCause(t).printStackTrace(System.out);
                }
            }
            if (problems.isEmpty()) {
                System.out.println("OK    " + rel);
                notes.forEach(n -> System.out.println("      note : " + n));
            } else {
                errors++;
                System.out.println("ERROR " + rel);
                problems.forEach(p -> System.out.println("      " + p));
            }
        }
        System.out.println(checked + " fichiers vérifiés, " + errors + " en erreur");
        String blocks = System.getProperty("blocks");
        if (blocks != null) {
            errors += checkBlockIds(root, Path.of(blocks));
        }
        System.exit(errors == 0 ? 0 : 1);
    }
}
