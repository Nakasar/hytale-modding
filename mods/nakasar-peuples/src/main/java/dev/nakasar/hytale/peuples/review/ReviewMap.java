package dev.nakasar.hytale.peuples.review;

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;
import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.environment.config.Environment;
import com.hypixel.hytale.server.core.asset.type.model.config.Model;
import com.hypixel.hytale.server.core.asset.type.model.config.ModelAsset;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.entity.nameplate.Nameplate;
import com.hypixel.hytale.server.core.modules.entity.component.ModelComponent;
import com.hypixel.hytale.server.core.modules.entity.component.PersistentModel;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.WorldConfig;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.universe.world.worldgen.provider.FlatWorldGenProvider;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import org.joml.Vector3d;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.CompletableFuture;

/**
 * Carte plate de revue des bâtiments (Kevin, 16 novembre 2026, « parking à idées » du tableau blanc) : chaque bâtiment
 * des cinq peuples (base, artisan, projets de terrain, avant-postes, lieux-dits) en ses quatre paliers, chacun dans son
 * rectangle liseré de briques sur un monde plat, avec un panneau qui dit ce que c'est (bloc de panneau vanilla et
 * texte flottant au-dessus). Kevin y retouche les prefabs à la main en créatif, puis les enregistre.
 *
 * <p>Les compositions et la grille viennent de {@code nakasar-peuples/revue-batiments.json}, écrit par
 * {@code tools/building_tiers.py}. Le monde ({@value #WORLD_DEFAULT} par défaut) est créé au premier
 * {@code /village revue} avec le générateur plat vanilla ; un rectangle n'est bâti qu'une fois (liste des rectangles
 * faits dans {@value #STATE_FILE}, dans le dossier du monde) pour ne jamais écraser une retouche, sauf demande
 * explicite ({@code --rebatir}).
 */
public final class ReviewMap {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    private static final String RESOURCE = "/nakasar-peuples/revue-batiments.json";
    public static final String WORLD_DEFAULT = "nakasar_revue_batiments";
    static final String STATE_FILE = "nakasar_revue_batiments.txt";
    public static final String KEYS = "nakasar_peuples.review.";
    /** Haut du sol du monde plat (couches ci-dessous : pierre, terre, herbe). */
    static final int GROUND = 80;
    /** Liseré des rectangles. */
    static final String BORDER = "Rock_Stone_Brick";
    static final String SIGN = "Furniture_Village_Sign";
    /** Modèle porteur du texte flottant : le repère de point d'apparition vanilla (celui de /spawnmarkers add). */
    static final String LABEL_MODEL = "NPC_Spawn_Marker";
    /** Hauteur dégagée au-dessus du sol quand on rebâtit un rectangle. */
    private static final int CLEAR_ABOVE = 12;
    private static final int REPORT_EVERY = 25;

    private static Data data;
    private static boolean running;

    private ReviewMap() {
    }

    // ---- Données ----

    static final class Data {
        @SerializedName("World")
        String world;
        @SerializedName("Margin")
        int margin;
        @SerializedName("Sections")
        List<Section> sections;
        @SerializedName("Cells")
        List<Cell> cells;
    }

    public static final class Section {
        @SerializedName("People")
        public String people;
        @SerializedName("Name")
        public String name;
        @SerializedName("X")
        public int x;
        @SerializedName("Width")
        public int width;
        @SerializedName("Spawn")
        public int[] spawn;
        @SerializedName("Label")
        public int[] label;
        @SerializedName("Categories")
        public List<Category> categories;
    }

    public static final class Category {
        @SerializedName("Category")
        public String category;
        @SerializedName("Name")
        public String name;
        @SerializedName("Z")
        public int z;
    }

    static final class Cell {
        @SerializedName("Key")
        String key;
        @SerializedName("People")
        String people;
        @SerializedName("Category")
        String category;
        @SerializedName("Label")
        String label;
        @SerializedName("Source")
        String source;
        @SerializedName("Notes")
        List<String> notes;
        /** [x0, x1, z0, z1] du rectangle, liseré compris. */
        @SerializedName("Cell")
        int[] cell;
        /** Point (x, z) où tombe l'origine de la composition. */
        @SerializedName("Origin")
        int[] origin;
        @SerializedName("Sign")
        int[] sign;
        @SerializedName("Height")
        int height;
        @SerializedName("Ground")
        String ground;
        /** « chemin dx dz rotation ». */
        @SerializedName("Pieces")
        List<String> pieces;
        /** « dx dy dz rotation Bloc », dy 0 = posé sur le sol. */
        @SerializedName("Blocks")
        List<String> blocks;
    }

    static synchronized Data data() {
        if (data == null) {
            try (InputStream in = ReviewMap.class.getResourceAsStream(RESOURCE)) {
                if (in == null) {
                    throw new IllegalStateException("ressource absente " + RESOURCE);
                }
                data = new Gson().fromJson(new InputStreamReader(in, StandardCharsets.UTF_8), Data.class);
            } catch (IOException e) {
                throw new IllegalStateException("lecture de " + RESOURCE, e);
            }
        }
        return data;
    }

    public static List<Section> sections() {
        return data().sections;
    }

    public static Section section(String people) {
        for (Section s : data().sections) {
            if (people == null || s.people.equalsIgnoreCase(people) || s.name.equalsIgnoreCase(people)) {
                return s;
            }
        }
        return null;
    }

    // ---- Monde ----

    /** Le monde de revue, chargé ou créé (générateur plat vanilla, créatif, sans apparition de PNJ). */
    public static CompletableFuture<World> world() {
        String name = data().world == null ? WORLD_DEFAULT : data().world;
        Universe universe = Universe.get();
        World loaded = universe.getWorld(name);
        if (loaded != null) {
            return CompletableFuture.completedFuture(loaded);
        }
        if (universe.isWorldLoadable(name)) {
            return universe.loadWorld(name);
        }
        String env = Environment.UNKNOWN.getId();
        FlatWorldGenProvider flat = new FlatWorldGenProvider(FlatWorldGenProvider.DEFAULT_TINT, new FlatWorldGenProvider.Layer[] {
                new FlatWorldGenProvider.Layer(0, GROUND - 3, env, "Rock_Stone"),
                new FlatWorldGenProvider.Layer(GROUND - 3, GROUND, env, "Soil_Dirt"),
                new FlatWorldGenProvider.Layer(GROUND, GROUND + 1, env, "Soil_Grass")});
        WorldConfig config = new WorldConfig();
        config.setWorldGenProvider(flat);
        config.setDisplayName("Revue des bâtiments (Peuples d'Orbis)");
        config.setGameMode(com.hypixel.hytale.protocol.GameMode.Creative);
        config.setSpawningNPC(false);
        config.setPvpEnabled(false);
        config.setFallDamageEnabled(false);
        config.markChanged();
        Path path = universe.validateWorldPath(name);
        LOGGER.atInfo().log("Nakasar Peuples : création du monde de revue %s", name);
        return universe.makeWorld(name, path, config);
    }

    /** Envoie le joueur au début de la bande d'un peuple (ou d'une de ses catégories) dans le monde de revue. */
    public static void teleport(Ref<EntityStore> ref, Store<EntityStore> store, World target, Section s, Category c) {
        double x = s.spawn[0] + 0.5;
        double z = c == null ? s.spawn[1] + 0.5 : c.z - 3.5;
        Teleport tp = Teleport.createForPlayer(target, new Vector3d(x, GROUND + 3, z), new Rotation3f(0f, (float) Math.PI, 0f));
        store.putComponent(ref, Teleport.getComponentType(), tp);
    }

    // ---- Construction ----

    /**
     * Bâtit dans `world` les rectangles du peuple `people` (null : tous) pas encore faits, ou tous si `rebuild`. Un
     * seul chantier à la fois ; les rectangles se font l'un après l'autre (chargement des chunks puis collage sur le
     * thread du monde). Les messages vont à `player`.
     */
    public static boolean build(World world, String people, boolean rebuild, PlayerRef player) {
        synchronized (ReviewMap.class) {
            if (running) {
                return false;
            }
            running = true;
        }
        Set<String> done = loadState(world);
        Deque<Cell> queue = new ArrayDeque<>();
        for (Cell c : data().cells) {
            if ((people == null || c.people.equalsIgnoreCase(people)) && (rebuild || !done.contains(c.key))) {
                queue.add(c);
            }
        }
        int total = queue.size();
        player.sendMessage(Message.translation(KEYS + "start").param("count", total));
        if (total == 0) {
            synchronized (ReviewMap.class) {
                running = false;
            }
            return true;
        }
        world.execute(() -> {
            // Titres des bandes et des catégories, une fois par monde.
            if (!done.contains("#titres")) {
                labels(world);
                done.add("#titres");
                saveState(world, done);
            }
            next(world, queue, done, total, player);
        });
        return true;
    }

    private static void next(World world, Deque<Cell> queue, Set<String> done, int total, PlayerRef player) {
        Cell c = queue.poll();
        if (c == null) {
            synchronized (ReviewMap.class) {
                running = false;
            }
            saveState(world, done);
            player.sendMessage(Message.translation(KEYS + "done").param("count", total));
            return;
        }
        int pad = 24; // prefabs plus larges que leurs bornes mesurées (pièces enterrées, arbres)
        Terrain.load(world, c.cell[0] - pad, c.cell[1] + pad, c.cell[2] - pad, c.sign[1] + pad).whenComplete((v, error) ->
                world.execute(() -> {
                    try {
                        if (error != null) {
                            LOGGER.atWarning().withCause(error).log("Nakasar Peuples : revue, chunks de %s non chargés", c.key);
                        } else {
                            buildCell(world, c);
                            done.add(c.key);
                        }
                    } catch (RuntimeException e) {
                        LOGGER.atWarning().withCause(e).log("Nakasar Peuples : revue, rectangle %s raté", c.key);
                    }
                    int left = queue.size();
                    if ((total - left) % REPORT_EVERY == 0) {
                        saveState(world, done);
                        player.sendMessage(Message.translation(KEYS + "progress").param("done", total - left).param("count", total));
                    }
                    next(world, queue, done, total, player);
                }));
    }

    private static void buildCell(World world, Cell c) {
        ChunkStore chunks = world.getChunkStore();
        Store<EntityStore> store = world.getEntityStore().getStore();
        int x0 = c.cell[0], x1 = c.cell[1], z0 = c.cell[2], z1 = c.cell[3];
        int ground = GROUND;
        // Rectangle : air au-dessus, sol du peuple dedans, liseré de briques au bord.
        for (int x = x0; x <= x1; x++) {
            for (int z = z0; z <= z1; z++) {
                for (int y = ground + 1; y <= ground + c.height + CLEAR_ABOVE; y++) {
                    if (!Blocks.isEmpty(chunks, x, y, z)) {
                        Blocks.set(chunks, x, y, z, null, 0);
                    }
                }
                boolean edge = x == x0 || x == x1 || z == z0 || z == z1;
                Blocks.set(chunks, x, ground, z, edge ? BORDER : c.ground, 0);
            }
        }
        int ox = c.origin[0], oz = c.origin[1];
        for (String line : c.pieces) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 4) {
                continue;
            }
            VillageBuilder.paste(world, store, p[0], ox + Integer.parseInt(p[1]), ground, oz + Integer.parseInt(p[2]),
                    Integer.parseInt(p[3]));
        }
        for (String line : c.blocks) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            int x = ox + Integer.parseInt(p[0]);
            int y = ground + 1 + Integer.parseInt(p[1]);
            int z = oz + Integer.parseInt(p[2]);
            // Un décor ne remplace jamais un bloc du bâtiment (seulement l'air, la végétation ou le sol pour un sentier).
            String current = Blocks.name(chunks, x, y, z);
            if (current == null || Terrain.isVegetation(current) || (y <= ground && Terrain.isGround(current))) {
                Blocks.set(chunks, x, y, z, p[4], Integer.parseInt(p[3]));
            }
        }
        // Panneau devant le coin sud-ouest, et son texte.
        int sx = c.sign[0], sz = c.sign[1];
        Blocks.set(chunks, sx, ground, sz, BORDER, 0);
        Blocks.set(chunks, sx, ground + 1, sz, SIGN, 0);
        removeLabels(store, sx, sz);
        label(store, sx + 0.5, ground + 2.4, sz + 0.5, c.label);
        String notes = notes(c);
        if (!notes.isEmpty()) {
            label(store, sx + 0.5, ground + 1.9, sz + 0.5, notes);
        }
    }

    private static String notes(Cell c) {
        List<String> parts = new ArrayList<>();
        if (c.source != null && !c.source.isEmpty()) {
            parts.add(c.source);
        }
        if (c.notes != null) {
            parts.addAll(c.notes);
        }
        return String.join(" · ", parts);
    }

    /** Titres des bandes de peuple et de leurs catégories. */
    private static void labels(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (Section s : data().sections) {
            label(store, s.label[0] + 0.5, GROUND + 4.0, s.label[1] + 0.5, s.name.toUpperCase(Locale.ROOT) + " : bâtiments, paliers 1 à 4 (d'ouest en est)");
            for (Category c : s.categories) {
                label(store, s.x - 5.5, GROUND + 3.0, c.z + 0.5, s.name + " · " + c.name);
            }
        }
    }

    /** Pose un texte flottant (entité sans IA : repère vanilla + plaque de nom, sauvés avec le monde). */
    static void label(Store<EntityStore> store, double x, double y, double z, String text) {
        ModelAsset asset = ModelAsset.getAssetMap().getAsset(LABEL_MODEL);
        Holder<EntityStore> holder = EntityStore.REGISTRY.newHolder();
        holder.addComponent(TransformComponent.getComponentType(), new TransformComponent(new Vector3d(x, y, z), new Rotation3f()));
        holder.addComponent(Nameplate.getComponentType(), new Nameplate(text));
        holder.ensureComponent(UUIDComponent.getComponentType());
        if (asset != null) {
            Model model = Model.createScaledModel(asset, 0.2f);
            holder.addComponent(ModelComponent.getComponentType(), new ModelComponent(model));
            holder.addComponent(PersistentModel.getComponentType(), new PersistentModel(model.toReference()));
        }
        store.addEntity(holder, AddReason.SPAWN);
    }

    /** Retire les textes flottants d'un panneau (avant de le reposer quand on rebâtit). */
    private static void removeLabels(Store<EntityStore> store, int sx, int sz) {
        List<Ref<EntityStore>> old = new ArrayList<>();
        store.forEachChunk(Nameplate.getComponentType(), (chunk, buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                TransformComponent t = chunk.getComponent(i, TransformComponent.getComponentType());
                if (t != null && Math.floor(t.getPosition().x()) == sx && Math.floor(t.getPosition().z()) == sz) {
                    old.add(chunk.getReferenceTo(i));
                }
            }
        });
        for (Ref<EntityStore> r : old) {
            if (r.isValid()) {
                store.removeEntity(r, com.hypixel.hytale.component.RemoveReason.REMOVE);
            }
        }
    }

    // ---- État ----

    private static Path stateFile(World world) {
        return Universe.get().getWorldsPath().resolve(world.getName()).resolve(STATE_FILE);
    }

    static Set<String> loadState(World world) {
        Set<String> keys = new LinkedHashSet<>();
        Path f = stateFile(world);
        try {
            if (Files.exists(f)) {
                for (String line : Files.readAllLines(f, StandardCharsets.UTF_8)) {
                    if (!line.isBlank()) {
                        keys.add(line.trim());
                    }
                }
            }
        } catch (IOException e) {
            LOGGER.atWarning().withCause(e).log("Nakasar Peuples : revue, lecture de %s", f);
        }
        return keys;
    }

    private static void saveState(World world, Set<String> keys) {
        Path f = stateFile(world);
        try {
            Files.createDirectories(f.getParent());
            Files.write(f, keys, StandardCharsets.UTF_8);
        } catch (IOException e) {
            LOGGER.atWarning().withCause(e).log("Nakasar Peuples : revue, écriture de %s", f);
        }
    }
}
