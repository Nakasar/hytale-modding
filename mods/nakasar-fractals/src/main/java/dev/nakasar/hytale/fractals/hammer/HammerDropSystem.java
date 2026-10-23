package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.Interactable;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;

/**
 * Un marteau du culte au sol ne se ramasse qu'avec la touche d'interaction : toute entité d'objet {@value Hammer#ID}
 * (lâché par la Corruption, par l'Archidevin ou jeté par un joueur) reçoit {@link Interactable}, que le ramassage
 * automatique vanilla ignore ({@code PlayerItemEntityPickupSystem}), et l'interaction Use {@value #ROOT}
 * ({@link PickUpHammerInteraction}), comme le wagonnet vanilla ({@code SpawnMinecartInteraction}).
 */
public final class HammerDropSystem extends RefSystem<EntityStore> {

    public static final String ROOT = "Root_Nakasar_Fractal_PickUp_Hammer";
    public static final String HINT = "nakasar_fractals_cliffside.hints.takeHammer";

    @Override
    public Query<EntityStore> getQuery() {
        return ItemComponent.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        ItemComponent item = store.getComponent(ref, ItemComponent.getComponentType());
        ItemStack stack = item == null ? null : item.getItemStack();
        if (stack == null || !Hammer.ID.equals(stack.getItemId())
                || store.getArchetype(ref).contains(Interactable.getComponentType())) {
            return;
        }
        Interactions interactions = new Interactions(Map.of(InteractionType.Use, ROOT));
        interactions.setInteractionHint(HINT);
        buffer.ensureComponent(ref, Interactable.getComponentType());
        buffer.putComponent(ref, Interactions.getComponentType(), interactions);
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
