package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Cercle d'harmonisation de l'Observatoire, deux fois par seconde : qui est présent (et donc qui mène), qui se tient
 * sur le cercle (le groupe, {@value Observatory#MAX_GROUP} au plus, dans l'ordre d'arrivée sur le cercle).
 *
 * <p>Un joueur est sur le cercle quand ses pieds sont entre {@link ObservatoryLayout#CIRCLE_INNER} et
 * {@link ObservatoryLayout#CIRCLE_OUTER} blocs du centre de l'Astrolabe, à moins de 2 blocs du dallage. Il est prévenu
 * quand il rejoint ou quitte le groupe, ou quand le cercle est complet.
 */
public final class HarmonyCircleSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.5f;
    /** Temps écoulé depuis le dernier passage, par monde (le système sert à tous les mondes). */
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (!FractalCatalog.isObservatory(world)) {
            return;
        }
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        elapsed[0] = 0f;
        // Le store est en plein traitement : on regarde juste après.
        world.execute(() -> scan(world));
    }

    private static void scan(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        FractalRuns.releaseHolds(world);
        Observatory.State state = Observatory.state(world);
        Set<UUID> here = new HashSet<>();
        Set<UUID> onCircle = new HashSet<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            UUID id = player.getUuid();
            here.add(id);
            Ref<EntityStore> ref = player.getReference();
            TransformComponent transform = ref == null || !ref.isValid() ? null
                    : store.getComponent(ref, TransformComponent.getComponentType());
            if (transform != null && onCircle(transform.getPosition())) {
                onCircle.add(id);
            }
        }
        state.present.retainAll(here);
        state.present.addAll(here);   // nouveaux arrivants en fin d'ordre
        updateLeader(world, state);

        for (UUID id : Set.copyOf(state.circle)) {
            if (!onCircle.contains(id)) {
                state.circle.remove(id);
                send(world, id, Message.translation(Observatory.MESSAGES + "left"));
            }
        }
        state.refused.retainAll(onCircle);
        for (UUID id : onCircle) {
            if (state.circle.contains(id)) {
                continue;
            }
            if (state.circle.size() >= Observatory.MAX_GROUP) {
                if (state.refused.add(id)) {
                    send(world, id, Message.translation(Observatory.MESSAGES + "full"));
                }
                continue;
            }
            state.circle.add(id);
            state.refused.remove(id);
            send(world, id, Message.translation(Observatory.MESSAGES + "joined").param("count", state.circle.size()));
        }
    }

    private static void updateLeader(World world, Observatory.State state) {
        if (state.leader != null && state.present.contains(state.leader)) {
            return;
        }
        UUID next = state.present.isEmpty() ? null : state.present.iterator().next();
        state.leader = next;
        if (next == null) {
            return;
        }
        String name = Observatory.nameOf(world, next);
        for (PlayerRef player : world.getPlayerRefs()) {
            player.sendMessage(next.equals(player.getUuid())
                    ? Message.translation(Observatory.MESSAGES + "leader")
                    : Message.translation(Observatory.MESSAGES + "newLeader").param("name", name));
        }
    }

    static boolean onCircle(Vector3d feet) {
        double dx = feet.x() - 0.5;
        double dz = feet.z() - 0.5;
        double distance = Math.sqrt(dx * dx + dz * dz);
        return distance >= ObservatoryLayout.CIRCLE_INNER && distance <= ObservatoryLayout.CIRCLE_OUTER
                && Math.abs(feet.y() - ObservatoryLayout.GROUND_Y) < 2;
    }

    private static void send(World world, UUID id, Message message) {
        PlayerRef player = Observatory.find(world, id);
        if (player != null) {
            player.sendMessage(message);
        }
    }
}
