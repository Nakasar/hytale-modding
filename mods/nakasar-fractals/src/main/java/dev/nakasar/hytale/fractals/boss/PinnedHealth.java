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
import com.hypixel.hytale.server.npc.NPCPlugin;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Vie fixée par le Java ({@link #pin}) : remise à chaque tick, juste après la régénération naturelle des PNJ et avant
 * l'envoi des changements de stats aux clients. Sans cela, la régénération remonte la vie entre deux pas du Java et la
 * barre de boss monte et redescend sans cesse (Abîme de Jade, retour du 2026-10-24).
 * La dépendance vise la sous-classe enregistrée par le NPCPlugin : la classe générique
 * {@code EntityStatsSystems.Regenerate} n'est jamais enregistrée, et la citer fait échouer le chargement du plugin.
 *
 * <p>{@link #noRegen} : la vie ne peut que descendre (boss qui attend les pierres imprégnées, retour du 2026-10-24) ;
 * les soins voulus par le Java passent par {@link #heal}.
 */
public final class PinnedHealth extends TickingSystem<EntityStore> {

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency(Order.AFTER, NPCPlugin.NPCEntityRegenerateStatsSystem.class),
            new SystemDependency(Order.BEFORE, EntityStatsSystems.Changes.class));

    private static final Map<Ref<EntityStore>, Float> PINNED = new ConcurrentHashMap<>();
    /** Vie la plus basse vue, par entité sans régénération. */
    private static final Map<Ref<EntityStore>, Float> LOWEST = new ConcurrentHashMap<>();

    /** Fixe la vie de `ref` à `value` jusqu'à {@link #unpin}. */
    public static void pin(Ref<EntityStore> ref, float value) {
        if (ref != null) {
            PINNED.put(ref, value);
        }
    }

    public static void unpin(Ref<EntityStore> ref) {
        if (ref != null) {
            PINNED.remove(ref);
            LOWEST.remove(ref);
        }
    }

    /** La vie de `ref` ne remonte plus d'elle-même : seulement par {@link #heal}, jusqu'à {@link #unpin}. */
    public static void noRegen(Ref<EntityStore> ref) {
        if (ref != null) {
            LOWEST.putIfAbsent(ref, Float.MAX_VALUE);
        }
    }

    /** Soin voulu de `ref` (sans régénération) : sa vie passe à `value`. */
    public static void heal(Store<EntityStore> store, Ref<EntityStore> ref, float value) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        if (stats != null) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), value);
        }
        if (LOWEST.containsKey(ref)) {
            LOWEST.put(ref, value);
        }
    }

    public static void clearAll() {
        PINNED.clear();
        LOWEST.clear();
    }

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        if (PINNED.isEmpty() && LOWEST.isEmpty()) {
            return;
        }
        int healthIndex = DefaultEntityStatTypes.getHealth();
        for (Map.Entry<Ref<EntityStore>, Float> entry : LOWEST.entrySet()) {
            Ref<EntityStore> ref = entry.getKey();
            if (!ref.isValid()) {
                LOWEST.remove(ref);
                continue;
            }
            if (ref.getStore() != store) {
                continue;
            }
            EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
            EntityStatValue health = stats == null ? null : stats.get(healthIndex);
            if (health == null) {
                continue;
            }
            if (health.get() > entry.getValue() + 0.01f) {
                stats.setStatValue(healthIndex, entry.getValue());
            } else {
                entry.setValue(health.get());
            }
        }
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
