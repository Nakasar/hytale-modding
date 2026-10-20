package dev.nakasar.hytale.fractals.defiance;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.hammer.Hammer;

/**
 * Coups des joueurs sur un boss dont la barre de défiance est ouverte ({@link Defiance}) : 1 point, 2 pour un coup
 * lourd, 3 pour le marteau du culte. Lu après les réductions (groupe d'inspection).
 */
public final class DefianceDamageSystem extends DamageEventSystem {

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
        if (damage.isCancelled() || !(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> boss = chunk.getReferenceTo(index);
        Ref<EntityStore> attacker = source.getRef();
        if (!Defiance.isOpen(boss) || attacker == null || !attacker.isValid()
                || buffer.getComponent(attacker, Player.getComponentType()) == null) {
            return;
        }
        ItemStack held = InventoryComponent.getItemInHand(buffer, attacker);
        int points = held != null && Hammer.ID.equals(held.getItemId()) ? 3 : damage.getAmount() >= Defiance.HEAVY ? 2 : 1;
        World world = store.getExternalData().getWorld();
        world.execute(() -> Defiance.hit(world, world.getEntityStore().getStore(), boss, points));
    }
}
