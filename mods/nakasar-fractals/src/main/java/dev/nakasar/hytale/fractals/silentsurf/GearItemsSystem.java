package dev.nakasar.hytale.fractals.silentsurf;

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
 * L'équipement de prospection ne sert que dans le Ressac silencieux : un joueur qui arrive dans un autre monde le perd
 * (comme les noyaux et diapasons de l'Observatoire, {@code observatory.SelectionItemsSystem}).
 */
public final class GearItemsSystem extends RefSystem<EntityStore> {

    private static final Set<String> GEAR = Set.of(SurveyGear.ITEMS);

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        if (world == null || SilentSurf.FRACTAL.equals(FractalCatalog.fractalOf(world))) {
            return;
        }
        InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING)
                .replaceAll((slot, stack) -> !ItemStack.isEmpty(stack) && GEAR.contains(stack.getItemId()) ? ItemStack.EMPTY : stack);
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
