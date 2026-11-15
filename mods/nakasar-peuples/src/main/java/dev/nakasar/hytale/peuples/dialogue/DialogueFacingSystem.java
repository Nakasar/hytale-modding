package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.physics.util.PhysicsMath;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.movement.Steering;
import com.hypixel.hytale.server.npc.role.Role;
import com.hypixel.hytale.server.npc.systems.AvoidanceSystem;
import com.hypixel.hytale.server.npc.systems.SteeringSystem;
import org.joml.Vector3d;

import java.util.Set;

/**
 * Le PNJ en conversation ({@link DialogueFacing}) fait face au joueur : à chaque tick, entre le calcul de son IA et son
 * application (comme l'évitement du feu purificateur du mod Vampires), son déplacement est annulé, son corps tourné vers
 * le joueur et sa tête le regarde (même écart de hauteur que leurs pieds), avec les fonctions de la tête « Watch » vanilla (HeadMotionWatch).
 */
public final class DialogueFacingSystem extends EntityTickingSystem<EntityStore> {

    private static final Query<EntityStore> QUERY =
            Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, AvoidanceSystem.class),
            new SystemDependency<>(Order.BEFORE, SteeringSystem.class));
    /** Au-delà, le joueur est parti sans fermer la fenêtre : le PNJ reprend sa vie. */
    private static final double MAX_DISTANCE = 12.0;

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        if (DialogueFacing.TALKS.isEmpty()) {
            return;
        }
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        DialogueFacing.Talk talk = DialogueFacing.TALKS.get(ref);
        if (talk == null) {
            return;
        }
        Ref<EntityStore> player = talk.player();
        TransformComponent pt = player.isValid() && player.getStore() == store
                ? store.getComponent(player, TransformComponent.getComponentType()) : null;
        Vector3d at = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        if (pt == null || System.nanoTime() - talk.since() > DialogueFacing.MAX_NANOS) {
            DialogueFacing.TALKS.remove(ref, talk);
            return;
        }
        Vector3d p = pt.getPosition();
        double dx = p.x() - at.x();
        double dy = p.y() - at.y();
        double dz = p.z() - at.z();
        double flat = Math.sqrt(dx * dx + dz * dz);
        if (flat > MAX_DISTANCE) {
            DialogueFacing.TALKS.remove(ref, talk);
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Role role = npc == null ? null : npc.getRole();
        if (role == null || flat < 1e-3) {
            return;
        }
        float yaw = PhysicsMath.normalizeTurnAngle(PhysicsMath.headingFromDirection(dx, dz));
        Steering body = role.getBodySteering();
        body.clearTranslation();
        body.setYaw(yaw);
        Steering head = role.getHeadSteering();
        head.clearTranslation();
        head.setYaw(yaw);
        head.setPitch(PhysicsMath.pitchFromDirection(dx, dy, dz));
    }
}
