package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Objets de mécanique des fractales (pierre imprégnée, larmes de Vieux Tom) : ramassés au sol, portés dans
 * l'inventaire, consommés par le Java. Mêmes appels que le marteau de la Falaise ({@code hammer.Hammer}).
 */
public final class Carried {

    private Carried() {
    }

    static CombinedItemContainer inventory(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
    }

    /** Nombre d'objets `id` portés (jusqu'à 64). */
    public static int count(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        CombinedItemContainer inventory = inventory(store, ref);
        int n = 0;
        while (n < 64 && inventory.canRemoveItemStack(new ItemStack(id, n + 1))) {
            n++;
        }
        return n;
    }

    /** Retire un objet `id` ; vrai s'il y en avait un. */
    public static boolean takeOne(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        return inventory(store, ref).removeItemStack(new ItemStack(id, 1), true, true).succeeded();
    }

    /** Retire tous les objets `id` ; rend combien. */
    public static int removeAll(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        int n = 0;
        while (n < 64 && takeOne(store, ref, id)) {
            n++;
        }
        return n;
    }

    public static boolean holds(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        ItemStack held = InventoryComponent.getItemInHand(store, ref);
        return held != null && id.equals(held.getItemId());
    }

    public static void give(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        SimpleItemContainer.addOrDropItemStack(store, ref, inventory(store, ref), new ItemStack(id, 1));
    }

    /** Donne `n` objets `id` d'un coup s'il y a la place ; sinon rien (rien ne tombe au sol). */
    public static boolean giveIfRoom(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id, int n) {
        CombinedItemContainer inventory = inventory(store, ref);
        ItemStack stack = new ItemStack(id, n);
        if (!inventory.canAddItemStack(stack)) {
            return false;
        }
        inventory.addItemStack(stack);
        return true;
    }

    /** Fait tomber l'objet `id` au sol en `at` (ramassable au bout d'une seconde). */
    public static void drop(Store<EntityStore> store, String id, Vector3d at) {
        Holder<EntityStore> holder = ItemComponent.generateItemDrop(store, new ItemStack(id, 1), new Vector3d(at).add(0, 0.5, 0),
                new Rotation3f(), 0f, 2f, 0f);
        if (holder != null) {
            ItemComponent item = holder.getComponent(ItemComponent.getComponentType());
            if (item != null) {
                item.setPickupDelay(1f);
            }
            store.addEntity(holder, AddReason.SPAWN);
        }
    }
}
