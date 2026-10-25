package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.protocol.MovementStates;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/** Mouvements de joueur posés par le serveur (vitesse, téléportation) et ce qu'on lit de son état. */
final class Moves {

    private Moves() {
    }

    /** Pose la vitesse du joueur (le client la reçoit au tick suivant). */
    static void velocity(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, Vector3d v) {
        Velocity velocity = ref != null && ref.isValid() ? store.getComponent(ref, Velocity.getComponentType()) : null;
        if (velocity != null) {
            velocity.addInstruction(new Vector3d(v), null, ChangeVelocityType.Set);
        }
    }

    static void teleport(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, Vector3d at) {
        if (ref != null && ref.isValid()) {
            HeadRotation head = store.getComponent(ref, HeadRotation.getComponentType());
            Rotation3f rot = head == null ? new Rotation3f() : new Rotation3f(head.getRotation());
            store.putComponent(ref, Teleport.getComponentType(), Teleport.createForPlayer(new Transform(new Vector3d(at), rot)));
        }
    }

    /** Direction du regard (unitaire), null si inconnue. */
    static Vector3d look(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        HeadRotation head = ref != null && ref.isValid() ? store.getComponent(ref, HeadRotation.getComponentType()) : null;
        return head == null ? null : new Vector3d(head.getDirection()).normalize();
    }

    /** Direction horizontale du regard (unitaire). */
    static Vector3d flatLook(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        Vector3d look = look(store, ref);
        if (look == null || Math.abs(look.x()) + Math.abs(look.z()) < 1e-4) {
            return new Vector3d(0, 0, -1);
        }
        return new Vector3d(look.x(), 0, look.z()).normalize();
    }

    static boolean onGround(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        MovementStates s = states(store, ref);
        return s != null && s.onGround;
    }

    static boolean crouching(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        MovementStates s = states(store, ref);
        return s != null && (s.crouching || s.forcedCrouching);
    }

    static boolean moving(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        MovementStates s = states(store, ref);
        return s != null && !s.horizontalIdle;
    }

    private static MovementStates states(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        MovementStatesComponent m = ref != null && ref.isValid()
                ? store.getComponent(ref, MovementStatesComponent.getComponentType()) : null;
        return m == null ? null : m.getMovementStates();
    }
}
