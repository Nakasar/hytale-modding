package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.HealthRegenState;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import org.joml.Vector3d;

import java.util.List;
import java.util.Set;

/**
 * Aucun mob ne se régénère hors combat ou invulnérable (règle permanente de Kevin, AGENTS.md). Les prefabs vanilla des
 * villages font apparaître des Kweebecs (marqueurs d'apparition) : on coupe {@link HealthRegenState}, avant la
 * régénération vanilla, pour tout PNJ à moins de {@value #RADIUS} blocs d'un village du mod, comme le
 * {@code NoRegenSystem} du mod Vampires.
 */
public final class VillageNoRegenSystem extends EntityTickingSystem<EntityStore> {

    public static final int RADIUS = 96;

    private static final Query<EntityStore> QUERY = Query.and(NPCEntity.getComponentType(), HealthRegenState.getComponentType());

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency(Order.BEFORE, NPCPlugin.NPCEntityRegenerateStatsSystem.class));

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
        HealthRegenState regen = chunk.getComponent(index, HealthRegenState.getComponentType());
        if (regen == null || !regen.isRegenEnabled()) {
            return;
        }
        List<Village> villages = Villages.registry(store.getExternalData().getWorld()).all();
        if (villages.isEmpty()) {
            return;
        }
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        if (transform == null) {
            return;
        }
        Vector3d pos = transform.getPosition();
        for (Village village : villages) {
            if (village.horizontalDistanceSquared(pos.x(), pos.z()) <= (double) RADIUS * RADIUS) {
                regen.setRegenEnabled(false);
                return;
            }
        }
    }
}
