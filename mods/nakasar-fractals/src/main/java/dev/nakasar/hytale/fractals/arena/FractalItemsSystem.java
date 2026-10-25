package dev.nakasar.hytale.fractals.arena;

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
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

import java.util.Set;

/**
 * Objets et effets qui ne servent que dans une fractale (torche de la Tempête de neige, équipement du Ressac, trésor
 * maudit du Récif...) : un joueur qui arrive dans un autre monde les perd (comme les noyaux et diapasons de
 * l'Observatoire, {@code observatory.SelectionItemsSystem}). Un système par fractale.
 */
public final class FractalItemsSystem extends RefSystem<EntityStore> {

    private final String fractal;
    private final Set<String> items;
    private final String[] effects;

    public FractalItemsSystem(String fractal, Set<String> items, String... effects) {
        this.fractal = fractal;
        this.items = Set.copyOf(items);
        this.effects = effects.clone();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        if (world == null || fractal.equals(FractalCatalog.fractalOf(world))) {
            return;
        }
        InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING)
                .replaceAll((slot, stack) -> !ItemStack.isEmpty(stack) && items.contains(stack.getItemId()) ? ItemStack.EMPTY : stack);
        for (String effect : effects) {
            Hurt.clear(buffer, ref, effect);
        }
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
