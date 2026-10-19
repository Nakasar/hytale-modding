package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.builtin.triggervolumes.manager.TriggerVolumeManager;
import com.hypixel.hytale.server.core.universe.world.World;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Barrière d'une arène de boss, comme les portes du Festin de Deepworks : la statue du point de contrôle est dehors ;
 * quand un joueur vivant est entré dans l'arène, la barrière se lève quelques secondes plus tard (volume
 * {@code <boss>_Gate}, tools/alchemist_traps.py, Traps.arena_gate : {@code Gate = Close}). Qui meurt revient à la statue
 * et ne peut plus rejoindre le combat. Plus aucun joueur vivant dans l'arène pendant le délai de remise à zéro du boss
 * (plus une seconde, pour que l'arène soit remise à zéro d'abord) : la barrière s'abaisse ({@code Gate = Open}) et le
 * groupe peut retenter. Boss vaincu : elle s'abaisse pour de bon.
 *
 * <p>Une barrière par volume et par monde (chaque instance de la tour a les siennes) ; à la première mise à jour dans un
 * monde, on l'abaisse : une barrière restée levée dans une instance rechargée ne bloque personne.
 */
final class ArenaGate {

    /** Présence continue d'un joueur vivant dans l'arène avant que la barrière ne commence à se lever. */
    private static final float ENTER_SECONDS = 1f;

    private static final Map<World, Map<String, ArenaGate>> GATES = Collections.synchronizedMap(new WeakHashMap<>());

    private final String volume;
    private final float reopenSeconds;
    private boolean closed;
    private boolean done;
    private float timer;

    private ArenaGate(String volume, float reopenSeconds) {
        this.volume = volume;
        this.reopenSeconds = reopenSeconds;
    }

    /** La barrière du volume {@code volume} dans ce monde ; {@code resetSeconds} : délai de remise à zéro du boss. */
    static ArenaGate of(World world, String volume, float resetSeconds, TriggerVolumeManager volumes) {
        Map<String, ArenaGate> gates = GATES.computeIfAbsent(world, w -> new HashMap<>());
        ArenaGate gate = gates.get(volume);
        if (gate == null) {
            gate = new ArenaGate(volume, resetSeconds + 1f);
            gates.put(volume, gate);
            gate.set(volumes, "Open");
        }
        return gate;
    }

    /** À chaque passage du système du boss (vivant) : {@code inside} = un joueur vivant est dans l'arène. */
    void update(TriggerVolumeManager volumes, boolean inside, float dt) {
        if (done || volumes == null) {
            return;
        }
        if (closed == inside) {
            timer = 0f;
            return;
        }
        timer += dt;
        if (!closed && timer >= ENTER_SECONDS) {
            closed = true;
            timer = 0f;
            set(volumes, "Close");
        } else if (closed && timer >= reopenSeconds) {
            closed = false;
            timer = 0f;
            set(volumes, "Open");
        }
    }

    /** Boss vaincu : la barrière s'abaisse et ne se relève plus. */
    void finish(TriggerVolumeManager volumes) {
        if (done || volumes == null) {
            return;
        }
        done = true;
        closed = false;
        set(volumes, "Open");
    }

    private void set(TriggerVolumeManager volumes, String value) {
        if (volumes != null) {
            volumes.setTag(volume, "Gate", value, null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
        }
    }
}
