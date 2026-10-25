package dev.nakasar.hytale.vampires.boss;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.HealthRegenState;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

import java.util.Set;

/**
 * Aucun PNJ du mod ne se régénère hors combat ou invulnérable (consigne permanente de Kevin, 25 octobre 2026, voir
 * AGENTS.md). La vie des PNJ vanilla remonte de 5 % toutes les 0,5 s après 15 s sans dégâts (Server/Entity/Stats/
 * Health.json, condition {@code RegenHealth}), donc justement hors combat ou sous le composant {@code Invulnerable} des
 * élites protégées : on coupe {@link HealthRegenState} des rôles {@value #PREFIX}* à chaque tick, avant la
 * régénération. Les soins voulus (seigneurs, rouages) passent par le Java et ne valent qu'en combat
 * ({@link RecentDamage}).
 */
public final class NoRegenSystem extends EntityTickingSystem<EntityStore> {

    public static final String PREFIX = "Nakasar_";

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
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        String role = npc == null ? null : npc.getRoleName();
        if (role != null && role.startsWith(PREFIX)) {
            regen.setRegenEnabled(false);
        }
    }
}
