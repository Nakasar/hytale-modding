package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.modules.entity.component.HealthRegenState;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;
import dev.nakasar.hytale.peuples.request.RequestSpawns;
import org.joml.Vector3d;

import java.util.EnumSet;
import java.util.List;
import java.util.Set;

/**
 * Régénération des PNJ du mod. Les PNJ amicaux (villageois, gardes, défenseurs, marchands, voyageurs, captifs,
 * escortés, bêtes des enclos, troupeaux) gardent la régénération vanilla des PNJ ({@code Server/Entity/Stats/
 * Health.json}, condition {@code RegenHealth} : +5 % toutes les 0,5 s après 15 s sans dégâts), demandée par Kevin le
 * 16 novembre 2026. Les mobs hostiles ne se régénèrent JAMAIS (règle permanente n° 1, AGENTS.md) : on coupe
 * {@link HealthRegenState}, avant {@code NPCPlugin.NPCEntityRegenerateStatsSystem}, pour
 * <ul>
 *   <li>tout PNJ dont l'attitude par défaut envers les joueurs est {@code Hostile} (chefs de demandes de boss,
 *       assaillants des raids, et mobs vanilla hostiles), partout pour un rôle {@code Nakasar_Peuples_*} ou une
 *       demande, à moins de {@value #RADIUS} blocs d'un village pour les autres ;</li>
 *   <li>les PNJ des demandes de genre hostile ({@link #HOSTILE_KINDS} : bandes, embuscades, chefs et renforts), quel
 *       que soit leur rôle.</li>
 * </ul>
 * Le composant n'est pas sauvegardé (pas de codec) et revient activé à chaque création du rôle.
 */
public final class VillageNoRegenSystem extends EntityTickingSystem<EntityStore> {

    public static final int RADIUS = 96;

    /** Genres de PNJ de demande qui combattent les joueurs. */
    public static final Set<RequestSpawns.Kind> HOSTILE_KINDS = EnumSet.of(
            RequestSpawns.Kind.FOE, RequestSpawns.Kind.AMBUSH, RequestSpawns.Kind.BOSS, RequestSpawns.Kind.ADD);

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
        RequestSpawns.Owner owner = RequestSpawns.owner(chunk.getReferenceTo(index));
        if (owner != null && HOSTILE_KINDS.contains(owner.kind())) {
            regen.setRegenEnabled(false);
            return;
        }
        WorldSupport world = chunk.getComponent(index, WorldSupport.getComponentType());
        if (world == null || world.getDefaultPlayerAttitude() != Attitude.HOSTILE) {
            return; // PNJ amical, neutre ou indifférent : régénération vanilla
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        if (owner != null || (npc != null && npc.getRoleName() != null && npc.getRoleName().startsWith("Nakasar_Peuples_"))) {
            regen.setRegenEnabled(false);
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
