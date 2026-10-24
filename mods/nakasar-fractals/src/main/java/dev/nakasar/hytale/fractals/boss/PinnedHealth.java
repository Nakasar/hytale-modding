package dev.nakasar.hytale.fractals.boss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatsSystems;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Vie fixée par le Java ({@link #pin}) : remise à chaque tick, juste après la régénération naturelle des PNJ et avant
 * l'envoi des changements de stats aux clients. Sans cela, la régénération remonte la vie entre deux pas du Java et la
 * barre de boss monte et redescend sans cesse (Abîme de Jade, retour du 2026-10-24).
 */
public final class PinnedHealth extends TickingSystem<EntityStore> {

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency(Order.AFTER, EntityStatsSystems.Regenerate.class),
            new SystemDependency(Order.BEFORE, EntityStatsSystems.Changes.class));

    private static final Map<Ref<EntityStore>, Float> PINNED = new ConcurrentHashMap<>();

    /** Fixe la vie de `ref` à `value` jusqu'à {@link #unpin}. */
    public static void pin(Ref<EntityStore> ref, float value) {
        if (ref != null) {
            PINNED.put(ref, value);
        }
    }

    public static void unpin(Ref<EntityStore> ref) {
        if (ref != null) {
            PINNED.remove(ref);
        }
    }

    public static void clearAll() {
        PINNED.clear();
    }

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        if (PINNED.isEmpty()) {
            return;
        }
        int healthIndex = DefaultEntityStatTypes.getHealth();
        for (Map.Entry<Ref<EntityStore>, Float> entry : PINNED.entrySet()) {
            Ref<EntityStore> ref = entry.getKey();
            if (!ref.isValid()) {
                PINNED.remove(ref);
                continue;
            }
            if (ref.getStore() != store) {
                continue;
            }
            EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
            EntityStatValue health = stats == null ? null : stats.get(healthIndex);
            if (health != null && Math.abs(health.get() - entry.getValue()) > 0.01f) {
                stats.setStatValue(healthIndex, entry.getValue());
            }
        }
    }
}
