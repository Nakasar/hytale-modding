package dev.nakasar.hytale.peuples.raid;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

import java.util.UUID;

/** Les morts des PNJ d'un raid (pillards et gardes) : décompte du bilan, tueurs qui reçoivent le trophée. */
public final class RaidDeathSystem extends DeathSystems.OnDeathSystem {

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        if (Raids.kind(ref) == null) {
            return;
        }
        UUID killer = null;
        Damage info = death.getDeathInfo();
        if (info != null && info.getSource() instanceof Damage.EntitySource source) {
            Ref<EntityStore> by = source.getRef();
            PlayerRef player = by == null || !by.isValid() ? null : buffer.getComponent(by, PlayerRef.getComponentType());
            if (player != null) {
                killer = player.getUuid();
            }
        }
        Raids.died(ref, killer);
    }
}
