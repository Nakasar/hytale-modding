package dev.nakasar.hytale.fractals.boss;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.HealthRegenState;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Aucun PNJ des fractales ne se régénère (consigne permanente de Kevin, 25 octobre 2026 : « les mobs ne doivent pas se
 * régénérer quand ils sont hors combat ou invulnérables »). La vie des PNJ vanilla remonte de 5 % toutes les 0,5 s après
 * 15 s sans dégâts (Server/Entity/Stats/Health.json, condition {@code RegenHealth}) : cette condition lit
 * {@link HealthRegenState}, que chaque rôle porte. On le coupe à chaque tick, avant la régénération, pour que même une
 * action {@code SetHealthRegen} d'un rôle ne la rallume pas. Les soins voulus (incantateurs, boss qui se nourrit) passent
 * par le Java et ne sont pas touchés.
 */
public final class NoRegenSystem extends EntityTickingSystem<EntityStore> {

    private static final Query<EntityStore> QUERY = Query.and(NPCEntity.getComponentType(), HealthRegenState.getComponentType());

    /** Monde de fractale ou non, retenu par monde (la config d'instance ne change pas) : pas de recherche à chaque tick. */
    private static final Map<World, Boolean> FRACTAL_WORLDS = Collections.synchronizedMap(new WeakHashMap<>());

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
        World world = store.getExternalData().getWorld();
        if (world != null && FRACTAL_WORLDS.computeIfAbsent(world, w -> FractalCatalog.fractalOf(w) != null)) {
            regen.setRegenEnabled(false);
        }
    }
}
