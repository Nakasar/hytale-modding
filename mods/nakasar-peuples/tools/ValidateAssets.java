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
        CODECS.put("Entity/Damage/", "com.hypixel.hytale.server.core.modules.entity.damage.DamageCause");
        CODECS.put("BarterShops/", "com.hypixel.hytale.builtin.adventure.shop.barter.BarterShopAsset");
        // Réputation (étape 4) : groupes et rangs du ReputationPlugin vanilla.
        CODECS.put("NPC/Reputation/Groups/", "com.hypixel.hytale.builtin.adventure.reputation.assets.ReputationGroup");
        CODECS.put("NPC/Reputation/Ranks/", "com.hypixel.hytale.builtin.adventure.reputation.assets.ReputationRank");
        CODECS.put("WorldEvent/Event/", WE + "event.WorldEventAsset");
        // Dialogues des PNJ : type d'asset écrit en Java par le plugin du mod (build/classes sur le classpath).
        CODECS.put("Nakasar/Dialogues/", "dev.nakasar.hytale.peuples.dialogue.Dialogue");
        CODECS.put("Nakasar/VillageLayouts/", "dev.nakasar.hytale.peuples.village.VillageLayout");
        CODECS.put("Nakasar/Requests/", "dev.nakasar.hytale.peuples.request.RequestTemplate");
        CODECS.put("Nakasar/Workshops/", "dev.nakasar.hytale.peuples.workshop.Workshop");
        CODECS.put("Nakasar/Hamlets/", "dev.nakasar.hytale.peuples.world.Hamlet");
        CODECS.put("WorldEvent/Stage/", WE + "event.StageAsset");
    }

    /**
     * Types des évènements de monde : WorldEventsPlugin#setup les enregistre par appels chaînés et par
     * registerCondition, que replayCodecRegistrations ne sait pas relire. Ligne = codec à types (classe#champ),
     * id du type, classe ; un type écrit en Java viendrait du plugin du mod (build/classes sur le classpath).
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
            // Condition du mod (raid/RaidLocationCondition) : donne au raid son lieu.
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "Nakasar_Peuples_RaidLocation", "dev.nakasar.hytale.peuples.raid.RaidLocationCondition$Config"},
            // Condition du mod (world/WorldLocationCondition) : lieu des fêtes, foires et migrations.
            {WE + "condition.EventCondition$Config#TYPE_CODEC", "Nakasar_Peuples_WorldLocation", "dev.nakasar.hytale.peuples.world.WorldLocationCondition$Config"},
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
        if (!Files.isDirectory(root.resolve("Instances"))) {
            return 0;   // pas encore d'instance dans le pack
        }
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
    private static final Pattern REQUEST_ROLES_REF = Pattern.compile("\"(?:Spawns|Roles)\"\\s*:\\s*\\[([^\\]]*)\\]");
    /** Chef d'une demande de boss ({@code "Boss": "<rôle>"}, tools/generate_quests.py). */
    private static final Pattern REQUEST_BOSS_REF = Pattern.compile("\"Boss\"\\s*:\\s*(\"[^\"]*\")");
    private static final Pattern QUOTED = Pattern.compile("\"([^\"]+)\"");
    private static final Pattern NPC_GROUPS_REF = Pattern.compile("\"NPCGroups\"\\s*:\\s*\\[([^\\]]*)\\]");
    private static final Pattern SHOP_REF = Pattern.compile("\"Shop\"\\s*:\\s*\"([^\"]+)\"");
    /** Fichiers clients cités par les assets serveur (modèles, animations, textures). */
    private static final Pattern CLIENT_FILE_REF = Pattern.compile("\"([^\"]+\\.(?:blockymodel|blockyanim|png))\"");

    private static int checkReferences(Path root, Path refsFile) throws Exception {
        Map<String, Set<String>> known = new HashMap<>();
        known.put("droplist", new HashSet<>(assetIds(root.resolve("Drops"))));
        known.put("npc", new HashSet<>(assetIds(root.resolve("NPC/Roles"))));
        known.put("marker", new HashSet<>(assetIds(root.resolve("NPC/Spawn/Markers"))));
        known.put("animations", new HashSet<>(assetIds(root.resolve("Item/Animations"))));
        known.put("npcgroup", new HashSet<>(assetIds(root.resolve("NPC/Groups"))));
        known.put("shop", new HashSet<>(assetIds(root.resolve("BarterShops"))));
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
            } else if (rel.startsWith("Nakasar/Requests/")) {
                // Bandes (Spawns) et rôles chassés (Roles) des modèles de demande : posés ou comptés par le Java.
                Matcher lists = REQUEST_ROLES_REF.matcher(json);
                while (lists.find()) {
                    refs += checkRefs(QUOTED, lists.group(1), "npc", "rôle de PNJ inconnu", known, problems);
                }
                Matcher boss = REQUEST_BOSS_REF.matcher(json);
                while (boss.find()) {
                    refs += checkRefs(QUOTED, boss.group(1), "npc", "rôle de PNJ inconnu", known, problems);
                }
            }
            if (rel.startsWith("NPC/Reputation/Groups/")) {
                // Un groupe PNJ inconnu fait lever NPCReputationHolderSystem à chaque apparition de PNJ.
                Matcher groups = NPC_GROUPS_REF.matcher(json);
                while (groups.find()) {
                    refs += checkRefs(QUOTED, groups.group(1), "npcgroup", "groupe de PNJ inconnu", known, problems);
                }
            }
            refs += checkRefs(SHOP_REF, json, "shop", "boutique de troc inconnue", known, problems);
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
    /** Textures vanilla admises pour une zone d'annonce (celles des annonces vanilla) ; une texture du pack doit exister dans Common. */
    private static final Pattern WARNING_VANILLA_TEXTURE =
            Pattern.compile("Particles/Textures/(?:Indicators/Warning_[A-Za-z0-9_]+|Basic/Ball5)\\.png");
    /** Zones favorables : pas d'annonce de danger, elles gardent leur couleur (cercle vert de Carnasse). */
    private static final Set<String> POSITIVE_ZONES = Set.of("Nakasar_Fractal_Green_Zone_Edge");
    /**
     * Anneaux d'onde de choc du Boss en fusion (contour Warning_Circle_Base qui grandit) : c'est le coup lui-même, pas
     * son annonce ; blanc au sol (à sauter), bleu en l'air (rester au sol), comme dans GW2.
     */
    private static final String SHOCK_RINGS = "Nakasar_Fractal_Molten_Shock_";

    /**
     * Zones d'annonce des attaques (Kevin, 26 octobre 2026 : « une zone d'annonce ennemie/danger doit être rouge orangée
     * légère », jamais blanche opaque) : tout émetteur rangé dans un dossier Warnings ou tracé avec une texture Warning_*
     * est en mélange normal (BlendLinear : l'additif disparaît sur un sol clair), teinté du rouge Deepworks sur l'image de départ et sur chaque image clé (une image sans
     * couleur laisserait la texture blanche), avec des opacités entre 0 et 1 et une texture qui existe.
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
            if (!warning || POSITIVE_ZONES.contains(id) || id.startsWith(SHOCK_RINGS)) {
                continue;
            }
            zones++;
            List<String> problems = new ArrayList<>();
            String blend = doc.containsKey("RenderMode") ? doc.getString("RenderMode").getValue() : "(aucun)";
            if (!blend.equals("BlendLinear")) {
                problems.add("RenderMode " + blend + " : une zone d'annonce est en BlendLinear (l'additif blanchit sur un sol clair)");
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
        System.out.println(zones + " émetteurs de zones d'annonce vérifiés (rouge Deepworks " + WARNING_RED + ", BlendLinear), "
                + errors + " en erreur");
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

    /**
     * Textes et objets des dialogues ({@code Nakasar/Dialogues}) et des modèles de demande ({@code Nakasar/Requests}) : chaque clé {@code ...Key} doit exister dans les
     * fichiers .lang fr-FR et en-US du pack (une clé absente s'affiche brute en jeu), chaque {@code ItemId} dans le
     * pack ou dans la liste des objets vanilla (un id inconnu fait échouer l'effet en jeu).
     */
    /** Le suivi d'objectif coupe le titre vers 30 caractères en capitales : un titre de demande tient en 24, sans paramètre. */
    static final int MAX_REQUEST_TITLE = 24;

    private static int checkRequestTitles(Path root) throws Exception {
        int errors = 0;
        for (String locale : List.of("fr-FR", "en-US")) {
            Path lang = root.resolve("Languages/" + locale + "/nakasar_peuples.lang");
            if (!Files.isRegularFile(lang)) {
                continue;
            }
            for (String line : Files.readAllLines(lang, java.nio.charset.StandardCharsets.UTF_8)) {
                int eq = line.indexOf('=');
                if (eq < 0) {
                    continue;
                }
                String key = line.substring(0, eq).trim();
                String text = line.substring(eq + 1).trim();
                if (!key.startsWith("request.") || !key.endsWith(".title")) {
                    continue;
                }
                if (text.length() > MAX_REQUEST_TITLE || text.contains("{")) {
                    System.out.println("  " + locale + " " + key + " : titre de demande trop long ou paramétré (" + text.length()
                            + " > " + MAX_REQUEST_TITLE + " caractères ou {param}) : « " + text + " »");
                    errors++;
                }
            }
        }
        return errors;
    }

    private static int checkDialogueTexts(Path root, String vanillaItems) throws Exception {
        List<Path> dirs = new ArrayList<>();
        for (String d : List.of("Nakasar/Dialogues", "Nakasar/Requests", "BarterShops", "Nakasar/VillageLayouts", "Nakasar/Workshops")) {
            if (Files.isDirectory(root.resolve(d))) {
                dirs.add(root.resolve(d));
            }
        }
        if (dirs.isEmpty()) {
            return 0;
        }
        Map<String, Set<String>> langs = new LinkedHashMap<>();
        for (String locale : List.of("fr-FR", "en-US")) {
            Set<String> keys = new HashSet<>();
            Path dir = root.resolve("Languages/" + locale);
            if (Files.isDirectory(dir)) {
                try (Stream<Path> files = Files.list(dir)) {
                    for (Path lang : files.filter(f -> f.toString().endsWith(".lang")).toList()) {
                        String prefix = lang.getFileName().toString().replace(".lang", "") + ".";
                        for (String line : Files.readAllLines(lang, java.nio.charset.StandardCharsets.UTF_8)) {
                            int eq = line.indexOf('=');
                            if (eq > 0) {
                                keys.add(prefix + line.substring(0, eq).trim());
                            }
                        }
                    }
                }
            }
            langs.put(locale, keys);
        }
        Set<String> items = new HashSet<>();
        if (vanillaItems != null) {
            for (String line : Files.readAllLines(Path.of(vanillaItems))) {
                if (!line.isBlank()) {
                    items.add(line.trim());
                }
            }
        }
        Path itemDir = root.resolve("Item/Items");
        if (Files.isDirectory(itemDir)) {
            try (Stream<Path> walk = Files.walk(itemDir)) {
                walk.filter(f -> f.toString().endsWith(".json"))
                        .forEach(f -> items.add(f.getFileName().toString().replace(".json", "")));
            }
        }
        // Modèles de demande, cités par les étapes de chaîne des dialogues ("Template").
        Set<String> templates = new HashSet<>();
        Path requestDir = root.resolve("Nakasar/Requests");
        if (Files.isDirectory(requestDir)) {
            try (Stream<Path> walk = Files.walk(requestDir)) {
                walk.filter(f -> f.toString().endsWith(".json"))
                        .forEach(f -> templates.add(f.getFileName().toString().replace(".json", "")));
            }
        }
        int errors = 0;
        List<Path> files = new ArrayList<>();
        for (Path dir : dirs) {
            try (Stream<Path> walk = Files.walk(dir)) {
                files.addAll(walk.filter(f -> f.toString().endsWith(".json")).sorted().toList());
            }
        }
        for (Path file : files) {
            List<String> problems = new ArrayList<>();
            BsonDocument doc = BsonDocument.parse(Files.readString(file));
            collectDialogueRefs(doc, langs, vanillaItems == null ? null : items, templates, problems);
            String rel = root.relativize(file).toString().replace('\\', '/');
            if (problems.isEmpty()) {
                System.out.println("OK    textes et objets de " + rel);
            } else {
                errors++;
                System.out.println("ERROR textes et objets de " + rel);
                problems.forEach(p -> System.out.println("      " + p));
            }
        }
        return errors;
    }

    private static void collectDialogueRefs(BsonValue value, Map<String, Set<String>> langs, Set<String> items, Set<String> templates,
                                            List<String> problems) {
        if (value.isDocument()) {
            for (Map.Entry<String, BsonValue> e : value.asDocument().entrySet()) {
                if (e.getKey().endsWith("Key") && e.getValue().isString()) {
                    String key = e.getValue().asString().getValue();
                    langs.forEach((locale, keys) -> {
                        if (!keys.contains(key)) {
                            problems.add("clé " + key + " absente des .lang " + locale);
                        }
                    });
                } else if (e.getKey().equals("ItemId") && e.getValue().isString() && items != null
                        && !items.contains(e.getValue().asString().getValue())) {
                    problems.add("objet inconnu " + e.getValue().asString().getValue()
                            + " (ni dans le pack ni dans tools/vanilla-item-ids-0.7.2.txt)");
                } else if (e.getKey().equals("Template") && e.getValue().isString()
                        && !templates.contains(e.getValue().asString().getValue())) {
                    problems.add("modèle de demande inconnu " + e.getValue().asString().getValue() + " (Server/Nakasar/Requests)");
                } else {
                    collectDialogueRefs(e.getValue(), langs, items, templates, problems);
                }
            }
        } else if (value.isArray()) {
            for (BsonValue v : value.asArray()) {
                collectDialogueRefs(v, langs, items, templates, problems);
            }
        }
    }

    /**
     * Plans de village ({@code Nakasar/VillageLayouts}) : chaque {@code Prefab} doit être un prefab vanilla relevé dans
     * Assets.zip ({@code -Dprefabs}, tools/vanilla-prefabs-0.7.2.txt) ; un chemin inconnu laisse un trou dans le village.
     */
    /**
     * Bâtiments de métier ({@code Nakasar/Workshops}) : plan, bâtiment et métier existent, le métier travaille dans ce
     * bâtiment, chaque bâtiment a au moins {@value #MIN_WORKSHOP_ORDERS} commandes ; chaque commande
     * ({@code "Workshop"} d'un modèle de demande) cite un bâtiment de métier qui existe.
     */
    private static int checkWorkshops(Path root, String prefabsFile) throws Exception {
        Path dir = root.resolve("Nakasar/Workshops");
        Path layouts = root.resolve("Nakasar/VillageLayouts");
        Path requests = root.resolve("Nakasar/Requests");
        int errors = 0;
        Map<String, Integer> orders = new LinkedHashMap<>();
        if (Files.isDirectory(dir)) {
            try (Stream<Path> walk = Files.list(dir)) {
                for (Path f : walk.filter(p -> p.toString().endsWith(".json")).sorted().toList()) {
                    orders.put(f.getFileName().toString().replace(".json", ""), 0);
                }
            }
        }
        if (Files.isDirectory(requests)) {
            try (Stream<Path> walk = Files.walk(requests)) {
                for (Path f : walk.filter(p -> p.toString().endsWith(".json")).sorted().toList()) {
                    BsonDocument doc = BsonDocument.parse(Files.readString(f));
                    if (!doc.containsKey("Workshop")) {
                        continue;
                    }
                    String w = doc.getString("Workshop").getValue();
                    boolean master = doc.containsKey("Master") && doc.getBoolean("Master").getValue();
                    if (!orders.containsKey(w)) {
                        errors++;
                        System.out.println("ERROR " + root.relativize(f) + " : bâtiment de métier inconnu " + w);
                    } else if (!master) {
                        orders.merge(w, 1, Integer::sum);
                    }
                }
            }
        }
        for (Map.Entry<String, Integer> e : orders.entrySet()) {
            Path f = dir.resolve(e.getKey() + ".json");
            BsonDocument doc = BsonDocument.parse(Files.readString(f));
            List<String> problems = new ArrayList<>();
            String layoutId = doc.containsKey("Annex") ? null : doc.getString("Layout").getValue();
            Path layoutFile = layoutId == null ? null : layouts.resolve(layoutId + ".json");
            if (doc.containsKey("Annex")) {
                checkAnnex(root, doc.getDocument("Annex"), prefabsFile, problems);
            } else if (!Files.isRegularFile(layoutFile)) {
                problems.add("plan inconnu " + layoutId);
            } else {
                BsonDocument layout = BsonDocument.parse(Files.readString(layoutFile));
                String building = doc.getString("Building").getValue();
                String job = doc.getString("Job").getValue();
                boolean hasBuilding = layout.getArray("Buildings").stream().anyMatch(b -> b.asDocument().getString("Id").getValue().equals(building));
                BsonDocument jobDoc = layout.getArray("Jobs").stream().map(BsonValue::asDocument)
                        .filter(j -> j.getString("Id").getValue().equals(job)).findFirst().orElse(null);
                if (!hasBuilding) {
                    problems.add("bâtiment " + building + " absent du plan " + layoutId);
                }
                if (jobDoc == null) {
                    problems.add("métier " + job + " absent du plan " + layoutId);
                } else if (!jobDoc.getString("Building", new org.bson.BsonString("")).getValue().equals(building)) {
                    problems.add("le métier " + job + " ne travaille pas dans " + building);
                }
            }
            // Décor des chantiers d'amélioration : « dx dy dz lacet Bloc », bloc vanilla connu.
            if (doc.containsKey("Upgrades")) {
                for (BsonValue u : doc.getArray("Upgrades")) {
                    if (!u.asDocument().containsKey("Decor")) {
                        continue;
                    }
                    for (BsonValue d : u.asDocument().getArray("Decor")) {
                        String[] p = d.asString().getValue().trim().split("\\s+");
                        if (p.length != 5 || (WORKSHOP_BLOCKS != null && !WORKSHOP_BLOCKS.contains(p[4]))) {
                            problems.add("décor mal formé ou bloc inconnu : " + d.asString().getValue());
                        }
                    }
                }
            }
            // Étape 3 : spécialités (ids uniques) et bêtes d'enclos (rôle du mod présent, ou rôle vanilla relevé).
            Set<String> specIds = new HashSet<>();
            List<String> animals = new ArrayList<>();
            if (doc.containsKey("Livestock")) {
                doc.getArray("Livestock").forEach(v -> animals.add(v.asString().getValue()));
                if (!doc.containsKey("Pen") || doc.getArray("Pen").size() != 4) {
                    problems.add("enclos sans Pen [x0, x1, z0, z1]");
                }
            }
            if (doc.containsKey("Specialties")) {
                for (BsonValue v : doc.getArray("Specialties")) {
                    BsonDocument spec = v.asDocument();
                    String sid = spec.getString("Id").getValue();
                    if (!specIds.add(sid)) {
                        problems.add("spécialité en double " + sid);
                    }
                    if (spec.containsKey("Animals")) {
                        spec.getArray("Animals").forEach(a -> animals.add(a.asString().getValue()));
                    }
                    // Étape 4 : une boutique par niveau II et III, et le lot de la Part de l'Hôte.
                    if (!spec.containsKey("Shops") || spec.getArray("Shops").size() != 2) {
                        problems.add("spécialité " + sid + " : il faut Shops [niveau II, niveau III]");
                    } else {
                        for (BsonValue shop : spec.getArray("Shops")) {
                            if (!Files.isRegularFile(root.resolve("BarterShops/" + shop.asString().getValue() + ".json"))) {
                                problems.add("spécialité " + sid + " : boutique absente " + shop.asString().getValue());
                            }
                        }
                    }
                    if (!spec.containsKey("ShareItem")) {
                        problems.add("spécialité " + sid + " : pas de lot de Part de l'Hôte (ShareItem)");
                    }
                }
            }
            String baseShop = doc.containsKey("Shop") ? doc.getString("Shop").getValue() : null;
            if (baseShop == null || !Files.isRegularFile(root.resolve("BarterShops/" + baseShop + ".json"))) {
                problems.add("boutique du niveau I absente : " + baseShop);
            }
            for (String a : animals) {
                if (a.startsWith("Nakasar_")) {
                    if (!Files.isRegularFile(root.resolve("NPC/Roles/Nakasar/Peuples/" + a + ".json"))) {
                        problems.add("bête : rôle du mod absent " + a);
                    }
                } else if (WORKSHOP_NPCS != null && !WORKSHOP_NPCS.contains(a)) {
                    problems.add("bête : rôle vanilla non relevé " + a + " (tools/vanilla-refs-0.7.2.txt)");
                }
            }
            if (e.getValue() < MIN_WORKSHOP_ORDERS) {
                problems.add(e.getValue() + " commande(s), il en faut au moins " + MIN_WORKSHOP_ORDERS);
            }
            if (problems.isEmpty()) {
                System.out.println("OK    bâtiment de métier " + e.getKey() + " (" + e.getValue() + " commandes)");
            } else {
                errors++;
                System.out.println("ERROR bâtiment de métier " + e.getKey());
                problems.forEach(p -> System.out.println("      " + p));
            }
        }
        return errors;
    }

    private static final Set<String> ANNEX_RULES = Set.of("FERTILE", "ROCK", "TREES", "WATER", "NONE");

    /**
     * Avant-poste de métier (champ {@code Annex}, tools/outposts.py) : prefabs vanilla relevés ({@code -Dprefabs}) au
     * format « chemin x z rot », emprise [x0, x1, z0, z1] au nord de la fondation, objet de fondation du pack, règle connue,
     * villageois (rôle du mod présent, ou vanilla relevé) et décor « dx dy dz lacet Bloc ».
     */
    /**
     * Lieux-dits ({@code Nakasar/Hamlets}, tools/generate_hamlets.py) : bâtiments « chemin x z rot côté chance x0 x1 z0 z1
     * haut » bien formés, un seul principal (M), chances d'un côté à 1 au plus, prefabs vanilla relevés, décor en blocs
     * connus, 1 à 3 habitants dont les rôles existent, dialogue et trocs présents.
     */
    private static int checkHamlets(Path root, String prefabsFile) throws Exception {
        Path dir = root.resolve("Nakasar/Hamlets");
        if (!Files.isDirectory(dir)) {
            return 0;
        }
        Set<String> known = new HashSet<>();
        if (prefabsFile != null) {
            for (String line : Files.readAllLines(Path.of(prefabsFile))) {
                if (!line.isBlank() && !line.startsWith("#")) {
                    known.add(line.trim().split("\\s+")[0]);
                }
            }
        }
        int errors = 0;
        int count = 0;
        try (Stream<Path> walk = Files.list(dir)) {
            for (Path f : walk.filter(p -> p.toString().endsWith(".json")).sorted().toList()) {
                count++;
                BsonDocument doc = BsonDocument.parse(Files.readString(f));
                List<String> problems = new ArrayList<>();
                String rule = doc.containsKey("Rule") ? doc.getString("Rule").getValue() : "NONE";
                if (!ANNEX_RULES.contains(rule)) {
                    problems.add("règle inconnue " + rule);
                }
                int mains = 0;
                Map<String, Double> sides = new LinkedHashMap<>();
                if (!doc.containsKey("Buildings") || doc.getArray("Buildings").isEmpty()) {
                    problems.add("aucun bâtiment");
                } else {
                    for (BsonValue v : doc.getArray("Buildings")) {
                        String[] p = v.asString().getValue().trim().split("\\s+");
                        if (p.length != 11) {
                            problems.add("bâtiment mal formé « " + v.asString().getValue() + " »");
                            continue;
                        }
                        if (prefabsFile != null && !known.contains(p[0])) {
                            problems.add("prefab vanilla non relevé " + p[0] + " (tools/vanilla-prefabs-0.7.2.txt)");
                        }
                        try {
                            double chance = Double.parseDouble(p[5]);
                            for (int i : new int[] {1, 2, 3, 6, 7, 8, 9, 10}) {
                                Integer.parseInt(p[i]);
                            }
                            if ("M".equals(p[4])) {
                                mains++;
                            } else if ("W".equals(p[4]) || "E".equals(p[4])) {
                                sides.merge(p[4], chance, Double::sum);
                            } else {
                                problems.add("côté inconnu " + p[4] + " (M, W ou E)");
                            }
                        } catch (NumberFormatException e) {
                            problems.add("nombre illisible dans « " + v.asString().getValue() + " »");
                        }
                    }
                }
                if (mains != 1) {
                    problems.add("il faut un seul bâtiment principal (côté M), pas " + mains);
                }
                for (Map.Entry<String, Double> e : sides.entrySet()) {
                    if (e.getValue() > 1.0001) {
                        problems.add("chances du côté " + e.getKey() + " au-delà de 1 : " + e.getValue());
                    }
                }
                if (doc.containsKey("Decor")) {
                    for (BsonValue v : doc.getArray("Decor")) {
                        String[] p = v.asString().getValue().trim().split("\\s+");
                        if (p.length != 5) {
                            problems.add("décor mal formé « " + v.asString().getValue() + " »");
                        } else if (WORKSHOP_BLOCKS != null && !WORKSHOP_BLOCKS.contains(p[4])) {
                            problems.add("bloc de décor inconnu " + p[4]);
                        }
                    }
                }
                int residents = doc.containsKey("Residents") ? doc.getArray("Residents").size() : 0;
                if (residents < 1 || residents > 3) {
                    problems.add("il faut 1 à 3 habitants, pas " + residents);
                } else {
                    for (BsonValue v : doc.getArray("Residents")) {
                        String role = v.asString().getValue();
                        if (!Files.isRegularFile(root.resolve("NPC/Roles/Nakasar/Peuples/" + role + ".json"))) {
                            problems.add("rôle d'habitant absent " + role);
                        }
                    }
                }
                String dialogue = doc.containsKey("Dialogue") ? doc.getString("Dialogue").getValue() : "";
                try (Stream<Path> d = Files.walk(root.resolve("Nakasar/Dialogues"))) {
                    if (d.noneMatch(x -> x.getFileName().toString().equals(dialogue + ".json"))) {
                        problems.add("dialogue absent " + dialogue);
                    }
                }
                for (String key : new String[] {"Shop", "ShopBusy"}) {
                    String shop = doc.containsKey(key) ? doc.getString(key).getValue() : "";
                    if (!Files.isRegularFile(root.resolve("BarterShops/" + shop + ".json"))) {
                        problems.add("troc absent " + key + " " + shop);
                    }
                }
                for (String problem : problems) {
                    errors++;
                    System.out.println("ERROR " + root.relativize(f) + " : " + problem);
                }
            }
        }
        System.out.println("Lieux-dits : " + count + " genres vérifiés");
        return errors;
    }

    private static void checkAnnex(Path root, BsonDocument annex, String prefabsFile, List<String> problems) throws Exception {
        Set<String> known = new HashSet<>();
        if (prefabsFile != null) {
            for (String line : Files.readAllLines(Path.of(prefabsFile))) {
                if (!line.isBlank() && !line.startsWith("#")) {
                    known.add(line.trim().split("\\s+")[0]);
                }
            }
        }
        String item = annex.containsKey("Item") ? annex.getString("Item").getValue() : "";
        try (Stream<Path> walk = Files.walk(root.resolve("Item/Items"))) {
            if (walk.noneMatch(f -> f.getFileName().toString().equals(item + ".json"))) {
                problems.add("avant-poste : objet de fondation absent " + item);
            }
        }
        String rule = annex.containsKey("Rule") ? annex.getString("Rule").getValue() : "NONE";
        if (!ANNEX_RULES.contains(rule)) {
            problems.add("avant-poste : règle inconnue " + rule);
        }
        if (!annex.containsKey("Prefabs") || annex.getArray("Prefabs").isEmpty()) {
            problems.add("avant-poste sans Prefabs");
        } else {
            for (BsonValue v : annex.getArray("Prefabs")) {
                String[] p = v.asString().getValue().trim().split("\\s+");
                if (p.length != 4) {
                    problems.add("avant-poste : prefab mal formé « " + v.asString().getValue() + " »");
                } else if (prefabsFile != null && !known.contains(p[0])) {
                    problems.add("avant-poste : prefab vanilla non relevé " + p[0] + " (tools/vanilla-prefabs-0.7.2.txt)");
                }
            }
        }
        if (!annex.containsKey("Rect") || annex.getArray("Rect").size() != 4) {
            problems.add("avant-poste : il faut Rect [x0, x1, z0, z1]");
        } else if (annex.getArray("Rect").get(3).asInt32().getValue() >= 0) {
            problems.add("avant-poste : l'emprise doit rester au nord de la fondation (z1 < 0)");
        }
        if (!annex.containsKey("Workers") || annex.getArray("Workers").isEmpty()) {
            problems.add("avant-poste sans villageois (Workers)");
        } else {
            for (BsonValue v : annex.getArray("Workers")) {
                String role = v.asDocument().getString("Role").getValue();
                if (role.startsWith("Nakasar_")) {
                    if (!Files.isRegularFile(root.resolve("NPC/Roles/Nakasar/Peuples/" + role + ".json"))) {
                        problems.add("avant-poste : rôle du mod absent " + role);
                    }
                } else if (WORKSHOP_NPCS != null && !WORKSHOP_NPCS.contains(role)) {
                    problems.add("avant-poste : rôle vanilla non relevé " + role);
                }
            }
        }
        if (annex.containsKey("Decor")) {
            for (BsonValue d : annex.getArray("Decor")) {
                String[] p = d.asString().getValue().trim().split("\\s+");
                if (p.length != 5 || (WORKSHOP_BLOCKS != null && !WORKSHOP_BLOCKS.contains(p[4]))) {
                    problems.add("avant-poste : décor mal formé ou bloc inconnu " + d.asString().getValue());
                }
            }
        }
    }

    /** Blocs vanilla connus (tools/vanilla-block-ids-0.7.2.txt), pour le décor des bâtiments de métier, ou null. */
    static Set<String> WORKSHOP_BLOCKS;

    /**
     * Demandes de destruction (tools/generate_quests.py) : le {@code TargetBlock} posé par le Java au lieu de la demande
     * doit être un bloc vanilla relevé ({@code -Dblocks}) ou un bloc du pack ; un id inconnu ne pose rien.
     */
    private static int checkTargetBlocks(Path root) throws Exception {
        Path requests = root.resolve("Nakasar/Requests");
        if (!Files.isDirectory(requests)) {
            return 0;
        }
        Set<String> pack = new HashSet<>(assetIds(root.resolve("Item/Items")));
        int errors = 0;
        try (Stream<Path> walk = Files.walk(requests)) {
            for (Path f : walk.filter(p -> p.toString().endsWith(".json")).sorted().toList()) {
                BsonDocument doc = BsonDocument.parse(Files.readString(f));
                if (!doc.containsKey("TargetBlock")) {
                    continue;
                }
                String block = doc.getString("TargetBlock").getValue();
                if (!pack.contains(block) && WORKSHOP_BLOCKS != null && !WORKSHOP_BLOCKS.contains(block)) {
                    errors++;
                    System.out.println("ERROR " + root.relativize(f) + " : bloc à détruire inconnu " + block
                            + " (ni dans le pack ni dans tools/vanilla-block-ids-0.7.2.txt)");
                }
            }
        }
        if (errors == 0) {
            System.out.println("OK    blocs à détruire des demandes de destruction");
        }
        return errors;
    }
    /** Rôles vanilla relevés ({@code -Drefs}) : bêtes des enclos. */
    static Set<String> WORKSHOP_NPCS;

    /** Commandes d'un bâtiment de métier : de quoi remplir les 3 cases du niveau III sans doublon. */
    static final int MIN_WORKSHOP_ORDERS = 3;

    private static int checkVillageLayouts(Path root, String vanillaPrefabs) throws Exception {
        Path layouts = root.resolve("Nakasar/VillageLayouts");
        if (!Files.isDirectory(layouts) || vanillaPrefabs == null) {
            return 0;
        }
        Set<String> known = new HashSet<>();
        for (String line : Files.readAllLines(Path.of(vanillaPrefabs))) {
            if (!line.isBlank() && !line.startsWith("#")) {
                known.add(line.trim().split("\\s+")[0]);
            }
        }
        int errors = 0;
        List<Path> files;
        try (Stream<Path> walk = Files.walk(layouts)) {
            files = walk.filter(f -> f.toString().endsWith(".json")).sorted().toList();
        }
        for (Path file : files) {
            List<String> problems = new ArrayList<>();
            BsonDocument doc = BsonDocument.parse(Files.readString(file));
            if (doc.containsKey("Buildings") && doc.get("Buildings").isArray()) {
                for (BsonValue b : doc.getArray("Buildings")) {
                    if (!b.isDocument() || !b.asDocument().containsKey("Prefab")) {
                        continue;
                    }
                    String prefab = b.asDocument().getString("Prefab").getValue();
                    // Prefab du mod (enclos des peuples, tools/generate_pens.py) : présent dans le pack.
                    boolean mod = prefab.startsWith("Nakasar/") && Files.isRegularFile(root.resolve("Prefabs/" + prefab + ".prefab.json"));
                    if (!known.contains(prefab) && !mod) {
                        problems.add("prefab vanilla inconnu : " + prefab);
                    }
                }
            }
            checkVillageLife(root, doc, problems);
            String rel = root.relativize(file).toString().replace('\\', '/');
            if (problems.isEmpty()) {
                System.out.println("OK    prefabs, chantiers et métiers de " + rel);
            } else {
                errors++;
                System.out.println("ERROR prefabs, chantiers et métiers de " + rel);
                problems.forEach(pb -> System.out.println("      " + pb));
            }
        }
        return errors;
    }

    /**
     * Étape 5 des Peuples : chaque métier ({@code Jobs}) cite un rôle PNJ et un dialogue du pack, chaque bâtiment et
     * métier a son nom dans les .lang ({@code building.<Id>}, {@code job.<Id>}), et les blocs posés par le code
     * (ruines calcinées, échafaudages, {@code Burning.REQUIRED_BLOCKS}) existent en vanilla ({@code -Dblocks}).
     * Les {@code ItemId} des matériaux de chantier sont vérifiés avec les dialogues.
     */
    /** Rôles vanilla de {@code -Drefs} (lignes « npc <id> »). */
    private static Set<String> vanillaNpcRefs() throws Exception {
        Set<String> out = new HashSet<>();
        String refs = System.getProperty("refs");
        if (refs != null) {
            for (String line : Files.readAllLines(Path.of(refs))) {
                String[] parts = line.trim().split("\\s+");
                if (parts.length == 2 && parts[0].equals("npc")) {
                    out.add(parts[1]);
                }
            }
        }
        return out;
    }

    private static void checkVillageLife(Path root, BsonDocument doc, List<String> problems) throws Exception {
        Set<String> roles = new HashSet<>();
        Set<String> dialogues = new HashSet<>();
        for (String[] pair : new String[][] {{"NPC/Roles", "r"}, {"Nakasar/Dialogues", "d"}}) {
            Path dir = root.resolve(pair[0]);
            if (Files.isDirectory(dir)) {
                try (Stream<Path> walk = Files.walk(dir)) {
                    walk.filter(f -> f.toString().endsWith(".json")).forEach(f -> {
                        String id = f.getFileName().toString().replace(".json", "");
                        (pair[1].equals("r") ? roles : dialogues).add(id);
                    });
                }
            }
        }
        Map<String, Set<String>> langs = new LinkedHashMap<>();
        for (String locale : List.of("fr-FR", "en-US")) {
            Set<String> keys = new HashSet<>();
            Path lang = root.resolve("Languages/" + locale + "/nakasar_peuples.lang");
            if (Files.exists(lang)) {
                for (String line : Files.readAllLines(lang, java.nio.charset.StandardCharsets.UTF_8)) {
                    int eq = line.indexOf('=');
                    if (eq > 0) {
                        keys.add(line.substring(0, eq).trim());
                    }
                }
            }
            langs.put(locale, keys);
        }
        java.util.function.Consumer<String> needKey = key -> langs.forEach((locale, keys) -> {
            if (!keys.contains(key)) {
                problems.add("clé nakasar_peuples." + key + " absente des .lang " + locale);
            }
        });
        if (doc.containsKey("Buildings")) {
            for (BsonValue b : doc.getArray("Buildings")) {
                if (b.isDocument() && b.asDocument().containsKey("Id")) {
                    needKey.accept("building." + b.asDocument().getString("Id").getValue());
                }
            }
        }
        if (doc.containsKey("Jobs")) {
            for (BsonValue j : doc.getArray("Jobs")) {
                BsonDocument job = j.asDocument();
                String id = job.getString("Id").getValue();
                needKey.accept("job." + id);
                String role = job.getString("Role").getValue();
                // Étape 7 : un métier peut être un rôle vanilla (Trorks du camp), cité dans -Drefs (« npc <id> »).
                if (!roles.contains(role) && !vanillaNpcRefs().contains(role)) {
                    problems.add("métier " + id + " : rôle PNJ inconnu " + role);
                }
                String dialogue = job.getString("Dialogue").getValue();
                if (!dialogue.isEmpty() && !dialogues.contains(dialogue)) {
                    problems.add("métier " + id + " : dialogue inconnu " + dialogue);
                }
            }
        }
        String blocks = System.getProperty("blocks");
        if (blocks != null) {
            Set<String> known = new HashSet<>();
            for (String line : Files.readAllLines(Path.of(blocks))) {
                if (!line.isBlank() && !line.startsWith("#")) {
                    known.add(line.trim().split("\\s+")[0]);
                }
            }
            @SuppressWarnings("unchecked")
            List<String> required = (List<String>) Class.forName("dev.nakasar.hytale.peuples.village.Burning")
                    .getField("REQUIRED_BLOCKS").get(null);
            for (String id : required) {
                if (!known.contains(id)) {
                    problems.add("bloc posé par le code inconnu en vanilla : " + id);
                }
            }
        }
    }

    /**
     * Pages .ui du mod (Common/UI/Custom/Pages/Nakasar) : chaque texture citée existe, dans le pack ou parmi les
     * textures vanilla relevées dans Assets.zip ({@code -Duitextures}) ; chaque élément que remplit
     * {@code request.BoardPage} ({@code "#Id"} et {@code "#Id" + n}, case 0) existe dans chaque mise en page du tableau
     * (un id absent d'une page ouverte fait planter le client) ; les icônes de type de demande sont des objets vanilla.
     */
    private static int checkUiPages(Path root, String vanillaTextures, String vanillaItems) throws Exception {
        Path custom = root.resolveSibling("Common/UI/Custom");
        Path pages = custom.resolve("Pages/Nakasar");
        if (!Files.isDirectory(pages)) {
            return 0;
        }
        Set<String> vanilla = new HashSet<>();
        if (vanillaTextures != null) {
            for (String line : Files.readAllLines(Path.of(vanillaTextures))) {
                if (!line.isBlank() && !line.startsWith("#")) {
                    vanilla.add(line.trim());
                }
            }
        }
        int errors = 0;
        List<Path> uis;
        try (Stream<Path> walk = Files.walk(pages)) {
            uis = walk.filter(f -> f.toString().endsWith(".ui")).sorted().toList();
        }
        Pattern texture = Pattern.compile("\"([^\"]+\\.png)\"");
        for (Path ui : uis) {
            Matcher m = texture.matcher(Files.readString(ui));
            while (m.find()) {
                Path target = ui.getParent().resolve(m.group(1)).normalize();
                if (Files.exists(target)) {
                    continue;
                }
                String rel = custom.relativize(target).toString().replace('\\', '/');
                if (vanillaTextures != null && !vanilla.contains(rel)) {
                    errors++;
                    System.out.println("ERROR " + root.getParent().relativize(ui) + " : texture introuvable " + m.group(1) + " (" + rel + ")");
                }
            }
        }
        // Chaque id rempli par une page Java existe dans chacune de ses mises en page (BoardPage*.ui, WorkshopPage*.ui).
        for (String[] pageSpec : new String[][] {{"request/BoardPage.java", "BoardPage"}, {"workshop/WorkshopPage.java", "WorkshopPage"},
                {"workshop/WorkshopSpecialtyPage.java", "WorkshopSpecialtyPage"}, {"village/PlotPage.java", "PlotPage"},
                {"annex/AnnexPage.java", "AnnexPage"}, {"world/WorldPage.java", "WorldPage"},
                // Barre des onglets du panneau : mêmes ids dans les quatre pages.
                {"request/BoardTabs.java", "BoardPage"}, {"request/BoardTabs.java", "PlotPage"},
                {"request/BoardTabs.java", "AnnexPage"}, {"request/BoardTabs.java", "WorldPage"}}) {
        Path java = root.getParent().getParent().resolve("java/dev/nakasar/hytale/peuples/" + pageSpec[0]);
        String pageName = pageSpec[1];
        if (Files.isRegularFile(java)) {
            String code = Files.readString(java);
            Set<String> ids = new HashSet<>();
            Matcher indexed = Pattern.compile("\"#([A-Z][A-Za-z]*)\"\\s*\\+\\s*[a-z]\\b").matcher(code);
            while (indexed.find()) {
                ids.add(indexed.group(1) + "0");
            }
            Matcher plain = Pattern.compile("\"#([A-Z][A-Za-z0-9]*)(?:\\.[A-Za-z.]+\"|\"(?!\\s*\\+))").matcher(code);
            while (plain.find()) {
                ids.add(plain.group(1));
            }
            for (Path ui : uis) {
                if (!ui.getFileName().toString().startsWith(pageName + "_") && !ui.getFileName().toString().equals(pageName + ".ui")) {
                    continue;
                }
                String text = Files.readString(ui);
                for (String id : ids) {
                    if (!Pattern.compile("#" + id + "\\b").matcher(text).find()) {
                        errors++;
                        System.out.println("ERROR " + root.getParent().relativize(ui) + " : élément #" + id + " rempli par " + pageName + ".java absent");
                    }
                }
            }
            if (vanillaItems != null) {
                Set<String> items = new HashSet<>(Files.readAllLines(Path.of(vanillaItems)));
                Matcher icon = Pattern.compile("case [A-Z, ]+ -> \"([A-Z][A-Za-z_]+)\"").matcher(code);
                while (icon.find()) {
                    if (!items.contains(icon.group(1))) {
                        errors++;
                        System.out.println("ERROR " + pageName + ".java : icône de type " + icon.group(1) + " absente des objets vanilla");
                    }
                }
            }
        }
        }
        return errors;
    }

    /** Icônes des marqueurs de carte des blocs du pack ({@code BlockMapMarker}) : présentes sous Common/UI/WorldMap/MapMarkers. */
    private static int checkMapMarkerIcons(Path root) throws Exception {
        Path items = root.resolve("Item/Items");
        Path icons = root.getParent().resolve("Common/UI/WorldMap/MapMarkers");
        if (!Files.isDirectory(items)) {
            return 0;
        }
        int errors = 0;
        List<Path> files;
        try (Stream<Path> walk = Files.walk(items)) {
            files = walk.filter(f -> f.toString().endsWith(".json")).sorted().toList();
        }
        for (Path file : files) {
            String text = Files.readString(file);
            if (!text.contains("BlockMapMarker")) {
                continue;
            }
            BsonDocument doc = BsonDocument.parse(text);
            BsonValue marker = doc;
            for (String key : List.of("BlockType", "BlockEntity", "Components", "BlockMapMarker")) {
                marker = marker != null && marker.isDocument() ? marker.asDocument().get(key) : null;
            }
            if (marker == null || !marker.isDocument()) {
                continue;
            }
            for (String key : List.of("Icon", "CompassIcon")) {
                BsonValue icon = marker.asDocument().get(key);
                if (icon != null && icon.isString() && icon.asString().getValue().startsWith("Nakasar")
                        && !Files.exists(icons.resolve(icon.asString().getValue()))) {
                    errors++;
                    System.out.println("ERROR " + root.relativize(file) + " : icône de carte absente " + icon.asString().getValue());
                }
            }
        }
        return errors;
    }

    /**
     * Réputation (étape 4) : chaque rang de l'enum Java {@code reputation.Rank} a son asset
     * {@code NPC/Reputation/Ranks/<assetId>.json} avec les mêmes bornes et la même attitude (le Java calcule les rangs
     * lui-même, le jeu en tire l'attitude des PNJ), aucun autre rang n'existe (les rangs du ReputationPlugin sont
     * communs à tous les groupes), chaque peuple a son groupe {@code NPC/Reputation/Groups/Nakasar_Peuples_<Peuple>.json}
     * et ses échoppes {@code BarterShops/<shop>.json}.
     */
    private static int checkReputation(Path root) throws Exception {
        Path ranks = root.resolve("NPC/Reputation/Ranks");
        if (!Files.isDirectory(ranks)) {
            return 0;
        }
        List<String> problems = new ArrayList<>();
        Class<?> rankClass = Class.forName("dev.nakasar.hytale.peuples.reputation.Rank");
        Set<String> expected = new HashSet<>();
        for (Object rank : rankClass.getEnumConstants()) {
            String id = (String) rankClass.getMethod("assetId").invoke(rank);
            int min = (int) rankClass.getMethod("min").invoke(rank);
            int max = (int) rankClass.getMethod("max").invoke(rank);
            String attitude = rankClass.getMethod("defaultAttitude").invoke(rank).toString();
            expected.add(id);
            Path file = ranks.resolve(id + ".json");
            if (!Files.exists(file)) {
                problems.add("rang " + id + " sans asset " + root.relativize(file));
                continue;
            }
            BsonDocument doc = BsonDocument.parse(Files.readString(file));
            int fileMin = doc.containsKey("MinValue") ? doc.getNumber("MinValue").intValue() : Integer.MIN_VALUE;
            int fileMax = doc.containsKey("MaxValue") ? doc.getNumber("MaxValue").intValue() : Integer.MIN_VALUE;
            String fileAttitude = doc.containsKey("Attitude") ? doc.getString("Attitude").getValue() : "";
            if (fileMin != min || fileMax != max) {
                problems.add(id + " : bornes " + fileMin + ".." + fileMax + " dans l'asset, " + min + ".." + max + " dans Rank.java");
            }
            if (!fileAttitude.equalsIgnoreCase(attitude)) {
                problems.add(id + " : attitude " + fileAttitude + " dans l'asset, " + attitude + " dans Rank.java");
            }
        }
        try (Stream<Path> files = Files.list(ranks)) {
            for (Path f : files.filter(f -> f.toString().endsWith(".json")).toList()) {
                String id = f.getFileName().toString().replace(".json", "");
                if (!expected.contains(id)) {
                    problems.add("rang " + id + " absent de Rank.java (les rangs vanilla sont communs à tous les groupes)");
                }
            }
        }
        Class<?> peopleClass = Class.forName("dev.nakasar.hytale.peuples.village.People");
        for (Object people : peopleClass.getEnumConstants()) {
            String id = (String) peopleClass.getMethod("id").invoke(people);
            Path group = root.resolve("NPC/Reputation/Groups/Nakasar_Peuples_" + id + ".json");
            if (!Files.exists(group)) {
                problems.add("peuple " + id + " sans groupe de réputation NPC/Reputation/Groups/Nakasar_Peuples_" + id + ".json");
            } else {
                // Étape 7 : la réputation de départ du groupe vanilla et celle des villages du peuple sont la même.
                BsonDocument g = BsonDocument.parse(Files.readString(group));
                int initial = g.containsKey("InitialReputationValue") ? g.getInt32("InitialReputationValue").getValue() : 0;
                int start = (int) peopleClass.getMethod("initialReputation").invoke(people);
                if (initial != start) {
                    problems.add("peuple " + id + " : InitialReputationValue " + initial + " ≠ People.initialReputation() " + start);
                }
            }
            for (Object rank : rankClass.getEnumConstants()) {
                String shop = (String) peopleClass.getMethod("shop", rankClass).invoke(people, rank);
                if (shop != null && !Files.exists(root.resolve("BarterShops/" + shop + ".json"))) {
                    problems.add("peuple " + id + " : échoppe " + shop + " absente de BarterShops");
                }
            }
        }
        if (problems.isEmpty()) {
            System.out.println("OK    rangs, groupes de réputation et échoppes des peuples");
            return 0;
        }
        System.out.println("ERROR rangs, groupes de réputation et échoppes des peuples");
        problems.forEach(p -> System.out.println("      " + p));
        return 1;
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
        errors += checkDialogueTexts(root, System.getProperty("items"));
        errors += checkRequestTitles(root);
        errors += checkVillageLayouts(root, System.getProperty("prefabs"));
        String blockIds = System.getProperty("blocks");
        if (blockIds != null && Files.isRegularFile(Path.of(blockIds))) {
            WORKSHOP_BLOCKS = new HashSet<>(Files.readAllLines(Path.of(blockIds)));
        }
        WORKSHOP_NPCS = System.getProperty("refs") == null ? null : vanillaNpcRefs();
        errors += checkWorkshops(root, System.getProperty("prefabs"));
        errors += checkHamlets(root, System.getProperty("prefabs"));
        errors += checkTargetBlocks(root);
        errors += checkMapMarkerIcons(root);
        errors += checkReputation(root);
        errors += checkUiPages(root, System.getProperty("uitextures"), System.getProperty("items"));
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
