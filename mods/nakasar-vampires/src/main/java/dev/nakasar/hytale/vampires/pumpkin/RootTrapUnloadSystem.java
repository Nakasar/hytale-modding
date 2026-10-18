package dev.nakasar.hytale.vampires.pumpkin;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Quand une victime du piège de vrilles quitte le monde (chunk déchargé, arrêt du serveur, suppression), on retire
 * de ce qui sera sauvegardé le gel posé par le piège : sans cela, le PNJ resterait gelé pour toujours au
 * rechargement, sa vrille (non sauvegardée) n'étant plus là pour être détruite.
 */
public final class RootTrapUnloadSystem extends HolderSystem<EntityStore> {

    @Override
    public Query<EntityStore> getQuery() {
        return RootTrapped.getComponentType();
    }

    @Override
    public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
    }

    @Override
    public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {
        RootTrapped trapped = holder.getComponent(RootTrapped.getComponentType());
        if (trapped != null && trapped.frozenByUs) {
            holder.tryRemoveComponent(Frozen.getComponentType());
        }
        holder.tryRemoveComponent(RootTrapped.getComponentType());
    }
}
