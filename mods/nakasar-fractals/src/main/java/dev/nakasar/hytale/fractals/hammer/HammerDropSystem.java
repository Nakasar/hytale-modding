package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.cliffside.Cliffside;
import org.joml.Vector3d;

/**
 * Un marteau du culte au sol ne se ramasse qu'avec la touche d'interaction. Le client ne vise pas les entités
 * d'objet (essai en jeu du 2026-10-23 : une entité d'objet {@code Interactable} n'offrait aucune interaction), donc
 * toute entité d'objet {@value Hammer#ID} de la Falaise (jetée par un joueur) est remplacée par le bloc
 * {@value Hammer#DROPPED_BLOCK} posé au sol ({@link Hammer#place}), que l'on ramasse avec « Utiliser »
 * ({@code CliffsideUseInteraction}, action {@code Hammer_Dropped}). Sans sol libre à moins de 6 blocs, l'objet
 * reste une entité ordinaire, ramassée en passant dessus.
 */
public final class HammerDropSystem extends RefSystem<EntityStore> {

    @Override
    public Query<EntityStore> getQuery() {
        return ItemComponent.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        ItemComponent item = store.getComponent(ref, ItemComponent.getComponentType());
        ItemStack stack = item == null ? null : item.getItemStack();
        World world = store.getExternalData().getWorld();
        if (stack == null || !Hammer.ID.equals(stack.getItemId()) || world == null || !Cliffside.isCliffside(world)) {
            return;
        }
        // Hors du système en cours : on pose un bloc et on retire l'entité.
        world.execute(() -> {
            if (!ref.isValid()) {
                return;
            }
            Store<EntityStore> entities = world.getEntityStore().getStore();
            TransformComponent transform = entities.getComponent(ref, TransformComponent.getComponentType());
            if (transform != null && Hammer.place(world, new Vector3d(transform.getPosition()))) {
                entities.removeEntity(ref, RemoveReason.REMOVE);
            }
        });
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
    }
}
