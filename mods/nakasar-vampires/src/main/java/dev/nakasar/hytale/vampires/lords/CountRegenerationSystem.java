package dev.nakasar.hytale.vampires.lords;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

/**
 * Régénération du Comte Vampire : {@value #HEALTH_PER_SECOND} PV par seconde en permanence, en combat compris
 * (plafonnés à son maximum par sa table de statistiques). Avec ses 8000 PV, il faut un groupe armé d'argent qui frappe
 * sans relâche pour le faire plier : le Comté n'est pas l'endroit pour le vaincre (un donjon lui sera consacré).
 */
public final class CountRegenerationSystem extends EntityTickingSystem<EntityStore> {

    public static final String COUNT_ROLE = "Nakasar_Vampire_Count";
    public static final float HEALTH_PER_SECOND = 150f;

    private static final Query<EntityStore> QUERY = Query.and(NPCEntity.getComponentType(), EntityStatMap.getComponentType());

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        if (npc == null || !COUNT_ROLE.equals(npc.getRoleName())
                || chunk.getComponent(index, DeathComponent.getComponentType()) != null) {
            return;
        }
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        EntityStatValue health = stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null && health.get() > 0f && health.get() < health.getMax()) {
            stats.addStatValue(DefaultEntityStatTypes.getHealth(), HEALTH_PER_SECOND * dt);
        }
    }
}
