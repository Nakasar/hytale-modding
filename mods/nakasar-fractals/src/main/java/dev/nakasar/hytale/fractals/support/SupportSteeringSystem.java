package dev.nakasar.hytale.fractals.support;

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
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.movement.Steering;
import com.hypixel.hytale.server.npc.role.Role;
import com.hypixel.hytale.server.npc.systems.AvoidanceSystem;
import com.hypixel.hytale.server.npc.systems.SteeringSystem;
import org.joml.Vector3d;

import java.util.Set;

/**
 * Ralentissements et peur des runes de soutien sur les PNJ. Un effet de statut qui ralentit n'agit que sur les joueurs
 * (leur mouvement vient du client) : pour un PNJ, on corrige à chaque tick le déplacement voulu par son rôle, entre le
 * calcul de l'IA (et l'évitement des obstacles) et son application, comme l'évitement du feu purificateur du mod
 * Vampires.
 * <ul>
 *   <li>ralenti : la vitesse voulue est multipliée par (1 - part) ({@link SupportStates#slowOf}) ;</li>
 *   <li>effrayé : il marche droit à l'opposé du point de peur, à pleine vitesse ralentie comprise.</li>
 * </ul>
 */
public final class SupportSteeringSystem extends EntityTickingSystem<EntityStore> {

    private static final Query<EntityStore> QUERY =
            Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, AvoidanceSystem.class),
            new SystemDependency<>(Order.BEFORE, SteeringSystem.class));
    private static final long PRUNE_EVERY = 5_000_000_000L;

    private long nextPrune;

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
        if (SupportStates.SLOWS.isEmpty() && SupportStates.FEARS.isEmpty()) {
            return;
        }
        long now = System.nanoTime();
        if (now - nextPrune >= 0) {
            nextPrune = now + PRUNE_EVERY;
            SupportStates.prune();
        }
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        float slow = SupportStates.slowOf(ref, now);
        SupportStates.Fear fear = SupportStates.FEARS.get(ref);
        if (fear != null && now >= fear.until()) {
            SupportStates.FEARS.remove(ref);
            fear = null;
        }
        if (slow <= 0f && fear == null) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Role role = npc == null ? null : npc.getRole();
        if (role == null) {
            return;
        }
        Steering steering = role.getBodySteering();
        Vector3d move = steering.getTranslation();
        double x = move.x;
        double z = move.z;
        if (fear != null) {
            Vector3d at = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
            double dx = at.x - fear.from().x();
            double dz = at.z - fear.from().z();
            double d = Math.sqrt(dx * dx + dz * dz);
            if (d < 1e-3) {
                dx = 1;
                dz = 0;
                d = 1;
            }
            x = dx / d;
            z = dz / d;
        }
        double keep = 1.0 - slow;
        steering.setTranslation(x * keep, move.y, z * keep);
    }
}
