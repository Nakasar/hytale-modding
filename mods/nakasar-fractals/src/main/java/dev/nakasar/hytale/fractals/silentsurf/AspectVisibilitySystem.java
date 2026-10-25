package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.tracker.EntityTrackerSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Aspects de la Fantasmagorie (GW2) : chacun n'est visible que de son joueur. Comme le {@code HideFromPlayer} vanilla
 * (joueurs cachés), ce système retire l'Aspect privé des entités vues par les autres joueurs, juste après qu'elles ont
 * été rassemblées ({@code CollectVisible}) : leur client ne le reçoit jamais. Ses coups, eux, ne comptent que de son
 * joueur ({@link Kanaxai#filter}).
 */
public final class AspectVisibilitySystem extends EntityTickingSystem<EntityStore> {

    /** Aspect privé -> son joueur. */
    private static final Map<Ref<EntityStore>, UUID> OWNERS = new ConcurrentHashMap<>();

    private static final Query<EntityStore> QUERY = Query.and(EntityTrackerSystems.EntityViewer.getComponentType(),
            PlayerRef.getComponentType());
    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, EntityTrackerSystems.CollectVisible.class));

    static void hide(Ref<EntityStore> aspect, UUID owner) {
        OWNERS.put(aspect, owner);
    }

    static void forget(Ref<EntityStore> aspect) {
        OWNERS.remove(aspect);
    }

    static UUID owner(Ref<EntityStore> aspect) {
        return OWNERS.get(aspect);
    }

    public static void clearAll() {
        OWNERS.clear();
    }

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return EntityTrackerSystems.FIND_VISIBLE_ENTITIES_GROUP;
    }

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

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
        if (OWNERS.isEmpty()) {
            return;
        }
        // Aspect d'une instance fermée en pleine Fantasmagorie : sa Ref n'est plus valide, on l'oublie.
        OWNERS.keySet().removeIf(ref -> !ref.isValid());
        PlayerRef viewer = chunk.getComponent(index, PlayerRef.getComponentType());
        EntityTrackerSystems.EntityViewer seen = chunk.getComponent(index, EntityTrackerSystems.EntityViewer.getComponentType());
        if (viewer == null || seen == null) {
            return;
        }
        Iterator<Ref<EntityStore>> it = seen.visible.iterator();
        while (it.hasNext()) {
            UUID owner = OWNERS.get(it.next());
            if (owner != null && !owner.equals(viewer.getUuid())) {
                it.remove();
                seen.hiddenCount++;
            }
        }
    }
}
