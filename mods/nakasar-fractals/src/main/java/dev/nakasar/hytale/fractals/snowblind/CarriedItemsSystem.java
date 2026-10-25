package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

import java.util.Set;

/**
 * La torche et les fagots ne servent que dans la Tempête de neige : un joueur qui arrive dans un autre monde les perd
 * (comme l'équipement du Ressac silencieux, {@code silentsurf.GearItemsSystem}).
 */
public final class CarriedItemsSystem extends RefSystem<EntityStore> {

    private static final Set<String> CARRIED = Set.of(Snowblind.TORCH, Snowblind.FIREWOOD);

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        if (world == null || Snowblind.FRACTAL.equals(FractalCatalog.fractalOf(world))) {
            return;
        }
        InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING)
                .replaceAll((slot, stack) -> !ItemStack.isEmpty(stack) && CARRIED.contains(stack.getItemId()) ? ItemStack.EMPTY : stack);
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
