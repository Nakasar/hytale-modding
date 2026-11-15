package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Mort d'une bête d'enclos ({@link Livestock}) : pas de butin (le rôle est marqué « butin déjà lâché » avant le système
 * vanilla DropDeathItems), elle manque à son enclos jusqu'au matin, et le joueur qui l'a tuée perd
 * {@value Livestock#KILL_REPUTATION} de réputation auprès du village.
 */
public final class LivestockDeathSystem extends DeathSystems.OnDeathSystem {

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        if (Livestock.owner(ref) == null) {
            return;
        }
        NPCEntity npc = buffer.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null) {
            Livestock.noLoot(npc);
        }
        Livestock.Key key = Livestock.died(store, ref);
        Damage info = death.getDeathInfo();
        if (key == null || info == null || !(info.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> killer = source.getRef();
        PlayerRef player = killer == null || !killer.isValid() ? null : buffer.getComponent(killer, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        World world = store.getExternalData().getWorld();
        world.execute(() -> {
            Village village = Villages.registry(world).byId(key.village());
            Ref<EntityStore> playerRef = player.getReference();
            if (village != null && playerRef != null && playerRef.isValid()) {
                Reputations.change(world, world.getEntityStore().getStore(), playerRef, player, village, Livestock.KILL_REPUTATION,
                        Reputations.KEYS + "reason.livestock");
            }
        });
    }
}
