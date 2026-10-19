package dev.nakasar.hytale.vampires.elite;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

/**
 * Quand une élite protégée par ses serviteurs ({@link MinionShieldSystem}) quitte le monde (chunk déchargé, arrêt du
 * serveur), on retire de ce qui sera sauvegardé son invulnérabilité : ses serviteurs, non sauvegardés, ne seront plus
 * là au rechargement pour la lever.
 */
public final class ShieldUnloadSystem extends HolderSystem<EntityStore> {

    @Override
    public Query<EntityStore> getQuery() {
        return Invulnerable.getComponentType();
    }

    @Override
    public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
    }

    @Override
    public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {
        NPCEntity npc = holder.getComponent(NPCEntity.getComponentType());
        if (npc != null && MinionShieldSystem.SHIELDS.containsKey(npc.getRoleName())) {
            holder.tryRemoveComponent(Invulnerable.getComponentType());
        }
    }
}
