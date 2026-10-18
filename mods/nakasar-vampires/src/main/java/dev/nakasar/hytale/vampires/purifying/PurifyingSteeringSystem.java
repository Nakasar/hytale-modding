package dev.nakasar.hytale.vampires.purifying;

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
import java.util.Set;
import org.joml.Vector3d;

/**
 * Évitement du feu purificateur : à chaque tick, entre le calcul du déplacement voulu par le rôle (et l'évitement
 * des obstacles du jeu) et son application, on corrige la direction de marche d'un mort-vivant proche d'un feu.
 * Il ne reçoit aucune poussée : il marche, à sa propre vitesse.
 * <ul>
 *   <li>à moins de {@value PurifyingFireSystem#RADIUS} + {@value PurifyingFireSystem#APPROACH} blocs, la part de
 *       son déplacement qui le rapprocherait du feu est retirée : il longe la limite au lieu d'avancer ;</li>
 *   <li>dans le rayon {@value PurifyingFireSystem#RADIUS}, il s'éloigne en plus en marchant, d'autant plus vite
 *       qu'il est près du feu.</li>
 * </ul>
 * Les feux proches de chaque mort-vivant sont relevés par {@link PurifyingFireSystem} (quatre fois par seconde).
 */
public final class PurifyingSteeringSystem extends EntityTickingSystem<EntityStore> {

    /** Vitesse relative de fuite au bord du rayon et contre le feu. */
    private static final double FLEE_MIN = 0.35;
    private static final double FLEE_MAX = 0.8;

    private static final Query<EntityStore> QUERY =
            Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, AvoidanceSystem.class),
            new SystemDependency<>(Order.BEFORE, SteeringSystem.class));

    private final PurifyingFires fires;

    public PurifyingSteeringSystem(PurifyingFires fires) {
        this.fires = fires;
    }

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
        return false; // lit la table des feux tenue par PurifyingFireSystem
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        if (fires.isEmpty()) {
            return;
        }
        double[] nearby = fires.get(chunk.getReferenceTo(index));
        if (nearby == null) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Role role = npc == null ? null : npc.getRole();
        if (role == null) {
            return;
        }
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        // direction de fuite : somme des répulsions des feux proches, la plus forte près du feu le plus proche
        double awayX = 0;
        double awayZ = 0;
        double nearest = Double.MAX_VALUE;
        double outer = PurifyingFireSystem.RADIUS + PurifyingFireSystem.APPROACH;
        for (int i = 0; i < nearby.length; i += 2) {
            double dx = position.x - nearby[i];
            double dz = position.z - nearby[i + 1];
            double d = Math.max(0.5, Math.sqrt(dx * dx + dz * dz));
            if (d > outer) {
                continue;
            }
            nearest = Math.min(nearest, d);
            double weight = (outer - d) / (d * d);
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
        double x = move.x;
        double z = move.z;
        double toward = -(x * awayX + z * awayZ);
        if (toward > 0) {
            // retire la part du déplacement qui va vers le feu : il glisse le long de la limite
            x += awayX * toward;
            z += awayZ * toward;
        }
        if (nearest < PurifyingFireSystem.RADIUS) {
            double closeness = 1 - nearest / PurifyingFireSystem.RADIUS;
            double flee = FLEE_MIN + (FLEE_MAX - FLEE_MIN) * closeness;
            double outward = x * awayX + z * awayZ;
            if (outward < flee) {
                x += awayX * (flee - outward);
                z += awayZ * (flee - outward);
            }
        } else if (toward <= 0) {
            return;
        }
        double horizontal = Math.sqrt(x * x + z * z);
        if (horizontal > 1) {
            x /= horizontal;
            z /= horizontal;
        }
        steering.setTranslation(x, move.y, z);
    }
}
