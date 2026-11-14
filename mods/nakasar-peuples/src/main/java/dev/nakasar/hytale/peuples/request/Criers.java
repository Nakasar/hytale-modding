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
 * Le crieur de chaque village (GDD : « une demande se prend au tableau ou auprès d'un villageois, et se rend par une
 * réponse ») : un Kweebec posé à deux blocs au sud du tableau quand un joueur approche, qu'on utilise pour ouvrir son
 * dialogue ({@code <Peuple>_Crieur}). Non sauvegardé : il revient à chaque session. Tué, il ne revient qu'au matin
 * suivant (GDD, Villageois et métiers : « un PNJ tué réapparaît au prochain matin »).
 */
public final class Criers {

    /** Le crieur apparaît quand un joueur passe à moins de cette distance du cœur. */
    public static final int RANGE = 48;

    private static final Map<String, Ref<EntityStore>> BY_VILLAGE = new HashMap<>();
    private static final Map<Ref<EntityStore>, String> VILLAGES = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Village -> jour de jeu de la mort de son crieur. */
    private static final Map<String, Long> DEATHS = new HashMap<>();

    private Criers() {
    }

    /** Pose le crieur des villages proches de `at` qui n'en ont pas. */
    public static synchronized void ensureNear(World world, Store<EntityStore> store, Vector3d at) {
        for (Village village : Villages.registry(world).all()) {
            if (village.horizontalDistanceSquared(at.x(), at.z()) > (double) RANGE * RANGE) {
                continue;
            }
            Ref<EntityStore> crier = BY_VILLAGE.get(village.id());
            if (crier != null && crier.isValid()) {
                continue;
            }
            if (crier != null) {
                VILLAGES.remove(crier);
                BY_VILLAGE.remove(village.id());
            }
            Long death = DEATHS.get(village.id());
            if (death != null && death >= GameClock.day(store)) {
                continue;
            }
            spawn(store, village);
        }
    }

    /** Où se tient le crieur : deux blocs au sud du tableau. */
    public static Vector3d spot(Village village) {
        int[] b = village.board();
        return new Vector3d(b[0] + 0.5, b[1], b[2] + 2.5);
    }

    private static void spawn(Store<EntityStore> store, Village village) {
        String role = village.people().crierRole();
        Vector3d at = spot(village);
        // Tourné vers le nord (le tableau et la place).
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, 0f, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de poser le crieur '%s' du village %s", role, village.name());
            DEATHS.put(village.id(), Long.MAX_VALUE - 1);
            return;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        BY_VILLAGE.put(village.id(), ref);
        VILLAGES.put(ref, village.id());
    }

    /** Id du village dont `ref` est le crieur, ou null. */
    public static String villageOf(Ref<EntityStore> ref) {
        return ref == null ? null : VILLAGES.get(ref);
    }

    /** Le crieur `ref` est mort : il reviendra au matin. */
    public static synchronized void died(Store<EntityStore> store, Ref<EntityStore> ref) {
        String village = VILLAGES.remove(ref);
        if (village != null) {
            BY_VILLAGE.remove(village);
            DEATHS.put(village, GameClock.day(store));
        }
    }

    /** Retire le crieur du village (village effacé). */
    public static synchronized void remove(Store<EntityStore> store, String villageId) {
        Ref<EntityStore> ref = BY_VILLAGE.remove(villageId);
        if (ref != null) {
            VILLAGES.remove(ref);
            if (ref.isValid()) {
                store.removeEntity(ref, RemoveReason.REMOVE);
            }
        }
    }

    public static synchronized void clearAll() {
        BY_VILLAGE.clear();
        VILLAGES.clear();
        DEATHS.clear();
    }
}
