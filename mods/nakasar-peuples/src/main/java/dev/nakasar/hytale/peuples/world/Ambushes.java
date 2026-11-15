package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.People;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Étape 1 : les embuscades. Une caravane entre deux villages, ou le convoi d'un avant-poste vers son village, peut être
 * attaquée à mi-chemin (une chance sur {@value #ODDS}). Un joueur à moins de {@value #WITNESS} blocs : une bande de
 * {@value #MIN_BAND} à {@value #MAX_BAND} pillards de la zone (ceux des raids, {@link Raids#raiders}) surgit
 * {@value #AHEAD} blocs devant ; la file s'arrête jusqu'à ce que la bande soit morte ou repartie
 * ({@value #MAX_SECONDS} s). Personne : l'embuscade se règle seule, une fois sur deux la file perd un tiers de sa
 * cargaison. Les pillards et la file sont de camps ennemis ({@link WorldAttitudeSystem}).
 */
public final class Ambushes {

    public static final int ODDS = 3;
    public static final int WITNESS = 160;
    public static final int MIN_BAND = 3;
    public static final int MAX_BAND = 5;
    public static final int AHEAD = 12;
    public static final int MAX_SECONDS = 180;
    public static final String KEYS = WorldLife.KEYS + "ambush.";

    private record Band(List<Ref<EntityStore>> raiders, long started) {
    }

    private static final Map<String, Band> ACTIVE = new ConcurrentHashMap<>();
    private static final Set<String> CONVOYS_ROLLED = ConcurrentHashMap.newKeySet();

    private Ambushes() {
    }

    /**
     * Tirage à mi-chemin de la file `key` : vrai si une bande est posée (la file doit attendre). `people` : peuple de la
     * file (la bande est celle qui le menace).
     */
    static boolean roll(World world, Store<EntityStore> store, String key, double[] here, double[] dir, People people,
                        List<Ref<EntityStore>> walkers, List<Vector3d> players) {
        return roll(world, store, key, here, dir, people, walkers, players, false);
    }

    static boolean roll(World world, Store<EntityStore> store, String key, double[] here, double[] dir, People people,
                        List<Ref<EntityStore>> walkers, List<Vector3d> players, boolean force) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        if (!WorldLife.near(players, here[0], here[1], WITNESS)) {
            return false; // sans témoin : virtualLoss
        }
        if (!force && random.nextInt(ODDS) != 0) {
            return false;
        }
        int size = MIN_BAND + random.nextInt(MAX_BAND - MIN_BAND + 1);
        if (!WorldLife.budget(world, size)) {
            size = MIN_BAND;
        }
        String[] ranks = Raids.raiders(people);
        int ax = (int) Math.floor(here[0] + dir[0] * AHEAD);
        int az = (int) Math.floor(here[1] + dir[1] * AHEAD);
        List<Ref<EntityStore>> band = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            Vector3d spot = WorldLife.ground(world, ax + random.nextInt(-4, 5), az + random.nextInt(-4, 5), 6);
            if (spot == null) {
                continue;
            }
            String role = ranks[i == 0 && size >= 5 ? 2 : random.nextInt(2)];
            Ref<EntityStore> ref = WorldLife.spawn(store, role, spot, (float) random.nextDouble(-Math.PI, Math.PI));
            if (ref == null) {
                continue;
            }
            WorldLife.side(ref, key, 1);
            // Ils foncent sur la file : leur point d'attache est sur elle.
            WorldLife.leash(store, ref, new Vector3d(here[0], spot.y(), here[1]));
            band.add(ref);
        }
        if (band.isEmpty()) {
            return false;
        }
        for (Ref<EntityStore> w : walkers) {
            WorldLife.side(w, key, 0);
        }
        ACTIVE.put(key, new Band(band, System.currentTimeMillis()));
        WorldLife.announce(world, store, here[0], here[1], WITNESS, Message.translation(KEYS + "start"), NotificationStyle.Danger);
        return true;
    }

    /**
     * Embuscade sans témoin (personne à moins de {@value #WITNESS} blocs) : une chance sur {@value #ODDS} d'être attaquée,
     * puis une fois sur deux la file y perd une part de sa cargaison.
     */
    static boolean virtualLoss(List<Vector3d> players, double[] here) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        return !WorldLife.near(players, here[0], here[1], WITNESS) && random.nextInt(ODDS) == 0 && random.nextBoolean();
    }

    /** Vrai si l'embuscade de la file `key` est finie (bande morte, ou repartie au bout de {@value #MAX_SECONDS} s). */
    static boolean over(World world, Store<EntityStore> store, String key) {
        Band band = ACTIVE.get(key);
        if (band == null) {
            return true;
        }
        band.raiders().removeIf(ref -> !ref.isValid());
        boolean timeout = System.currentTimeMillis() - band.started() > MAX_SECONDS * 1000L;
        if (!band.raiders().isEmpty() && !timeout) {
            return false;
        }
        for (Ref<EntityStore> ref : band.raiders()) {
            WorldLife.remove(store, ref);
        }
        ACTIVE.remove(key);
        if (!timeout) {
            Vector3d at = null;
            Walk w = Walk.peek(key);
            if (w != null && !w.alive().isEmpty()) {
                at = Requests.position(store, w.alive().get(0));
            }
            if (at != null) {
                WorldLife.announce(world, store, at.x(), at.z(), WITNESS, Message.translation(KEYS + "won"), NotificationStyle.Success);
            }
        }
        return true;
    }

    public static boolean active(String key) {
        return ACTIVE.containsKey(key);
    }

    /**
     * Convois des avant-postes ({@code annex/Convoys}) : tirage à mi-chemin, une fois par convoi ; vrai tant que la bande
     * est là (le convoi attend, ses porteurs restent sur place).
     */
    public static boolean convoy(World world, Store<EntityStore> store, String key, AnnexState a, Routes.Path path, People people,
                                 List<Ref<EntityStore>> porters, List<Vector3d> players) {
        String walkKey = "C:" + key;
        if (ACTIVE.containsKey(walkKey)) {
            double[] at0 = path.point(a.convoyAt());
            if (porters.isEmpty() && WorldLife.near(players, at0[0], at0[1], WorldLife.REAL_RANGE)) {
                return false; // un joueur arrive : les porteurs se posent (le pas suivant, ils attendent)
            }
            for (Ref<EntityStore> p : porters) {
                WorldLife.side(p, walkKey, 0);
                Vector3d at = Requests.position(store, p);
                if (at != null) {
                    WorldLife.leash(store, p, at);
                }
            }
            return !over(world, store, walkKey);
        }
        String rolled = key + "@" + a.deliveryDay();
        if (a.convoyAt() < path.length() / 2 || CONVOYS_ROLLED.contains(rolled)) {
            return false;
        }
        CONVOYS_ROLLED.add(rolled);
        double[] here = path.point(a.convoyAt());
        if (roll(world, store, walkKey, here, path.dir(a.convoyAt()), people, porters, players)) {
            return true;
        }
        if (virtualLoss(players, here)) {
            a.raidCargo(Math.max(1, a.convoyCargo() / 3));
        }
        return false;
    }

    /** Embuscade forcée sur une caravane (commande /monde). */
    public static boolean force(World world, Store<EntityStore> store, String key, double[] here, double[] dir, People people,
                                List<Ref<EntityStore>> walkers, List<Vector3d> players) {
        return roll(world, store, key, here, dir, people, walkers, players, true);
    }

    public static int count() {
        return ACTIVE.size();
    }

    public static void clearAll() {
        ACTIVE.clear();
        CONVOYS_ROLLED.clear();
    }
}
