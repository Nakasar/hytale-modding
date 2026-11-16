package dev.nakasar.hytale.peuples.review;

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.environment.config.Environment;
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
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;

/**
 * Carte plate de revue des bâtiments (Kevin, 16 novembre 2026, « parking à idées » du tableau blanc, puis ses retours
 * du même jour) : tous les bâtiments des cinq peuples (cœur, base, artisan, projets, avant-postes, lieux-dits) en leurs
 * quatre paliers, et les structures du monde vivant (auberges, campements, vestiges, Source de l'Écho), chacun dans
 * son rectangle liseré de laine rouge sur un monde plat. Kevin y retouche les prefabs à la main en créatif.
 *
 * <ul>
 *   <li>Les rectangles d'un même bâtiment ont tous la même taille (la plus grande de ses paliers), le palier centré
 *   dedans ; les paliers vont d'ouest en est, les bâtiments du nord au sud, une colonne par peuple.</li>
 *   <li>Rien autour des bâtiments : le palier se voit au bâtiment lui-même (prefab plus grand de la même famille).</li>
 *   <li>Un panneau muet dans le coin sud-ouest de chaque rectangle : l'utiliser affiche le bâtiment et son palier
 *   ({@link ReviewSignInteraction}).</li>
 * </ul>
 *
 * <p>Les compositions viennent de {@code nakasar-peuples/revue-batiments.json}, écrit par
 * {@code tools/building_tiers.py}. Les tailles se mesurent ici sur les prefabs chargés, une fois par monde : le plan
 * obtenu est gardé dans {@value #PLAN_FILE} (dossier du monde) pour qu'un prefab retouché puis rechargé ne décale
 * jamais la carte. Un rectangle n'est bâti qu'une fois (liste dans {@value #STATE_FILE}) pour ne jamais écraser une
 * retouche, sauf demande explicite ({@code --rebatir}).
 */
public final class ReviewMap {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    private static final String RESOURCE = "/nakasar-peuples/revue-batiments.json";
    public static final String WORLD_DEFAULT = "nakasar_revue_batiments_v2";
    static final String STATE_FILE = "nakasar_revue_batiments.txt";
    static final String PLAN_FILE = "nakasar_revue_batiments_plan.txt";
    public static final String KEYS = "nakasar_peuples.review.";
    /** Haut du sol du monde plat (couches ci-dessous : pierre, terre, herbe). */
    static final int GROUND = 80;
    static final String GRASS = "Soil_Grass";
    /** Liseré des rectangles (Kevin : laine rouge). */
    static final String BORDER = "Cloth_Block_Wool_Red";
    public static final String SIGN = "Nakasar_Peuples_Review_Sign";
    /** Herbe libre entre le liseré et le bâtiment (le panneau y tient). */
    static final int MARGIN = 3;
    /** Herbe entre deux rectangles d'une rangée, entre deux rangées, entre deux catégories, entre deux peuples. */
    static final int GAP = 3;
    static final int ROW_GAP = 4;
    static final int CATEGORY_GAP = 10;
    static final int SECTION_GAP = 16;
    /** Hauteur dégagée au-dessus du plus haut bloc mesuré quand on bâtit un rectangle. */
    private static final int CLEAR_ABOVE = 12;
    private static final int REPORT_EVERY = 25;

    private static Data data;
    private static final Map<String, Layout> LAYOUTS = new HashMap<>();
    private static boolean running;

    private ReviewMap() {
    }

    // ---- Données ----

    static final class Data {
        @SerializedName("World")
        String world;
        @SerializedName("Sections")
        List<Section> sections;
    }

    static final class Section {
        @SerializedName("People")
        String people;
        @SerializedName("Name")
        String name;
        @SerializedName("Rows")
        List<Row> rows;
    }

    static final class Row {
        @SerializedName("Category")
        String category;
        @SerializedName("CategoryName")
        String categoryName;
        @SerializedName("Id")
        String id;
        @SerializedName("Name")
        String name;
        @SerializedName("Source")
        String source;
        @SerializedName("Tiers")
        List<Tier> tiers;
    }

    static final class Tier {
        /** 1 à 4 ; 0 pour une structure sans paliers (auberge, campement, vestige). */
        @SerializedName("Tier")
        int tier;
        /** « chemin dx dy dz rotation » : ancre du prefab en (origine + dx, sol + dy, origine + dz). */
        @SerializedName("Pieces")
        List<String> pieces;
        /** « dx dy dz rotation Bloc », dy 0 = posé sur le sol, Empty = vider. */
        @SerializedName("Blocks")
        List<String> blocks;
        /** « dx dy dz Bloc » : retiré s'il est là (étapes du cœur). */
        @SerializedName("Clear")
        List<String> clear;
        @SerializedName("Notes")
        List<String> notes;
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

    /** Id du peuple (ou « Monde ») nommé `name`, null s'il n'a pas de colonne sur la carte. */
    public static String people(String name) {
        for (Section s : data().sections) {
            if (s.people.equalsIgnoreCase(name) || s.name.equalsIgnoreCase(name)) {
                return s.people;
            }
        }
        return null;
    }

    // ---- Plan de la carte ----

    /** Plan d'un monde de revue : les colonnes des peuples et chaque rectangle, rangé aussi par position de panneau. */
    public static final class Layout {
        final List<Column> columns = new ArrayList<>();
        final List<Spot> spots = new ArrayList<>();
        final Map<Long, Spot> signs = new HashMap<>();
    }

    static final class Column {
        Section section;
        int x0;
        int z0;
        /** Catégorie → z de sa première rangée. */
        final Map<String, Integer> categories = new LinkedHashMap<>();
    }

    /** Un rectangle : un palier d'un bâtiment. */
    static final class Spot {
        String key;
        Section section;
        Row row;
        Tier tier;
        /** Rectangle, liseré compris. */
        int x0, x1, z0, z1;
        /** Point (x, z) où tombe l'origine de la composition. */
        int ox, oz;
        int height;
        int signX, signZ;
    }

    /** Boîte mesurée d'une composition autour de son origine : x0, x1, z0, z1, haut. */
    private static int[] measure(Tier t) {
        int[] box = null;
        for (String line : t.pieces) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            int[] b = VillageBuilder.bounds(p[0], Integer.parseInt(p[1]), Integer.parseInt(p[2]), Integer.parseInt(p[3]),
                    Integer.parseInt(p[4]));
            if (b == null) {
                LOGGER.atWarning().log("Nakasar Peuples : revue, prefab introuvable %s", p[0]);
                continue;
            }
            box = union(box, b[0], b[1], b[4], b[5], b[3]);
        }
        for (String line : t.blocks) {
            String[] p = line.trim().split("\\s+");
            if (p.length >= 3) {
                int x = Integer.parseInt(p[0]), z = Integer.parseInt(p[2]);
                box = union(box, x, x, z, z, 1 + Integer.parseInt(p[1]));
            }
        }
        return box == null ? new int[]{-2, 2, -2, 2, 4} : box;
    }

    private static int[] union(int[] box, int x0, int x1, int z0, int z1, int top) {
        if (box == null) {
            return new int[]{x0, x1, z0, z1, top};
        }
        return new int[]{Math.min(box[0], x0), Math.max(box[1], x1), Math.min(box[2], z0), Math.max(box[3], z1),
                Math.max(box[4], top)};
    }

    private static String rowKey(Section s, Row r) {
        return s.people + "/" + r.category + "/" + r.id;
    }

    private static String tierKey(Section s, Row r, Tier t) {
        return rowKey(s, r) + "#" + t.tier;
    }

    /**
     * Plan du monde de revue `world`, calculé une fois (mesure des prefabs) puis relu de {@value #PLAN_FILE} : taille
     * de chaque bâtiment et place de chaque palier dans son rectangle. Les positions en découlent dans l'ordre du JSON.
     */
    public static synchronized Layout layout(World world) {
        Layout cached = LAYOUTS.get(world.getName());
        if (cached != null) {
            return cached;
        }
        Map<String, int[]> plan = loadPlan(world);
        boolean changed = false;
        Layout layout = new Layout();
        int x = 0;
        for (Section s : data().sections) {
            Column col = new Column();
            col.section = s;
            col.x0 = x;
            col.z0 = 0;
            int z = 0;
            int width = 0;
            String lastCategory = null;
            for (Row r : s.rows) {
                if (lastCategory != null && !lastCategory.equals(r.category)) {
                    z += CATEGORY_GAP;
                }
                lastCategory = r.category;
                col.categories.putIfAbsent(r.category, z);
                // Taille du bâtiment : la plus grande boîte de ses paliers ; place de chaque palier : centré.
                String rk = rowKey(s, r);
                int[] size = plan.get("R " + rk);
                if (size == null || r.tiers.stream().anyMatch(t -> !plan.containsKey("T " + tierKey(s, r, t)))) {
                    int w = 1, d = 1, h = 1;
                    List<int[]> boxes = new ArrayList<>();
                    for (Tier t : r.tiers) {
                        int[] b = measure(t);
                        boxes.add(b);
                        w = Math.max(w, b[1] - b[0] + 1);
                        d = Math.max(d, b[3] - b[2] + 1);
                        h = Math.max(h, b[4]);
                    }
                    int cw = w + 2 * MARGIN + 2, cd = d + 2 * MARGIN + 2;
                    size = new int[]{cw, cd, h};
                    plan.put("R " + rk, size);
                    for (int i = 0; i < r.tiers.size(); i++) {
                        int[] b = boxes.get(i);
                        int offX = 1 + MARGIN + (w - (b[1] - b[0] + 1)) / 2 - b[0];
                        int offZ = 1 + MARGIN + (d - (b[3] - b[2] + 1)) / 2 - b[2];
                        plan.put("T " + tierKey(s, r, r.tiers.get(i)), new int[]{offX, offZ});
                    }
                    changed = true;
                }
                int cw = size[0], cd = size[1];
                int cx = x;
                for (Tier t : r.tiers) {
                    int[] off = plan.get("T " + tierKey(s, r, t));
                    Spot spot = new Spot();
                    spot.key = tierKey(s, r, t);
                    spot.section = s;
                    spot.row = r;
                    spot.tier = t;
                    spot.x0 = cx;
                    spot.x1 = cx + cw - 1;
                    spot.z0 = z;
                    spot.z1 = z + cd - 1;
                    spot.ox = cx + off[0];
                    spot.oz = z + off[1];
                    spot.height = size[2];
                    spot.signX = spot.x0 + 1;
                    spot.signZ = spot.z1 - 1;
                    layout.spots.add(spot);
                    layout.signs.put(pack(spot.signX, spot.signZ), spot);
                    cx += cw + GAP;
                }
                width = Math.max(width, cx - x);
                z += cd + ROW_GAP;
            }
            layout.columns.add(col);
            x += width + SECTION_GAP;
        }
        if (changed) {
            savePlan(world, plan);
        }
        LAYOUTS.put(world.getName(), layout);
        return layout;
    }

    private static long pack(int x, int z) {
        return ((long) x << 32) ^ (z & 0xffffffffL);
    }

    /** Le rectangle dont le panneau est en (x, y, z) dans `world`, ou null. */
    static Spot spotAtSign(World world, int x, int y, int z) {
        if (y != GROUND + 1 || !world.getName().equals(worldName())) {
            return null;
        }
        return layout(world).signs.get(pack(x, z));
    }

    // ---- Monde ----

    static String worldName() {
        return data().world == null ? WORLD_DEFAULT : data().world;
    }

    /** Le monde de revue, chargé ou créé (générateur plat vanilla, créatif, sans apparition de PNJ). */
    public static CompletableFuture<World> world() {
        String name = worldName();
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
                new FlatWorldGenProvider.Layer(GROUND, GROUND + 1, env, GRASS)});
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

    /**
     * Envoie le joueur au nord de la colonne du peuple `people` (null : la première), ou devant sa catégorie
     * `category` (préfixe d'id, null : la première rangée). Faux si le peuple n'est pas sur la carte.
     */
    public static boolean teleport(Ref<EntityStore> ref, Store<EntityStore> store, World target, String people, String category) {
        Layout layout = layout(target);
        Column col = null;
        for (Column c : layout.columns) {
            if (people == null || c.section.people.equalsIgnoreCase(people)) {
                col = c;
                break;
            }
        }
        if (col == null) {
            return false;
        }
        int z = col.z0;
        if (category != null) {
            String want = category.toLowerCase(java.util.Locale.ROOT).replace("-", "").replace(" ", "");
            for (Map.Entry<String, Integer> e : col.categories.entrySet()) {
                String id = e.getKey().toLowerCase(java.util.Locale.ROOT);
                if (id.startsWith(want) || want.startsWith(id)) {
                    z = e.getValue();
                    break;
                }
            }
        }
        Teleport tp = Teleport.createForPlayer(target, new Vector3d(col.x0 + 2.5, GROUND + 3, z - 3.5),
                new Rotation3f(0f, (float) Math.PI, 0f));
        store.putComponent(ref, Teleport.getComponentType(), tp);
        return true;
    }

    // ---- Construction ----

    /**
     * Bâtit dans `world` les rectangles du peuple `people` (null : toute la carte) pas encore faits, ou tous si
     * `rebuild`. Un seul chantier à la fois ; les rectangles se font l'un après l'autre (chargement des chunks puis
     * collage sur le thread du monde). Les messages vont à `player`.
     */
    public static boolean build(World world, String people, boolean rebuild, PlayerRef player) {
        synchronized (ReviewMap.class) {
            if (running) {
                return false;
            }
            running = true;
        }
        try {
            Set<String> done = loadState(world);
            Deque<Spot> queue = new ArrayDeque<>();
            for (Spot s : layout(world).spots) {
                if ((people == null || s.section.people.equalsIgnoreCase(people)) && (rebuild || !done.contains(s.key))) {
                    queue.add(s);
                }
            }
            int total = queue.size();
            player.sendMessage(Message.translation(KEYS + "start").param("count", total));
            if (total == 0) {
                finish();
                return true;
            }
            world.execute(() -> next(world, queue, done, total, player));
            return true;
        } catch (RuntimeException e) {
            finish();
            throw e;
        }
    }

    private static void finish() {
        synchronized (ReviewMap.class) {
            running = false;
        }
    }

    private static void next(World world, Deque<Spot> queue, Set<String> done, int total, PlayerRef player) {
        Spot s = queue.poll();
        if (s == null) {
            finish();
            saveState(world, done);
            player.sendMessage(Message.translation(KEYS + "done").param("count", total));
            return;
        }
        int pad = 24; // prefabs plus larges que leurs bornes mesurées (pièces enterrées, arbres)
        Terrain.load(world, s.x0 - pad, s.x1 + pad, s.z0 - pad, s.z1 + pad).whenComplete((v, error) ->
                world.execute(() -> {
                    try {
                        if (error != null) {
                            LOGGER.atWarning().withCause(error).log("Nakasar Peuples : revue, chunks de %s non chargés", s.key);
                        } else {
                            buildSpot(world, s);
                            done.add(s.key);
                        }
                    } catch (RuntimeException e) {
                        LOGGER.atWarning().withCause(e).log("Nakasar Peuples : revue, rectangle %s raté", s.key);
                    }
                    int left = queue.size();
                    if ((total - left) % REPORT_EVERY == 0) {
                        saveState(world, done);
                        player.sendMessage(Message.translation(KEYS + "progress").param("done", total - left).param("count", total));
                    }
                    next(world, queue, done, total, player);
                }));
    }

    private static void buildSpot(World world, Spot s) {
        ChunkStore chunks = world.getChunkStore();
        Store<EntityStore> store = world.getEntityStore().getStore();
        // Rectangle : air au-dessus, herbe dedans, liseré de laine rouge au bord.
        for (int x = s.x0; x <= s.x1; x++) {
            for (int z = s.z0; z <= s.z1; z++) {
                for (int y = GROUND + 1; y <= GROUND + s.height + CLEAR_ABOVE; y++) {
                    if (!Blocks.isEmpty(chunks, x, y, z)) {
                        Blocks.set(chunks, x, y, z, null, 0);
                    }
                }
                boolean edge = x == s.x0 || x == s.x1 || z == s.z0 || z == s.z1;
                Blocks.set(chunks, x, GROUND, z, edge ? BORDER : GRASS, 0);
            }
        }
        for (String line : s.tier.pieces) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            VillageBuilder.paste(world, store, p[0], s.ox + Integer.parseInt(p[1]), GROUND + Integer.parseInt(p[2]),
                    s.oz + Integer.parseInt(p[3]), Integer.parseInt(p[4]));
        }
        boolean heart = "Coeur".equals(s.row.category);
        for (String line : s.tier.blocks) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            int x = s.ox + Integer.parseInt(p[0]);
            int y = GROUND + 1 + Integer.parseInt(p[1]);
            int z = s.oz + Integer.parseInt(p[2]);
            String block = p[4];
            if ("Empty".equals(block)) {
                Blocks.set(chunks, x, y, z, null, 0);
                continue;
            }
            // Le cœur pose ses blocs comme au village ; un décor de lieu-dit ne remplace jamais un bloc du bâtiment.
            String current = Blocks.name(chunks, x, y, z);
            if (heart || current == null || Terrain.isVegetation(current) || (y <= GROUND && Terrain.isGround(current))) {
                Blocks.set(chunks, x, y, z, block, Integer.parseInt(p[3]));
            }
        }
        for (String line : s.tier.clear) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 4) {
                continue;
            }
            int x = s.ox + Integer.parseInt(p[0]);
            int y = GROUND + 1 + Integer.parseInt(p[1]);
            int z = s.oz + Integer.parseInt(p[2]);
            if (p[3].equals(Blocks.name(chunks, x, y, z))) {
                Blocks.set(chunks, x, y, z, null, 0);
            }
        }
        // Panneau muet dans le coin sud-ouest : l'utiliser dit le bâtiment et le palier.
        Blocks.set(chunks, s.signX, GROUND + 1, s.signZ, SIGN, 0);
    }

    // ---- Panneau ----

    /** Ce qu'affiche le panneau d'un rectangle : titre (bâtiment), sous-titre (peuple, palier, catégorie), détails. */
    static Message[] describe(Spot s) {
        Message title = Message.raw(s.row.name);
        Message subtitle = s.tier.tier == 0
                ? Message.translation(KEYS + "signUntiered").param("people", s.section.name).param("category", s.row.categoryName)
                : Message.translation(KEYS + "sign").param("people", s.section.name).param("tier", s.tier.tier)
                        .param("category", s.row.categoryName);
        List<String> prefabs = new ArrayList<>();
        for (String line : s.tier.pieces) {
            String path = line.trim().split("\\s+")[0];
            if (!prefabs.contains(path)) {
                prefabs.add(path);
            }
        }
        List<String> notes = new ArrayList<>();
        if (s.row.source != null && !s.row.source.isEmpty()) {
            notes.add(s.row.source);
        }
        if (s.tier.notes != null) {
            notes.addAll(s.tier.notes);
        }
        Message details = Message.translation(KEYS + "signDetails").param("prefabs", String.join(", ", prefabs))
                .param("notes", String.join(" · ", notes));
        return new Message[]{title, subtitle, details};
    }

    // ---- État ----

    private static Path worldFile(World world, String name) {
        return Universe.get().getWorldsPath().resolve(world.getName()).resolve(name);
    }

    private static List<String> readLines(Path f) {
        try {
            if (Files.exists(f)) {
                return Files.readAllLines(f, StandardCharsets.UTF_8);
            }
        } catch (IOException e) {
            LOGGER.atWarning().withCause(e).log("Nakasar Peuples : revue, lecture de %s", f);
        }
        return List.of();
    }

    private static void writeLines(Path f, Iterable<String> lines) {
        try {
            Files.createDirectories(f.getParent());
            Files.write(f, lines, StandardCharsets.UTF_8);
        } catch (IOException e) {
            LOGGER.atWarning().withCause(e).log("Nakasar Peuples : revue, écriture de %s", f);
        }
    }

    static Set<String> loadState(World world) {
        Set<String> keys = new LinkedHashSet<>();
        for (String line : readLines(worldFile(world, STATE_FILE))) {
            if (!line.isBlank()) {
                keys.add(line.trim());
            }
        }
        return keys;
    }

    private static void saveState(World world, Set<String> keys) {
        writeLines(worldFile(world, STATE_FILE), keys);
    }

    /** Lignes « R clé largeur profondeur hauteur » (rectangle d'un bâtiment) et « T clé dx dz » (origine d'un palier). */
    private static Map<String, int[]> loadPlan(World world) {
        Map<String, int[]> plan = new LinkedHashMap<>();
        for (String line : readLines(worldFile(world, PLAN_FILE))) {
            String[] p = line.trim().split("\\s+");
            try {
                if (p.length == 5 && p[0].equals("R")) {
                    plan.put("R " + p[1], new int[]{Integer.parseInt(p[2]), Integer.parseInt(p[3]), Integer.parseInt(p[4])});
                } else if (p.length == 4 && p[0].equals("T")) {
                    plan.put("T " + p[1], new int[]{Integer.parseInt(p[2]), Integer.parseInt(p[3])});
                }
            } catch (NumberFormatException e) {
                LOGGER.atWarning().log("Nakasar Peuples : revue, ligne de plan illisible « %s »", line);
            }
        }
        return plan;
    }

    private static void savePlan(World world, Map<String, int[]> plan) {
        List<String> lines = new ArrayList<>();
        for (Map.Entry<String, int[]> e : plan.entrySet()) {
            StringBuilder b = new StringBuilder(e.getKey());
            for (int v : e.getValue()) {
                b.append(' ').append(v);
            }
            lines.add(b.toString());
        }
        writeLines(worldFile(world, PLAN_FILE), lines);
    }
}
