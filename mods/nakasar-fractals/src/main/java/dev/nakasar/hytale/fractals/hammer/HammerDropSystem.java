package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.modules.entity.item.PreventPickup;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.cliffside.Cliffside;

import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Un marteau du culte au sol ne se ramasse pas en passant dessus : toute entité d'objet {@value Hammer#ID} de la
 * Falaise (lâchée par la Corruption, par l'Archidevin ou jetée par un joueur) reçoit {@link PreventPickup}, que le
 * ramassage automatique vanilla ignore ({@code PlayerItemEntityPickupSystem}), et est suivie ici pour
 * {@link HammerPickupSystem} (s'accroupir tout près la ramasse).
 *
 * <p>Pas de touche d'interaction : le client n'affiche « Interagir » que pour ce qu'il vise, et il ne vise pas les
 * entités d'objet (essai en jeu du 2026-10-23).
 */
public final class HammerDropSystem extends RefSystem<EntityStore> {

    private static final Map<World, Set<Ref<EntityStore>>> GROUND = new WeakHashMap<>();

    /** Marteaux au sol suivis dans ce monde (vue vivante, à lire sur le fil du monde). */
    static synchronized Set<Ref<EntityStore>> onGround(World world) {
        return GROUND.computeIfAbsent(world, w -> ConcurrentHashMap.newKeySet());
    }

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
        buffer.ensureComponent(ref, PreventPickup.getComponentType());
        onGround(world).add(ref);
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        if (world != null) {
            onGround(world).remove(ref);
        }
    }
}
