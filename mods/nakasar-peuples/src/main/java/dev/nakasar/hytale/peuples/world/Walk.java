package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Villagers;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.IntFunction;

/**
 * Une file de marcheurs sur une route (voyageurs, caravanes, troupeaux, patrouilles) : la simulation à deux vitesses
 * des convois des avant-postes ({@code annex/Convoys}), rendue commune. La progression (en blocs sur la route) est
 * gardée par l'appelant (état sauvé) ; ici ne vivent que les PNJ et le compteur « coincé ».
 * <ul>
 *   <li>Un joueur à moins de {@value WorldLife#REAL_RANGE} blocs : de vrais PNJ marchent, leur point d'attache
 *       {@value #LEAD} blocs devant (jamais au-delà de la prochaine balise) ; la progression est celle du meneur.</li>
 *   <li>Personne : pas de PNJ, la file avance seule ({@code speed} blocs/s).</li>
 *   <li>Coincés {@value #STUCK_SECONDS} s sans témoin à moins de {@value WorldLife#WATCHED} blocs : un saut de
 *       {@value #HOP} blocs le long de la route.</li>
 * </ul>
 */
public final class Walk {

    public static final int LEAD = 10;
    public static final double SPEED = 3.0;
    public static final double ROUTE_SPEED = 4.0;
    private static final double TURN_MARGIN = 7.0;
    public static final double ARRIVE = 4.0;
    private static final float STUCK_SECONDS = 30f;
    private static final int HOP = 8;
    /** Rayon de recherche d'une place sûre autour de la place en file. */
    private static final int SAFE_RADIUS = 6;

    private static final Map<String, Walk> WALKS = new ConcurrentHashMap<>();

    final String key;
    final List<Ref<EntityStore>> refs = new ArrayList<>();
    private double best;
    private float stuckFor;

    private Walk(String key) {
        this.key = key;
    }

    public static Walk of(String key) {
        return WALKS.computeIfAbsent(key, Walk::new);
    }

    public static Walk peek(String key) {
        return WALKS.get(key);
    }

    /** PNJ vivants de la file. */
    public List<Ref<EntityStore>> alive() {
        refs.removeIf(ref -> {
            if (ref.isValid()) {
                return false;
            }
            WorldLife.forget(ref);
            return true;
        });
        return refs;
    }

    public boolean real() {
        return !alive().isEmpty();
    }

    /**
     * Un pas : rend la nouvelle progression. `spawner` pose le marcheur `i` à la place donnée (null s'il ne peut pas) ;
     * `count` marcheurs au plus. `moving` faux : la file reste où elle est (la nuit), les PNJ attendent sur place.
     */
    public double step(World world, Store<EntityStore> store, List<Vector3d> players, Routes.Path path, double at, float dt,
                       int count, boolean moving, int fallbackY, Spawner spawner) {
        double length = path.length();
        double[] here = path.point(at);
        if (!WorldLife.near(players, here[0], here[1], WorldLife.REAL_RANGE)) {
            despawn(store);
            if (!moving) {
                return at;
            }
            double speed = path.beacons() > 0 ? ROUTE_SPEED : SPEED;
            return Math.min(length, at + speed * dt);
        }
        List<Ref<EntityStore>> live = alive();
        if (live.isEmpty()) {
            if (!WorldLife.budget(world, count)) {
                return at; // trop de PNJ : la file attend que la place se libère (sans avancer, sous les yeux d'un joueur)
            }
            for (int i = 0; i < count; i++) {
                Vector3d spot = safeSpot(world, path, at, i);
                if (spot == null) {
                    continue; // ni eau, ni lave, ni bloc : pas de place sûre ici, ce marcheur viendra au pas suivant
                }
                float yaw = (float) Math.atan2(-path.dir(at)[0], path.dir(at)[1]);
                Ref<EntityStore> ref = spawner.spawn(i, spot, yaw);
                if (ref != null) {
                    refs.add(ref);
                }
            }
            best = at;
            stuckFor = 0;
            return at;
        }
        double lead = at;
        for (Ref<EntityStore> ref : live) {
            Vector3d p = Requests.position(store, ref);
            if (p != null) {
                lead = Math.max(lead, path.closest(p.x(), p.z(), at - 2, at + LEAD + 6));
            }
        }
        if (lead > best + 1) {
            best = lead;
            stuckFor = 0;
        } else if (moving) {
            stuckFor += dt;
        }
        if (moving && stuckFor >= STUCK_SECONDS && !WorldLife.near(players, here[0], here[1], WorldLife.WATCHED)) {
            lead = Math.min(length, lead + HOP);
            for (int i = 0; i < live.size(); i++) {
                Vector3d to = safeSpot(world, path, lead, i);
                if (to != null) {
                    store.putComponent(live.get(i), Teleport.getComponentType(), new Teleport(to, new Rotation3f(0f, 0f, 0f)));
                }
            }
            best = lead;
            stuckFor = 0;
        }
        double target = moving ? Math.min(Math.min(length, lead + LEAD), path.nextTurn(lead, TURN_MARGIN)) : lead;
        for (int i = 0; i < live.size(); i++) {
            WorldLife.leash(store, live.get(i), spot(world, path, target, i, fallbackY));
        }
        return lead;
    }

    /** Retire les PNJ de la file (personne près d'elle, arrivée, fin). */
    public void despawn(Store<EntityStore> store) {
        for (Ref<EntityStore> ref : refs) {
            WorldLife.remove(store, ref);
        }
        refs.clear();
        stuckFor = 0;
    }

    /** Fin de la file : PNJ retirés et file oubliée. */
    public static void end(Store<EntityStore> store, String key) {
        Walk w = WALKS.remove(key);
        if (w != null) {
            w.despawn(store);
        }
    }

    /** Point d'attache du marcheur `i` à `at` blocs : en file, décalé sur le côté pour ne pas s'empiler. */
    public static Vector3d spot(World world, Routes.Path path, double at, int i, int fallbackY) {
        double[] p = path.point(at);
        double[] d = path.dir(at);
        double side = (i % 2 == 0 ? 1 : -1) * 1.5 * ((i + 1) / 2);
        double back = 1.5 * i;
        int x = (int) Math.floor(p[0] - d[0] * back - d[1] * side);
        int z = (int) Math.floor(p[1] - d[1] * back + d[0] * side);
        return Villagers.groundAt(world, x, z, fallbackY);
    }

    /**
     * Place sûre du marcheur `i` à `at` blocs, pour le poser ou le téléporter ({@link WorldLife#ground} : jamais dans
     * l'eau, la lave ou un bloc) ; null s'il n'y en a pas (ou que la zone n'est pas chargée).
     */
    public static Vector3d safeSpot(World world, Routes.Path path, double at, int i) {
        double[] p = path.point(at);
        double[] d = path.dir(at);
        double side = (i % 2 == 0 ? 1 : -1) * 1.5 * ((i + 1) / 2);
        double back = 1.5 * i;
        int x = (int) Math.floor(p[0] - d[0] * back - d[1] * side);
        int z = (int) Math.floor(p[1] - d[1] * back + d[0] * side);
        return WorldLife.ground(world, x, z, SAFE_RADIUS);
    }

    /** Pose du marcheur `i`. */
    @FunctionalInterface
    public interface Spawner {
        Ref<EntityStore> spawn(int i, Vector3d at, float yaw);
    }

    /** Rôle par marcheur (le meneur peut différer). */
    public static Spawner roles(Store<EntityStore> store, IntFunction<String> role) {
        return (i, at, yaw) -> WorldLife.spawn(store, role.apply(i), at, yaw);
    }

    public static void clearAll() {
        WALKS.clear();
    }
}
