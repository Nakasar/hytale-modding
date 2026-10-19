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
 * Invulnérabilité des élites protégées par leurs serviteurs ({@link MinionShieldSystem}) et sauvegarde : leurs
 * serviteurs ne sont jamais sauvegardés, ils ne seront plus là au rechargement pour la lever. On la retire donc quand
 * l'élite quitte le monde (chunk déchargé, arrêt du serveur) et, si elle a quand même été sauvegardée (sauvegarde
 * automatique en plein combat puis plantage), quand l'élite est rechargée.
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
        if (npc != null && MinionShieldSystem.SHIELDS.containsKey(npc.getRoleName())) {
            holder.tryRemoveComponent(Invulnerable.getComponentType());
        }
    }
}
