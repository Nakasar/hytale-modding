package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

/** Annonce au joueur les dégâts qu'il inflige au golem d'essai ({@link TrialGolemSystem}), après réductions. */
public final class TrialHitSystem extends DamageEventSystem {

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
        if (damage.isCancelled() || !(damage.getSource() instanceof Damage.EntitySource source) || source.getRef() == null) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        if (npc == null || !TrialGolemSystem.ROLE.equals(npc.getRoleName())) {
            return;
        }
        PlayerRef attacker = buffer.getComponent(source.getRef(), PlayerRef.getComponentType());
        if (attacker != null) {
            float amount = Math.round(damage.getAmount() * 10f) / 10f;
            attacker.sendMessage(Message.translation("nakasar_fractals.trial.hit").param("damage", amount));
        }
    }
}
