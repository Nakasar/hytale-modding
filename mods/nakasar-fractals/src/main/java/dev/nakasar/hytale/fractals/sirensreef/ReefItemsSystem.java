package dev.nakasar.hytale.fractals.sirensreef;

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
 * Le trésor maudit, les boulets du canon des ombres et les effets du Récif de la Sirène ne servent que dans cette
 * fractale : un joueur qui arrive dans un autre monde les perd (comme l'équipement du Ressac, {@code silentsurf.GearItemsSystem}).
 */
public final class ReefItemsSystem extends RefSystem<EntityStore> {

    private static final Set<String> ITEMS = Set.of(SirensReef.TREASURE, ShadowCannon.ITEMS[0], ShadowCannon.ITEMS[1],
            ShadowCannon.ITEMS[2]);
    private static final String[] EFFECTS = {"Nakasar_Fractal_Cursed_1", "Nakasar_Fractal_Cursed_2",
            "Nakasar_Fractal_Cursed_3", CursedTreasure.RELIEF, "Nakasar_Fractal_Fetid_Fog", "Nakasar_Fractal_Piranhas",
            "Nakasar_Fractal_Grim_Lagoon", "Nakasar_Fractal_Cinders", "Nakasar_Fractal_Chilled", "Nakasar_Fractal_Dazed"};

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        if (world == null || SirensReef.FRACTAL.equals(FractalCatalog.fractalOf(world))) {
            return;
        }
        InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING)
                .replaceAll((slot, stack) -> !ItemStack.isEmpty(stack) && ITEMS.contains(stack.getItemId()) ? ItemStack.EMPTY : stack);
        for (String effect : EFFECTS) {
            Hurt.clear(buffer, ref, effect);
        }
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
