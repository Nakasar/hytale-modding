package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Étape 4 : les campements temporaires. Chaque matin, une chance sur quatre ({@value #CHANCE}) qu'un campement
 * s'installe entre {@value #MIN_DISTANCE} et {@value #MAX_DISTANCE} blocs d'un village (au plus {@value #MAX_WORLD}
 * à la fois), pour trois à cinq jours : chasseurs (viande crue contre cuir), bûcherons (pain contre sève), prospecteurs
 * (à défendre contre une bande), halte de marchands (troc du peuple). Le campement est un prefab vanilla posé pour un
 * temps ({@link Sites#pasteTemporary}) et rendu à la fin.
 *
 * <p>Réfugiés : un raid perdu brûle un bâtiment (le village ne disparaît jamais) ; ses habitants campent au bord du
 * village jusqu'à ce qu'il soit relevé. Leur donner à manger fait avancer l'essor du village.
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#CAMPS}) : {@code id = genre|x|z|village|fin|posé|quête|bâtiment}.
 */
public final class Camps {

    public static final double CHANCE = 0.25;
    public static final int MAX_WORLD = 4;
    public static final int MIN_DISTANCE = 150;
    public static final int MAX_DISTANCE = 400;
    public static final int CAMPERS = 3;
    public static final int REPUTATION = 15;
    public static final int DONATION_MAX = 10;
    public static final String KEYS = WorldLife.KEYS + "camp.";
    public static final String FLAG = "Camp:";

    public enum Type {
        HUNTERS, WOODCUTTERS, PROSPECTORS, MERCHANTS, REFUGEES;

        public String key() {
            return name().toLowerCase();
        }

        public String dialogue() {
            return "Monde_Camp_" + name().charAt(0) + name().substring(1).toLowerCase();
        }
    }

    /** Un campement (état sauvé). Quête : 0 rien, 1 bande en vue, 2 défendu. */
    public static final class Camp {
        final String id;
        Type type;
        int x;
        int z;
        String village;
        long end;
        boolean placed;
        int quest;
        String building = "-";

        Camp(String id) {
            this.id = id;
        }

        static Camp parse(String id, String v) {
            String[] p = v.split("\\|", -1);
            if (p.length < 8) {
                return null;
            }
            try {
                Camp c = new Camp(id);
                c.type = Type.valueOf(p[0]);
                c.x = Integer.parseInt(p[1]);
                c.z = Integer.parseInt(p[2]);
                c.village = p[3];
                c.end = Long.parseLong(p[4]);
                c.placed = "1".equals(p[5]);
                c.quest = Integer.parseInt(p[6]);
                c.building = p[7];
                return c;
            } catch (IllegalArgumentException e) {
                return null;
            }
        }

        String format() {
            return type.name() + "|" + x + "|" + z + "|" + village + "|" + end + "|" + (placed ? 1 : 0) + "|" + quest + "|" + building;
        }

        public Type type() {
            return type;
        }

        public int x() {
            return x;
        }

        public int z() {
            return z;
        }

        public String village() {
            return village;
        }

        String structure() {
            return "camp:" + id;
        }
    }

    private static final Map<String, List<Ref<EntityStore>>> CAMPERS_OF = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, String> CAMP_OF = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<String, List<Ref<EntityStore>>> RAIDERS = new ConcurrentHashMap<>();

    private Camps() {
    }

    public static List<Camp> all(World world) {
        List<Camp> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.CAMPS).entrySet()) {
            Camp c = Camp.parse(e.getKey(), e.getValue());
            if (c != null) {
                out.add(c);
            }
        }
        return out;
    }

    public static Camp get(World world, String id) {
        String v = id == null ? null : WorldLife.registry(world).get(WorldLifeRegistry.Part.CAMPS, id);
        return v == null ? null : Camp.parse(id, v);
    }

    static void save(World world, Camp c) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.CAMPS, c.id, c.format());
    }

    public static Camp of(World world, Ref<EntityStore> npc) {
        return get(world, npc == null ? null : CAMP_OF.get(npc));
    }

    // ---- Prefabs ----

    static String[] prefabs(Type type, int zone) {
        return switch (type) {
            case HUNTERS -> new String[] {switch (zone) {
                case 2 -> "Monuments/Incidental/Sandstone/Tent/Incidental_Sandstone_001";
                case 3 -> "Monuments/Incidental/Softwood/Tent/Incidental_Softwood_001";
                case 4 -> "Monuments/Incidental/Slothian/Land/Hunting/Incidental_Slothian_Slothian_Hunting_002";
                default -> "Monuments/Incidental/Grasslands/Hunting/Camps/Incidental_Grasslands_Incidentals_Grasslands_Hunting_Camps_001";
            }};
            case WOODCUTTERS -> new String[] {zone == 2 ? "Monuments/Incidental/Sandstone/Tent/Incidental_Sandstone_003"
                    : "Monuments/Incidental/Softwood/Misc/Incidental_Softwood_002"};
            case PROSPECTORS -> new String[] {zone == 2 ? "Monuments/Incidental/Sandstone/Normal/Incidental_Sandstone_002"
                    : "Monuments/Incidental/Softwood/Tent/Incidental_Softwood_003"};
            case MERCHANTS -> new String[] {"Orbis/Enkindled/Deco_Carts/Deco_Carts_001", "Orbis/Enkindled/Deco_Stalls/Deco_Stalls_001"};
            case REFUGEES -> new String[] {switch (zone) {
                case 2 -> "Monuments/Incidental/Sandstone/Tent/Incidental_Sandstone_002";
                case 3 -> "Monuments/Incidental/Softwood/Tent/Incidental_Softwood_002";
                case 4 -> "Monuments/Incidental/Slothian/Land/Hunting/Incidental_Slothian_Slothian_Hunting_001";
                default -> "Monuments/Incidental/Grasslands/Camps/Plains/Incidental_Grasslands_Plains_Incidentals_Grasslands_Camps_Plains_001";
            }};
        };
    }

    public static String camperRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Camper";
    }

    // ---- Chaque matin ----

    static void morning(World world, Store<EntityStore> store, long day, Random random) {
        List<Camp> camps = all(world);
        for (Camp c : camps) {
            Village v = Villages.registry(world).byId(c.village);
            boolean over = c.type == Type.REFUGEES ? v == null || v.isStanding(c.building) : day > c.end;
            if (over) {
                end(world, store, c, v);
            }
        }
        long normal = all(world).stream().filter(c -> c.type != Type.REFUGEES).count();
        if (normal < MAX_WORLD && random.nextDouble() < CHANCE) {
            List<Village> villages = new ArrayList<>(Villages.registry(world).all());
            if (!villages.isEmpty()) {
                Village v = villages.get(random.nextInt(villages.size()));
                Type type = Type.values()[random.nextInt(4)];
                start(world, type, v, day, random);
            }
        }
    }

    /** Installe un campement près du village (aussi /monde) ; null si aucune place n'a été trouvée. */
    public static Camp start(World world, Type type, Village village, long day, Random random) {
        for (int tries = 0; tries < 8; tries++) {
            double angle = random.nextDouble() * Math.PI * 2;
            int d = MIN_DISTANCE + random.nextInt(MAX_DISTANCE - MIN_DISTANCE);
            int x = village.x() + (int) Math.round(Math.cos(angle) * d);
            int z = village.z() + (int) Math.round(Math.sin(angle) * d);
            if (WorldLife.nearestVillage(world, x, z, MIN_DISTANCE - 30) != null || nearCamp(world, x, z, 120)) {
                continue;
            }
            Camp c = new Camp(Long.toString(System.currentTimeMillis(), 36) + tries);
            c.type = type;
            c.x = x;
            c.z = z;
            c.village = village.id();
            c.end = day + 3 + random.nextInt(3);
            save(world, c);
            Chantiers.announce(world, village, Message.translation(KEYS + "new." + type.key())
                    .param("distance", d).param("direction", direction(village, x, z)), null, NotificationStyle.Default);
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples (monde vivant) : campement %s près de %s en %d %d", type, village.name(), x, z);
            return c;
        }
        return null;
    }

    private static Message direction(Village v, int x, int z) {
        return Message.translation(Villages.MESSAGES + "dir." + Requests.direction(x - v.x(), z - v.z()));
    }

    private static boolean nearCamp(World world, int x, int z, int range) {
        for (Camp c : all(world)) {
            if ((c.x - x) * (double) (c.x - x) + (c.z - z) * (double) (c.z - z) < (double) range * range) {
                return true;
            }
        }
        return false;
    }

    /**
     * Un raid perdu a brûlé `building` : ses habitants campent au bord du village jusqu'à ce qu'il soit relevé, et les
     * arbres brûlés restent ({@link Traces#raid}).
     */
    public static void refugees(World world, Store<EntityStore> store, Village village, String building) {
        long day = GameClock.day(store);
        Random random = new Random();
        double angle = random.nextDouble() * Math.PI * 2;
        int r = Chantiers.layout(village) == null ? Villages.RADIUS : Chantiers.layout(village).radius();
        Camp c = new Camp("ref_" + Long.toString(System.currentTimeMillis(), 36));
        c.type = Type.REFUGEES;
        c.x = village.x() + (int) Math.round(Math.cos(angle) * (r + 10));
        c.z = village.z() + (int) Math.round(Math.sin(angle) * (r + 10));
        c.village = village.id();
        c.end = Long.MAX_VALUE;
        c.building = building;
        save(world, c);
        Traces.raid(world, village, day);
        Chantiers.announce(world, village, Message.translation(KEYS + "refugees").param("village", village.name()), null,
                NotificationStyle.Warning);
    }

    private static void end(World world, Store<EntityStore> store, Camp c, Village v) {
        removeCampers(store, c.id);
        List<Ref<EntityStore>> raiders = RAIDERS.remove(c.id);
        if (raiders != null) {
            raiders.forEach(r -> WorldLife.remove(store, r));
        }
        if (c.placed && !Sites.restore(world, c.structure())) {
            return; // pas chargé : on rendra les blocs plus tard
        }
        WorldLife.registry(world).put(WorldLifeRegistry.Part.CAMPS, c.id, null);
        if (v != null) {
            Chantiers.announce(world, v, Message.translation(KEYS + "gone." + c.type.key()).param("village", v.name()), null,
                    NotificationStyle.Default);
        }
    }

    /** Lève un campement tout de suite (commande). */
    public static void endNow(World world, Store<EntityStore> store, Camp c) {
        end(world, store, c, Villages.registry(world).byId(c.village));
    }

    // ---- Pas ----

    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        for (Camp c : all(world)) {
            Village v = Villages.registry(world).byId(c.village);
            if (v == null) {
                end(world, store, c, null);
                continue;
            }
            if (!c.placed && WorldLife.near(players, c.x, c.z, Traces.PLACE_RANGE) && Sites.loaded(world, c.x, c.z)) {
                place(world, store, c, v.people());
            }
            boolean near = c.placed && WorldLife.near(players, c.x, c.z, WorldLife.REAL_RANGE);
            List<Ref<EntityStore>> campers = CAMPERS_OF.get(c.id);
            if (campers != null) {
                campers.removeIf(r -> !r.isValid());
            }
            if (!near) {
                removeCampers(store, c.id);
            } else if ((campers == null || campers.isEmpty()) && WorldLife.budget(world, CAMPERS)) {
                spawnCampers(world, store, c, v.people());
            }
            if (c.quest == 1) {
                List<Ref<EntityStore>> band = RAIDERS.get(c.id);
                if (band == null) {
                    c.quest = 0; // serveur relancé pendant l'attaque : on pourra la refaire
                    save(world, c);
                } else {
                    band.removeIf(r -> !r.isValid());
                    if (band.isEmpty()) {
                        RAIDERS.remove(c.id);
                        c.quest = 2;
                        save(world, c);
                        defended(world, store, c, v);
                    }
                }
            }
        }
    }

    private static void place(World world, Store<EntityStore> store, Camp c, People people) {
        String[] pool = prefabs(c.type, Math.max(1, people.zone()));
        boolean any = false;
        for (int i = 0; i < pool.length; i++) {
            int x = c.x + i * 9;
            int ground = Sites.ground(world, pool[i], x, c.z, 0);
            if (ground != Terrain.NONE && Sites.pasteTemporary(world, store, c.structure(), pool[i], x, ground, c.z, 0)) {
                any = true;
            }
        }
        if (any) {
            c.placed = true;
            save(world, c);
        }
    }

    private static void spawnCampers(World world, Store<EntityStore> store, Camp c, People people) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        Random random = new Random();
        for (int i = 0; i < CAMPERS; i++) {
            Vector3d at = WorldLife.ground(world, c.x + random.nextInt(-6, 7), c.z + 6 + random.nextInt(-3, 4), 8);
            Ref<EntityStore> ref = at == null ? null : WorldLife.spawn(store, camperRole(people), at, (float) random.nextDouble(-Math.PI, Math.PI));
            if (ref == null) {
                continue;
            }
            WorldLife.talker(ref, Camps::talk);
            WorldLife.side(ref, "CP:" + c.id, 0);
            CAMP_OF.put(ref, c.id);
            out.add(ref);
        }
        CAMPERS_OF.put(c.id, out);
    }

    private static void removeCampers(Store<EntityStore> store, String id) {
        List<Ref<EntityStore>> refs = CAMPERS_OF.remove(id);
        if (refs != null) {
            for (Ref<EntityStore> r : refs) {
                CAMP_OF.remove(r);
                WorldLife.remove(store, r);
            }
        }
    }

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Camp c = of(world, npc);
        Dialogue dialogue = c == null ? null : Dialogue.get(c.type.dialogue());
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    // ---- Quêtes (effets de dialogue) ----

    /** Ce que le campement demande et ce qu'il donne : {objet demandé, nombre, objet donné, nombre}. */
    static String[] trade(Type type) {
        return switch (type) {
            case HUNTERS -> new String[] {"Food_Wildmeat_Raw", "5", "Ingredient_Leather_Light", "3"};
            case WOODCUTTERS -> new String[] {"Food_Bread", "3", "Ingredient_Tree_Sap", "4"};
            default -> null;
        };
    }

    /** Le joueur remet ce que le campement demande (une fois par campement). */
    static boolean turnIn(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Camp c) {
        String[] t = trade(c.type);
        Village v = Villages.registry(world).byId(c.village);
        if (t == null || v == null) {
            return false;
        }
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        if (data.hasFlag(FLAG + c.id)) {
            player.sendMessage(Message.translation(KEYS + "already"));
            return false;
        }
        int need = Integer.parseInt(t[1]);
        if (WorldLife.count(store, ref, t[0]::equals) < need) {
            player.sendMessage(Message.translation(KEYS + "missing").param("count", need)
                    .param("item", dev.nakasar.hytale.peuples.village.VillageBoard.itemName(t[0])));
            return false;
        }
        WorldLife.take(store, ref, t[0]::equals, need);
        data.setFlag(FLAG + c.id, true);
        Requests.give(store, ref, new ItemStack(t[2], Integer.parseInt(t[3])));
        Requests.give(store, ref, new ItemStack(v.people().favorItem(), 1));
        Reputations.change(world, store, ref, player, v, REPUTATION, KEYS + "reason");
        player.sendMessage(Message.translation(KEYS + "thanks"));
        return true;
    }

    /** Les prospecteurs demandent de l'aide : une bande arrive (une fois par campement). */
    static boolean defend(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Camp c) {
        Village v = Villages.registry(world).byId(c.village);
        if (v == null || c.quest != 0) {
            player.sendMessage(Message.translation(KEYS + (c.quest == 1 ? "underAttack" : "already")));
            return false;
        }
        String[] ranks = Raids.raiders(v.people());
        Random random = new Random();
        List<Ref<EntityStore>> band = new ArrayList<>();
        double angle = random.nextDouble() * Math.PI * 2;
        int bx = c.x + (int) Math.round(Math.cos(angle) * 24);
        int bz = c.z + (int) Math.round(Math.sin(angle) * 24);
        for (int i = 0; i < 4; i++) {
            Vector3d at = WorldLife.ground(world, bx + random.nextInt(-3, 4), bz + random.nextInt(-3, 4), 6);
            Ref<EntityStore> r = at == null ? null : WorldLife.spawn(store, ranks[i == 3 ? 1 : 0], at, 0f);
            if (r == null) {
                continue;
            }
            WorldLife.side(r, "CP:" + c.id, 1);
            WorldLife.leash(store, r, new Vector3d(c.x, at.y(), c.z));
            band.add(r);
        }
        if (band.isEmpty()) {
            return false;
        }
        RAIDERS.put(c.id, band);
        c.quest = 1;
        save(world, c);
        WorldLife.announce(world, store, c.x, c.z, Ambushes.WITNESS, Message.translation(KEYS + "attack"), NotificationStyle.Danger);
        return true;
    }

    private static void defended(World world, Store<EntityStore> store, Camp c, Village v) {
        for (PlayerRef p : WorldLife.playersNear(world, store, c.x, c.z, 48)) {
            Ref<EntityStore> ref = p.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            Requests.give(store, ref, new ItemStack("Ore_Iron", 6));
            Requests.give(store, ref, new ItemStack(v.people().favorItem(), 1));
            Reputations.change(world, store, ref, p, v, REPUTATION, KEYS + "reason");
            Message m = Message.translation(KEYS + "defended");
            p.sendMessage(m);
            NotificationUtil.sendNotification(p.getPacketHandler(), m, NotificationStyle.Success);
        }
    }

    /** Don de nourriture aux réfugiés : essor du village et réputation. */
    static boolean donate(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Camp c) {
        Village v = Villages.registry(world).byId(c.village);
        if (v == null) {
            return false;
        }
        int given = WorldLife.take(store, ref, WorldLife::isFood, DONATION_MAX);
        if (given <= 0) {
            player.sendMessage(Message.translation(KEYS + "noFood"));
            return false;
        }
        Villages.addEssor(v, Math.max(1, given / 2));
        Reputations.change(world, store, ref, player, v, given * 2, KEYS + "donationReason");
        player.sendMessage(Message.translation(KEYS + "donated").param("count", given).param("village", v.name()));
        return true;
    }

    static boolean shop(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Camp c) {
        Village v = Villages.registry(world).byId(c.village);
        return v != null && dev.nakasar.hytale.peuples.reputation.Shops.open(store, ref, player, v, Travellers.shop(v.people()));
    }

    public static void clearAll() {
        CAMPERS_OF.clear();
        CAMP_OF.clear();
        RAIDERS.clear();
    }
}
