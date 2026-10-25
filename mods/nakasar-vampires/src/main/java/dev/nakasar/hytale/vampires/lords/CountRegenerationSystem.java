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
import dev.nakasar.hytale.vampires.boss.RecentDamage;

/**
 * Régénération du Comte et de la Comtesse Vampire : {@value #HEALTH_PER_SECOND} PV par seconde pendant le combat
 * (plafonnés à leur maximum par leur table de statistiques). Avec leurs 8000 PV, il faut un groupe armé d'argent qui
 * frappe sans relâche pour les faire plier : le Comté n'est pas l'endroit pour les vaincre (un donjon leur sera
 * consacré). Jamais hors combat ni invulnérables ({@link RecentDamage}, consigne permanente de Kevin, AGENTS.md).
 */
public final class CountRegenerationSystem extends EntityTickingSystem<EntityStore> {

    public static final String COUNT_ROLE = "Nakasar_Vampire_Count";
    public static final String COUNTESS_ROLE = "Nakasar_Vampire_Countess";
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
        if (npc == null || !(COUNT_ROLE.equals(npc.getRoleName()) || COUNTESS_ROLE.equals(npc.getRoleName()))
                || chunk.getComponent(index, DeathComponent.getComponentType()) != null
                || !RecentDamage.mayHeal(chunk.getReferenceTo(index), store)) {
            return;
        }
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        EntityStatValue health = stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null && health.get() > 0f && health.get() < health.getMax()) {
            stats.addStatValue(DefaultEntityStatTypes.getHealth(), HEALTH_PER_SECOND * dt);
        }
    }
}
