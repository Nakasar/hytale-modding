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
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Décode les assets JSON du pack avec les codecs du serveur Hytale pour détecter
 * les clés inconnues et les valeurs invalides sans lancer le jeu.
 *
 * Usage : java -cp Server-0.7.2.jar ValidateAssets.java <dossier Server du pack>
 */
public class ValidateAssets {
    private static final Map<String, String> CODECS = new LinkedHashMap<>();
    private static final String WE = "com.hypixel.hytale.builtin.adventure.worldevents.";
    /** Particules (systèmes et émetteurs) : reconnues à l'extension du fichier, pas au dossier. */
    private static final String PARTICLE = "com.hypixel.hytale.server.core.asset.type.particle.config.";
    private static final String PARTICLE_SYSTEM = ".particlesystem";
    private static final String PARTICLE_SPAWNER = ".particlespawner";

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
            // TeleportInstance (brèche des chasseurs) et sections Instance / PortalWorldConfig des instances.
            "com.hypixel.hytale.builtin.instances.InstancesPlugin#setup",
            "com.hypixel.hytale.builtin.portals.PortalsPlugin#setup",
            // Types d'établis (Crafting, Processing...).
            "com.hypixel.hytale.server.core.blocktype.BlockTypeModule#setup",
            // Fournisseurs de point d'apparition (Global, Individual...) : PortalTypes.Spawn.
            "com.hypixel.hytale.server.core.universe.Universe#setup"
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
        CODECS.put("Item/Animations/", "com.hypixel.hytale.server.core.asset.type.itemanimation.config.ItemPlayerAnimations");
        CODECS.put("Item/RootInteractions/", "com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction");
        CODECS.put("Item/Interactions/", "com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction");
        CODECS.put("WorldEvent/Event/", WE + "event.WorldEventAsset");
        CODECS.put("WorldEvent/Stage/", WE + "event.StageAsset");
    }

    /**
     * Types des évènements de monde : WorldEventsPlugin#setup les enregistre par appels chaînés et par
     * registerCondition, que replayCodecRegistrations ne sait pas relire. Ligne = codec à types (classe#champ),
     * id du type, classe ; la condition « nuit » vient du plugin du mod (build/classes sur le classpath).
     */
    private static final String[][] WORLD_EVENT_TYPES = {
            {WE + "action.EventAction#TYPE_CODEC", "None", WE + "action.NoAction"},
            {WE + "action.EventAction#TYPE_CODEC", "EffectsAction", WE + "action.EffectsAction"},
            {WE + "action.EventAction#TYPE_CODEC", "EventStartAction", WE + "action.EventStartAction"},
            {WE + "action.EventAction#TYPE_CODEC", "EventStopAction", WE + "action.EventStopAction"},
            {WE + "action.EventAction#TYPE_CODEC", "GlobalEventStartAction", WE + "action.GlobalEventStartAction"},
            {WE + "action.EventAction#TYPE_CODEC", "GlobalEventStopAction", WE + "action.GlobalEventStopAction"},
            {WE + "action.EventAction#TYPE_CODEC", "MapMarkerOverrideAddAction", WE + "action.MapMarkerOverrideAddAction"},
            {WE + "action.EventAction#TYPE_CODEC", "MapMarkerOverrideRemoveAction", WE + "action.MapMarkerOverrideRemoveAction"},
            {WE + "action.EventAction#TYPE_CODEC", "MessageAction", WE + "action.MessageAction"},
            {WE + "action.EventAction#TYPE_CODEC", "PrefabPasteAction", WE + "action.PrefabPasteAction"},
            {WE + "action.EventAction#TYPE_CODEC", "PrefabRemoveAction", WE + "action.PrefabRemoveAction"},
            {WE + "action.EventAction#TYPE_CODEC", "ShowEventTitleAction", WE + "action.ShowEventTitleAction"},
            {WE + "action.effect.shape.Shape#TYPE_CODEC", "Point", WE + "action.effect.shape.Point"},
            {WE + "action.effect.shape.Shape#TYPE_CODEC", "Ring", WE + "action.effect.shape.Ring"},
            {WE + "condition.spawner.Spawner$Config#TYPE_CODEC", "NoSpawner", WE + "condition.spawner.NoSpawner$Config"},
            {WE + "condition.spawner.Spawner$Config#TYPE_CODEC", "PrefabSpawner", WE + "condition.spawner.PrefabSpawner$Config"},
            {WE + "condition.location.EventLocation$Config#TYPE_CODEC", "WildernessLocation",
                    "com.hypixel.hytale.builtin.adventure.wilderness.component.WildernessLocation$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "None", WE + "condition.NoCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "IntervalCondition", WE + "condition.IntervalCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "LocationCondition", WE + "condition.LocationCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "ProximityCondition", WE + "condition.ProximityCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "TimeCondition", WE + "condition.TimeCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "WorldClosedCondition", WE + "condition.WorldClosedCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "EventEndCondition", WE + "condition.EventEndCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "SignalCondition", WE + "condition.SignalCondition$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "GameFlagLevelCondition",
                    "com.hypixel.hytale.builtin.gameflags.integration.GameFlagLevelCondition$Config"},
            {WE + "condition.location.EventLocation$Config#TYPE_CODEC", "None", WE + "condition.location.NoLocation$Config"},
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "Nakasar_NightCondition", "dev.nakasar.hytale.vampires.breach.NightCondition$Config"},
    };

    /** Types d'évènements de monde qui n'ont pas pu être enregistrés : comptés en erreur. */
    private static int registrationErrors;

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static int registerWorldEventTypes() {
        int count = 0;
        for (String[] row : WORLD_EVENT_TYPES) {
            try {
                String[] owner = row[0].split("#");
                var map = (com.hypixel.hytale.codec.lookup.CodecMapCodec) Class.forName(owner[0]).getField(owner[1]).get(null);
                Class<?> type = Class.forName(row[2]);
                map.register(row[1], type, (Codec) type.getField("CODEC").get(null));
                count++;
            } catch (Throwable t) {
                registrationErrors++;
                System.out.println("ERROR type d'évènement " + row[1] + " non enregistré : " + rootCause(t));
            }
        }
        return count;
    }

    /**
     * Rejoue la validation que le serveur fait au premier lancement d'un évènement (WorldEventAsset#valid) : étape
     * racine et étapes « Next » présentes, variables (LocationKey, PrefabKey...) définies avant d'être lues, pas de
     * cycle. Un évènement invalide ne démarre jamais en jeu, avec un seul avertissement dans le journal.
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    private static int checkWorldEvents(Path root) throws Exception {
        Path events = root.resolve("WorldEvent/Event");
        Path stages = root.resolve("WorldEvent/Stage");
        if (!Files.isDirectory(events)) {
            return 0;
        }
        Class stageClass = Class.forName(WE + "event.StageAsset");
        Class eventClass = Class.forName(WE + "event.WorldEventAsset");
        Object stageMap = stageClass.getField("ASSET_MAP").get(null);
        Field mapField = com.hypixel.hytale.assetstore.map.DefaultAssetMap.class.getDeclaredField("assetMap");
        mapField.setAccessible(true);
        Map<Object, Object> stageAssets = (Map<Object, Object>) mapField.get(stageMap);
        if (Files.isDirectory(stages)) {
            for (Path file : jsonFiles(stages)) {
                try {
                    stageAssets.put(assetKey(file), decodeQuietly(stageClass, file));
                } catch (Throwable t) {
                    // Déjà compté en erreur par la boucle principale ; l'évènement qui l'utilise le signalera absent.
                    System.out.println("WARN  étape " + root.relativize(file) + " non décodée : " + rootCause(t));
                }
            }
        }
        int errors = 0;
        for (Path file : jsonFiles(events)) {
            String rel = root.relativize(file).toString().replace('\\', '/');
            Object asset;
            try {
                asset = decodeQuietly(eventClass, file);
            } catch (Throwable t) {
                errors++;
                System.out.println("ERROR évènement " + rel + " : non décodé : " + rootCause(t));
                continue;
            }
            Object result;
            String code;
            while (true) {
                Object validator = Class.forName(WE + "event.Validator").getConstructor().newInstance();
                result = validator.getClass().getMethod("validate", eventClass).invoke(validator, asset);
                code = String.valueOf(result.getClass().getMethod("code").invoke(result));
                String message = String.valueOf(result.getClass().getMethod("message").invoke(result));
                java.util.regex.Matcher inline = INLINE_PREFAB_LIST.matcher(message);
                if (code.equals("PASS") || !inline.find() || !stubPrefabList(inline.group(1))) {
                    break;
                }
                // Liste de prefabs écrite dans l'étape : le serveur l'enregistre au chargement ; ses chemins sont
                // vérifiés par checkPrefabPaths, on la remplace donc par une liste non vide pour la suite.
                System.out.println("NOTE  évènement " + rel + " : liste de prefabs en ligne " + inline.group(1) + " (chemins vérifiés à part)");
            }
            if (code.equals("PASS")) {
                System.out.println("OK    évènement " + rel + " : étapes et variables cohérentes");
            } else {
                errors++;
                System.out.println("ERROR évènement " + rel + " : " + result.getClass().getMethod("message").invoke(result));
            }
        }
        return errors;
    }

    private static final java.util.regex.Pattern INLINE_PREFAB_LIST = java.util.regex.Pattern.compile("Failed to find PrefabList: (\\*\\S+)");

    /** Ajoute une liste de prefabs non vide sous {@code key} ; faux si elle existait déjà. */
    @SuppressWarnings({"unchecked", "rawtypes"})
    private static boolean stubPrefabList(String key) throws Exception {
        Class<?> listClass = Class.forName("com.hypixel.hytale.server.core.asset.type.buildertool.config.PrefabListAsset");
        Object map = listClass.getMethod("getAssetMap").invoke(null);
        Field mapField = com.hypixel.hytale.assetstore.map.DefaultAssetMap.class.getDeclaredField("assetMap");
        mapField.setAccessible(true);
        Map<Object, Object> lists = (Map<Object, Object>) mapField.get(map);
        if (lists.containsKey(key)) {
            return false;
        }
        var constructor = listClass.getDeclaredConstructor();
        constructor.setAccessible(true);
        Object stub = constructor.newInstance();
        Field paths = listClass.getDeclaredField("prefabPaths");
        paths.setAccessible(true);
        paths.set(stub, new Path[]{Path.of(key)});
        lists.put(key, stub);
        return true;
    }

    private static List<Path> jsonFiles(Path dir) throws Exception {
        try (Stream<Path> walk = Files.walk(dir)) {
            return walk.filter(Files::isRegularFile).filter(p -> p.toString().endsWith(".json")).sorted().toList();
        }
    }

    private static String assetKey(Path file) {
        return file.getFileName().toString().replaceFirst("\\.json$", "");
    }

    /** Décode un asset pour s'en servir (les erreurs de décodage sont déjà rapportées par la boucle principale). */
    @SuppressWarnings({"unchecked", "rawtypes"})
    private static Object decodeQuietly(Class<?> assetClass, Path file) throws Exception {
        var codec = (com.hypixel.hytale.assetstore.codec.AssetCodec) assetClass.getField("CODEC").get(null);
        AssetExtraInfo info = (AssetExtraInfo) newExtraInfo(assetClass, file);
        try {
            return codec.decodeJsonAsset(RawJsonReader.fromJsonString(Files.readString(file)), info);
        } catch (Throwable t) {
            // Le post-traitement d'une liste de prefabs écrite dans l'étape cherche le pack du jeu, absent hors
            // serveur : PrefabReference#processPrefabPath attrape son erreur et journalise, mais le premier appel au
            // journal du magasin PrefabListAsset échoue encore (initialisation paresseuse). Un second décodage passe.
            if (!isAfterDecode(t)) {
                throw t;
            }
        }
        return codec.decodeJsonAsset(RawJsonReader.fromJsonString(Files.readString(file)), info);
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

    private static final Pattern STEREO_WORLD_SOUND = Pattern.compile("\"WorldSoundEventId\"\\s*:\\s*\"([^\"]*)\"");
    private static Set<String> stereoSounds;

    /** Évènements sonores vanilla stéréo (liste -Dstereo, lue dans Assets.zip) ; les "_Local" le sont tous. */
    private static boolean isStereo(String id) throws Exception {
        if (stereoSounds == null) {
            stereoSounds = new HashSet<>();
            String list = System.getProperty("stereo");
            if (list != null) {
                for (String line : Files.readAllLines(Path.of(list))) {
                    if (!line.isBlank() && !line.startsWith("#")) {
                        stereoSounds.add(line.trim());
                    }
                }
            }
        }
        return id.endsWith("_Local") || stereoSounds.contains(id);
    }

    private static void decodeAsset(Class<?> assetClass, Path file, List<String> problems, List<String> notes) throws Exception {
        Codec<?> codec = (Codec<?>) assetClass.getField("CODEC").get(null);
        ExtraInfo extraInfo = newExtraInfo(assetClass, file);
        String json = Files.readString(file);
        if (json.contains("\"GradientSet\"")) {
            json = checkGradients(json, problems, notes);
        }
        // Les sons vanilla ne sont pas chargés hors jeu, donc le validateur MONO de WorldSoundEventId ne tourne pas ; on regarde le texte,
        // avant le décodage (qui s'arrête tôt sur un type d'interaction Java ou un parent vanilla).
        // Un son stéréo (les variantes "_Local", et ceux de la liste -Dstereo) fait rejeter en jeu l'interaction entière.
        Matcher stereo = STEREO_WORLD_SOUND.matcher(json);
        while (stereo.find()) {
            if (isStereo(stereo.group(1))) {
                problems.add("WorldSoundEventId " + stereo.group(1) + " : son stéréo, refusé par le validateur MONO du serveur ; choisir un son mono");
            }
        }
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
        if (json.contains("\"Parent\"")) {
            // Les champs obligatoires viennent du parent vanilla.
            problems.removeIf(p -> p.contains("Can't be null"));
        }
    }


    /**
     * Le validateur de GradientSet lit le CosmeticsModule, qui n'existe que dans un serveur démarré : on vérifie
     * les couples (GradientSet, GradientId) contre la liste vanilla passée en -Dgradients, puis on décode le JSON
     * sans ces clés.
     */
    private static String checkGradients(String json, List<String> problems, List<String> notes) throws Exception {
        String list = System.getProperty("gradients");
        Map<String, List<String>> known = new HashMap<>();
        if (list != null) {
            for (String line : Files.readAllLines(Path.of(list))) {
                String[] parts = line.trim().split("\\s+");
                if (parts.length == 2 && !line.startsWith("#")) {
                    known.computeIfAbsent(parts[0], k -> new ArrayList<>()).add(parts[1]);
                }
            }
        } else {
            notes.add("dégradés non vérifiés (pas de -Dgradients)");
        }
        BsonDocument document = BsonDocument.parse(json);
        stripGradients(document, known, list != null, problems);
        return document.toJson();
    }

    private static void stripGradients(BsonValue value, Map<String, List<String>> known, boolean check, List<String> problems) {
        if (value.isArray()) {
            value.asArray().forEach(v -> stripGradients(v, known, check, problems));
        } else if (value.isDocument()) {
            BsonDocument document = value.asDocument();
            if (document.containsKey("GradientSet")) {
                String set = document.getString("GradientSet").getValue();
                String id = document.containsKey("GradientId") ? document.getString("GradientId").getValue() : null;
                if (check && !known.containsKey(set)) {
                    problems.add("GradientSet inconnu : " + set);
                } else if (check && id != null && !known.get(set).contains(id)) {
                    problems.add("GradientId inconnu dans " + set + " : " + id);
                }
                document.remove("GradientSet");
            }
            document.values().forEach(v -> stripGradients(v, known, check, problems));
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
     * « *Bloc_State_Definitions_État ») ; nos propres blocs (Nakasar_) doivent exister dans le pack
     * (Item/Items/.../Nakasar_X.json) : un bloc d'apparition attendu d'une autre PR serait sinon un damier.
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
        java.util.Set<String> ours = new java.util.HashSet<>();
        Path items = root.resolve("Item").resolve("Items");
        if (Files.isDirectory(items)) {
            try (Stream<Path> walk = Files.walk(items)) {
                walk.map(p -> p.getFileName().toString())
                        .filter(n -> n.startsWith("Nakasar_") && n.endsWith(".json"))
                        .forEach(n -> ours.add(n.substring(0, n.length() - ".json".length())));
            }
        }
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
                String base = id.startsWith("*") ? id.substring(1).split("_State_Definitions_")[0] : id;
                if (!known.contains(id) && !ours.contains(base)) {
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
            if (!path.startsWith("Nakasar/")) {
                continue; // prefab du jeu (Assets.zip, absent ici) : un chemin absent ne place rien
            }
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
                || !cause.getMessage().contains("getAssetStore(") && !cause.getMessage().contains("AssetModule.get()")) {
            return false;
        }
        for (StackTraceElement frame : cause.getStackTrace()) {
            // processPrefabPath : une liste de prefabs résout ses chemins dans le pack du jeu, absent hors serveur.
            if (frame.getMethodName().equals("afterDecodeAndValidate") || frame.getMethodName().equals("processPrefabPath")) {
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

    /**
     * InstanceValidator (TeleportInstance.InstanceName) cherche l'instance dans les packs chargés par AssetModule,
     * absent hors serveur : il est remplacé par la même vérification dans Server/Instances du pack, comptée en
     * erreur (le message évite « does not exist », réservé aux références notées).
     */
    @SuppressWarnings({"unchecked", "rawtypes"})
    /**
     * Volumes déclencheurs des instances (resources/TriggerVolumeData.json : pièges, points de contrôle...). Le serveur
     * les lit avec des listes « tolérantes » qui ignorent en silence un effet ou une condition invalide : on décode donc
     * chaque effet et chaque condition à part, avec les types que TriggerVolumesPlugin enregistre (rejoués depuis son
     * bytecode), pour signaler un type inconnu ou un champ invalide (énumération, nombre...).
     */
    private static int checkTriggerVolumes(Path root) throws Exception {
        Map<String, Codec<?>> codecs = Map.of(
                "registerEffectType", com.hypixel.hytale.builtin.triggervolumes.effect.TriggerEffect.CODEC,
                "registerConditionType", com.hypixel.hytale.builtin.triggervolumes.effect.TriggerCondition.CODEC,
                "registerRuleType", com.hypixel.hytale.builtin.triggervolumes.effect.TriggerRule.CODEC);
        com.hypixel.hytale.builtin.triggervolumes.shape.TriggerVolumeShape.registerBuiltinShapes();
        int types = replayCodecRegistrations(
                "com.hypixel.hytale.builtin.triggervolumes.TriggerVolumesPlugin#registerEffectTypes");
        System.out.println("INFO  " + types + " types d'effets et de conditions de volumes enregistrés");
        List<Path> files;
        try (Stream<Path> walk = Files.walk(root.resolve("Instances"))) {
            files = walk.filter(f -> f.getFileName().toString().equals("TriggerVolumeData.json")).sorted().toList();
        }
        int errors = 0;
        for (Path file : files) {
            List<String> problems = new ArrayList<>();
            String json = Files.readString(file);
            ExtraInfo whole = new ExtraInfo();
            try {
                com.hypixel.hytale.builtin.triggervolumes.manager.TriggerVolumeManager.CODEC
                        .decodeJson(RawJsonReader.fromJsonString(json), whole);
            } catch (Throwable t) {
                if (!isAfterDecode(t)) {
                    problems.add(describe(t));
                }
            }
            whole.getUnknownKeys().forEach(k -> problems.add("clé inconnue : " + k));
            int count = 0;
            BsonDocument volumes = BsonDocument.parse(json).getDocument("Volumes");
            for (var entry : volumes.entrySet()) {
                BsonDocument volume = entry.getValue().asDocument();
                String name = volume.getString("Name").getValue();
                count++;
                for (var field : List.of(Map.entry("Effects", "registerEffectType"),
                        Map.entry("Conditions", "registerConditionType"), Map.entry("Rules", "registerRuleType"))) {
                    if (!volume.containsKey(field.getKey())) {
                        continue;
                    }
                    for (BsonValue item : volume.getArray(field.getKey())) {
                        ExtraInfo info = new ExtraInfo();
                        String type = item.asDocument().getString("Type").getValue();
                        try {
                            Object value = codecs.get(field.getValue())
                                    .decodeJson(RawJsonReader.fromJsonString(item.asDocument().toJson()), info);
                            if (value == null) {
                                problems.add(name + " : " + type + " non décodé (type inconnu ?)");
                            }
                        } catch (Throwable t) {
                            problems.add(name + " : " + type + " : " + describe(t));
                            continue;
                        }
                        info.getUnknownKeys().forEach(k -> problems.add(name + " : " + type + " : clé inconnue " + k));
                        List<String> found = new ArrayList<>();
                        collectResults(info.getValidationResults(), found, new ArrayList<>());
                        found.stream().distinct().forEach(r -> problems.add(name + " : " + type + " : " + r));
                    }
                }
            }
            String rel = root.relativize(file).toString().replace('\\', '/');
            if (problems.isEmpty()) {
                System.out.println("OK    " + rel + " : " + count + " volumes");
            } else {
                errors++;
                System.out.println("ERROR " + rel);
                problems.stream().distinct().limit(40).forEach(p -> System.out.println("      " + p));
            }
        }
        return errors;
    }

    private static void checkInstanceNamesOffline(Path root) throws Exception {
        Class<?> teleport = Class.forName("com.hypixel.hytale.builtin.instances.interactions.TeleportInstanceInteraction");
        BuilderCodec<?> codec = (BuilderCodec<?>) teleport.getField("CODEC").get(null);
        Class<?> original = Class.forName("com.hypixel.hytale.builtin.instances.InstanceValidator");
        var offline = new com.hypixel.hytale.codec.validation.Validator<String>() {
            @Override
            public void accept(String name, ValidationResults results) {
                if (!Files.exists(root.resolve("Instances").resolve(name).resolve("instance.bson"))) {
                    results.fail("instance '" + name + "' absente de Server/Instances du pack");
                }
            }

            @Override
            public void updateSchema(com.hypixel.hytale.codec.schema.SchemaContext context,
                                     com.hypixel.hytale.codec.schema.config.Schema target) {
            }
        };
        for (BuilderField<?, ?> field : codec.getEntries().get("InstanceName")) {
            List validators = field.getValidators();
            validators.replaceAll(v -> original.isInstance(v) ? offline : v);
        }
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

    /**
     * Références entre assets que les codecs ne résolvent pas hors jeu : en jeu, un id manquant rejette l'asset qui
     * le cite, et la chaîne peut faire échouer tout le mod (liste de butin inconnue -> rôle rejeté -> marqueur
     * d'apparition sans rôle -> « Asset validation FAILED »). Ids connus : ceux du pack (nom des fichiers) et ceux
     * du fichier -Drefs (« droplist <id> » ou « npc <id> » par ligne).
     */
    private static final Pattern DROPLIST_REF = Pattern.compile("\"(?:DroplistId|DropList|Droplist)\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern MARKER_NPC_REF = Pattern.compile("\"Name\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern WORLD_NPC_REF = Pattern.compile("\"Id\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern SPAWN_KIND_REF = Pattern.compile("\"Kind\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern SPAWN_MARKER_REF = Pattern.compile("\"SpawnMarker\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern ITEM_ANIMATIONS_REF = Pattern.compile("\"ItemPlayerAnimationsId\"\\s*:\\s*\"([^\"]+)\"");
    /** Fichiers clients cités par les assets serveur (modèles, animations, textures). */
    private static final Pattern CLIENT_FILE_REF = Pattern.compile("\"([^\"]+\\.(?:blockymodel|blockyanim|png))\"");

    private static int checkReferences(Path root, Path refsFile) throws Exception {
        Map<String, Set<String>> known = new HashMap<>();
        known.put("droplist", new HashSet<>(assetIds(root.resolve("Drops"))));
        known.put("npc", new HashSet<>(assetIds(root.resolve("NPC/Roles"))));
        known.put("marker", new HashSet<>(assetIds(root.resolve("NPC/Spawn/Markers"))));
        known.put("animations", new HashSet<>(assetIds(root.resolve("Item/Animations"))));
        for (String line : Files.readAllLines(refsFile)) {
            String[] parts = line.strip().split("\\s+");
            if (parts.length == 2 && !parts[0].startsWith("#")) {
                known.computeIfAbsent(parts[0], k -> new HashSet<>()).add(parts[1]);
            }
        }
        List<Path> files;
        try (Stream<Path> walk = Files.walk(root)) {
            files = walk.filter(Files::isRegularFile).filter(p -> p.toString().endsWith(".json")).sorted().toList();
        }
        int errors = 0;
        int refs = 0;
        for (Path file : files) {
            String rel = root.relativize(file).toString().replace('\\', '/');
            String json = Files.readString(file);
            List<String> problems = new ArrayList<>();
            refs += checkRefs(DROPLIST_REF, json, "droplist", "liste de butin inconnue", known, problems);
            if (rel.startsWith("NPC/Spawn/Markers/")) {
                refs += checkRefs(MARKER_NPC_REF, json, "npc", "rôle de PNJ inconnu", known, problems);
            } else if (rel.startsWith("NPC/Spawn/")) {
                refs += checkRefs(WORLD_NPC_REF, json, "npc", "rôle de PNJ inconnu", known, problems);
            } else if (rel.startsWith("NPC/Roles/")) {
                refs += checkRefs(SPAWN_KIND_REF, json, "npc", "rôle de PNJ inconnu", known, problems);
            }
            refs += checkRefs(SPAWN_MARKER_REF, json, "marker", "marqueur d'apparition inconnu", known, problems);
            refs += checkRefs(ITEM_ANIMATIONS_REF, json, "animations", "jeu d'animations (ItemPlayerAnimationsId) inconnu", known, problems);
            refs += checkClientFiles(root.resolveSibling("Common"), json, problems);
            if (!problems.isEmpty()) {
                errors++;
                System.out.println("ERROR " + rel);
                problems.forEach(p -> System.out.println("      " + p));
            }
        }
        System.out.println(refs + " références vers des listes de butin, rôles, marqueurs, jeux d'animations et fichiers clients vérifiées, " + errors + " fichier(s) en erreur");
        return errors;
    }

    /**
     * Les fichiers clients du mod (chemin depuis Common contenant « Nakasar ») doivent exister dans Common : un modèle ou une
     * animation absente ne se voit qu'en jeu (PNJ invisible, animation figée).
     */
    private static int checkClientFiles(Path common, String json, List<String> problems) {
        int count = 0;
        Matcher m = CLIENT_FILE_REF.matcher(json);
        while (m.find()) {
            String path = m.group(1);
            if (path.contains("Nakasar") && path.contains("/")) {
                count++;
                if (!Files.isRegularFile(common.resolve(path))) {
                    problems.add("fichier client absent de Common : " + path);
                }
            }
        }
        return count;
    }

    private static int checkRefs(Pattern pattern, String json, String type, String label, Map<String, Set<String>> known,
                                 List<String> problems) {
        int count = 0;
        Matcher m = pattern.matcher(json);
        while (m.find()) {
            count++;
            if (!known.getOrDefault(type, Set.of()).contains(m.group(1))) {
                problems.add(label + " : " + m.group(1) + " (ni dans le pack, ni dans le fichier des ids vanilla)");
            }
        }
        return count;
    }

    private static List<String> assetIds(Path dir) throws Exception {
        if (!Files.isDirectory(dir)) {
            return List.of();
        }
        try (Stream<Path> walk = Files.walk(dir)) {
            return walk.filter(Files::isRegularFile).map(p -> p.getFileName().toString())
                    .filter(n -> n.endsWith(".json")).map(n -> n.substring(0, n.length() - 5)).toList();
        }
    }

    /** Rouge des zones d'annonce : celui des annonces du donjon Deepworks vanilla (Gobliterator_*_Warning, Assets.zip 0.7.2). */
    private static final String WARNING_RED = "#ff0000";
    /** Suffixe du voile BlendLinear posé sous chaque couche additive d'une annonce (sols clairs). */
    private static final String WARNING_TINT = "_Tint";
    /** Textures vanilla admises pour une zone d'annonce (celles des annonces vanilla) ; une texture du pack doit exister dans Common. */
    private static final Pattern WARNING_VANILLA_TEXTURE =
            Pattern.compile("Particles/Textures/(?:Indicators/Warning_[A-Za-z0-9_]+|Basic/Ball5)\\.png");
    /** Zones favorables : pas d'annonce de danger, elles gardent leur couleur (aucune pour l'instant). */
    private static final Set<String> POSITIVE_ZONES = Set.of();

    /**
     * Zones d'annonce des attaques (Kevin, 26 octobre 2026 : « une zone d'annonce ennemie/danger doit être rouge orangée
     * légère », jamais blanche opaque) : tout émetteur rangé dans un dossier Warnings ou tracé avec une texture Warning_*
     * est en mélange additif (son voile _Tint en mélange normal), teinté du rouge Deepworks sur l'image de départ et
     * sur chaque image clé (une image sans couleur laisserait la texture blanche), avec des opacités entre 0 et 1 et une
     * texture qui existe.
     */
    private static int checkWarningZones(Path root) throws Exception {
        Path particles = root.resolve("Particles");
        if (!Files.isDirectory(particles)) {
            return 0;
        }
        Path common = root.resolveSibling("Common");
        List<Path> files;
        try (Stream<Path> walk = Files.walk(particles)) {
            files = walk.filter(Files::isRegularFile).filter(f -> f.toString().endsWith(PARTICLE_SPAWNER)).sorted().toList();
        }
        int errors = 0;
        int zones = 0;
        for (Path file : files) {
            String rel = root.relativize(file).toString().replace('\\', '/');
            String name = file.getFileName().toString();
            String id = name.substring(0, name.length() - PARTICLE_SPAWNER.length());
            BsonDocument doc = BsonDocument.parse(Files.readString(file));
            BsonDocument particle = doc.containsKey("Particle") ? doc.getDocument("Particle") : new BsonDocument();
            String texture = particle.containsKey("Texture") ? particle.getString("Texture").getValue() : "";
            String textureName = texture.substring(texture.lastIndexOf('/') + 1);
            boolean warning = rel.contains("/Warnings/") || textureName.startsWith("Warning_");
            if (!warning || POSITIVE_ZONES.contains(id)) {
                continue;
            }
            zones++;
            List<String> problems = new ArrayList<>();
            String blend = doc.containsKey("RenderMode") ? doc.getString("RenderMode").getValue() : "(aucun)";
            String expected = id.endsWith(WARNING_TINT) ? "BlendLinear" : "BlendAdd";
            if (!blend.equals(expected)) {
                problems.add("RenderMode " + blend + ", attendu " + expected + " (couche Deepworks en BlendAdd, voile "
                        + WARNING_TINT + " en BlendLinear)");
            }
            if (!WARNING_VANILLA_TEXTURE.matcher(texture).matches() && !Files.isRegularFile(common.resolve(texture))) {
                problems.add("texture " + texture + " : ni une texture d'annonce vanilla, ni un fichier du pack (Common)");
            }
            checkWarningFrame("InitialAnimationFrame", particle.get("InitialAnimationFrame"), problems);
            BsonValue animation = particle.get("Animation");
            if (animation == null || !animation.isDocument() || animation.asDocument().isEmpty()) {
                problems.add("Animation absente : la couleur doit être posée sur chaque image clé");
            } else {
                for (Map.Entry<String, BsonValue> frame : animation.asDocument().entrySet()) {
                    checkWarningFrame("Animation." + frame.getKey(), frame.getValue(), problems);
                }
            }
            if (!problems.isEmpty()) {
                errors++;
                System.out.println("ERROR " + rel);
                problems.forEach(pb -> System.out.println("      " + pb));
            }
        }
        errors += checkWarningTints(particles);
        System.out.println(zones + " émetteurs de zones d'annonce vérifiés (rouge Deepworks " + WARNING_RED + ", voiles _Tint), "
                + errors + " en erreur");
        return errors;
    }

    /**
     * Chaque couche additive d'un système d'annonce (dossier Warnings) a son voile {@code <couche>_Tint} en BlendLinear
     * dans le même système : sans lui, la zone ne se voit pas sur un sol clair (l'additif n'ajoute rien au blanc).
     */
    private static int checkWarningTints(Path particles) throws Exception {
        List<Path> systems;
        try (Stream<Path> walk = Files.walk(particles)) {
            systems = walk.filter(Files::isRegularFile).filter(f -> f.toString().endsWith(PARTICLE_SYSTEM))
                    .filter(f -> f.toString().replace('\\', '/').contains("/Warnings/")).sorted().toList();
        }
        int errors = 0;
        for (Path file : systems) {
            BsonDocument doc = BsonDocument.parse(Files.readString(file));
            Set<String> ids = new HashSet<>();
            doc.getArray("Spawners", new org.bson.BsonArray())
                    .forEach(v -> ids.add(v.asDocument().getString("SpawnerId").getValue()));
            List<String> missing = new ArrayList<>();
            for (String spawner : ids) {
                if (spawner.endsWith(WARNING_TINT) || POSITIVE_ZONES.contains(spawner)) {
                    continue;
                }
                Path spawnerFile = file.resolveSibling(spawner + PARTICLE_SPAWNER);
                if (!Files.isRegularFile(spawnerFile)) {
                    continue;   // émetteur rangé ailleurs : décodé avec les autres
                }
                BsonDocument s = BsonDocument.parse(Files.readString(spawnerFile));
                if (s.containsKey("RenderMode") && s.getString("RenderMode").getValue().equals("BlendAdd")
                        && !ids.contains(spawner + WARNING_TINT)) {
                    missing.add(spawner + WARNING_TINT);
                }
            }
            if (!missing.isEmpty()) {
                errors++;
                System.out.println("ERROR " + particles.getParent().relativize(file).toString().replace('\\', '/'));
                System.out.println("      voile BlendLinear absent du système : " + String.join(", ", missing));
            }
        }
        return errors;
    }

    private static void checkWarningFrame(String where, BsonValue value, List<String> problems) {
        if (value == null || !value.isDocument()) {
            problems.add(where + " absent : la couleur " + WARNING_RED + " doit y être");
            return;
        }
        BsonDocument frame = value.asDocument();
        String color = frame.containsKey("Color") && frame.get("Color").isString() ? frame.getString("Color").getValue() : null;
        if (color == null || !color.equalsIgnoreCase(WARNING_RED)) {
            problems.add(where + " : Color " + (color == null ? "absente" : color) + ", attendu " + WARNING_RED
                    + " (rouge des annonces Deepworks)");
        }
        if (frame.containsKey("Opacity")) {
            double opacity = frame.get("Opacity").isNumber() ? frame.get("Opacity").asNumber().doubleValue() : -1;
            if (opacity < 0 || opacity > 1) {
                problems.add(where + " : Opacity " + frame.get("Opacity") + " hors de [0, 1]");
            }
        }
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
        System.out.println("INFO  " + registerWorldEventTypes() + " types d'évènements de monde enregistrés");
        checkInstanceNamesOffline(root);
        List<Path> files;
        try (Stream<Path> walk = Files.walk(root)) {
            files = walk.filter(Files::isRegularFile)
                    .filter(p -> p.toString().endsWith(".json") || p.toString().endsWith(".bson")
                            || p.toString().endsWith(PARTICLE_SYSTEM) || p.toString().endsWith(PARTICLE_SPAWNER))
                    .filter(p -> !p.toString().endsWith(".prefab.json"))
                    .sorted()
                    .toList();
        }
        int errors = 0;
        int checked = 0;
        for (Path file : files) {
            String rel = root.relativize(file).toString().replace('\\', '/');
            String className = rel.endsWith(PARTICLE_SYSTEM) ? PARTICLE + "ParticleSystem"
                    : rel.endsWith(PARTICLE_SPAWNER) ? PARTICLE + "ParticleSpawner"
                    : CODECS.entrySet().stream()
                    .filter(e -> rel.startsWith(e.getKey()))
                    .map(Map.Entry::getValue)
                    .findFirst()
                    .orElse(null);
            if (className == null || rel.matches("Instances/[^/]+/resources/.*")) {
                continue; // ressources du monde copiées dans l'instance (TriggerVolumeData...), pas une config de monde
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
                if (rel.startsWith("HytaleGenerator/") || rel.startsWith("WorldEvent/")) {
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
        errors += checkWorldEvents(root) + registrationErrors;
        errors += checkTriggerVolumes(root);
        errors += checkWarningZones(root);
        String blocks = System.getProperty("blocks");
        if (blocks != null) {
            errors += checkBlockIds(root, Path.of(blocks));
        }
        String refs = System.getProperty("refs");
        if (refs != null) {
            errors += checkReferences(root, Path.of(refs));
        }
        System.exit(errors == 0 ? 0 : 1);
    }
}
