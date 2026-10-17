import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.JsonAsset;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.ExtraInfo;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.builder.BuilderField;
import com.hypixel.hytale.codec.util.RawJsonReader;
import com.hypixel.hytale.codec.validation.ValidationResults;

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

    private static final List<String> BOOTSTRAP = List.of(
            "com.hypixel.hytale.builtin.hytalegenerator.assets.AssetManager"
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
    }

    private static int replayCodecRegistrations(String className) throws Exception {
        byte[] bytes;
        try (var in = ClassLoader.getSystemResourceAsStream(className.replace('.', '/') + ".class")) {
            bytes = in.readAllBytes();
        }
        ClassModel model = ClassFile.of().parse(bytes);
        int count = 0;
        for (MethodModel method : model.methods()) {
            if (!method.methodName().equalsString("<clinit>") || method.code().isEmpty()) {
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
                    if (args.get(0) instanceof FieldInstruction mapField
                            && args.get(1) instanceof ConstantInstruction typeName
                            && args.get(2) instanceof ConstantInstruction typeClass
                            && args.get(3) instanceof FieldInstruction typeCodec
                            && typeName.constantValue() instanceof String name
                            && typeClass.constantValue() instanceof ClassDesc classDesc) {
                        Object mapCodec = staticField(mapField);
                        Class<?> type = Class.forName(binaryName(classDesc));
                        Object codec = staticField(typeCodec);
                        for (Method register : mapCodec.getClass().getMethods()) {
                            if (register.getName().equals("register") && register.getParameterCount() == 3
                                    && register.getParameterTypes()[0] == String.class
                                    && register.getParameterTypes()[2].isInstance(codec)) {
                                register.invoke(mapCodec, name, type, codec);
                                count++;
                                break;
                            }
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

    private static void decodeAsset(Class<?> assetClass, Path file, List<String> problems, List<String> notes) throws Exception {
        Codec<?> codec = (Codec<?>) assetClass.getField("CODEC").get(null);
        ExtraInfo extraInfo = newExtraInfo(assetClass, file);
        RawJsonReader reader = RawJsonReader.fromJsonString(Files.readString(file));
        try {
            codec.decodeJson(reader, extraInfo);
        } catch (Throwable t) {
            if (!isAfterDecode(t)) {
                throw t;
            }
            // Le JSON est décodé ; seul le post-traitement (qui lit les assets vanilla chargés) a échoué.
            notes.add("post-traitement ignoré hors serveur : " + rootCause(t).getMessage());
        }
        for (String key : extraInfo.getUnknownKeys()) {
            problems.add("clé inconnue : " + key);
        }
        ValidationResults results = extraInfo.getValidationResults();
        results._processValidationResults();
        if (results.getResults() != null) {
            results.getResults().forEach(r -> problems.add(String.valueOf(r)));
        }
    }

    private static final Pattern PREFAB_PATH = Pattern.compile("\"Path\"\\s*:\\s*\"([^\"]+)\"");

    /** Les props Prefab référencent un fichier ou un dossier relatif à Server/ : il doit exister dans le pack. */
    private static void checkPrefabPaths(Path root, Path file, List<String> problems) throws Exception {
        Matcher matcher = PREFAB_PATH.matcher(Files.readString(file));
        while (matcher.find()) {
            String path = matcher.group(1);
            Path target = root.resolve(path);
            boolean found = Files.isRegularFile(root.resolve(path + ".prefab.json"));
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
        System.exit(errors == 0 ? 0 : 1);
    }
}
