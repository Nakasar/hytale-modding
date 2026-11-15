package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Étape 5 : les relations entre villages, de {@value #MIN} à {@value #MAX} par paire de villages liés
 * ({@link WorldLifeRegistry.Part#RELATIONS} : {@code a|b = valeur|trêve jusqu'au jour|dernière escarmouche}).
 * <ul>
 *   <li>Départ : même peuple {@value #SAME}, peuples alliés {@value #ALLIED}, Kweebecs et Trorks {@value #RIVALS},
 *       sinon 0. Tous les {@value #DRIFT_DAYS} jours, la valeur revient d'un point vers son départ ; une caravane arrivée
 *       ajoute {@value Travellers#CARAVAN_RELATION}, un autre voyageur {@value Travellers#TRAVELLER_RELATION} ; chaque
 *       semaine, une querelle (5 %) en retire 15.</li>
 *   <li>Alliés (≥ {@value #ALLY}) : une caravane par jour entre eux, et des renforts dans les raids
 *       ({@link #reinforcements}).</li>
 *   <li>Rivaux (≤ {@value #RIVAL}) : plus de voyageurs sauf les messagers, et une escarmouche par semaine au milieu de
 *       la liaison (de vrais combattants si un joueur est à moins de {@value Ambushes#WITNESS} blocs, sinon réglée
 *       seule).</li>
 *   <li>Trêve : un joueur Ami des deux villages porte une lettre de paix du messager ({@link Travellers}) : trêve de
 *       {@value #TRUCE_DAYS} jours (pas d'escarmouche) et +{@value #PARLEY}.</li>
 * </ul>
 * Pas de pacte Kweebec/Trork pour l'instant (Kevin, 15 novembre 2026).
 */
public final class Relations {

    public static final int MIN = -100;
    public static final int MAX = 100;
    public static final int SAME = 40;
    public static final int ALLIED = 20;
    public static final int RIVALS = -60;
    public static final int ALLY = 50;
    public static final int RIVAL = -20;
    public static final int TRUCE_DAYS = 7;
    public static final int PARLEY = 25;
    public static final double QUARREL_CHANCE = 0.05;
    public static final int QUARREL = -15;
    /** Le retour vers la valeur de départ : un point tous les {@value #DRIFT_DAYS} jours. */
    public static final int DRIFT_DAYS = 3;
    public static final int REINFORCE_RANGE = 1200;
    public static final int MAX_REINFORCEMENTS = 2;
    public static final int SKIRMISH_FIGHTERS = 3;
    public static final int SKIRMISH_SECONDS = 240;
    public static final int SKIRMISH_REPUTATION = 15;
    public static final String KEYS = WorldLife.KEYS + "relation.";
    private static final String PENDING = "~sk:";

    private record Skirmish(String link, double x, double z, List<Ref<EntityStore>> a, List<Ref<EntityStore>> b, long started) {
    }

    private static final Map<String, Skirmish> SKIRMISHES = new ConcurrentHashMap<>();

    private Relations() {
    }

    /** Valeur de départ entre deux peuples. */
    public static int base(People a, People b) {
        if (a == b) {
            return SAME;
        }
        if (a.rival() == b || b.rival() == a) {
            return RIVALS;
        }
        if (a.ally() == b || b.ally() == a) {
            return ALLIED;
        }
        return 0;
    }

    private static int[] read(World world, Village a, Village b) {
        String v = WorldLife.registry(world).get(WorldLifeRegistry.Part.RELATIONS, Links.key(a.id(), b.id()));
        int[] out = {base(a.people(), b.people()), Integer.MIN_VALUE, Integer.MIN_VALUE};
        if (v != null) {
            String[] p = v.split("\\|");
            for (int i = 0; i < Math.min(3, p.length); i++) {
                try {
                    out[i] = Integer.parseInt(p[i].trim());
                } catch (NumberFormatException ignored) {
                    // valeur abîmée : celle de départ
                }
            }
        }
        return out;
    }

    private static void write(World world, Village a, Village b, int[] v) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.RELATIONS, Links.key(a.id(), b.id()), v[0] + "|" + v[1] + "|" + v[2]);
    }

    public static int value(World world, Village a, Village b) {
        return read(world, a, b)[0];
    }

    public static boolean truce(World world, Village a, Village b, long day) {
        return read(world, a, b)[1] >= day;
    }

    public static int change(World world, Village a, Village b, int delta) {
        int[] v = read(world, a, b);
        v[0] = Math.max(MIN, Math.min(MAX, v[0] + delta));
        write(world, a, b, v);
        return v[0];
    }

    public static void set(World world, Village a, Village b, int value) {
        int[] v = read(world, a, b);
        v[0] = Math.max(MIN, Math.min(MAX, value));
        write(world, a, b, v);
    }

    /** Nom de l'état (clé de texte) : allié, ami, neutre, tendu, rival. */
    public static String state(int value) {
        if (value >= ALLY) {
            return "ally";
        }
        if (value >= 20) {
            return "friendly";
        }
        if (value > RIVAL) {
            return "neutral";
        }
        if (value > -50) {
            return "tense";
        }
        return "rival";
    }

    /** Renforts alliés d'un village attaqué : un garde par village allié à moins de {@value #REINFORCE_RANGE} blocs. */
    public static int reinforcements(World world, Village village) {
        int n = 0;
        for (Links.Link l : Links.of(world, village)) {
            if (l.length() <= REINFORCE_RANGE && value(world, l.a(), l.b()) >= ALLY) {
                n++;
            }
        }
        return Math.min(MAX_REINFORCEMENTS, n);
    }

    /** Trêve conclue par un joueur (lettre de paix livrée). */
    public static void parley(World world, Village a, Village b, long day) {
        int[] v = read(world, a, b);
        v[0] = Math.max(MIN, Math.min(MAX, v[0] + PARLEY));
        v[1] = (int) (day + TRUCE_DAYS);
        write(world, a, b, v);
        Message m = Message.translation(KEYS + "truce").param("a", a.name()).param("b", b.name()).param("days", TRUCE_DAYS);
        Chantiers.announce(world, a, m, null, NotificationStyle.Success);
        Chantiers.announce(world, b, m, null, NotificationStyle.Success);
    }

    // ---- Chaque jour ----

    static void morning(World world, Store<EntityStore> store, long day, Random random) {
        for (Links.Link l : Links.all(world)) {
            int[] v = read(world, l.a(), l.b());
            int base = base(l.a().people(), l.b().people());
            if (v[0] != base && Math.floorMod(day, (long) DRIFT_DAYS) == 0) {
                v[0] += v[0] < base ? 1 : -1;
            }
            if (Math.floorMod(day, 7L) == 0 && random.nextDouble() < QUARREL_CHANCE) {
                v[0] = Math.max(MIN, v[0] + QUARREL);
                Message m = Message.translation(KEYS + "quarrel").param("a", l.a().name()).param("b", l.b().name());
                Chantiers.announce(world, l.a(), m, null, NotificationStyle.Warning);
                Chantiers.announce(world, l.b(), m, null, NotificationStyle.Warning);
            }
            write(world, l.a(), l.b(), v);
            if (v[0] <= RIVAL && v[1] < day && (v[2] == Integer.MIN_VALUE || day - v[2] >= 7)) {
                // Une escarmouche cette semaine, en plein jour.
                WorldLife.registry(world).put(WorldLifeRegistry.Part.RELATIONS, PENDING + l.key(),
                        day + "|" + (9 + random.nextInt(7)));
                v[2] = (int) day;
                write(world, l.a(), l.b(), v);
            }
        }
    }

    // ---- Escarmouches ----

    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        long day = GameClock.day(store);
        int hour = GameClock.hour(store);
        Map<String, String> part = WorldLife.registry(world).part(WorldLifeRegistry.Part.RELATIONS);
        for (String key : new ArrayList<>(part.keySet())) {
            if (!key.startsWith(PENDING)) {
                continue;
            }
            String[] p = part.get(key).split("\\|");
            long d;
            int h;
            try {
                d = Long.parseLong(p[0]);
                h = Integer.parseInt(p[1]);
            } catch (RuntimeException e) {
                part.remove(key);
                continue;
            }
            if (d < day) {
                part.remove(key); // journée passée (serveur arrêté) : l'escarmouche n'a pas eu lieu
                continue;
            }
            if (hour < h) {
                continue;
            }
            part.remove(key);
            String[] ids = key.substring(PENDING.length()).split("\\|");
            Links.Link link = ids.length == 2 ? Links.of(world, ids[0], ids[1]) : null;
            if (link != null && !truce(world, link.a(), link.b(), day)) {
                start(world, store, link, players);
            }
        }
        for (Skirmish s : new ArrayList<>(SKIRMISHES.values())) {
            s.a().removeIf(r -> !r.isValid());
            s.b().removeIf(r -> !r.isValid());
            boolean timeout = System.currentTimeMillis() - s.started() > SKIRMISH_SECONDS * 1000L;
            if (s.a().isEmpty() || s.b().isEmpty() || timeout) {
                finish(world, store, s, timeout);
            }
        }
    }

    /** Lance une escarmouche entre les deux villages de la liaison (aussi par /monde). */
    public static void start(World world, Store<EntityStore> store, Links.Link link, List<Vector3d> players) {
        if (SKIRMISHES.containsKey(link.key())) {
            return;
        }
        double[] mid = link.middle();
        if (!WorldLife.near(players, mid[0], mid[1], Ambushes.WITNESS) || !WorldLife.budget(world, SKIRMISH_FIGHTERS * 2)) {
            // Sans témoin : réglée seule, le plus grand village l'emporte plus souvent.
            Random random = new Random();
            double pa = (1.0 + link.a().tier()) / (2.0 + link.a().tier() + link.b().tier());
            Village winner = random.nextDouble() < pa ? link.a() : link.b();
            Village loser = winner == link.a() ? link.b() : link.a();
            change(world, link.a(), link.b(), -5);
            Message m = Message.translation(KEYS + "skirmishAway").param("winner", winner.name()).param("loser", loser.name());
            Chantiers.announce(world, link.a(), m, null, NotificationStyle.Warning);
            Chantiers.announce(world, link.b(), m, null, NotificationStyle.Warning);
            return;
        }
        double dx = link.b().x() - link.a().x();
        double dz = link.b().z() - link.a().z();
        double len = Math.max(1, Math.hypot(dx, dz));
        dx /= len;
        dz /= len;
        String side = "SK:" + link.key();
        List<Ref<EntityStore>> a = fighters(world, store, link.a(), mid[0] - dx * 8, mid[1] - dz * 8, mid, side, 0);
        List<Ref<EntityStore>> b = fighters(world, store, link.b(), mid[0] + dx * 8, mid[1] + dz * 8, mid, side, 1);
        if (a.isEmpty() || b.isEmpty()) {
            a.forEach(r -> WorldLife.remove(store, r));
            b.forEach(r -> WorldLife.remove(store, r));
            return;
        }
        SKIRMISHES.put(link.key(), new Skirmish(link.key(), mid[0], mid[1], a, b, System.currentTimeMillis()));
        WorldLife.announce(world, store, mid[0], mid[1], Ambushes.WITNESS,
                Message.translation(KEYS + "skirmish").param("a", link.a().name()).param("b", link.b().name()), NotificationStyle.Warning);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (monde vivant) : escarmouche %s", link.key());
    }

    private static List<Ref<EntityStore>> fighters(World world, Store<EntityStore> store, Village village, double x, double z,
                                                   double[] mid, String side, int team) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        String role = fighterRole(village.people());
        Random random = new Random();
        for (int i = 0; i < SKIRMISH_FIGHTERS; i++) {
            Vector3d spot = WorldLife.ground(world, (int) Math.floor(x) + random.nextInt(-3, 4), (int) Math.floor(z) + random.nextInt(-3, 4), 6);
            Ref<EntityStore> ref = spot == null ? null : WorldLife.spawn(store, role, spot, 0f);
            if (ref == null) {
                continue;
            }
            WorldLife.side(ref, side, team);
            WorldLife.leash(store, ref, new Vector3d(mid[0], spot.y(), mid[1]));
            out.add(ref);
        }
        return out;
    }

    /** Combattant d'un village (garde de raid ; patrouilleur pour les Trorks, qui n'ont pas de garde). */
    public static String fighterRole(People people) {
        return people == People.TRORK ? "Nakasar_Peuples_Trork_Patrol" : Raids.defenderRole(people);
    }

    private static void finish(World world, Store<EntityStore> store, Skirmish s, boolean timeout) {
        SKIRMISHES.remove(s.link());
        String[] ids = s.link().split("\\|");
        Village va = Villages.registry(world).byId(ids[0]);
        Village vb = Villages.registry(world).byId(ids[1]);
        s.a().forEach(r -> WorldLife.remove(store, r));
        s.b().forEach(r -> WorldLife.remove(store, r));
        if (va == null || vb == null) {
            return;
        }
        change(world, va, vb, -5);
        if (timeout || s.a().isEmpty() == s.b().isEmpty()) {
            WorldLife.announce(world, store, s.x(), s.z(), Ambushes.WITNESS, Message.translation(KEYS + "skirmishDraw"), NotificationStyle.Default);
            return;
        }
        Village winner = s.a().isEmpty() ? vb : va;
        Message m = Message.translation(KEYS + "skirmishWon").param("winner", winner.name());
        for (PlayerRef p : WorldLife.playersNear(world, store, s.x(), s.z(), WorldLife.REAL_RANGE)) {
            Reputations.change(world, store, p.getReference(), p, winner, SKIRMISH_REPUTATION, KEYS + "skirmishReason");
        }
        WorldLife.announce(world, store, s.x(), s.z(), Ambushes.WITNESS, m, NotificationStyle.Success);
    }

    /** Escarmouches en cours (commande). */
    public static int skirmishes() {
        return SKIRMISHES.size();
    }

    public static void clearAll() {
        SKIRMISHES.clear();
    }
}
