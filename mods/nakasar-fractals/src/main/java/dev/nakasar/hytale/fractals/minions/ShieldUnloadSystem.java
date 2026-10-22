package dev.nakasar.hytale.fractals.minions;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.BossStun;

/**
 * Invulnérabilité des élites protégées par leurs serviteurs ({@link MinionShieldSystem}) et sauvegarde : leurs
 * serviteurs ne sont jamais sauvegardés, ils ne seront plus là au rechargement pour la lever. On la retire donc quand
 * le boss quitte le monde (chunk déchargé, arrêt du serveur) et, s'il a quand même été sauvegardé (sauvegarde
 * automatique en plein combat puis plantage), quand il est rechargé. Vaut pour tous les PNJ du mod
 * ({@value BossStun#ROLE_PREFIX}…) : le mod ne rend invulnérables que les siens, le temps d'une phase.
 */
public final class ShieldUnloadSystem extends HolderSystem<EntityStore> {

    @Override
    public Query<EntityStore> getQuery() {
        return Invulnerable.getComponentType();
    }

    @Override
    public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
        if (reason == AddReason.LOAD) {
            unshield(holder);
        }
    }

    @Override
    public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {
        unshield(holder);
    }

    private static void unshield(Holder<EntityStore> holder) {
        NPCEntity npc = holder.getComponent(NPCEntity.getComponentType());
        if (npc != null && npc.getRoleName() != null && npc.getRoleName().startsWith(BossStun.ROLE_PREFIX)) {
            holder.tryRemoveComponent(Invulnerable.getComponentType());
        }
    }
}
