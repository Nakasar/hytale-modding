package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.movement.Steering;
import com.hypixel.hytale.server.npc.role.Role;
import com.hypixel.hytale.server.npc.systems.AvoidanceSystem;
import com.hypixel.hytale.server.npc.systems.SteeringSystem;
import org.joml.Vector3d;

import java.util.List;
import java.util.Set;

/**
 * Espacement des PNJ escortés (caravaniers, cueilleurs) : tous suivent le même joueur et s'arrêteraient au même point,
 * empilés. Entre le déplacement voulu par le rôle (et l'évitement d'obstacles du jeu) et son application, chacun
 * s'écarte en marchant des autres membres de sa demande à moins de {@value #SPACING} blocs. Pas de poussée : il marche.
 */
public final class EscortSpacingSystem extends EntityTickingSystem<EntityStore> {

    /** Distance voulue entre deux membres d'un même groupe. */
    static final double SPACING = 2.5;
    /** Vitesse relative de l'écart quand deux membres se touchent. */
    private static final double SPREAD_MAX = 0.7;

    private static final Query<EntityStore> QUERY = Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, AvoidanceSystem.class),
            new SystemDependency<>(Order.BEFORE, SteeringSystem.class));

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
        return false; // lit la position des autres membres du groupe
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> self = chunk.getReferenceTo(index);
        RequestSpawns.Owner owner = RequestSpawns.owner(self);
        if (owner == null || owner.kind() != RequestSpawns.Kind.ESCORTED || store.getComponent(self, Frozen.getComponentType()) != null) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Role role = npc == null ? null : npc.getRole();
        if (role == null) {
            return;
        }
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        List<Ref<EntityStore>> group = RequestSpawns.of(owner.key(), RequestSpawns.Kind.ESCORTED);
        double awayX = 0;
        double awayZ = 0;
        double nearest = Double.MAX_VALUE;
        for (int i = 0; i < group.size(); i++) {
            Ref<EntityStore> other = group.get(i);
            if (other == self || !other.isValid()) {
                continue;
            }
            TransformComponent t = store.getComponent(other, TransformComponent.getComponentType());
            if (t == null) {
                continue;
            }
            double dx = position.x - t.getPosition().x;
            double dz = position.z - t.getPosition().z;
            double d = Math.sqrt(dx * dx + dz * dz);
            if (d >= SPACING || Math.abs(position.y - t.getPosition().y) > 2) {
                continue;
            }
            if (d < 1.0e-3) {
                // Exactement au même point : chacun part dans une direction tirée de son rang dans le groupe.
                double angle = i * 2.399963;
                dx = Math.cos(angle) * 0.01;
                dz = Math.sin(angle) * 0.01;
                d = 0.01;
            }
            nearest = Math.min(nearest, d);
            double weight = (SPACING - d) / d;
            awayX += dx * weight;
            awayZ += dz * weight;
        }
        double length = Math.sqrt(awayX * awayX + awayZ * awayZ);
        if (nearest == Double.MAX_VALUE || length < 1.0e-6) {
            return;
        }
        awayX /= length;
        awayZ /= length;
        Steering steering = role.getBodySteering();
        Vector3d move = steering.getTranslation();
        double spread = SPREAD_MAX * (1 - nearest / SPACING);
        double x = move.x;
        double z = move.z;
        double outward = x * awayX + z * awayZ;
        if (outward < spread) {
            x += awayX * (spread - outward);
            z += awayZ * (spread - outward);
        }
        double horizontal = Math.sqrt(x * x + z * z);
        if (horizontal > 1) {
            x /= horizontal;
            z /= horizontal;
        }
        steering.setTranslation(x, move.y, z);
    }
}
