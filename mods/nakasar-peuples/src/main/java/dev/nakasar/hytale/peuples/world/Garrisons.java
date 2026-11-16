package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Village;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les gardes d'un lieu-dit tenu (GDD de la conquête, « Administration ») : {@value #BASE} garde au palier 2 du
 * propriétaire, {@value #BASE_TIER3} au palier 3, un de plus avec la spécialité Garnison de sa Maison du conseil et un
 * de plus dans une caserne. Ce sont les combattants du peuple du propriétaire ({@link Relations#fighterRole}), posés
 * autour de la place quand un joueur est à moins de {@value WorldLife#REAL_RANGE} blocs. Un garde mort est remplacé
 * par la relève qui part du village le lendemain matin (le jour même avec la spécialité Garnison). Les gardes sont du
 * camp 0 de la clé {@code HG:<lieu-dit>} contre les soldats d'une expédition (camp 1), et attaquent les joueurs Honnis
 * chez le propriétaire ({@link WorldAttitudeSystem}).
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#GARRISONS}) : {@code lieu-dit = gardes présents}.
 */
public final class Garrisons {

    public static final int BASE = 1;
    public static final int BASE_TIER3 = 2;
    /** Postes des gardes autour de la place (coordonnées locales du lieu-dit). */
    private static final int[][] POSTS = {{-3, Hamlets.MARKET_Z + 2}, {3, Hamlets.MARKET_Z + 2}, {0, Hamlets.MARKET_Z + 5}, {-5, Hamlets.MARKET_Z - 1}};

    private static final Map<String, List<Ref<EntityStore>>> LIVE = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, String> GUARD_OF = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Joueurs Honnis chez le propriétaire, près de chaque lieu-dit (recalculé à chaque pas). */
    private static final Map<String, Set<Ref<EntityStore>>> HOSTILE = new ConcurrentHashMap<>();

    private Garrisons() {
    }

    public static String sideKey(String hamlet) {
        return "HG:" + hamlet;
    }

    /** Gardes présents (sauvés). */
    public static int count(World world, Hamlets.Place h) {
        return (int) Math.max(0, WorldLife.registry(world).getLong(WorldLifeRegistry.Part.GARRISONS, h.id(), 0));
    }

    static void setCount(World world, Hamlets.Place h, int n) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.GARRISONS, h.id(), n <= 0 ? null : Integer.toString(n));
    }

    /** Gardes voulus par le propriétaire. */
    public static int target(World world, Hamlets.Place h, Village owner) {
        if (owner == null) {
            return 0;
        }
        int n = owner.tier() >= 3 ? BASE_TIER3 : BASE;
        if (Allegiance.councilSpecialty(owner, Allegiance.GARRISON)) {
            n++;
        }
        Hamlet type = h.type();
        if (type != null && "Caserne".equals(type.type())) {
            n++;
        }
        return Math.min(POSTS.length, n);
    }

    /** Nouveau propriétaire (ou plus de propriétaire) : les gardes en place s'en vont. */
    static void reset(World world, Store<EntityStore> store, Hamlets.Place h) {
        despawn(store, h.id());
        setCount(world, h, 0);
    }

    /** Ajoute des gardes (relève arrivée, garde d'une ambassade, soldats vainqueurs), jusqu'au nombre voulu. */
    static void add(World world, Hamlets.Place h, Village owner, int n) {
        setCount(world, h, Math.min(target(world, h, owner), count(world, h) + n));
    }

    /** La relève est arrivée : seulement si son village tient toujours le lieu-dit. */
    static void arrived(World world, Store<EntityStore> store, Hamlets.Place h, Village v, int n) {
        Village owner = Allegiance.owner(world, h);
        if (owner != null && owner.id().equals(v.id())) {
            add(world, h, owner, n);
        }
    }

    /** Relève du matin : les gardes manquants partent du village. */
    static void morning(World world, Store<EntityStore> store, long day) {
        for (Hamlets.Place h : Hamlets.all(world)) {
            relieve(world, h);
        }
    }

    private static void relieve(World world, Hamlets.Place h) {
        Village owner = Allegiance.owner(world, h);
        if (owner == null || h.stage() != Hamlets.BUILT) {
            return;
        }
        int missing = target(world, h, owner) - count(world, h);
        if (missing > 0) {
            HamletTrips.startKind(world, h, owner, HamletTrips.GUARDS, missing);
        }
    }

    /** Le pas : gardes posés près des joueurs, retirés sinon ; joueurs Honnis repérés. */
    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        for (Hamlets.Place h : Hamlets.all(world)) {
            HOSTILE.remove(h.id()); // seulement les lieux-dits de ce monde : les autres mondes ont leur propre pas
            List<Ref<EntityStore>> live = LIVE.get(h.id());
            if (live != null) {
                live.removeIf(ref -> !ref.isValid());
            }
            Village owner = Allegiance.owner(world, h);
            int count = count(world, h);
            int[] m = h.market();
            if (owner == null || count <= 0 || h.stage() != Hamlets.BUILT || !WorldLife.near(players, m[0], m[1], WorldLife.REAL_RANGE)) {
                despawn(store, h.id());
                continue;
            }
            if (live == null) {
                live = new ArrayList<>();
                LIVE.put(h.id(), live);
            }
            while (live.size() > count) {
                Ref<EntityStore> ref = live.remove(live.size() - 1);
                GUARD_OF.remove(ref);
                WorldLife.remove(store, ref);
            }
            if (live.size() < count && WorldLife.budget(world, count - live.size())) {
                for (int i = live.size(); i < count; i++) {
                    int[] p = h.world(POSTS[i][0], POSTS[i][1]);
                    Vector3d at = WorldLife.ground(world, p[0], p[1], 5);
                    if (at == null) {
                        continue;
                    }
                    Ref<EntityStore> ref = WorldLife.spawn(store, Relations.fighterRole(owner.people()), at,
                            (float) Math.atan2(-(m[0] - p[0]), m[1] - p[1]));
                    if (ref == null) {
                        continue;
                    }
                    String id = h.id();
                    WorldLife.side(ref, sideKey(id), 0);
                    WorldLife.mortal(ref, (w, npc, where, killer) -> died(w, id, npc));
                    GUARD_OF.put(ref, id);
                    live.add(ref);
                }
            }
            for (int i = 0; i < live.size(); i++) {
                int[] p = h.world(POSTS[i][0], POSTS[i][1]);
                Vector3d to = WorldLife.ground(world, p[0], p[1], 5);
                if (to != null && !Sieges.besieged(h.id())) {
                    WorldLife.leash(store, live.get(i), to);
                }
            }
            Set<Ref<EntityStore>> hostile = ConcurrentHashMap.newKeySet();
            for (PlayerRef p : WorldLife.playersNear(world, store, m[0], m[1], WorldLife.REAL_RANGE)) {
                Ref<EntityStore> ref = p.getReference();
                if (ref != null && ref.isValid() && !Reputations.rank(store, ref, owner).atLeast(Rank.ETRANGER)) {
                    hostile.add(ref);
                }
            }
            if (!hostile.isEmpty()) {
                HOSTILE.put(h.id(), hostile);
            }
        }
    }

    /** Gardes vivants (réels) du lieu-dit. */
    static List<Ref<EntityStore>> alive(String hamlet) {
        List<Ref<EntityStore>> live = LIVE.get(hamlet);
        if (live == null) {
            return List.of();
        }
        live.removeIf(ref -> !ref.isValid());
        return live;
    }

    private static void died(World world, String hamlet, Ref<EntityStore> npc) {
        GUARD_OF.remove(npc);
        List<Ref<EntityStore>> live = LIVE.get(hamlet);
        if (live != null) {
            live.remove(npc);
        }
        Hamlets.Place h = Hamlets.get(world, hamlet);
        if (h == null) {
            return;
        }
        setCount(world, h, count(world, h) - 1);
        Village owner = Allegiance.owner(world, h);
        if (owner != null && Allegiance.councilSpecialty(owner, Allegiance.GARRISON) && !Sieges.besieged(hamlet)) {
            relieve(world, h); // Garnison : la relève part le jour même
        }
    }

    /** Attitude d'un garde envers un joueur Honni chez le propriétaire (null : rien à dire). */
    static Attitude attitude(Ref<EntityStore> ref, Ref<EntityStore> target) {
        String hamlet = GUARD_OF.get(ref);
        if (hamlet == null) {
            return null;
        }
        Set<Ref<EntityStore>> hostile = HOSTILE.get(hamlet);
        return hostile != null && hostile.contains(target) ? Attitude.HOSTILE : null;
    }

    private static void despawn(Store<EntityStore> store, String hamlet) {
        List<Ref<EntityStore>> live = LIVE.remove(hamlet);
        if (live == null) {
            return;
        }
        for (Ref<EntityStore> ref : live) {
            GUARD_OF.remove(ref);
            WorldLife.remove(store, ref);
        }
    }

    static void forget(Ref<EntityStore> ref) {
        String hamlet = GUARD_OF.remove(ref);
        if (hamlet != null) {
            List<Ref<EntityStore>> live = LIVE.get(hamlet);
            if (live != null) {
                live.remove(ref);
            }
        }
    }

    public static void clearAll() {
        LIVE.clear();
        GUARD_OF.clear();
        HOSTILE.clear();
    }
}
