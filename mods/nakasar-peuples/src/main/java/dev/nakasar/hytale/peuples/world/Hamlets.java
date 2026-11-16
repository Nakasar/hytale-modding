package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Annexes;
import dev.nakasar.hytale.peuples.annex.LandPath;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.reputation.Shops;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Grading;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiPredicate;

/**
 * Les lieux-dits (Kevin, 16 novembre 2026) : pas des villages, un groupe de 1 à 3 bâtiments vanilla proches (mine
 * isolée, ferme, moulin, caserne et ses deux tours de guet, forge avec mine et comptoir ou tour...), dans le style du
 * peuple du village le plus proche ({@link Hamlet}). Comme les vestiges, ils sont tirés une fois pour toutes : zéro à
 * deux le long de chaque liaison de {@value #MIN_LINK} blocs ou plus, à {@value #ASIDE_MIN}-{@value #ASIDE_MAX} blocs de
 * la route, et parfois un aux alentours d'un village ({@value #AROUND_MIN}-{@value #AROUND_MAX} blocs). Ils sont posés
 * quand un joueur approche, sur une place sèche et assez plate cherchée autour du point tiré, avec le terrassement des
 * villages ({@link Grading} : plateformes aux coins arrondis, arbres gardés au-dessus des toits, retour au relief et
 * demi-blocs). Leurs habitants (vrais PNJ près d'un joueur) ont un dialogue et un troc ; les marchands et caravanes des
 * villages voisins viennent y commercer ({@link HamletTrips}) et un lieu-dit souvent visité devient animé (troc élargi).
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#HAMLETS}) : {@code id = genre|x|z|rotation|étape|y|village|bâtiments|rx|rz}.
 * Visites des marchands : trafic {@code H:<id>} des liaisons ({@link Links#pass}).
 */
public final class Hamlets {

    public static final String KEYS = "nakasar_peuples.hamlet.";
    public static final String FLAG = "Hamlet:";
    /** Liaison la plus courte qui porte des lieux-dits. */
    public static final int MIN_LINK = 300;
    public static final int ASIDE_MIN = 40;
    public static final int ASIDE_MAX = 64;
    public static final int AROUND_MIN = 200;
    public static final int AROUND_MAX = 380;
    /** Chance qu'un village ait un lieu-dit à ses alentours. */
    public static final double AROUND_CHANCE = 0.6;
    /** Écarts : au bord d'un village (rayon de son plan en plus), entre lieux-dits, aux avant-postes, à l'auberge. */
    public static final int VILLAGE_GAP = 70;
    public static final int HAMLET_GAP = 140;
    public static final int ANNEX_GAP = 64;
    public static final int INN_GAP = 60;
    /** Posé à moins de cette distance d'un joueur (zone chargée). */
    public static final int PLACE_RANGE = 112;
    /** Recherche de la place : décalages autour du point tiré. */
    private static final int[] SEARCH = {0, 14, 28};
    /** Relief admis sous l'emprise, avant terrassement. */
    public static final int MAX_RELIEF = 7;
    private static final int MAX_STEP = 2;
    private static final int MARGIN = 2;
    private static final int BLEND = 4;
    private static final int YARD_CORNER = 2;
    private static final int YARD_FRAY = 2;
    public static final int DISCOVER = 16;
    /** Marchands venus en 7 jours pour que le lieu-dit soit animé (troc élargi). */
    public static final int LIVELY = 4;
    /** Place du marché (local) : devant le lieu-dit, là où attendent les marchands. */
    public static final int MARKET_Z = 5;

    public static final int PLANNED = 0;
    public static final int BUILT = 1;
    public static final int FAILED = 2;

    private static final String SEEDED = "~seed:";

    /** Un lieu-dit du monde (état sauvé). */
    public static final class Place {
        final String id;
        String asset;
        int x;
        int z;
        int rotation;
        int stage;
        int y;
        String village;
        int mask;
        int rx;
        int rz;

        Place(String id) {
            this.id = id;
        }

        static Place parse(String id, String v) {
            String[] p = v.split("\\|", -1);
            if (p.length < 10) {
                return null;
            }
            try {
                Place h = new Place(id);
                h.asset = p[0];
                h.x = Integer.parseInt(p[1]);
                h.z = Integer.parseInt(p[2]);
                h.rotation = Integer.parseInt(p[3]);
                h.stage = Integer.parseInt(p[4]);
                h.y = Integer.parseInt(p[5]);
                h.village = p[6];
                h.mask = Integer.parseInt(p[7]);
                h.rx = Integer.parseInt(p[8]);
                h.rz = Integer.parseInt(p[9]);
                return h;
            } catch (NumberFormatException e) {
                return null;
            }
        }

        String format() {
            return asset + "|" + x + "|" + z + "|" + rotation + "|" + stage + "|" + y + "|" + village + "|" + mask + "|" + rx + "|" + rz;
        }

        public String id() {
            return id;
        }

        public int x() {
            return x;
        }

        public int z() {
            return z;
        }

        public int stage() {
            return stage;
        }

        public String village() {
            return village;
        }

        public Hamlet type() {
            return Hamlet.get(asset);
        }

        /** Point du monde du point local (lx, lz). */
        public int[] world(int lx, int lz) {
            int[] r = Annexes.rotate(lx, lz, rotation);
            return new int[] {x + r[0], z + r[1]};
        }

        /** Place du marché, où attendent les marchands. */
        public int[] market() {
            return world(0, MARKET_Z);
        }

        /** Nom affiché : le genre du lieu-dit. */
        public Message name() {
            Hamlet h = type();
            return h == null ? Message.raw(asset) : Message.translation(h.nameKey());
        }

        String trafficKey() {
            return "H:" + id;
        }
    }

    private static final Map<String, List<Ref<EntityStore>>> RESIDENTS = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, String> RESIDENT_OF = Collections.synchronizedMap(new IdentityHashMap<>());

    private Hamlets() {
    }

    // ---- Registre ----

    public static List<Place> all(World world) {
        List<Place> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.HAMLETS).entrySet()) {
            if (e.getKey().startsWith("~")) {
                continue;
            }
            Place h = Place.parse(e.getKey(), e.getValue());
            if (h != null) {
                out.add(h);
            }
        }
        return out;
    }

    public static Place get(World world, String id) {
        String v = id == null ? null : WorldLife.registry(world).get(WorldLifeRegistry.Part.HAMLETS, id);
        return v == null ? null : Place.parse(id, v);
    }

    static void save(World world, Place h) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.HAMLETS, h.id, h.format());
    }

    /** Le lieu-dit dont ce PNJ est un habitant. */
    public static Place of(World world, Ref<EntityStore> npc) {
        String id = npc == null ? null : RESIDENT_OF.get(npc);
        return id == null ? null : get(world, id);
    }

    /** Le village du lieu-dit (son troc, sa réputation). */
    public static Village village(World world, Place h) {
        return h == null ? null : Villages.registry(world).byId(h.village);
    }

    /** Marchands venus ces 7 derniers jours. */
    public static int visits(World world, Place h, long day) {
        return Links.traffic(world, h.trafficKey(), day);
    }

    public static boolean lively(World world, Place h, long day) {
        return visits(world, h, day) >= LIVELY;
    }

    /** Le lieu-dit le plus proche de (x, z) à moins de `range` (tous états), ou null. */
    public static Place nearest(World world, double x, double z, double range) {
        Place best = null;
        double bestD = range * range;
        for (Place h : all(world)) {
            double d = (h.x - x) * (h.x - x) + (h.z - z) * (h.z - z);
            if (h.stage != FAILED && d <= bestD) {
                best = h;
                bestD = d;
            }
        }
        return best;
    }

    // ---- Tirage (une fois par liaison et par village) ----

    static void seed(World world) {
        WorldLifeRegistry r = WorldLife.registry(world);
        for (Links.Link link : Links.all(world)) {
            String mark = SEEDED + link.key();
            if (r.get(WorldLifeRegistry.Part.HAMLETS, mark) != null) {
                continue;
            }
            r.put(WorldLifeRegistry.Part.HAMLETS, mark, "1");
            if (link.length() < MIN_LINK) {
                continue;
            }
            Random random = new Random(link.key().hashCode() * 131L + 17);
            double roll = random.nextDouble();
            int count = roll < 0.3 ? 0 : roll < 0.8 || link.length() < 2 * MIN_LINK ? 1 : 2;
            Routes.Path path = Links.path(world, link.a(), link.b());
            for (int i = 0; i < count; i++) {
                for (int attempt = 0; attempt < 8; attempt++) {
                    double at = path.length() * (0.3 + random.nextDouble() * 0.4);
                    double[] p = path.point(at);
                    double[] d = path.dir(at);
                    double side = (random.nextBoolean() ? 1 : -1) * (ASIDE_MIN + random.nextInt(ASIDE_MAX - ASIDE_MIN + 1));
                    int x = (int) Math.floor(p[0] - d[1] * side);
                    int z = (int) Math.floor(p[1] + d[0] * side);
                    Village v = link.a().horizontalDistanceSquared(x, z) <= link.b().horizontalDistanceSquared(x, z) ? link.a() : link.b();
                    if (create(world, "L" + Integer.toHexString(link.key().hashCode()) + "_" + i, v, x, z,
                            (int) Math.floor(p[0]), (int) Math.floor(p[1]), null, random) != null) {
                        break;
                    }
                }
            }
        }
        for (Village v : Villages.registry(world).all()) {
            String mark = SEEDED + "V:" + v.id();
            if (r.get(WorldLifeRegistry.Part.HAMLETS, mark) != null) {
                continue;
            }
            r.put(WorldLifeRegistry.Part.HAMLETS, mark, "1");
            Random random = new Random(v.id().hashCode() * 977L + 3);
            if (random.nextDouble() >= AROUND_CHANCE) {
                continue;
            }
            for (int attempt = 0; attempt < 8; attempt++) {
                double a = random.nextDouble() * Math.PI * 2;
                double dist = AROUND_MIN + random.nextInt(AROUND_MAX - AROUND_MIN + 1);
                int x = v.x() + (int) Math.round(Math.cos(a) * dist);
                int z = v.z() + (int) Math.round(Math.sin(a) * dist);
                if (create(world, "V" + Integer.toHexString(v.id().hashCode()), v, x, z, v.x(), v.z(), null, random) != null) {
                    break;
                }
            }
        }
    }

    /**
     * Prévoit un lieu-dit en (x, z), rattaché à `village`, la place tournée vers (rx, rz) (la route ou le village) ;
     * `asset` null : genre tiré parmi ceux du peuple. Null si la place est trop près d'un village, d'un autre lieu-dit,
     * d'un avant-poste ou d'une auberge, ou dans l'eau (terrain généré).
     */
    public static Place create(World world, String id, Village village, int x, int z, int rx, int rz, Hamlet asset, Random random) {
        if (get(world, id) != null) {
            id = id + "_" + Integer.toString(random.nextInt(1296), 36);
        }
        if (blocked(world, x, z, null) != null) {
            return null;
        }
        if (!LandPath.drySite(world, x, z, 24, 12)) {
            return null;
        }
        Hamlet h = asset;
        if (h == null) {
            // Un genre que les lieux-dits du même village n'ont pas encore, si possible.
            for (int tries = 0; tries < 4; tries++) {
                h = Hamlet.pick(village.people(), random);
                if (h == null || !hasType(world, village, h)) {
                    break;
                }
            }
        }
        if (h == null) {
            return null;
        }
        Place p = new Place(id);
        p.asset = h.getId();
        p.x = x;
        p.z = z;
        p.rotation = Annexes.rotationFacing(rx - x, rz - z);
        p.stage = PLANNED;
        p.y = Integer.MIN_VALUE;
        p.village = village.id();
        p.mask = h.roll(random);
        p.rx = rx;
        p.rz = rz;
        save(world, p);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (lieux-dits) : %s prévu en %d %d (%s)", h.getId(), x, z, village.name());
        return p;
    }

    private static boolean hasType(World world, Village village, Hamlet h) {
        for (Place o : all(world)) {
            if (o.village.equals(village.id()) && o.asset.equals(h.getId())) {
                return true;
            }
        }
        return false;
    }

    /** Ce qui empêche un lieu-dit en (x, z) (texte de journal), ou null. `self` : le lieu-dit qu'on déplace. */
    static String blocked(World world, int x, int z, Place self) {
        for (Village v : Villages.registry(world).all()) {
            VillageLayout l = Chantiers.layout(v);
            int min = (l == null ? 64 : l.radius()) + VILLAGE_GAP;
            if (v.horizontalDistanceSquared(x, z) < (double) min * min) {
                return "village " + v.name();
            }
            for (AnnexState a : v.annexes()) {
                if (!a.granted() && a.distanceSquared(x + 0.5, z + 0.5) < (double) ANNEX_GAP * ANNEX_GAP) {
                    return "avant-poste de " + v.name();
                }
            }
        }
        for (Place o : all(world)) {
            if (o != self && (self == null || !o.id.equals(self.id)) && o.stage != FAILED
                    && (o.x - x) * (double) (o.x - x) + (o.z - z) * (double) (o.z - z) < (double) HAMLET_GAP * HAMLET_GAP) {
                return "lieu-dit " + o.id;
            }
        }
        for (Links.Link link : Links.all(world)) {
            if (link.length() < Inns.MIN_LENGTH) {
                continue;
            }
            Inns.Inn inn = Inns.get(world, link.key());
            double[] m = inn == null ? link.middle() : new double[] {inn.x(), inn.z()};
            if ((m[0] - x) * (m[0] - x) + (m[1] - z) * (m[1] - z) < (double) INN_GAP * INN_GAP) {
                return "auberge " + link.key();
            }
        }
        return null;
    }

    // ---- Pas ----

    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        boolean placedOne = false;
        for (Place h : all(world)) {
            if (h.stage == FAILED) {
                continue;
            }
            if (h.stage == PLANNED) {
                if (!placedOne && WorldLife.near(players, h.x, h.z, PLACE_RANGE)) {
                    placedOne = true; // une recherche de place par pas, au plus
                    place(world, store, h);
                }
                continue;
            }
            int[] m = h.market();
            boolean near = WorldLife.near(players, m[0], m[1], WorldLife.REAL_RANGE);
            List<Ref<EntityStore>> live = RESIDENTS.get(h.id);
            if (live != null) {
                live.removeIf(ref -> !ref.isValid());
            }
            if (!near) {
                removeResidents(store, h.id);
            } else if (live == null || live.isEmpty()) {
                spawnResidents(world, store, h);
            }
            for (PlayerRef p : WorldLife.playersNear(world, store, m[0], m[1], DISCOVER)) {
                discover(world, store, p, h);
            }
        }
    }

    // ---- Pose ----

    /** Cherche la place et pose le lieu-dit ; sans effet tant que la zone n'est pas chargée. */
    static void place(World world, Store<EntityStore> store, Place h) {
        Hamlet type = h.type();
        Village village = village(world, h);
        if (type == null || village == null) {
            h.stage = FAILED;
            save(world, h);
            return;
        }
        Terrain terrain = new Terrain(world);
        int[] local = type.rect(h.mask);
        int ox = h.x;
        int oz = h.z;
        int[] best = null;
        int bestGround = Terrain.NONE;
        boolean waiting = false;
        boolean ruled = false;
        String why = "?";
        search:
        for (int ring : SEARCH) {
            for (int dir = 0; dir < (ring == 0 ? 1 : 8); dir++) {
                double a = dir * Math.PI / 4;
                int cx = ox + (int) Math.round(Math.cos(a) * ring);
                int cz = oz + (int) Math.round(Math.sin(a) * ring);
                Place probe = copyAt(h, cx, cz);
                int[] rect = worldRect(probe, local);
                int g = siteGround(world, terrain, rect, type);
                if (g == UNLOADED_SITE) {
                    waiting = true;
                    continue;
                }
                if (g == Terrain.NONE) {
                    continue;
                }
                String b = blocked(world, cx, cz, h);
                if (b != null) {
                    why = b;
                    continue;
                }
                boolean rule = ruleOk(world, terrain, village.people(), type.rule(), rect, g);
                if (best == null || (rule && !ruled)) {
                    best = new int[] {cx, cz};
                    bestGround = g;
                    ruled = rule;
                    if (rule) {
                        break search;
                    }
                }
            }
        }
        if (best == null) {
            if (!waiting) {
                h.stage = FAILED;
                save(world, h);
                PeuplesPlugin.get().getLogger().atInfo().log("Peuples (lieux-dits) : aucune place pour %s autour de %d %d (%s)",
                        h.asset, h.x, h.z, why);
            }
            return;
        }
        if (waiting && !ruled) {
            return; // une place meilleure attend peut-être dans une partie pas encore chargée
        }
        h.x = best[0];
        h.z = best[1];
        h.rotation = Annexes.rotationFacing(h.rx - h.x, h.rz - h.z);
        if (build(world, store, h, type, village.people(), bestGround)) {
            h.stage = BUILT;
            h.y = bestGround;
            save(world, h);
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples (lieux-dits) : %s posé en %d %d %d (%s)", h.asset, h.x, bestGround, h.z,
                    village.name());
        }
    }

    private static Place copyAt(Place h, int x, int z) {
        Place p = new Place(h.id);
        p.x = x;
        p.z = z;
        p.rx = h.rx;
        p.rz = h.rz;
        p.rotation = Annexes.rotationFacing(h.rx - x, h.rz - z);
        return p;
    }

    /** Emprise du monde {@code [x0, x1, z0, z1]} d'un rectangle local du lieu-dit. */
    static int[] worldRect(Place h, int[] r) {
        int[] a = h.world(r[0], r[2]);
        int[] b = h.world(r[1], r[3]);
        return new int[] {Math.min(a[0], b[0]), Math.max(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[1], b[1])};
    }

    private static final int UNLOADED_SITE = Integer.MIN_VALUE + 7;

    /**
     * Sol médian de l'emprise si la place convient (chargée, sèche, relief d'au plus {@value #MAX_RELIEF}, rien de bâti
     * par un joueur), {@link Terrain#NONE} si elle ne convient pas, UNLOADED_SITE si elle n'est pas chargée.
     */
    private static int siteGround(World world, Terrain terrain, int[] rect, Hamlet type) {
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        for (int x = rect[0] - MARGIN; x <= rect[1] + MARGIN; x += 3) {
            for (int z = rect[2] - MARGIN; z <= rect[3] + MARGIN; z += 3) {
                if (Blocks.id(world.getChunkStore(), x, 64, z) == Blocks.UNLOADED) {
                    return UNLOADED_SITE;
                }
                int h = terrain.surface(x, z);
                if (h == Terrain.NONE) {
                    return UNLOADED_SITE;
                }
                if (terrain.hasFluid(x, h + 1, z) || terrain.hasFluid(x, h, z)) {
                    return Terrain.NONE;
                }
                min = Math.min(min, h);
                max = Math.max(max, h);
            }
        }
        if (max - min > MAX_RELIEF) {
            return Terrain.NONE;
        }
        int ground = terrain.medianSurface(rect[0], rect[1], rect[2], rect[3], 2);
        if (ground == Terrain.NONE) {
            return UNLOADED_SITE;
        }
        ChunkStore chunks = world.getChunkStore();
        int top = 0;
        for (Hamlet.Building b : type.buildings()) {
            top = Math.max(top, b.height());
        }
        for (int y = ground + 1; y <= ground + Math.min(top, 12); y++) {
            for (int x = rect[0]; x <= rect[1]; x += 2) {
                for (int z = rect[2]; z <= rect[3]; z += 2) {
                    String name = Blocks.name(chunks, x, y, z);
                    if (name != null && !Annexes.natural(name)) {
                        return Terrain.NONE; // un bloc posé par un joueur (ou une ruine) : pas ici
                    }
                }
            }
        }
        return ground;
    }

    private static boolean ruleOk(World world, Terrain terrain, People people, String rule, int[] rect, int ground) {
        if ("NONE".equals(rule)) {
            return true;
        }
        return Annexes.ruleMet(world, terrain, people, rule, rect, ground);
    }

    /**
     * Terrassement et collage : une plateforme par bâtiment (hauteur prise sous son emprise, à {@value #MAX_STEP} blocs
     * au plus de la place), la cour de la place, talus doux et arbres gardés au-dessus des toits, puis retour au relief
     * autour de chaque bâtiment collé et décor vanilla. Faux si rien n'a pu être collé (zone pas chargée).
     */
    static boolean build(World world, Store<EntityStore> store, Place h, Hamlet type, People people, int ground) {
        Terrain terrain = new Terrain(world);
        List<Hamlet.Building> chosen = type.chosen(h.mask);
        List<int[]> rects = new ArrayList<>();
        List<Integer> heights = new ArrayList<>();
        for (Hamlet.Building b : chosen) {
            int[] rect = worldRect(h, new int[] {b.x0(), b.x1(), b.z0(), b.z1()});
            int g = terrain.medianSurface(rect[0], rect[1], rect[2], rect[3], 2);
            g = g == Terrain.NONE ? ground : Math.max(ground - MAX_STEP, Math.min(ground + MAX_STEP, g));
            rects.add(rect);
            heights.add(g);
        }
        int[] yard = worldRect(h, new int[] {-4, 4, -2, MARKET_Z + 1});
        BiPredicate<Integer, Integer> slabOk = (x, z) -> {
            if (x >= yard[0] - 1 && x <= yard[1] + 1 && z >= yard[2] - 1 && z <= yard[3] + 1) {
                return false;
            }
            for (int[] r : rects) {
                if (x >= r[0] - 1 && x <= r[1] + 1 && z >= r[2] - 1 && z <= r[3] + 1) {
                    return false;
                }
            }
            return true;
        };
        Grading grading = new Grading(world).slabs(people.slabs(), slabOk)
                .pad(yard[0], yard[1], yard[2], yard[3], ground, 1, people.ground(), 6, YARD_CORNER, YARD_FRAY);
        for (int i = 0; i < chosen.size(); i++) {
            int[] r = rects.get(i);
            grading.pad(r[0], r[1], r[2], r[3], heights.get(i), MARGIN, people.ground(), chosen.get(i).height() + 1, 2, 0);
        }
        grading.apply(BLEND, people.ground(), null);
        int pasted = 0;
        List<Integer> done = new ArrayList<>();
        for (int i = 0; i < chosen.size(); i++) {
            Hamlet.Building b = chosen.get(i);
            int[] at = h.world(b.x(), b.z());
            int rot = (b.rotation() + h.rotation) & 3;
            if (VillageBuilder.paste(world, store, b.prefab(), at[0], heights.get(i), at[1], rot)) {
                pasted++;
                done.add(i);
            }
        }
        if (pasted == 0) {
            return false;
        }
        for (int i : done) {
            int[] r = rects.get(i);
            int self = i;
            BiPredicate<Integer, Integer> keep = (x, z) -> {
                if (x >= yard[0] && x <= yard[1] && z >= yard[2] && z <= yard[3]) {
                    return true;
                }
                for (int j = 0; j < rects.size(); j++) {
                    int[] o = rects.get(j);
                    if (j != self && x >= o[0] && x <= o[1] && z >= o[2] && z <= o[3]) {
                        return true;
                    }
                }
                return false;
            };
            new Grading(world).slabs(people.slabs(), slabOk).settle(r[0], r[1], r[2], r[3], heights.get(i), people.ground(), keep);
        }
        decor(world, h, type, ground);
        return true;
    }

    /** Décor vanilla de la place ({@code "dx dy dz lacet Bloc"}), seulement dans l'air et sur un sol. */
    private static void decor(World world, Place h, Hamlet type, int ground) {
        ChunkStore chunks = world.getChunkStore();
        for (String line : type.decor()) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            try {
                int[] at = h.world(Integer.parseInt(p[0]), Integer.parseInt(p[2]));
                int s = new Terrain(world).surface(at[0], at[1]);
                int y = (s == Terrain.NONE ? ground : s) + 1 + Integer.parseInt(p[1]);
                int rot = (Integer.parseInt(p[3]) + h.rotation) & 3;
                String current = Blocks.name(chunks, at[0], y, at[1]);
                if (Blocks.id(chunks, at[0], y, at[1]) != Blocks.UNLOADED && (current == null || Terrain.isVegetation(current))
                        && Blocks.name(chunks, at[0], y - 1, at[1]) != null) {
                    Blocks.set(chunks, at[0], y, at[1], p[4], rot);
                }
            } catch (NumberFormatException ignored) {
                // ligne mal formée : ValidateAssets la signale
            }
        }
    }

    // ---- Habitants ----

    private static final int[][] HOMES = {{0, 2}, {-3, 3}, {3, 3}};

    private static void spawnResidents(World world, Store<EntityStore> store, Place h) {
        Hamlet type = h.type();
        if (type == null || !WorldLife.budget(world, type.residents().length)) {
            return;
        }
        List<Ref<EntityStore>> live = new ArrayList<>();
        for (int i = 0; i < type.residents().length && i < HOMES.length; i++) {
            int[] spot = h.world(HOMES[i][0], HOMES[i][1]);
            Vector3d at = WorldLife.ground(world, spot[0], spot[1], 5);
            if (at == null) {
                continue;
            }
            int[] face = h.world(0, MARKET_Z + 4);
            float yaw = (float) Math.atan2(-(face[0] - spot[0]), face[1] - spot[1]);
            Ref<EntityStore> ref = WorldLife.spawn(store, type.residents()[i], at, yaw);
            if (ref == null) {
                continue;
            }
            WorldLife.talker(ref, Hamlets::talk);
            live.add(ref);
            RESIDENT_OF.put(ref, h.id);
        }
        RESIDENTS.put(h.id, live);
    }

    private static void removeResidents(Store<EntityStore> store, String id) {
        List<Ref<EntityStore>> live = RESIDENTS.remove(id);
        if (live == null) {
            return;
        }
        for (Ref<EntityStore> ref : live) {
            RESIDENT_OF.remove(ref);
            WorldLife.remove(store, ref);
        }
    }

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Place h = of(world, npc);
        Hamlet type = h == null ? null : h.type();
        Dialogue dialogue = type == null ? null : Dialogue.get(type.dialogue());
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    /** Troc du lieu-dit : rang Toléré dans son village ; élargi quand il est animé. */
    static boolean openShop(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Place h) {
        Village v = village(world, h);
        Hamlet type = h.type();
        if (v == null || type == null) {
            return false;
        }
        if (!Reputations.rank(store, ref, v).atLeast(Rank.TOLERE)) {
            DialogueSpeech.say(player, Message.translation(KEYS + "shopRank").param("village", v.name()));
            return false;
        }
        boolean busy = lively(world, h, GameClock.day(store));
        return Shops.open(store, ref, player, v, busy ? type.shopBusy() : type.shop());
    }

    /** « Qui vient commercer ici ? » */
    static boolean sayVisits(World world, Store<EntityStore> store, PlayerRef player, Place h) {
        long day = GameClock.day(store);
        int n = visits(world, h, day);
        String last = HamletTrips.lastVillage(world, h);
        Village lv = last == null ? null : Villages.registry(world).byId(last);
        Message m = n <= 0 || lv == null ? Message.translation(KEYS + "visits.none")
                : Message.translation(KEYS + (n >= LIVELY ? "visits.lively" : "visits.some")).param("count", n).param("village", lv.name());
        DialogueSpeech.say(player, m);
        return true;
    }

    private static void discover(World world, Store<EntityStore> store, PlayerRef player, Place h) {
        Ref<EntityStore> ref = player.getReference();
        PeuplesPlayer data = ref == null || !ref.isValid() ? null : PeuplesPlayer.ensure(store, ref);
        if (data == null || data.hasFlag(FLAG + h.id)) {
            return;
        }
        data.setFlag(FLAG + h.id, true);
        Village v = village(world, h);
        Hamlet type = h.type();
        Message people = Message.translation(type == null ? "?" : type.people().nameKey());
        Message title = Message.translation(KEYS + "discover").param("name", h.name()).param("people", people);
        player.sendMessage(title);
        player.sendMessage(Message.translation(KEYS + "discoverLine").param("people", people).param("village", v == null ? "?" : v.name()));
        NotificationUtil.sendNotification(player.getPacketHandler(), title, NotificationStyle.Default);
    }

    /** Annonce aux joueurs proches qu'il est devenu animé. */
    static void announceLively(World world, Store<EntityStore> store, Place h) {
        int[] m = h.market();
        Message msg = Message.translation(KEYS + "lively").param("name", h.name());
        WorldLife.announce(world, store, m[0], m[1], 96, msg, NotificationStyle.Success);
        Village v = village(world, h);
        if (v != null) {
            Chantiers.announce(world, v, msg, null, NotificationStyle.Success);
        }
    }

    /** Rumeur : un lieu-dit pas encore vu par le joueur (le plus proche). */
    static Message rumour(World world, Store<EntityStore> store, Ref<EntityStore> player) {
        Vector3d at = Requests.position(store, player);
        PeuplesPlayer data = PeuplesPlayer.get(store, player);
        Place best = null;
        double bestD = Double.MAX_VALUE;
        for (Place h : all(world)) {
            if (at == null || h.stage == FAILED || data != null && data.hasFlag(FLAG + h.id)) {
                continue;
            }
            double d = (h.x - at.x()) * (h.x - at.x()) + (h.z - at.z()) * (h.z - at.z());
            if (d < bestD) {
                bestD = d;
                best = h;
            }
        }
        if (best == null) {
            return null;
        }
        Hamlet type = best.type();
        return Message.translation(KEYS + "rumour").param("name", best.name())
                .param("people", Message.translation(type == null ? "?" : type.people().nameKey()))
                .param("distance", (int) Math.round(Math.sqrt(bestD)))
                .param("dir", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(best.x - at.x(), best.z - at.z())));
    }

    /** Le PNJ n'est plus (retiré ou mort). */
    static void forget(Ref<EntityStore> ref) {
        String id = RESIDENT_OF.remove(ref);
        if (id != null) {
            List<Ref<EntityStore>> live = RESIDENTS.get(id);
            if (live != null) {
                live.remove(ref);
            }
        }
    }

    public static void clearAll() {
        RESIDENTS.clear();
        RESIDENT_OF.clear();
    }
}
