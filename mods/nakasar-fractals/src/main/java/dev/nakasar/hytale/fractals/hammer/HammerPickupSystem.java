package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.MovementStates;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Ramasser un marteau du culte au sol ({@link HammerDropSystem}) : un joueur à moins de {@value #REACH} blocs reçoit
 * une fois l'indication « Accroupissez-vous pour ramasser le marteau », et s'accroupir à cette distance le ramasse
 * (le coût en PV reste celui de {@link HammerSystem}). L'indication revient s'il s'éloigne au-delà de
 * {@value #FORGET} blocs puis revient.
 */
public final class HammerPickupSystem extends TickingSystem<EntityStore> {

    public static final double REACH = 2.0;
    public static final double FORGET = 4.0;
    private static final float INTERVAL = 0.15f;
    private static final String MESSAGES = "nakasar_fractals_cliffside.hammer.";
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());
    /** Joueurs qui ont déjà eu l'indication, par monde (vidé quand ils s'éloignent de tout marteau). */
    private static final Map<World, Set<UUID>> HINTED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL || HammerDropSystem.onGround(world).isEmpty()) {
            return;
        }
        elapsed[0] = 0f;
        world.execute(() -> step(world));
    }

    private static void step(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Set<Ref<EntityStore>> hammers = HammerDropSystem.onGround(world);
        hammers.removeIf(ref -> !ref.isValid());
        Set<UUID> hinted = HINTED.computeIfAbsent(world, w -> new HashSet<>());
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                continue;
            }
            TransformComponent body = store.getComponent(ref, TransformComponent.getComponentType());
            if (body == null) {
                continue;
            }
            Vector3d at = body.getPosition();
            Ref<EntityStore> closest = null;
            double best = Double.MAX_VALUE;
            for (Ref<EntityStore> hammer : hammers) {
                TransformComponent t = store.getComponent(hammer, TransformComponent.getComponentType());
                if (t != null) {
                    double d = t.getPosition().distance(at);
                    if (d < best) {
                        best = d;
                        closest = hammer;
                    }
                }
            }
            if (closest == null || best > FORGET) {
                hinted.remove(player.getUuid());
                continue;
            }
            if (best > REACH || Hammer.carries(store, ref)) {
                continue;
            }
            if (crouching(store, ref)) {
                hammers.remove(closest);
                store.removeEntity(closest, RemoveReason.REMOVE);
                Hammer.give(store, ref);
                hinted.remove(player.getUuid());
            } else if (hinted.add(player.getUuid())) {
                NotificationUtil.sendNotification(player.getPacketHandler(),
                        Message.translation(MESSAGES + "crouchToTake"), NotificationStyle.Default);
            }
        }
    }

    private static boolean crouching(Store<EntityStore> store, Ref<EntityStore> ref) {
        MovementStatesComponent movement = store.getComponent(ref, MovementStatesComponent.getComponentType());
        MovementStates states = movement == null ? null : movement.getMovementStates();
        return states != null && (states.crouching || states.forcedCrouching);
    }
}
