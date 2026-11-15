package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Étape 3 : les traces anciennes. Le long de chaque liaison, zéro à deux vestiges vanilla de la zone (ruines,
 * vieux campement, autel), tirés une fois pour toutes d'après la liaison, à l'écart de la route ; ils sont posés quand
 * un joueur approche. Le premier passage d'un joueur à moins de {@value #DISCOVER} blocs lui raconte le lieu (une note
 * de lore par vestige, drapeau {@code Trace:<id>}). Un raid perdu laisse aussi sa trace : des arbres brûlés au bord du
 * village et le récit du raid ({@link #raid}).
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#TRACES}) : {@code id = genre|x|z|posé|prefab|rotation|lore|village}.
 */
public final class Traces {

    public static final int DISCOVER = 10;
    public static final int PLACE_RANGE = 96;
    public static final String FLAG = "Trace:";
    public static final String KEYS = WorldLife.KEYS + "trace.";
    public static final int LORE_VARIANTS = 3;
    private static final String SEEDED = "~seed:";

    private static final String[][] RUINS = {
            {},
            {"Monuments/Incidental/Shale/Ruins/Normal/Incidental_Shale_Monuments_Incidental_Shale_Normal_001",
                    "Monuments/Incidental/Shale/Ruins/Normal/Incidental_Shale_Monuments_Incidental_Shale_Normal_003",
                    "Monuments/Incidental/Slate/Ruins/Incidental_Slate_Ruin_001",
                    "Monuments/Encounter/City_Ruins/Towers/Encounter_City_Ruins_001"},
            {"Monuments/Incidental/Quartzite/Ruins/Incidental_Quartzite_001",
                    "Monuments/Incidental/Quartzite/Ruins/Incidental_Quartzite_003",
                    "Monuments/Incidental/Sandstone/Normal/Incidental_Sandstone_001"},
            {"Monuments/Incidental/Shale/Ruins/Frozen/Incidental_Shale_Monuments_Incidental_Shale_Frozen_001",
                    "Monuments/Incidental/Shale/Ruins/Frozen/Incidental_Shale_Monuments_Incidental_Shale_Frozen_003",
                    "Monuments/Incidental/Slate/Ruins/Incidental_Slate_Ruin_002"},
            {"Monuments/Incidental/Slothian/Land/Shrine/Incidental_Slothian_Shrine_Slothian_Shrine_001",
                    "Monuments/Incidental/Slothian/Land/Well/Incidental_Slothian_Well_Slothian_Well_001",
                    "Monuments/Incidental/Slate/Ruins/Incidental_Slate_Ruin_003"},
    };

    private static final String[][] OLD_CAMPS = {
            {},
            {"Monuments/Incidental/Grasslands/Camps/Plains/Incidental_Grasslands_Plains_Incidentals_Grasslands_Camps_Plains_001",
                    "Monuments/Incidental/Grasslands/Hunting/Camps/Incidental_Grasslands_Incidentals_Grasslands_Hunting_Camps_001"},
            {"Monuments/Incidental/Sandstone/Tent/Incidental_Sandstone_002"},
            {"Monuments/Incidental/Softwood/Misc/Incidental_Softwood_004"},
            {"Monuments/Incidental/Slothian/Land/Hunting/Incidental_Slothian_Slothian_Hunting_001"},
    };

    /** Arbres brûlés vanilla laissés par un raid perdu. */
    public static final String[] BURNT_TREES = {
            "Orbis/Trees/Burnt/Stage_1/Burnt_Stage1_002", "Orbis/Trees/Burnt/Stage_1/Burnt_Stage1_005",
            "Orbis/Trees/Burnt/Stage_1/Burnt_Stage1_009", "Orbis/Trees/Burnt/Stage_2/Burnt_Stage2_001",
            "Orbis/Trees/Burnt/Stage_2/Burnt_Stage2_003"};

    /** Un vestige (état sauvé). */
    public record Trace(String id, String type, int x, int z, boolean placed, String prefab, int rotation, int lore, String village) {

        static Trace parse(String id, String v) {
            String[] p = v.split("\\|", -1);
            if (p.length < 8) {
                return null;
            }
            try {
                return new Trace(id, p[0], Integer.parseInt(p[1]), Integer.parseInt(p[2]), "1".equals(p[3]), p[4],
                        Integer.parseInt(p[5]), Integer.parseInt(p[6]), p[7]);
            } catch (NumberFormatException e) {
                return null;
            }
        }

        String format() {
            return type + "|" + x + "|" + z + "|" + (placed ? 1 : 0) + "|" + prefab + "|" + rotation + "|" + lore + "|" + village;
        }

        Trace placedNow() {
            return new Trace(id, type, x, z, true, prefab, rotation, lore, village);
        }
    }

    private Traces() {
    }

    public static List<Trace> all(World world) {
        List<Trace> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.TRACES).entrySet()) {
            if (e.getKey().startsWith("~")) {
                continue;
            }
            Trace t = Trace.parse(e.getKey(), e.getValue());
            if (t != null) {
                out.add(t);
            }
        }
        return out;
    }

    private static void save(World world, Trace t) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRACES, t.id(), t.format());
    }

    /** Tirage des vestiges des nouvelles liaisons (une fois par liaison). */
    static void seed(World world) {
        WorldLifeRegistry r = WorldLife.registry(world);
        for (Links.Link link : Links.all(world)) {
            if (r.get(WorldLifeRegistry.Part.TRACES, SEEDED + link.key()) != null) {
                continue;
            }
            r.put(WorldLifeRegistry.Part.TRACES, SEEDED + link.key(), "1");
            Random random = new Random(link.key().hashCode() * 31L + 7);
            double roll = random.nextDouble();
            int count = roll < 0.4 ? 0 : roll < 0.85 ? 1 : 2;
            if (link.length() < 160) {
                count = 0; // trop près : on verrait les vestiges depuis les villages
            }
            Routes.Path path = Links.path(world, link.a(), link.b());
            int zone = Math.max(1, Math.min(4, link.a().people().zone()));
            for (int i = 0; i < count; i++) {
                double at = path.length() * (0.25 + random.nextDouble() * 0.5);
                double[] p = path.point(at);
                double[] d = path.dir(at);
                double side = (random.nextBoolean() ? 1 : -1) * (16 + random.nextInt(10));
                int x = (int) Math.floor(p[0] - d[1] * side);
                int z = (int) Math.floor(p[1] + d[0] * side);
                boolean ruin = zone == 4 || random.nextDouble() < 0.6;
                String[] pool = ruin ? RUINS[zone] : OLD_CAMPS[zone];
                String prefab = pool[random.nextInt(pool.length)];
                String type = ruin ? (zone == 4 && prefab.contains("Shrine") ? "shrine" : "ruin") : "oldcamp";
                Trace t = new Trace(link.key().hashCode() + "_" + i, type, x, z, false, prefab, random.nextInt(4),
                        1 + random.nextInt(LORE_VARIANTS), link.a().id());
                save(world, t);
            }
        }
    }

    /** Un raid perdu : arbres brûlés au bord du village et récit (le village ne disparaît jamais). */
    public static void raid(World world, Village village, long day) {
        Random random = new Random();
        double angle = random.nextDouble() * Math.PI * 2;
        int radius = Villages.RADIUS + 6;
        for (int i = 0; i < 3; i++) {
            double a = angle + (i - 1) * 0.25;
            int x = village.x() + (int) Math.round(Math.cos(a) * (radius + random.nextInt(6)));
            int z = village.z() + (int) Math.round(Math.sin(a) * (radius + random.nextInt(6)));
            Trace t = new Trace("raid_" + village.id().hashCode() + "_" + day + "_" + i, i == 0 ? "raid" : "burnt", x, z, false,
                    BURNT_TREES[random.nextInt(BURNT_TREES.length)], random.nextInt(4), 1 + random.nextInt(LORE_VARIANTS), village.id());
            save(world, t);
        }
    }

    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        for (Trace t : all(world)) {
            if (!t.placed()) {
                if (WorldLife.near(players, t.x(), t.z(), PLACE_RANGE) && Sites.loaded(world, t.x(), t.z())) {
                    int ground = Sites.ground(world, t.prefab(), t.x(), t.z(), t.rotation());
                    if (ground != Terrain.NONE && Sites.pastePermanent(world, store, t.prefab(), t.x(), ground, t.z(), t.rotation())) {
                        save(world, t.placedNow());
                    }
                }
                continue;
            }
            if ("burnt".equals(t.type())) {
                continue; // simple décor : le récit est porté par le premier arbre
            }
            for (PlayerRef p : WorldLife.playersNear(world, store, t.x(), t.z(), DISCOVER)) {
                discover(world, store, p, t);
            }
        }
    }

    private static void discover(World world, Store<EntityStore> store, PlayerRef player, Trace t) {
        Ref<EntityStore> ref = player.getReference();
        PeuplesPlayer data = ref == null || !ref.isValid() ? null : PeuplesPlayer.ensure(store, ref);
        if (data == null || data.hasFlag(FLAG + t.id())) {
            return;
        }
        data.setFlag(FLAG + t.id(), true);
        Village v = Villages.registry(world).byId(t.village());
        Message title = Message.translation(KEYS + t.type() + ".title");
        Message lore = Message.translation(KEYS + t.type() + "." + t.lore()).param("village", v == null ? "?" : v.name());
        player.sendMessage(title);
        player.sendMessage(lore);
        NotificationUtil.sendNotification(player.getPacketHandler(), title, NotificationStyle.Default);
    }

    /** Le vestige non découvert le plus proche du joueur (rumeurs). */
    static Trace nearestUnknown(World world, Store<EntityStore> store, Ref<EntityStore> player) {
        Vector3d at = Requests.position(store, player);
        PeuplesPlayer data = PeuplesPlayer.get(store, player);
        Trace best = null;
        double bestD = Double.MAX_VALUE;
        for (Trace t : all(world)) {
            if (at == null || "burnt".equals(t.type()) || data != null && data.hasFlag(FLAG + t.id())) {
                continue;
            }
            double d = (t.x() - at.x()) * (t.x() - at.x()) + (t.z() - at.z()) * (t.z() - at.z());
            if (d < bestD) {
                bestD = d;
                best = t;
            }
        }
        return best;
    }
}
