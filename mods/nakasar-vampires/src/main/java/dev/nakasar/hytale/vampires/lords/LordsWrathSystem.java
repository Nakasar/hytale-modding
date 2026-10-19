package dev.nakasar.hytale.vampires.lords;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Allume et entretient la colère des seigneurs vampires ({@link LordsWrath}) : un coup qui a vraiment porté (après
 * les filtres, d'où le groupe d'inspection) entre un joueur et le Comte ou la Comtesse, dans un sens ou dans l'autre.
 * Coups directs et projectiles : la source d'un projectile est son tireur.
 */
public final class LordsWrathSystem extends DamageEventSystem {

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Query.any();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || !(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> attacker = source.getRef();
        Ref<EntityStore> target = chunk.getReferenceTo(index);
        if (attacker == null || target == null || !attacker.isValid() || attacker.equals(target)) {
            return;
        }
        if (LordsWrath.isPlayer(attacker, buffer) && LordsWrath.isLord(target, buffer)) {
            LordsWrath.provoke(target);
        } else if (LordsWrath.isEnraged(attacker) && LordsWrath.isPlayer(target, buffer)) {
            LordsWrath.provoke(attacker);
        }
    }
}
