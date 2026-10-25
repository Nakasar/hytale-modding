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
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

import java.util.Set;

/**
 * L'équipement de prospection et les effets du Ressac silencieux (Garde de Thess...) ne servent que dans cette
 * fractale : un joueur qui arrive dans un autre monde les perd (comme les noyaux et diapasons de l'Observatoire, {@code observatory.SelectionItemsSystem}).
 */
public final class GearItemsSystem extends RefSystem<EntityStore> {

    private static final Set<String> GEAR = Set.of(SurveyGear.ITEMS);
    /** Effets propres au Ressac (la Garde de Thess dure une heure, rafraîchie dans la fractale). */
    private static final String[] EFFECTS = {SilentSurf.WARD_EFFECT, "Nakasar_Fractal_Phantasmagoria",
            "Nakasar_Fractal_Torment", "Nakasar_Fractal_Parachute_Open"};

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
        for (String effect : EFFECTS) {
            Hurt.clear(buffer, ref, effect);
        }
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
