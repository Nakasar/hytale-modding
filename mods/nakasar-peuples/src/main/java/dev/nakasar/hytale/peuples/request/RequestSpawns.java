package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/**
 * Les PNJ apparus pour les demandes (bande d'une chasse, attaque d'une défense, guetteur d'une livraison, captif d'une
 * escorte et ses gardiens) : non sauvegardés avec le monde, retrouvés par demande et par joueur pendant la session.
 * Après un redémarrage, ils réapparaissent quand le joueur revient près du lieu (seulement ce qui manque encore).
 */
public final class RequestSpawns {

    /** Ce qu'un PNJ apparu représente pour sa demande. */
    public enum Kind { FOE, LOOKOUT, CAPTIVE, GUARD, DEPARTING,
        /** PNJ du village escorté (caravanier, cueilleur). */
        ESCORTED,
        /** Assaillant d'une embuscade. */
        AMBUSH,
        /** Chef d'une demande de boss. */
        BOSS,
        /** Renfort d'un chef. */
        ADD }

    /** Clé des PNJ qui restent après leur demande (guetteur d'une missive) : ils partent quand plus personne n'est près. */
    public static final String LINGER = "linger";
    /** Un PNJ restant disparaît quand aucun joueur n'est à moins de cette distance (hors de vue). */
    public static final int DEPART_RANGE = 56;

    public record Owner(String key, Kind kind) {
    }

    private static final Map<String, List<Ref<EntityStore>>> BY_KEY = new HashMap<>();
    private static final Map<Ref<EntityStore>, Owner> OWNERS = Collections.synchronizedMap(new IdentityHashMap<>());

    private RequestSpawns() {
    }

    /** Clé d'une demande d'un joueur. */
    public static String key(java.util.UUID player, String requestId) {
        return player + "|" + requestId;
    }

    /** Fait apparaître `role` (non sauvegardé) en `at` pour la demande `key` ; null si le jeu refuse. */
    public static synchronized Ref<EntityStore> spawn(Store<EntityStore> store, String key, Kind kind, String role, Vector3d at, float yaw) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, yaw, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de faire apparaître '%s' pour une demande", role);
            return null;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        BY_KEY.computeIfAbsent(key, k -> new ArrayList<>()).add(ref);
        OWNERS.put(ref, new Owner(key, kind));
        return ref;
    }

    /** PNJ encore valides de la demande `key` (du genre `kind`, ou tous si null). */
    public static synchronized List<Ref<EntityStore>> of(String key, Kind kind) {
        List<Ref<EntityStore>> refs = BY_KEY.get(key);
        List<Ref<EntityStore>> out = new ArrayList<>();
        if (refs == null) {
            return out;
        }
        refs.removeIf(r -> {
            if (!r.isValid()) {
                OWNERS.remove(r);
                return true;
            }
            return false;
        });
        for (Ref<EntityStore> r : refs) {
            Owner o = OWNERS.get(r);
            if (kind == null || (o != null && o.kind() == kind)) {
                out.add(r);
            }
        }
        return out;
    }

    /** Tous les PNJ valides du genre `kind`, toutes demandes confondues, avec leur clé. */
    public static synchronized Map<Ref<EntityStore>, String> all(Kind kind) {
        Map<Ref<EntityStore>, String> out = new java.util.LinkedHashMap<>();
        for (Map.Entry<String, List<Ref<EntityStore>>> e : BY_KEY.entrySet()) {
            for (Ref<EntityStore> r : e.getValue()) {
                Owner o = OWNERS.get(r);
                if (r.isValid() && o != null && o.kind() == kind) {
                    out.put(r, e.getKey());
                }
            }
        }
        return out;
    }

    /** Premier PNJ valide du genre `kind` de la demande, ou null. */
    public static Ref<EntityStore> first(String key, Kind kind) {
        List<Ref<EntityStore>> refs = of(key, kind);
        return refs.isEmpty() ? null : refs.get(0);
    }

    /** À quelle demande appartient ce PNJ (null : à aucune). */
    public static Owner owner(Ref<EntityStore> ref) {
        return ref == null ? null : OWNERS.get(ref);
    }

    /** Oublie un PNJ (mort) sans le retirer du monde. */
    public static synchronized void forget(Ref<EntityStore> ref) {
        Owner o = OWNERS.remove(ref);
        if (o != null) {
            List<Ref<EntityStore>> refs = BY_KEY.get(o.key());
            if (refs != null) {
                refs.remove(ref);
            }
        }
    }

    /** Retire du monde les PNJ de la demande `key` (du genre `kind`, ou tous si null). */
    public static synchronized void remove(Store<EntityStore> store, String key, Kind kind) {
        for (Ref<EntityStore> r : of(key, kind)) {
            forget(r);
            if (r.isValid()) {
                store.removeEntity(r, RemoveReason.REMOVE);
            }
        }
        List<Ref<EntityStore>> refs = BY_KEY.get(key);
        if (refs != null && refs.isEmpty()) {
            BY_KEY.remove(key);
        }
    }

    /**
     * Les PNJ `kind` de la demande `key` ne disparaissent pas avec elle : ils restent (le guetteur reprend sa garde)
     * jusqu'à ce qu'aucun joueur ne soit à moins de {@value #DEPART_RANGE} blocs ({@link #stepLingering}).
     */
    public static synchronized void release(String key, Kind kind) {
        for (Ref<EntityStore> r : of(key, kind)) {
            forget(r);
            BY_KEY.computeIfAbsent(LINGER, k -> new ArrayList<>()).add(r);
            OWNERS.put(r, new Owner(LINGER, Kind.DEPARTING));
        }
    }

    /** Retire les PNJ restants que plus aucun joueur ne voit (thread du monde). */
    public static synchronized void stepLingering(Store<EntityStore> store, List<Vector3d> players) {
        for (Ref<EntityStore> r : of(LINGER, null)) {
            Vector3d at = Requests.position(store, r);
            boolean seen = false;
            for (Vector3d p : players) {
                if (at != null && p.distanceSquared(at) <= (double) DEPART_RANGE * DEPART_RANGE) {
                    seen = true;
                    break;
                }
            }
            if (!seen) {
                forget(r);
                store.removeEntity(r, RemoveReason.REMOVE);
            }
        }
    }

    /** Rôle du PNJ, ou null. */
    public static String role(Store<EntityStore> store, Ref<EntityStore> ref) {
        NPCEntity npc = ref == null || !ref.isValid() ? null : store.getComponent(ref, NPCEntity.getComponentType());
        return npc == null ? null : npc.getRoleName();
    }

    public static synchronized void clearAll() {
        BY_KEY.clear();
        OWNERS.clear();
    }
}
