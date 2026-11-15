package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/**
 * Étape 3 : les auberges de relais. Une liaison de plus de {@value #MIN_LENGTH} blocs (le relais est à plus de
 * {@value #MIN_LENGTH_HALF} blocs de chaque village) qui voit {@value #TRAFFIC_1} passages en
 * {@value Links#WINDOW_DAYS} jours lance le chantier d'une auberge à mi-chemin, un peu à l'écart de la route : une
 * journée de travaux ({@value #WORK_HOURS} h de jeu), puis le prefab vanilla de la zone et un aubergiste du peuple du
 * premier village. Niveaux : relais (repas), auberge à {@value #TRAFFIC_2} passages (troc des voyageurs), grand relais à
 * {@value #TRAFFIC_3} (rumeurs et lettres). Les voyageurs y passent la nuit. Sans passage pendant
 * {@value #CLOSE_DAYS} jours, l'aubergiste s'en va : l'auberge reste debout, vide (une trace de plus).
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#INNS}) : {@code a|b = étape|x|y|z|niveau|fin des travaux|sens}.
 */
public final class Inns {

    public static final int MIN_LENGTH = 400;
    public static final int MIN_LENGTH_HALF = MIN_LENGTH / 2;
    public static final int TRAFFIC_1 = 40;
    public static final int TRAFFIC_2 = 80;
    public static final int TRAFFIC_3 = 120;
    public static final int WORK_HOURS = 12;
    public static final int CLOSE_DAYS = 14;
    /** Écart entre la route et l'auberge. */
    private static final int ASIDE = 12;
    public static final String KEYS = WorldLife.KEYS + "inn.";
    public static final String DIALOGUE = "Monde_Aubergiste";
    public static final String SHOP = "Nakasar_Peuples_Inn";

    public static final int WORKS = 0;
    public static final int OPEN = 1;
    public static final int CLOSED = 2;

    /** Une auberge (état sauvé). */
    public static final class Inn {
        final String link;
        int stage;
        int x;
        int y;
        int z;
        int level;
        long end;
        int rotation;
        boolean built;
        /** Point de la route en face de l'auberge. */
        int rx;
        int rz;

        Inn(String link) {
            this.link = link;
        }

        static Inn parse(String link, String v) {
            String[] p = v.split("\\|");
            if (p.length < 10) {
                return null;
            }
            try {
                Inn i = new Inn(link);
                i.stage = Integer.parseInt(p[0]);
                i.x = Integer.parseInt(p[1]);
                i.y = Integer.parseInt(p[2]);
                i.z = Integer.parseInt(p[3]);
                i.level = Integer.parseInt(p[4]);
                i.end = Long.parseLong(p[5]);
                i.rotation = Integer.parseInt(p[6]);
                i.built = "1".equals(p[7]);
                i.rx = Integer.parseInt(p[8]);
                i.rz = Integer.parseInt(p[9]);
                return i;
            } catch (NumberFormatException e) {
                return null;
            }
        }

        String format() {
            return stage + "|" + x + "|" + y + "|" + z + "|" + level + "|" + end + "|" + rotation + "|" + (built ? 1 : 0) + "|" + rx + "|" + rz;
        }

        public int level() {
            return level;
        }

        public boolean open() {
            return stage == OPEN;
        }

        public int x() {
            return x;
        }

        public int z() {
            return z;
        }

        public String link() {
            return link;
        }
    }

    private static final Map<String, Ref<EntityStore>> KEEPERS = new java.util.concurrent.ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, String> KEEPER_OF = Collections.synchronizedMap(new IdentityHashMap<>());

    private Inns() {
    }

    public static List<Inn> all(World world) {
        List<Inn> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.INNS).entrySet()) {
            Inn i = Inn.parse(e.getKey(), e.getValue());
            if (i != null) {
                out.add(i);
            }
        }
        return out;
    }

    public static Inn get(World world, String link) {
        String v = WorldLife.registry(world).get(WorldLifeRegistry.Part.INNS, link);
        return v == null ? null : Inn.parse(link, v);
    }

    private static void save(World world, Inn inn) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.INNS, inn.link, inn.format());
    }

    /** L'auberge tenue par ce PNJ. */
    public static Inn of(World world, Ref<EntityStore> npc) {
        String link = npc == null ? null : KEEPER_OF.get(npc);
        return link == null ? null : get(world, link);
    }

    /** Prefab vanilla de l'auberge selon la zone du peuple. */
    public static String prefab(People people) {
        return switch (people.zone()) {
            case 2 -> "Monuments/Incidental/Sandstone/Normal/Incidental_Sandstone_003";
            case 3 -> "Monuments/Incidental/Softwood/Misc/Incidental_Softwood_001";
            case 4 -> "Monuments/Incidental/Slothian/Land/Merchant/Incidental_Slothian_Merchant_Slothian_Merchant_001";
            default -> "Monuments/Incidental/Grasslands/Hunting/Cabins/Incidental_Grasslands_Cabins_Incidentals_Grasslands_Hunting_Cabins_002";
        };
    }

    public static String keeperRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Innkeeper";
    }

    // ---- Chaque matin ----

    static void morning(World world, Store<EntityStore> store, long day) {
        for (Links.Link link : Links.all(world)) {
            Inn inn = get(world, link.key());
            int traffic = Links.traffic(world, link.key(), day);
            if (inn == null) {
                if (link.length() >= MIN_LENGTH && traffic >= TRAFFIC_1) {
                    begin(world, store, link);
                }
                continue;
            }
            if (inn.stage == OPEN) {
                int level = traffic >= TRAFFIC_3 ? 3 : traffic >= TRAFFIC_2 ? 2 : 1;
                if (level > inn.level) {
                    inn.level = level;
                    Message m = Message.translation(KEYS + "level." + level).param("a", link.a().name()).param("b", link.b().name());
                    Chantiers.announce(world, link.a(), m, null, NotificationStyle.Success);
                    Chantiers.announce(world, link.b(), m, null, NotificationStyle.Success);
                }
                long last = Links.lastPass(world, link.key());
                if (last != Long.MIN_VALUE && day - last >= CLOSE_DAYS) {
                    inn.stage = CLOSED;
                    removeKeeper(store, inn.link);
                    Chantiers.announce(world, link.a(), Message.translation(KEYS + "closed").param("a", link.a().name())
                            .param("b", link.b().name()), null, NotificationStyle.Warning);
                }
                save(world, inn);
            } else if (inn.stage == CLOSED && traffic >= TRAFFIC_1) {
                inn.stage = OPEN;
                inn.level = 1;
                save(world, inn);
            }
        }
    }

    /** Lance le chantier de l'auberge de la liaison (aussi /monde). */
    public static Inn begin(World world, Store<EntityStore> store, Links.Link link) {
        Routes.Path path = Links.path(world, link.a(), link.b());
        double at = path.length() / 2;
        double[] p = path.point(at);
        double[] d = path.dir(at);
        Inn inn = new Inn(link.key());
        inn.x = (int) Math.floor(p[0] - d[1] * ASIDE);
        inn.z = (int) Math.floor(p[1] + d[0] * ASIDE);
        inn.y = Integer.MIN_VALUE;
        inn.rx = (int) Math.floor(p[0]);
        inn.rz = (int) Math.floor(p[1]);
        // Porte vers la route : le prefab est tourné d'un quart de tour par quadrant de la route.
        inn.rotation = Math.floorMod((int) Math.round(Math.atan2(d[1], d[0]) / (Math.PI / 2)), 4);
        inn.stage = WORKS;
        inn.level = 1;
        inn.end = GameClock.seconds(store) + WORK_HOURS * 3600L;
        save(world, inn);
        Message m = Message.translation(KEYS + "works").param("a", link.a().name()).param("b", link.b().name());
        Chantiers.announce(world, link.a(), m, null, NotificationStyle.Default);
        Chantiers.announce(world, link.b(), m, null, NotificationStyle.Default);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (monde vivant) : chantier d'auberge %s en %d %d", link.key(), inn.x, inn.z);
        return inn;
    }

    // ---- Pas ----

    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        long now = GameClock.seconds(store);
        for (Inn inn : all(world)) {
            String[] ids = inn.link.split("\\|");
            Links.Link link = ids.length == 2 ? Links.of(world, ids[0], ids[1]) : null;
            if (link == null) {
                removeKeeper(store, inn.link);
                continue;
            }
            if (inn.stage == WORKS && now >= inn.end) {
                inn.stage = OPEN;
                save(world, inn);
                Message m = Message.translation(KEYS + "opened").param("a", link.a().name()).param("b", link.b().name());
                Chantiers.announce(world, link.a(), m, null, NotificationStyle.Success);
                Chantiers.announce(world, link.b(), m, null, NotificationStyle.Success);
            }
            boolean near = WorldLife.near(players, inn.x, inn.z, WorldLife.REAL_RANGE);
            if (!inn.built && inn.stage != WORKS && near && Sites.loaded(world, inn.x, inn.z)) {
                build(world, store, inn, link.a().people());
            }
            Ref<EntityStore> keeper = KEEPERS.get(inn.link);
            boolean wanted = inn.stage == OPEN && inn.built && near;
            if (!wanted && keeper != null) {
                removeKeeper(store, inn.link);
            } else if (wanted && (keeper == null || !keeper.isValid()) && WorldLife.budget(world, 1)) {
                spawnKeeper(world, store, inn, link.a().people());
            }
        }
    }

    private static void build(World world, Store<EntityStore> store, Inn inn, People people) {
        String prefab = prefab(people);
        int ground = Sites.ground(world, prefab, inn.x, inn.z, inn.rotation);
        if (ground == dev.nakasar.hytale.peuples.village.Terrain.NONE) {
            return;
        }
        int[] b = dev.nakasar.hytale.peuples.village.VillageBuilder.bounds(prefab, inn.x, ground, inn.z, inn.rotation);
        if (b != null) {
            new dev.nakasar.hytale.peuples.village.Terrain(world).flatten(b[0] + 1, b[1] - 1, b[4] + 1, b[5] - 1, ground, 1, 3,
                    people.ground(), (px, pz) -> false);
        }
        if (!Sites.pastePermanent(world, store, prefab, inn.x, ground, inn.z, inn.rotation)) {
            return;
        }
        inn.y = ground;
        inn.built = true;
        // L'enseigne de la taverne (vanilla), au bord de la route, sur un sol sûr.
        int[] sign = front(inn, 3);
        Vector3d at = WorldLife.ground(world, sign[0], sign[1], 3);
        if (at != null) {
            Blocks.set(world.getChunkStore(), (int) Math.floor(at.x()), (int) Math.floor(at.y()), (int) Math.floor(at.z()),
                    "Furniture_Tavern_Sign", inn.rotation);
        }
        save(world, inn);
    }

    private static void spawnKeeper(World world, Store<EntityStore> store, Inn inn, People people) {
        int[] spot = front(inn, 5);
        Vector3d at = WorldLife.ground(world, spot[0], spot[1], 6);
        if (at == null) {
            return;
        }
        Ref<EntityStore> ref = WorldLife.spawn(store, keeperRole(people), at, 0f);
        if (ref == null) {
            return;
        }
        WorldLife.talker(ref, Inns::talk);
        KEEPERS.put(inn.link, ref);
        KEEPER_OF.put(ref, inn.link);
    }

    private static void removeKeeper(Store<EntityStore> store, String link) {
        Ref<EntityStore> ref = KEEPERS.remove(link);
        if (ref != null) {
            KEEPER_OF.remove(ref);
            WorldLife.remove(store, ref);
        }
    }

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Dialogue dialogue = Dialogue.get(DIALOGUE);
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    /**
     * Vrai si le voyageur doit encore marcher de nuit jusqu'à l'auberge ouverte de sa liaison (elle est devant lui) ;
     * faux : il s'arrête là où il est.
     */
    static boolean nightStopAhead(World world, Travellers.Traveller t, Routes.Path path) {
        Inn inn = get(world, Links.key(t.from(), t.to()));
        if (inn == null || inn.stage != OPEN) {
            return false;
        }
        double innAt = path.closest(inn.x, inn.z, 0, path.length());
        return t.at < innAt - 3;
    }

    /** Point entre l'auberge et la route, à `fromRoad` blocs de la route. */
    private static int[] front(Inn inn, int fromRoad) {
        double dx = inn.x - inn.rx;
        double dz = inn.z - inn.rz;
        double len = Math.max(1, Math.hypot(dx, dz));
        return new int[] {(int) Math.floor(inn.rx + dx / len * fromRoad), (int) Math.floor(inn.rz + dz / len * fromRoad)};
    }

    /** L'auberge ouverte la plus proche du point (x, z) à moins de `range`, ou null. */
    public static Inn nearest(World world, double x, double z, double range) {
        Inn best = null;
        double bestD = range * range;
        for (Inn inn : all(world)) {
            double d = (inn.x - x) * (inn.x - x) + (inn.z - z) * (inn.z - z);
            if (inn.stage == OPEN && d <= bestD) {
                best = inn;
                bestD = d;
            }
        }
        return best;
    }

    /** Village du premier peuple de l'auberge (son troc). */
    static Village firstVillage(World world, Inn inn) {
        return Villages.registry(world).byId(inn.link.split("\\|")[0]);
    }

    public static void clearAll() {
        KEEPERS.clear();
        KEEPER_OF.clear();
    }
}
