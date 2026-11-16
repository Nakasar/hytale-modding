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
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.reputation.Shops;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les tournées des villages vers les lieux-dits (Kevin, 16 novembre 2026) : chaque matin, un marchand (ou une caravane
 * entre alliés) d'un village voisin part commercer dans un lieu-dit posé. Il marche de jour par la route à pied sec
 * ({@link Routes#path}), attend {@value #STAY_HOURS} heures de jeu sur la place du lieu-dit, puis rentre. Chaque
 * marcheur arrivé compte un passage au lieu-dit ({@link Links#pass}, clé {@code H:<id>}, sur 7 jours) : à
 * {@value Hamlets#LIVELY} passages, le lieu-dit est animé (troc élargi). Le retour apporte de l'essor au village.
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#HAMLET_TRIPS}) :
 * {@code id = lieu-dit|village|M ou C|étape (0 aller, 1 sur place, 2 retour)|blocs|marcheurs|fin du séjour (s de jeu)}.
 */
public final class HamletTrips {

    /** Tournées en cours au plus, par monde. */
    public static final int MAX_WORLD = 5;
    /** Un village part vers un lieu-dit à moins de ceci (blocs). */
    public static final int RANGE = 900;
    /** Chance qu'un lieu-dit libre voie venir un marchand chaque matin. */
    public static final double DEPARTURE_CHANCE = 0.4;
    /** Chance d'une caravane (trois porteurs) au lieu d'un marchand, entre villages non rivaux. */
    public static final double CARAVAN_CHANCE = 0.3;
    public static final int STAY_HOURS = 3;
    /** Essor rapporté au village : marchand, caravane (moins un par porteur perdu). */
    public static final int MERCHANT_ESSOR = 1;
    public static final int CARAVAN_ESSOR = 3;
    public static final String DIALOGUE = "Monde_Marchand_LieuDit";
    public static final String KEYS = Hamlets.KEYS + "trip.";

    public static final int OUT = 0;
    public static final int STAY = 1;
    public static final int BACK = 2;

    private static final String LAST = "~last:";

    /** Une tournée (état sauvé). */
    public static final class Trip {
        final String id;
        String hamlet;
        String village;
        boolean caravan;
        int leg;
        double at;
        int walkers;
        long until;

        Trip(String id) {
            this.id = id;
        }

        static Trip parse(String id, String v) {
            String[] p = v.split("\\|", -1);
            if (p.length < 7) {
                return null;
            }
            try {
                Trip t = new Trip(id);
                t.hamlet = p[0];
                t.village = p[1];
                t.caravan = "C".equals(p[2]);
                t.leg = Integer.parseInt(p[3]);
                t.at = Double.parseDouble(p[4]);
                t.walkers = Integer.parseInt(p[5]);
                t.until = Long.parseLong(p[6]);
                return t;
            } catch (NumberFormatException e) {
                return null;
            }
        }

        String format() {
            return hamlet + "|" + village + "|" + (caravan ? "C" : "M") + "|" + leg + "|" + String.format(Locale.ROOT, "%.1f", at)
                    + "|" + walkers + "|" + until;
        }

        String walkKey() {
            return "HT:" + id;
        }

        public String hamlet() {
            return hamlet;
        }

        public String village() {
            return village;
        }

        public boolean caravan() {
            return caravan;
        }

        public int leg() {
            return leg;
        }
    }

    private static final Map<Ref<EntityStore>, String> OWNER = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Routes par tournée et étape, recalculées quand les balises changent. */
    private static final Map<String, Routes.Path> PATHS = new ConcurrentHashMap<>();

    private HamletTrips() {
    }

    // ---- Registre ----

    public static List<Trip> all(World world) {
        List<Trip> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.HAMLET_TRIPS).entrySet()) {
            if (e.getKey().startsWith("~")) {
                continue;
            }
            Trip t = Trip.parse(e.getKey(), e.getValue());
            if (t != null) {
                out.add(t);
            }
        }
        return out;
    }

    public static Trip get(World world, String id) {
        String v = id == null ? null : WorldLife.registry(world).get(WorldLifeRegistry.Part.HAMLET_TRIPS, id);
        return v == null ? null : Trip.parse(id, v);
    }

    static void save(World world, Trip t) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.HAMLET_TRIPS, t.id, t.format());
    }

    static void drop(World world, Store<EntityStore> store, Trip t) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.HAMLET_TRIPS, t.id, null);
        Walk.end(store, t.walkKey());
        PATHS.remove(t.id + ":0");
        PATHS.remove(t.id + ":2");
    }

    /** Le village du dernier marchand arrivé au lieu-dit (ou null). */
    public static String lastVillage(World world, Hamlets.Place h) {
        return WorldLife.registry(world).get(WorldLifeRegistry.Part.HAMLET_TRIPS, LAST + h.id());
    }

    /** La tournée de ce PNJ (ou null). */
    public static Trip of(World world, Ref<EntityStore> npc) {
        String id = npc == null ? null : OWNER.get(npc);
        return id == null ? null : get(world, id);
    }

    static void forget(Ref<EntityStore> ref) {
        OWNER.remove(ref);
    }

    // ---- Départs ----

    /** Départs du matin (une fois par jour de jeu). */
    static void morning(World world, Store<EntityStore> store, Random random) {
        List<Trip> current = all(world);
        int count = current.size();
        List<Hamlets.Place> places = new ArrayList<>(Hamlets.all(world));
        Collections.shuffle(places, random);
        for (Hamlets.Place h : places) {
            if (count >= MAX_WORLD) {
                break;
            }
            if (h.stage() != Hamlets.BUILT || busy(current, h) || random.nextDouble() >= DEPARTURE_CHANCE) {
                continue;
            }
            Village from = pickVillage(world, h, random);
            if (from == null) {
                continue;
            }
            Village home = Hamlets.village(world, h);
            boolean rival = home != null && home != from && Relations.value(world, from, home) <= Relations.RIVAL;
            if (rival) {
                continue; // on ne va pas commercer chez les gens d'un village rival
            }
            if (start(world, h, from, random.nextDouble() < CARAVAN_CHANCE) != null) {
                count++;
            }
        }
    }

    private static boolean busy(List<Trip> current, Hamlets.Place h) {
        for (Trip t : current) {
            if (t.hamlet.equals(h.id())) {
                return true;
            }
        }
        return false;
    }

    /** Un village à moins de {@value #RANGE} blocs du lieu-dit, le plus proche ayant plus de chances. */
    static Village pickVillage(World world, Hamlets.Place h, Random random) {
        List<Village> near = new ArrayList<>();
        List<Double> weights = new ArrayList<>();
        double total = 0;
        for (Village v : Villages.registry(world).all()) {
            double d = Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z()));
            if (d <= RANGE) {
                double w = 1.0 / Math.max(100, d);
                near.add(v);
                weights.add(w);
                total += w;
            }
        }
        if (near.isEmpty()) {
            return null;
        }
        double r = random.nextDouble() * total;
        for (int i = 0; i < near.size(); i++) {
            r -= weights.get(i);
            if (r < 0) {
                return near.get(i);
            }
        }
        return near.get(near.size() - 1);
    }

    /** Fait partir une tournée (commande, départs du matin) ; null si le lieu-dit en a déjà une. */
    public static Trip start(World world, Hamlets.Place h, Village from, boolean caravan) {
        if (busy(all(world), h)) {
            return null;
        }
        Trip t = new Trip(Long.toString(System.currentTimeMillis(), 36) + Integer.toString(new Random().nextInt(1296), 36));
        t.hamlet = h.id();
        t.village = from.id();
        t.caravan = caravan;
        t.leg = OUT;
        t.walkers = caravan ? 3 : 1;
        save(world, t);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (monde vivant) : %s de %s vers le lieu-dit %s", caravan ? "caravane" : "marchand",
                from.name(), h.id());
        return t;
    }

    // ---- Marche ----

    /** Route de l'étape en cours (aller : cœur du village → place du lieu-dit ; retour : l'inverse). */
    static Routes.Path path(World world, Trip t, Village v, Hamlets.Place h, boolean fresh) {
        String key = t.id + ":" + t.leg;
        int version = Villages.registry(world).beaconVersion();
        Routes.Path p = fresh ? null : PATHS.get(key);
        if (p == null || p.version() != version) {
            int[] m = h.market();
            p = t.leg == BACK ? Routes.path(world, m[0] + 0.5, m[1] + 0.5, v.x() + 0.5, v.z() + 0.5, fresh)
                    : Routes.path(world, v.x() + 0.5, v.z() + 0.5, m[0] + 0.5, m[1] + 0.5, fresh);
            PATHS.put(key, p);
        }
        return p;
    }

    /** Le pas de toutes les tournées. */
    static void step(World world, Store<EntityStore> store, List<Vector3d> players, float dt) {
        boolean night = GameClock.isNight(store);
        for (Trip t : all(world)) {
            Village v = Villages.registry(world).byId(t.village);
            Hamlets.Place h = Hamlets.get(world, t.hamlet);
            if (v == null || h == null || h.stage() == Hamlets.FAILED || t.walkers <= 0) {
                drop(world, store, t);
                continue;
            }
            if (t.leg == STAY) {
                stay(world, store, players, t, v, h);
                save(world, t);
                continue;
            }
            Routes.Path path = path(world, t, v, h, false);
            if (t.at >= path.length() - Walk.ARRIVE) {
                if (t.leg == OUT) {
                    arriveAtHamlet(world, store, t, v, h);
                    save(world, t);
                } else {
                    home(world, store, t, v, h);
                }
                continue;
            }
            Walk walk = Walk.of(t.walkKey());
            boolean wasReal = walk.real();
            People people = v.people();
            t.at = walk.step(world, store, players, path, t.at, dt, t.walkers, !night, v.y(),
                    (i, at, yaw) -> spawnWalker(store, t, people, i, at, yaw));
            if (!wasReal && walk.real()) {
                for (Ref<EntityStore> ref : walk.alive()) {
                    OWNER.put(ref, t.id);
                }
                // Un joueur arrive : terrain réel chargé, le trajet est recalculé (pont, remblai).
                Routes.Path fresh = path(world, t, v, h, true);
                if (fresh != path) {
                    double[] was = path.point(t.at);
                    t.at = fresh.closest(was[0], was[1], 0, fresh.length());
                    walk.reset(t.at);
                }
            }
            save(world, t);
        }
    }

    /** Sur la place du lieu-dit : de vrais PNJ s'il y a un joueur près, sinon rien ; le séjour fini, retour. */
    private static void stay(World world, Store<EntityStore> store, List<Vector3d> players, Trip t, Village v, Hamlets.Place h) {
        Walk walk = Walk.of(t.walkKey());
        long now = GameClock.seconds(store);
        if (now >= t.until) {
            t.leg = BACK;
            t.at = 0;
            walk.reset(0);
            return; // les PNJ présents reprennent la route au pas suivant, depuis la place
        }
        int[] m = h.market();
        if (!WorldLife.near(players, m[0], m[1], WorldLife.REAL_RANGE)) {
            walk.despawn(store);
            return;
        }
        List<Ref<EntityStore>> live = walk.alive();
        if (live.isEmpty() && WorldLife.budget(world, t.walkers)) {
            People people = v.people();
            for (int i = 0; i < t.walkers; i++) {
                Vector3d spot = WorldLife.ground(world, m[0] + (i == 0 ? 0 : i == 1 ? 2 : -2), m[1] + (i == 0 ? 0 : 1), 6);
                if (spot == null) {
                    continue;
                }
                Ref<EntityStore> ref = spawnWalker(store, t, people, i, spot, (float) Math.PI);
                if (ref != null) {
                    walk.refs.add(ref);
                }
            }
            live = walk.alive();
        }
        for (int i = 0; i < live.size(); i++) {
            Vector3d to = WorldLife.ground(world, m[0] + (i == 0 ? 0 : i == 1 ? 2 : -2), m[1] + (i == 0 ? 0 : 1), 6);
            if (to != null) {
                WorldLife.leash(store, live.get(i), to);
            }
        }
    }

    /** Arrivée sur la place : passages comptés, le lieu-dit peut devenir animé, séjour de {@value #STAY_HOURS} h. */
    private static void arriveAtHamlet(World world, Store<EntityStore> store, Trip t, Village v, Hamlets.Place h) {
        long day = GameClock.day(store);
        int before = Hamlets.visits(world, h, day);
        Links.pass(world, h.trafficKey(), day, Math.max(1, t.walkers));
        WorldLife.registry(world).put(WorldLifeRegistry.Part.HAMLET_TRIPS, LAST + h.id(), v.id());
        if (before < Hamlets.LIVELY && Hamlets.visits(world, h, day) >= Hamlets.LIVELY) {
            Hamlets.announceLively(world, store, h);
        }
        t.leg = STAY;
        t.at = 0;
        t.until = GameClock.seconds(store) + STAY_HOURS * 3600L;
    }

    /** Retour au village : essor (caravane : un par porteur rentré), meilleure relation avec le village du lieu-dit. */
    private static void home(World world, Store<EntityStore> store, Trip t, Village v, Hamlets.Place h) {
        int essor = t.caravan ? Math.min(CARAVAN_ESSOR, t.walkers) : MERCHANT_ESSOR;
        Villages.addEssor(v, essor);
        Village owner = Hamlets.village(world, h);
        if (owner != null && owner != v) {
            Relations.change(world, v, owner, 1);
        }
        Chantiers.announce(world, v, Message.translation(KEYS + "home").param("hamlet", h.name()).param("essor", essor), null,
                NotificationStyle.Success);
        drop(world, store, t);
    }

    private static Ref<EntityStore> spawnWalker(Store<EntityStore> store, Trip t, People people, int i, Vector3d at, float yaw) {
        String role = i == 0 ? Travellers.peddlerRole(people) : Travellers.travellerRole(people);
        Ref<EntityStore> ref = WorldLife.spawn(store, role, at, yaw);
        if (ref == null) {
            return null;
        }
        WorldLife.side(ref, "HT:" + t.id, 0);
        WorldLife.talker(ref, HamletTrips::talk);
        WorldLife.mortal(ref, (world, npc, where, killer) -> died(world, t.id, npc));
        OWNER.put(ref, t.id);
        return ref;
    }

    private static void died(World world, String id, Ref<EntityStore> npc) {
        OWNER.remove(npc);
        Trip t = get(world, id);
        if (t == null) {
            return;
        }
        t.walkers--;
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (t.walkers <= 0) {
            Village v = Villages.registry(world).byId(t.village);
            Hamlets.Place h = Hamlets.get(world, t.hamlet);
            if (v != null && h != null) {
                Chantiers.announce(world, v, Message.translation(KEYS + "lost").param("hamlet", h.name()), null, NotificationStyle.Warning);
            }
            drop(world, store, t);
        } else {
            save(world, t);
        }
    }

    // ---- Dialogue ----

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Dialogue dialogue = of(world, npc) == null ? null : Dialogue.get(DIALOGUE);
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    /** Troc du marchand : celui des voyageurs de son peuple, au rang Toléré dans son village. */
    static boolean openShop(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Trip t) {
        Village v = Villages.registry(world).byId(t.village);
        if (v == null) {
            return false;
        }
        if (!Reputations.rank(store, ref, v).atLeast(Rank.TOLERE)) {
            DialogueSpeech.say(player, Message.translation(Hamlets.KEYS + "shopRank").param("village", v.name()));
            return false;
        }
        return Shops.open(store, ref, player, v, Travellers.shop(v.people()));
    }

    /** « Où vas-tu ? » */
    static boolean where(World world, Store<EntityStore> store, PlayerRef player, Trip t) {
        Village v = Villages.registry(world).byId(t.village);
        Hamlets.Place h = Hamlets.get(world, t.hamlet);
        if (v == null || h == null) {
            return false;
        }
        Message m = switch (t.leg) {
            case OUT -> Message.translation(KEYS + "where.out");
            case STAY -> {
                long left = Math.max(0, t.until - GameClock.seconds(store));
                int hour = GameClock.hour(store);
                yield Message.translation(KEYS + "where.stay").param("hour", hour < 0 ? 0 : (int) ((hour + (left + 1799) / 3600) % 24));
            }
            default -> Message.translation(KEYS + "where.back");
        };
        DialogueSpeech.say(player, m.param("hamlet", h.name()).param("village", v.name()));
        return true;
    }

    /** Rumeurs : les tournées en cours. */
    static List<Message> rumours(World world) {
        List<Message> out = new ArrayList<>();
        for (Trip t : all(world)) {
            Village v = Villages.registry(world).byId(t.village);
            Hamlets.Place h = Hamlets.get(world, t.hamlet);
            if (v != null && h != null && t.leg == OUT) {
                out.add(Message.translation(Hamlets.KEYS + "rumour.trip").param("village", v.name()).param("hamlet", h.name()));
            }
        }
        return out;
    }

    /** Ligne de la commande /monde. */
    static Message describe(World world, Store<EntityStore> store, Trip t) {
        Village v = Villages.registry(world).byId(t.village);
        Hamlets.Place h = Hamlets.get(world, t.hamlet);
        Message leg = Message.translation(Hamlets.KEYS + "cmd.leg." + t.leg);
        if (t.leg != STAY && v != null && h != null) {
            leg = leg.param("at", (int) t.at).param("length", (int) path(world, t, v, h, false).length());
        }
        return Message.translation(Hamlets.KEYS + "cmd.tripLine")
                .param("kind", Message.translation(Travellers.KEYS + "kind." + (t.caravan ? "caravan" : "merchant")))
                .param("village", v == null ? "?" : v.name()).param("hamlet", h == null ? Message.raw("?") : h.name()).param("leg", leg);
    }

    public static void clearAll() {
        OWNER.clear();
        PATHS.clear();
    }
}
