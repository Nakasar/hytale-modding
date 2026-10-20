package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

/**
 * Charge Brise-sceau du marteau du culte ({@link Hammer}) : un ennemi des fractales ({@link Foes}) frappé avec le
 * marteau en main, ou tué à moins de {@value Hammer#CHARGE_RADIUS} blocs d'un porteur, charge le marteau. Les sceaux
 * ne comptent pas (leurs coups sont annulés avant). Lu après les réductions (groupe d'inspection).
 */
public final class HammerDamageSystem extends DamageEventSystem {

    private static final String SEAL_ROLE = "Nakasar_Fractal_Seal";

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
        if (damage.isCancelled() || damage.getAmount() <= 0f || Hammer.CARRIERS.isEmpty()) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        if (npc == null || SEAL_ROLE.equals(npc.getRoleName()) || !Foes.inGroup(victim, buffer)) {
            return;
        }
        if (damage.getSource() instanceof Damage.EntitySource source && source.getRef() != null && source.getRef().isValid()) {
            PlayerRef attacker = buffer.getComponent(source.getRef(), PlayerRef.getComponentType());
            if (attacker != null && Hammer.holds(buffer, source.getRef())) {
                charge(attacker);
            }
        }
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        if (health == null || transform == null || health.get() > damage.getAmount()) {
            return;
        }
        Vector3d at = new Vector3d(transform.getPosition());
        World world = store.getExternalData().getWorld();
        for (PlayerRef player : world.getPlayerRefs()) {
            Hammer.Carrier carrier = Hammer.CARRIERS.get(player.getUuid());
            Vector3d where = carrier == null || !carrier.carrying ? null : Telegraphs.position(buffer, player.getReference());
            if (where != null && where.distance(at) <= Hammer.CHARGE_RADIUS) {
                charge(player);
            }
        }
    }

    private static void charge(PlayerRef player) {
        Hammer.Carrier carrier = Hammer.CARRIERS.get(player.getUuid());
        if (carrier == null || !carrier.carrying || carrier.charged) {
            return;
        }
        carrier.charged = true;
        player.sendMessage(Message.translation("nakasar_fractals_cliffside.hammer.charged"));
    }
}
