package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventRecord;
import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventsWorldConfig;
import com.hypixel.hytale.builtin.adventure.worldevents.action.EventStartAction;
import com.hypixel.hytale.builtin.adventure.worldevents.action.EventStopAction;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.boss.Telegraphs;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Étape 6 : le calendrier du monde. Trois rendez-vous, chacun un évènement de monde vanilla (titre et compte à rebours
 * sur la carte, lieu donné par {@link WorldLocationCondition}) :
 * <ul>
 *   <li>Fête des moissons, tous les {@value #FEAST_EVERY} jours à {@value #FEAST_HOUR} h, dans les villages qui ont
 *       une ferme, un potager ou un enclos au niveau 2 : l'hôte de la fête prend les offrandes de nourriture, dont la
 *       réputation compte double ({@value #FEAST_SECONDS} s).</li>
 *   <li>Migration, tous les {@value #MIGRATION_EVERY} jours au matin : un troupeau de la zone traverse les terres près
 *       d'un village. Tout près, une bête peut charger : ligne rouge de {@value #STAMPEDE_LENGTH} sur
 *       {@value #STAMPEDE_WIDTH} blocs (la ligne d'annonce du mod, même taille que le coup), {@value #STAMPEDE_DAMAGE}
 *       dégâts. Chasser une bête du troupeau rapporte viande et peau.</li>
 *   <li>Foire, tous les {@value #FAIR_EVERY} jours à {@value #FAIR_HOUR} h, au plus grand village (palier 2 ou plus)
 *       d'un peuple, à tour de rôle : étals vanilla posés pour la journée, marchands des autres peuples, course aux
 *       drapeaux de l'hôte ({@value #RACE_SECONDS} s, une fois par foire).</li>
 * </ul>
 * L'état durable ({@link WorldLifeRegistry.Part#CALENDAR}) ne garde que les derniers jours ; un rendez-vous coupé par un
 * redémarrage s'arrête (ses étals sont rendus au démarrage suivant).
 */
public final class Calendar {

    public static final int FEAST_EVERY = 7;
    public static final int FEAST_HOUR = 18;
    public static final int FEAST_SECONDS = 1200;
    public static final int FEAST_OFFERINGS = 10;
    public static final int MIGRATION_EVERY = 10;
    public static final int MIGRATION_SECONDS = 1200;
    public static final int MIGRATION_DISTANCE = 260;
    public static final int FAIR_EVERY = 14;
    public static final int FAIR_HOUR = 9;
    public static final int FAIR_SECONDS = 1800;
    public static final int RACE_SECONDS = 90;
    public static final int RACE_FLAGS = 3;
    public static final double STAMPEDE_LENGTH = 14;
    public static final double STAMPEDE_WIDTH = 3;
    public static final float STAMPEDE_SECONDS = 1.6f;
    public static final float STAMPEDE_DAMAGE = 18f;
    public static final int STAMPEDE_RANGE = 20;
    public static final long STAMPEDE_COOLDOWN_MS = 25_000L;
    /** Vitesse de la course du meneur (blocs/s) et poussée sur le côté des joueurs traversés. */
    public static final double STAMPEDE_SPEED = 14;
    public static final double STAMPEDE_KNOCKBACK = 7;
    /** Plus grand pas de la course entre deux tests (blocs) : un tick long ne doit traverser ni mur ni joueur. */
    private static final double CHARGE_STEP = 0.5;
    public static final String KEYS = WorldLife.KEYS + "calendar.";
    public static final String FEAST_EVENT = "Nakasar_Peuples_Harvest";
    public static final String FAIR_EVENT = "Nakasar_Peuples_Fair";
    public static final String MIGRATION_EVENT = "Nakasar_Peuples_Migration";
    public static final String FEAST_DIALOGUE = "Monde_Fete";
    public static final String FAIR_DIALOGUE = "Monde_Foire";
    public static final String RACE_FLAG = "Furniture_Human_Ruins_Banner";
    private static final String FAIR_STRUCTURE = "fair:";
    private static final String RACE_STRUCTURE = "race:";

    /** Un rendez-vous en cours (pas sauvé). */
    private static final class Gathering {
        final String kind;
        final String village;
        final long end;
        final UUID event = UUID.randomUUID();
        boolean eventRunning;
        Ref<EntityStore> host;
        final List<Ref<EntityStore>> merchants = new ArrayList<>();
        final Set<String> raced = new LinkedHashSet<>();
        boolean stalls;

        Gathering(String kind, String village, long end) {
            this.kind = kind;
            this.village = village;
            this.end = end;
        }
    }

    /** Le troupeau en route (pas sauvé). */
    private static final class Herd {
        final String species;
        final Routes.Path path;
        double at;
        /** Bêtes encore vivantes (une bête chassée ne revient pas). */
        int count;
        final int y;
        final long end;
        final UUID event = UUID.randomUUID();
        boolean eventRunning;
        Telegraphs.Strip charge;
        /** La course du meneur, après la zone rouge. */
        Run run;
        long nextCharge;

        Herd(String species, Routes.Path path, int count, int y, long end) {
            this.species = species;
            this.path = path;
            this.count = count;
            this.y = y;
            this.end = end;
        }

        String walkKey() {
            return "H:" + event;
        }
    }

    private static final Map<String, Gathering> GATHERINGS = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, String> HOST_OF = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<Ref<EntityStore>, String> MERCHANT_SHOP = Collections.synchronizedMap(new IdentityHashMap<>());
    private static volatile Herd herd;
    private static boolean restored;

    private Calendar() {
    }

    // ---- Jours ----

    /** Prochain jour (≥ `day`) du rendez-vous qui revient tous les `every` jours. */
    public static long next(long day, int every, int offset) {
        long d = day;
        while (Math.floorMod(d - offset, (long) every) != 0) {
            d++;
        }
        return d;
    }

    static boolean feastDay(long day) {
        return Math.floorMod(day - 3, (long) FEAST_EVERY) == 0;
    }

    static boolean fairDay(long day) {
        return Math.floorMod(day - 7, (long) FAIR_EVERY) == 0;
    }

    static boolean migrationDay(long day) {
        return Math.floorMod(day - 5, (long) MIGRATION_EVERY) == 0;
    }

    // ---- Pas ----

    static void step(World world, Store<EntityStore> store, List<Vector3d> players, float dt) {
        WorldLifeRegistry r = WorldLife.registry(world);
        long day = GameClock.day(store);
        int hour = GameClock.hour(store);
        if (!restored) {
            restored = true;
            for (String id : new ArrayList<>(r.part(WorldLifeRegistry.Part.STRUCTURES).keySet())) {
                if (id.startsWith(FAIR_STRUCTURE) || id.startsWith(RACE_STRUCTURE)) {
                    Sites.release(world, id); // foire coupée par un redémarrage : rendue dès que la zone est chargée
                }
            }
        }
        if (feastDay(day) && hour >= FEAST_HOUR && r.getLong(WorldLifeRegistry.Part.CALENDAR, "feast", Long.MIN_VALUE) != day) {
            r.put(WorldLifeRegistry.Part.CALENDAR, "feast", Long.toString(day));
            startFeast(world, store);
        }
        if (fairDay(day) && hour >= FAIR_HOUR && hour < GameClock.DUSK
                && r.getLong(WorldLifeRegistry.Part.CALENDAR, "fair", Long.MIN_VALUE) != day) {
            r.put(WorldLifeRegistry.Part.CALENDAR, "fair", Long.toString(day));
            startFair(world, store, day);
        }
        if (migrationDay(day) && hour >= GameClock.MORNING + 1 && hour < 16
                && r.getLong(WorldLifeRegistry.Part.CALENDAR, "migration", Long.MIN_VALUE) != day) {
            r.put(WorldLifeRegistry.Part.CALENDAR, "migration", Long.toString(day));
            startMigration(world, store, new Random());
        }
        long now = System.currentTimeMillis();
        for (Gathering g : new ArrayList<>(GATHERINGS.values())) {
            Village v = Villages.registry(world).byId(g.village);
            if (v == null || now >= g.end) {
                end(world, store, g, v);
            } else {
                stepGathering(world, store, g, v, players);
            }
        }
        stepHerd(world, store, players, dt);
    }

    // ---- Fête des moissons ----

    static boolean hasFarm(Village v) {
        for (WorkshopState w : v.workshops()) {
            String id = w.id();
            if (w.level() >= 2 && (id.contains("Ferme") || id.contains("Potager") || id.contains("Enclos") || id.contains("Rizi"))) {
                return true;
            }
        }
        return false;
    }

    /** Lance la fête des moissons (aussi /monde) ; rend le nombre de villages en fête. */
    public static int startFeast(World world, Store<EntityStore> store) {
        int n = 0;
        for (Village v : Villages.registry(world).all()) {
            if (!hasFarm(v) || GATHERINGS.containsKey("feast:" + v.id())) {
                continue;
            }
            Gathering g = new Gathering("feast", v.id(), System.currentTimeMillis() + FEAST_SECONDS * 1000L);
            GATHERINGS.put("feast:" + v.id(), g);
            g.eventRunning = startEvent(world, store, FEAST_EVENT, g.event, new Vector3i(v.x(), v.y(), v.z()));
            Chantiers.announce(world, v, Message.translation(KEYS + "feast.start").param("village", v.name()), null, NotificationStyle.Success);
            n++;
        }
        return n;
    }

    /** Offrande de nourriture à la fête : réputation doublée (2 par objet, ×2), un point d'essor par cinq objets. */
    static boolean feastOffering(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village v) {
        if (v == null || !GATHERINGS.containsKey("feast:" + v.id())) {
            player.sendMessage(Message.translation(KEYS + "feast.over"));
            return false;
        }
        // Au plus FEAST_OFFERINGS offrandes par joueur et par fête.
        long day = GameClock.day(store);
        String what = "feast:" + v.id();
        int left = WorldLife.allowance(player.getUuid(), what, day, FEAST_OFFERINGS);
        if (left <= 0) {
            player.sendMessage(Message.translation(KEYS + "feast.enough"));
            return false;
        }
        int given = WorldLife.take(store, ref, WorldLife::isFood, left);
        if (given <= 0) {
            player.sendMessage(Message.translation(Camps.KEYS + "noFood"));
            return false;
        }
        WorldLife.spend(player.getUuid(), what, day, given);
        Villages.addEssor(v, given / 5);
        Reputations.change(world, store, ref, player, v, given * 4, KEYS + "feast.reason");
        player.sendMessage(Message.translation(KEYS + "feast.thanks").param("count", given));
        return true;
    }

    // ---- Foire ----

    /** Lance la foire (aussi /monde) ; null si aucun village ne peut l'accueillir. */
    public static Village startFair(World world, Store<EntityStore> store, long day) {
        List<People> peoples = new ArrayList<>();
        for (People p : People.values()) {
            if (host(world, p) != null) {
                peoples.add(p);
            }
        }
        if (peoples.isEmpty()) {
            return null;
        }
        People turn = peoples.get((int) Math.floorMod(Math.floorDiv(day, (long) FAIR_EVERY), (long) peoples.size()));
        Village v = host(world, turn);
        if (v == null || GATHERINGS.containsKey("fair:" + v.id())) {
            return null;
        }
        Gathering g = new Gathering("fair", v.id(), System.currentTimeMillis() + FAIR_SECONDS * 1000L);
        GATHERINGS.put("fair:" + v.id(), g);
        g.eventRunning = startEvent(world, store, FAIR_EVENT, g.event, new Vector3i(v.x(), v.y(), v.z()));
        Message m = Message.translation(KEYS + "fair.start").param("village", v.name());
        for (Village other : Villages.registry(world).all()) {
            Chantiers.announce(world, other, m, null, NotificationStyle.Success);
        }
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (monde vivant) : foire à %s", v.name());
        return v;
    }

    /** Le plus grand village (palier 2 ou plus) du peuple, ou null. */
    static Village host(World world, People people) {
        Village best = null;
        for (Village v : Villages.registry(world).all()) {
            if (v.people() == people && v.tier() >= 2 && (best == null || v.tier() > best.tier()
                    || v.tier() == best.tier() && v.essor() > best.essor())) {
                best = v;
            }
        }
        return best;
    }

    /** Village de la prochaine foire et dans combien de jours (rumeurs). */
    static Object[] nextFair(World world, long day) {
        long d = next(day, FAIR_EVERY, 7);
        List<People> peoples = new ArrayList<>();
        for (People p : People.values()) {
            if (host(world, p) != null) {
                peoples.add(p);
            }
        }
        if (peoples.isEmpty()) {
            return null;
        }
        People turn = peoples.get((int) Math.floorMod(Math.floorDiv(d, (long) FAIR_EVERY), (long) peoples.size()));
        return new Object[] {host(world, turn), d - day};
    }

    private static void stepGathering(World world, Store<EntityStore> store, Gathering g, Village v, List<Vector3d> players) {
        boolean near = WorldLife.near(players, v.x(), v.z(), WorldLife.REAL_RANGE + 32);
        int radius = radius(v);
        if (g.kind.equals("fair") && !g.stalls && near) {
            String[] stalls = {"Orbis/Enkindled/Deco_Stalls/Deco_Stalls_001", "Orbis/Enkindled/Deco_Stalls/Deco_Stalls_002",
                    "Orbis/Enkindled/Deco_Carts/Deco_Carts_001"};
            for (int i = 0; i < stalls.length; i++) {
                double a = Math.PI / 6 + i * (Math.PI * 2 / 3);
                int x = v.x() + (int) Math.round(Math.cos(a) * (radius + 8));
                int z = v.z() + (int) Math.round(Math.sin(a) * (radius + 8));
                int ground = Sites.ground(world, stalls[i], x, z, 0);
                if (ground != dev.nakasar.hytale.peuples.village.Terrain.NONE) {
                    Sites.pasteTemporary(world, store, FAIR_STRUCTURE + v.id(), stalls[i], x, ground, z, 0);
                }
            }
            g.stalls = true;
        }
        if (!near) {
            removeNpcs(store, g);
            return;
        }
        if ((g.host == null || !g.host.isValid()) && WorldLife.budget(world, 1)) {
            Vector3d at = WorldLife.ground(world, v.x() - 3, v.z() - 5, 6);
            g.host = at == null ? null : WorldLife.spawn(store, hostRole(v.people()), at, 0f);
            if (g.host != null) {
                WorldLife.talker(g.host, Calendar::talk);
                HOST_OF.put(g.host, g.kind + ":" + v.id());
            }
        }
        if (g.kind.equals("fair")) {
            g.merchants.removeIf(r -> !r.isValid());
            if (g.merchants.isEmpty()) {
                int i = 0;
                for (People p : People.values()) {
                    if (p == v.people() || i >= 3 || !present(world, p) || !WorldLife.budget(world, 1)) {
                        continue;
                    }
                    double a = Math.PI / 6 + i * (Math.PI * 2 / 3);
                    Vector3d at = WorldLife.ground(world, v.x() + (int) Math.round(Math.cos(a) * (radius + 4)),
                            v.z() + (int) Math.round(Math.sin(a) * (radius + 4)), 6);
                    Ref<EntityStore> ref = at == null ? null : WorldLife.spawn(store, Travellers.peddlerRole(p), at, 0f);
                    if (ref != null) {
                        String shop = Travellers.shop(p);
                        MERCHANT_SHOP.put(ref, shop);
                        WorldLife.talker(ref, (w, s, pl, pr, npc) -> dev.nakasar.hytale.peuples.reputation.Shops.open(s, pl, pr, v, shop));
                        g.merchants.add(ref);
                    }
                    i++;
                }
            }
        }
    }

    private static boolean present(World world, People p) {
        for (Village v : Villages.registry(world).all()) {
            if (v.people() == p) {
                return true;
            }
        }
        return false;
    }

    private static int radius(Village v) {
        VillageLayout layout = Chantiers.layout(v);
        return layout == null ? Villages.RADIUS : layout.radius();
    }

    public static String hostRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Host";
    }

    private static void removeNpcs(Store<EntityStore> store, Gathering g) {
        if (g.host != null) {
            HOST_OF.remove(g.host);
            WorldLife.remove(store, g.host);
            g.host = null;
        }
        for (Ref<EntityStore> r : g.merchants) {
            MERCHANT_SHOP.remove(r);
            WorldLife.remove(store, r);
        }
        g.merchants.clear();
    }

    private static void end(World world, Store<EntityStore> store, Gathering g, Village v) {
        GATHERINGS.remove(g.kind + ":" + g.village);
        removeNpcs(store, g);
        if (g.eventRunning) {
            stopEvent(store, g.event);
        }
        if (g.kind.equals("fair")) {
            Sites.release(world, FAIR_STRUCTURE + g.village);
        }
        if (v != null) {
            Chantiers.announce(world, v, Message.translation(KEYS + g.kind + ".end").param("village", v.name()), null, NotificationStyle.Default);
        }
    }

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        String key = HOST_OF.get(npc);
        Dialogue dialogue = key == null ? null : Dialogue.get(key.startsWith("fair:") ? FAIR_DIALOGUE : FEAST_DIALOGUE);
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    /** Village de l'hôte (fête ou foire) à qui parle le joueur. */
    static Village hostVillage(World world, Ref<EntityStore> npc) {
        String key = npc == null ? null : HOST_OF.get(npc);
        return key == null ? null : Villages.registry(world).byId(key.substring(key.indexOf(':') + 1));
    }

    /** Course aux drapeaux de la foire (une fois par joueur et par foire). */
    static boolean race(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village v) {
        Gathering g = v == null ? null : GATHERINGS.get("fair:" + v.id());
        if (g == null) {
            player.sendMessage(Message.translation(KEYS + "fair.over"));
            return false;
        }
        if (g.raced.contains(player.getUuid().toString()) || Hunts.playing(player.getUuid())) {
            player.sendMessage(Message.translation(KEYS + "race.already"));
            return false;
        }
        g.raced.add(player.getUuid().toString());
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int radius = radius(v);
        List<Hunts.Spot> spots = new ArrayList<>();
        String id = RACE_STRUCTURE + player.getUuid();
        for (int i = 0; i < RACE_FLAGS; i++) {
            double a = random.nextDouble() * Math.PI * 2;
            int d = radius + 10 + random.nextInt(25);
            Vector3d at = WorldLife.ground(world, v.x() + (int) Math.round(Math.cos(a) * d), v.z() + (int) Math.round(Math.sin(a) * d), 6);
            if (at == null) {
                continue;
            }
            int bx = (int) Math.floor(at.x());
            int by = (int) Math.floor(at.y());
            int bz = (int) Math.floor(at.z());
            String structure = id + ":" + i;
            if (!Sites.setTemporary(world, structure, bx, by, bz, RACE_FLAG, 0)) {
                continue;
            }
            spots.add(new Hunts.Spot(null, at, () -> Sites.release(world, structure)));
            player.sendMessage(Message.translation(KEYS + "race.flag").param("n", i + 1)
                    .param("distance", d).param("direction",
                            Message.translation(Villages.MESSAGES + "dir." + Requests.direction(bx - v.x(), bz - v.z()))));
        }
        if (spots.isEmpty()) {
            return false;
        }
        player.sendMessage(Message.translation(KEYS + "race.start").param("count", spots.size()).param("seconds", RACE_SECONDS));
        Hunts.start(id, player, spots, RACE_SECONDS, KEYS + "race.found", (w, s, p, won) -> {
            if (p == null) {
                return;
            }
            Message m = Message.translation(KEYS + (won ? "race.won" : "race.lost"));
            p.sendMessage(m);
            NotificationUtil.sendNotification(p.getPacketHandler(), m, won ? NotificationStyle.Success : NotificationStyle.Default);
            Ref<EntityStore> pr = p.getReference();
            if (won && pr != null && pr.isValid()) {
                Requests.give(s, pr, new ItemStack(v.people().favorItem(), 2));
                Reputations.change(w, s, pr, p, v, 15, KEYS + "race.reason");
            }
        });
        return true;
    }

    // ---- Migration ----

    /** Espèces de troupeau par zone : {meneur, suiveur}. */
    static String[] species(int zone, Random random) {
        return switch (zone) {
            case 2 -> new String[] {"Camel", "Camel_Calf"};
            case 3 -> random.nextBoolean() ? new String[] {"Moose_Bull", "Moose_Cow"} : new String[] {"Mouflon", "Mouflon_Lamb"};
            case 4 -> new String[] {"Antelope", "Antelope"};
            default -> random.nextBoolean() ? new String[] {"Bison", "Bison_Calf"} : new String[] {"Deer_Stag", "Deer_Doe"};
        };
    }

    public static String herdRole(String species) {
        return "Nakasar_Peuples_Herd_" + species;
    }

    /** Lance la migration près d'un village tiré au hasard (aussi /monde) ; null s'il n'y a aucun village. */
    public static Village startMigration(World world, Store<EntityStore> store, Random random) {
        if (herd != null) {
            return null;
        }
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        if (villages.isEmpty()) {
            return null;
        }
        Village v = villages.get(random.nextInt(villages.size()));
        double a = random.nextDouble() * Math.PI * 2;
        double b = a + Math.PI + random.nextDouble(-0.6, 0.6);
        double fx = v.x() + Math.cos(a) * MIGRATION_DISTANCE;
        double fz = v.z() + Math.sin(a) * MIGRATION_DISTANCE;
        double tx = v.x() + Math.cos(b) * MIGRATION_DISTANCE;
        double tz = v.z() + Math.sin(b) * MIGRATION_DISTANCE;
        // Le troupeau contourne le village : la ligne passe à côté du cœur.
        double mx = (fx + tx) / 2;
        double mz = (fz + tz) / 2;
        double off = Math.hypot(mx - v.x(), mz - v.z());
        if (off < Villages.RADIUS + 40) {
            double side = a + Math.PI / 2;
            fx += Math.cos(side) * 120;
            fz += Math.sin(side) * 120;
            tx += Math.cos(side) * 120;
            tz += Math.sin(side) * 120;
        }
        String species = String.join("/", species(v.people().zone(), random));
        Routes.Path path = Routes.path(world, fx, fz, tx, tz);
        Herd h = new Herd(species, path, 6 + random.nextInt(3), v.y(), System.currentTimeMillis() + MIGRATION_SECONDS * 1000L);
        herd = h;
        double[] mid = path.point(path.length() / 2);
        h.eventRunning = startEvent(world, store, MIGRATION_EVENT, h.event, new Vector3i((int) mid[0], v.y(), (int) mid[1]));
        Chantiers.announce(world, v, Message.translation(KEYS + "migration.start").param("village", v.name())
                .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(fx - v.x(), fz - v.z()))),
                null, NotificationStyle.Default);
        return v;
    }

    private static void stepHerd(World world, Store<EntityStore> store, List<Vector3d> players, float dt) {
        Herd h = herd;
        if (h == null) {
            return;
        }
        if (System.currentTimeMillis() >= h.end || h.at >= h.path.length() - Walk.ARRIVE || h.count <= 0) {
            Walk.end(store, h.walkKey());
            if (h.eventRunning) {
                stopEvent(store, h.event);
            }
            herd = null;
            return;
        }
        String[] sp = h.species.split("/");
        Walk walk = Walk.of(h.walkKey());
        h.at = walk.step(world, store, players, h.path, h.at, dt, h.count, h.charge == null, h.y, (i, at, yaw) -> {
            Ref<EntityStore> ref = WorldLife.spawn(store, herdRole(i % 3 == 2 ? sp[1] : sp[0]), at, yaw);
            WorldLife.mortal(ref, (w, npc, where, killer) -> {
                h.count = Math.max(0, h.count - 1);
                hunted(w, npc, where, killer);
            });
            return ref;
        });
        // Charge : sous les yeux d'un joueur tout proche, le meneur fonce sur une ligne d'annonce. Elle se résout à
        // chaque image (stepCharge, appelé par WorldLifeSystem), pas au pas d'une seconde : les dégâts tombent à la fin
        // exacte de la zone rouge.
        long now = System.nanoTime();
        List<Ref<EntityStore>> live = walk.alive();
        if (h.charge != null) {
            return;
        }
        if (live.isEmpty() || System.currentTimeMillis() < h.nextCharge) {
            return;
        }
        Vector3d lead = Requests.position(store, live.get(0));
        if (lead == null || !WorldLife.near(players, lead.x(), lead.z(), STAMPEDE_RANGE)) {
            return;
        }
        double[] d = h.path.dir(h.at);
        double facing = Math.atan2(d[1], d[0]);
        h.charge = new Telegraphs.Strip(new Vector3d(lead.x(), Math.floor(lead.y()), lead.z()), facing, STAMPEDE_LENGTH, STAMPEDE_WIDTH,
                now, STAMPEDE_SECONDS);
        h.charge.step(store, now);
    }

    /** Une bête du troupeau abattue par un joueur : viande et peau. */
    private static void hunted(World world, Ref<EntityStore> npc, Vector3d where, PlayerRef killer) {
        Ref<EntityStore> ref = killer == null ? null : killer.getReference();
        if (ref == null || !ref.isValid()) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        Requests.give(store, ref, new ItemStack("Food_Wildmeat_Raw", 2));
        Requests.give(store, ref, new ItemStack("Ingredient_Hide_Medium", 1));
    }

    /** Vrai pendant une charge annoncée ou en course (WorldLifeSystem appelle alors {@link #stepCharge} à chaque image). */
    static boolean charging() {
        Herd h = herd;
        return h != null && (h.charge != null || h.run != null);
    }

    /**
     * La ruée, image par image, comme la charge des boss de fractales ({@code Nakasar_Fractal_Charge}) : la zone rouge,
     * puis le meneur, figé ({@link Frozen}) et déplacé par le Java, fonce tout droit à {@value #STAMPEDE_SPEED} blocs/s
     * jusqu'au bout de la ligne. Les joueurs qu'il traverse dans la zone prennent {@value #STAMPEDE_DAMAGE} dégâts et
     * sont projetés sur le côté. Un mur ou un vide l'arrête net ; il suit le relief d'un bloc en montée, deux en descente.
     */
    static void stepCharge(World world, Store<EntityStore> store) {
        Herd h = herd;
        if (h == null) {
            return;
        }
        long now = System.nanoTime();
        if (h.run == null) {
            if (h.charge == null || !h.charge.step(store, now)) {
                return;
            }
            Walk walk = Walk.peek(h.walkKey());
            List<Ref<EntityStore>> live = walk == null ? List.of() : walk.alive();
            if (live.isEmpty() || !live.get(0).isValid()) {
                endCharge(store, h);
                return;
            }
            h.run = new Run(live.get(0), h.charge, now);
            store.ensureAndGetComponent(h.run.src, Frozen.getComponentType());
            return;
        }
        Run run = h.run;
        Vector3d at = run.src.isValid() ? Requests.position(store, run.src) : null;
        if (at == null) {
            endCharge(store, h);
            return;
        }
        double move = Math.min(STAMPEDE_SPEED * (now - run.last) / 1e9, STAMPEDE_LENGTH - run.travelled);
        run.last = now;
        ChunkStore chunks = world.getChunkStore();
        int steps = Math.max(1, (int) Math.ceil(move / CHARGE_STEP));
        Vector3d current = new Vector3d(at.x(), run.y, at.z());
        boolean stop = false;
        for (int i = 0; i < steps && !stop; i++) {
            double step = move / steps;
            double nx = current.x() + run.dx * step;
            double nz = current.z() + run.dz * step;
            Double ny = groundAhead(chunks, nx, run.y, nz);
            if (ny == null) {
                stop = true; // mur ou vide : il s'arrête net
                break;
            }
            run.y = ny;
            current = new Vector3d(nx, ny, nz);
            run.travelled += step;
            trample(world, store, h, run, current);
        }
        store.putComponent(run.src, Teleport.getComponentType(), new Teleport(current, new Rotation3f(0f, run.yaw, 0f)));
        if (stop || run.travelled >= STAMPEDE_LENGTH - 1e-3) {
            WorldLife.leash(store, run.src, current);
            endCharge(store, h);
        }
    }

    private static void endCharge(Store<EntityStore> store, Herd h) {
        if (h.run != null && h.run.src.isValid()) {
            store.tryRemoveComponent(h.run.src, Frozen.getComponentType()); // jamais figé après la course
        }
        h.run = null;
        h.charge = null;
        h.nextCharge = System.currentTimeMillis() + STAMPEDE_COOLDOWN_MS;
    }

    /** Hauteur des pieds en (x, z) en partant de `y` : un bloc de montée, deux de descente ; null (mur, vide). */
    private static Double groundAhead(ChunkStore chunks, double x, double y, double z) {
        int bx = (int) Math.floor(x);
        int bz = (int) Math.floor(z);
        int by = (int) Math.floor(y);
        for (int dy : new int[] {0, 1, -1, -2}) {
            int feet = by + dy;
            if (Blocks.solid(chunks, bx, feet - 1, bz) && !Blocks.solid(chunks, bx, feet, bz) && !Blocks.solid(chunks, bx, feet + 1, bz)) {
                return (double) feet;
            }
        }
        return null;
    }

    /** Les joueurs que le meneur traverse, dans la zone annoncée : dégâts, une fois chacun, et projetés sur le côté. */
    private static void trample(World world, Store<EntityStore> store, Herd h, Run run, Vector3d at) {
        DamageCause cause = DamageCause.getAssetMap().getAsset("Physical");
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d p = ref == null || !ref.isValid() ? null : Requests.position(store, ref);
            if (p == null || run.struck.contains(ref) || !run.strip.contains(p)
                    || Math.hypot(p.x() - at.x(), p.z() - at.z()) > STAMPEDE_WIDTH / 2 + Telegraphs.BODY
                    || p.y() - at.y() < -1 || p.y() - at.y() > 3) {
                continue;
            }
            run.struck.add(ref);
            if (cause != null) {
                DamageSystems.executeDamage(ref, store, new Damage(new Damage.EntitySource(run.src), cause, STAMPEDE_DAMAGE));
            }
            Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
            if (velocity != null) {
                double side = Math.signum(-(p.x() - at.x()) * run.dz + (p.z() - at.z()) * run.dx);
                side = side == 0 ? 1 : side;
                velocity.addInstruction(new Vector3d((-run.dz * side + run.dx * 0.5) * STAMPEDE_KNOCKBACK, 6,
                        (run.dx * side + run.dz * 0.5) * STAMPEDE_KNOCKBACK), null, ChangeVelocityType.Set);
            }
        }
    }

    /** Une course de ruée en cours. */
    private static final class Run {
        final Ref<EntityStore> src;
        final Telegraphs.Strip strip;
        final double dx;
        final double dz;
        final float yaw;
        final Set<Ref<EntityStore>> struck = Collections.newSetFromMap(new IdentityHashMap<>());
        double travelled;
        double y;
        long last;

        Run(Ref<EntityStore> src, Telegraphs.Strip strip, long now) {
            this.src = src;
            this.strip = strip;
            double f = strip.facing();
            this.dx = Math.cos(f);
            this.dz = Math.sin(f);
            this.yaw = (float) Math.atan2(-dx, -dz);
            this.y = strip.origin().y();
            this.last = now;
        }
    }

    // ---- Évènements de monde ----

    private static boolean startEvent(World world, Store<EntityStore> store, String id, UUID uuid, Vector3i at) {
        if (!WorldEventsWorldConfig.isEnabled(world)) {
            return false;
        }
        WorldLocationCondition.put(uuid, at);
        try {
            EventStartAction.startEvent(store, new WorldEventRecord(uuid, id, true));
            return true;
        } catch (RuntimeException e) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples (monde vivant) : évènement %s non lancé (%s)", id, e.getMessage());
            return false;
        }
    }

    private static void stopEvent(Store<EntityStore> store, UUID uuid) {
        WorldLocationCondition.remove(uuid);
        try {
            EventStopAction.stopEvent(store, uuid, (event, id) -> id.equals(event.uuid));
        } catch (RuntimeException e) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples (monde vivant) : évènement non arrêté (%s)", e.getMessage());
        }
    }

    /** Rendez-vous en cours (commande). */
    static List<String> running() {
        List<String> out = new ArrayList<>(GATHERINGS.keySet());
        if (herd != null) {
            out.add("migration:" + herd.species);
        }
        return out;
    }

    /** Arrête tout de suite les rendez-vous (commande). */
    public static void stopAll(World world, Store<EntityStore> store) {
        for (Gathering g : new ArrayList<>(GATHERINGS.values())) {
            end(world, store, g, Villages.registry(world).byId(g.village));
        }
        if (herd != null) {
            Walk.end(store, herd.walkKey());
            if (herd.eventRunning) {
                stopEvent(store, herd.event);
            }
            herd = null;
        }
    }

    /** Le PNJ n'est plus (retiré ou mort). */
    static void forget(Ref<EntityStore> ref) {
        HOST_OF.remove(ref);
        MERCHANT_SHOP.remove(ref);
    }

    public static void clearAll() {
        GATHERINGS.clear();
        HOST_OF.clear();
        MERCHANT_SHOP.clear();
        herd = null;
        restored = false;
    }
}
