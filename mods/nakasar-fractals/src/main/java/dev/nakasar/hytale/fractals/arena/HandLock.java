package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.protocol.packets.inventory.SetActiveSlot;
import com.hypixel.hytale.server.core.event.events.ecs.InventoryActiveSlotRequestEvent;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Objets de mécanique qu'on garde en main tant qu'on les porte (marteau du culte, cristal réfléchissant) :
 * <ul>
 *   <li>{@link #putInHand} les met dans la barre d'inventaire et les sélectionne ;</li>
 *   <li>leur interaction {@code SwapFrom} ne fait rien (JSON, côté client) et {@link Lock} refuse toute demande de
 *   changement de case tant qu'ils sont en main ;</li>
 *   <li>{@link #ensureHeld}, appelé par le système de l'objet, les remet en main s'ils en sont sortis (rangés à la
 *   main dans le sac), sans les recréer : l'usure du marteau est gardée.</li>
 * </ul>
 * On peut toujours les jeter (touche de lâcher) : la Corruption du marteau compte dessus. La main secondaire n'est pas
 * touchée : comme une arme à deux mains vanilla, l'objet a {@code "Utility": {"Compatible": false}} (ou rien, même
 * défaut), le bouclier ou la torche se range le temps qu'on le tient et revient quand on reprend une arme à une main
 * (Kevin, 25 octobre 2026 ; vider la case active de la main secondaire la perdait).
 */
public final class HandLock {

    private static final Set<String> LOCKED = ConcurrentHashMap.newKeySet();

    private HandLock() {
    }

    /** L'objet `id` se garde en main. */
    public static void lock(String id) {
        LOCKED.add(id);
    }

    static boolean locked(ItemStack stack) {
        return stack != null && !stack.isEmpty() && LOCKED.contains(stack.getItemId());
    }

    private static boolean empty(ItemStack stack) {
        return stack == null || stack.isEmpty();
    }

    /**
     * Met `stack` dans la barre d'inventaire et le sélectionne : la case active si elle est vide, sinon la première
     * case vide, sinon la case active dont l'objet part dans le sac.
     */
    public static void putInHand(Store<EntityStore> store, Ref<EntityStore> ref, ItemStack stack) {
        InventoryComponent.Hotbar hotbar = store.getComponent(ref, InventoryComponent.Hotbar.getComponentType());
        if (hotbar == null) {
            SimpleItemContainer.addOrDropItemStack(store, ref,
                    InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK), stack);
            return;
        }
        ItemContainer bar = hotbar.getInventory();
        short slot = hotbar.getActiveSlot();
        if (slot < 0 || slot >= bar.getCapacity() || !empty(bar.getItemStack(slot))) {
            short free = -1;
            for (short i = 0; i < bar.getCapacity() && free < 0; i++) {
                if (empty(bar.getItemStack(i))) {
                    free = i;
                }
            }
            if (free >= 0) {
                slot = free;
            } else {
                slot = (short) Math.max(0, Math.min(bar.getCapacity() - 1, slot));
                ItemStack moved = bar.getItemStack(slot);
                bar.removeItemStackFromSlot(slot);
                SimpleItemContainer.addOrDropItemStack(store, ref,
                        InventoryComponent.getCombined(store, ref, InventoryComponent.STORAGE_FIRST), moved);
            }
        }
        bar.setItemStackForSlot(slot, stack);
        select(store, ref, hotbar, (byte) slot);
    }

    /**
     * Garde l'objet `id` en main s'il est porté : sélectionné s'il est déjà dans la barre, sinon déplacé dans la barre
     * (la même pile, usure comprise). Faux si le joueur ne le porte pas.
     */
    public static boolean ensureHeld(Store<EntityStore> store, Ref<EntityStore> ref, String id) {
        ItemStack held = InventoryComponent.getItemInHand(store, ref);
        if (held != null && id.equals(held.getItemId())) {
            return true;
        }
        InventoryComponent.Hotbar hotbar = store.getComponent(ref, InventoryComponent.Hotbar.getComponentType());
        if (hotbar != null) {
            ItemContainer bar = hotbar.getInventory();
            for (short i = 0; i < bar.getCapacity(); i++) {
                ItemStack stack = bar.getItemStack(i);
                if (!empty(stack) && id.equals(stack.getItemId())) {
                    select(store, ref, hotbar, (byte) i);
                    return true;
                }
            }
        }
        CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING);
        short[] found = {-1};
        ItemStack[] stack = {null};
        inventory.forEach((slot, s) -> {
            if (found[0] < 0 && !empty(s) && id.equals(s.getItemId())) {
                found[0] = slot;
                stack[0] = s;
            }
        });
        if (found[0] < 0) {
            return false;
        }
        inventory.removeItemStackFromSlot(found[0]);
        putInHand(store, ref, stack[0]);
        return true;
    }

    private static void select(Store<EntityStore> store, Ref<EntityStore> ref, InventoryComponent.Hotbar hotbar, byte slot) {
        if (hotbar.getActiveSlot() == slot) {
            return;
        }
        hotbar.setActiveSlot(slot, ref, store);
        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        if (player != null) {
            player.getPacketHandler().writeNoCache(new SetActiveSlot(InventoryComponent.HOTBAR_SECTION_ID, slot));
        }
    }

    /** Objet gardé en main : les demandes de changement de case (barre ou main secondaire) sont refusées. */
    public static final class Lock extends EntityEventSystem<EntityStore, InventoryActiveSlotRequestEvent> {

        public Lock() {
            super(InventoryActiveSlotRequestEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return PlayerRef.getComponentType();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, InventoryActiveSlotRequestEvent event) {
            if (event.isCancelled() || !event.isClientRequest() || LOCKED.isEmpty()) {
                return;
            }
            if (locked(InventoryComponent.getItemInHand(store, chunk.getReferenceTo(index)))) {
                event.setCancelled(true);
            }
        }
    }
}
