package dev.nakasar.hytale.fractals.observatory;

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

/**
 * Les noyaux et diapasons ne servent que dans l'Observatoire : un joueur qui arrive dans un autre monde (une fractale,
 * ou le monde quitté par le Fragment des Brumes) les perd, comme les objets éphémères des portails vanilla
 * ({@code DeleteEphemeralItemsOnSpawnSystem}). La console de sélection est vidée au lancement ({@link Observatory#harmonize}).
 */
public final class SelectionItemsSystem extends RefSystem<EntityStore> {

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        if (world == null || FractalCatalog.isObservatory(world)) {
            return;
        }
        InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING)
                .replaceAll((slot, stack) -> isSelection(stack) ? ItemStack.EMPTY : stack);
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }

    /** Noyau ({@code Nakasar_Fractal_Core_<Id>}) ou diapason ({@code Nakasar_Fractal_Level_<N>}). */
    static boolean isSelection(ItemStack stack) {
        if (ItemStack.isEmpty(stack)) {
            return false;
        }
        String id = stack.getItemId();
        return id.startsWith(ObservatoryLayout.CORE_PREFIX) || id.startsWith(ObservatoryLayout.LEVEL_PREFIX);
    }
}
