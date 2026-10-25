package dev.nakasar.hytale.vampires.boss;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * « En combat » pour les soins voulus du Java : un PNJ l'est s'il a pris un coup qui a vraiment porté (groupe
 * d'inspection, après les filtres) depuis moins de {@value #COMBAT_SECONDS} s, et s'il n'est pas invulnérable. Hors de
 * là, aucun soin (consigne permanente de Kevin, AGENTS.md).
 */
public final class RecentDamage extends DamageEventSystem {

    public static final float COMBAT_SECONDS = 15f;

    private static final long COMBAT_NANOS = (long) (COMBAT_SECONDS * 1_000_000_000L);

    private static final Map<Ref<EntityStore>, Long> LAST_HIT = new ConcurrentHashMap<>();
    /** Prochain élagage des PNJ qui ne sont plus en combat (une fois par fenêtre, pas à chaque coup). */
    private static volatile long nextPrune;

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || damage.getAmount() <= 0f) {
            return;
        }
        long now = System.nanoTime();
        LAST_HIT.put(chunk.getReferenceTo(index), now);
        if (now - nextPrune >= 0) {
            nextPrune = now + COMBAT_NANOS;
            LAST_HIT.entrySet().removeIf(e -> !e.getKey().isValid() || now - e.getValue() > COMBAT_NANOS);
        }
    }

    /** Vrai si `ref` a été touché depuis moins de {@value #COMBAT_SECONDS} s et n'est pas invulnérable. */
    public static boolean mayHeal(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        if (ref == null || !ref.isValid() || accessor.getComponent(ref, Invulnerable.getComponentType()) != null) {
            return false;
        }
        Long at = LAST_HIT.get(ref);
        return at != null && System.nanoTime() - at <= COMBAT_NANOS;
    }

    public static void clearAll() {
        LAST_HIT.clear();
    }
}
