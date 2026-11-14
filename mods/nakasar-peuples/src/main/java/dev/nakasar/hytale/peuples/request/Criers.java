package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;

/**
 * Les villageois à poste fixe de chaque village, posés par le Java quand un joueur approche :
 * <ul>
 *   <li>le <b>crieur</b> (étape 3 ; GDD : « une demande se prend au tableau ou auprès d'un villageois, et se rend par
 *       une réponse »), deux blocs au sud du tableau, dialogue {@code <Peuple>_Crieur} ;</li>
 *   <li>le <b>marchand</b> (étape 4 ; GDD, Le dépôt et le tableau : « les marchands du village ouvrent une boutique de
 *       troc vanilla, une par peuple et par rang »), deux blocs au sud du dépôt, dialogue {@code <Peuple>_Marchand} ;</li>
 *   <li>le <b>chef</b> (étape 6 ; GDD, Qui parle et de quoi : « la chaîne du peuple, l'état du village »), à l'est du
 *       cœur, dialogue {@code <Peuple>_Chef}.</li>
 * </ul>
 * Non sauvegardés : ils reviennent à chaque session. Tués, ils ne reviennent qu'au matin suivant (GDD, Villageois et
 * métiers : « un PNJ tué réapparaît au prochain matin »).
 */
public final class Criers {

    /** Un villageois à poste fixe. */
    public enum Post {
        CRIER,
        MERCHANT,
        CHIEF;

        String role(Village village) {
            return switch (this) {
                case CRIER -> village.people().crierRole();
                case MERCHANT -> village.people().merchantRole();
                case CHIEF -> village.people().chiefRole();
            };
        }

        /** Où il se tient : deux blocs au sud du tableau (crieur) ou du dépôt (marchand), à l'est du cœur (chef). */
        public Vector3d spot(Village village) {
            if (this == CHIEF) {
                return new Vector3d(village.x() + 3.5, village.y(), village.z() - 2.5);
            }
            int[] b = this == CRIER ? village.board() : village.deposit();
            return new Vector3d(b[0] + 0.5, b[1], b[2] + 2.5);
        }
    }

    /** Les villageois apparaissent quand un joueur passe à moins de cette distance du cœur. */
    public static final int RANGE = 48;

    private record Key(String village, Post post) {
    }

    private record Spawned(String village, Post post) {
    }

    private static final Map<Key, Ref<EntityStore>> BY_VILLAGE = new HashMap<>();
    private static final Map<Ref<EntityStore>, Spawned> SPAWNED = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Poste -> jour de jeu de la mort de son villageois. */
    private static final Map<Key, Long> DEATHS = new HashMap<>();

    private Criers() {
    }

    /** Pose les villageois des villages proches de `at` qui n'en ont pas. */
    public static synchronized void ensureNear(World world, Store<EntityStore> store, Vector3d at) {
        for (Village village : Villages.registry(world).all()) {
            if (village.horizontalDistanceSquared(at.x(), at.z()) > (double) RANGE * RANGE) {
                continue;
            }
            for (Post post : Post.values()) {
                Key key = new Key(village.id(), post);
                Ref<EntityStore> npc = BY_VILLAGE.get(key);
                if (npc != null && npc.isValid()) {
                    continue;
                }
                if (npc != null) {
                    SPAWNED.remove(npc);
                    BY_VILLAGE.remove(key);
                }
                Long death = DEATHS.get(key);
                if (death != null && death >= GameClock.day(store)) {
                    continue;
                }
                spawn(store, village, post);
            }
        }
    }

    /** Où se tient le crieur : deux blocs au sud du tableau. */
    public static Vector3d spot(Village village) {
        return Post.CRIER.spot(village);
    }

    private static void spawn(Store<EntityStore> store, Village village, Post post) {
        String role = post.role(village);
        Vector3d at = post.spot(village);
        Key key = new Key(village.id(), post);
        // Tourné vers le nord (le tableau, le dépôt et la place).
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, 0f, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de poser '%s' au village %s", role, village.name());
            DEATHS.put(key, Long.MAX_VALUE - 1);
            return;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        BY_VILLAGE.put(key, ref);
        SPAWNED.put(ref, new Spawned(village.id(), post));
    }

    /** Id du village dont `ref` est le crieur, ou null. */
    public static String villageOf(Ref<EntityStore> ref) {
        Spawned s = ref == null ? null : SPAWNED.get(ref);
        return s != null && s.post() == Post.CRIER ? s.village() : null;
    }

    /** Id du village dont `ref` est le marchand, ou null. */
    public static String merchantVillageOf(Ref<EntityStore> ref) {
        Spawned s = ref == null ? null : SPAWNED.get(ref);
        return s != null && s.post() == Post.MERCHANT ? s.village() : null;
    }

    /** Id du village dont `ref` est le chef, ou null. */
    public static String chiefVillageOf(Ref<EntityStore> ref) {
        Spawned s = ref == null ? null : SPAWNED.get(ref);
        return s != null && s.post() == Post.CHIEF ? s.village() : null;
    }

    /** Vrai si `ref` est un villageois à poste fixe (crieur, marchand). */
    public static boolean isPosted(Ref<EntityStore> ref) {
        return ref != null && SPAWNED.containsKey(ref);
    }

    /** Le villageois `ref` est mort : il reviendra au matin. */
    public static synchronized void died(Store<EntityStore> store, Ref<EntityStore> ref) {
        Spawned s = SPAWNED.remove(ref);
        if (s != null) {
            Key key = new Key(s.village(), s.post());
            BY_VILLAGE.remove(key);
            DEATHS.put(key, GameClock.day(store));
        }
    }

    /** Retire les villageois du village (village effacé). */
    public static synchronized void remove(Store<EntityStore> store, String villageId) {
        for (Post post : Post.values()) {
            Ref<EntityStore> ref = BY_VILLAGE.remove(new Key(villageId, post));
            if (ref != null) {
                SPAWNED.remove(ref);
                if (ref.isValid()) {
                    store.removeEntity(ref, RemoveReason.REMOVE);
                }
            }
        }
    }

    public static synchronized void clearAll() {
        BY_VILLAGE.clear();
        SPAWNED.clear();
        DEATHS.clear();
    }
}
