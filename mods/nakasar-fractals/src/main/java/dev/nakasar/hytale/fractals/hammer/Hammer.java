package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le marteau du culte de la Falaise ({@value #ID}) : seule arme qui brise les sceaux. Le porter (n'importe où dans
 * l'inventaire) donne des charges de Corruption ({@link HammerSystem}) ; il se charge (Brise-sceau) quand son porteur
 * frappe un ennemi avec, ou qu'un ennemi meurt à moins de {@value #CHARGE_RADIUS} blocs de lui
 * ({@link HammerDamageSystem}). Un coup chargé sur un sceau le fissure et consomme la charge.
 *
 * <p>L'état de chaque porteur est gardé en mémoire par joueur ; il ne survit ni à la sortie de la Falaise ni au
 * redémarrage (le marteau est alors retiré).
 */
public final class Hammer {

    public static final String ID = "Nakasar_Fractal_Cult_Hammer";
    public static final double CHARGE_RADIUS = 8;

    /** Porteur : charges de Corruption, marteau chargé, et ce qu'on a déjà annoncé. */
    static final class Carrier {
        float stacks;
        boolean carrying;
        boolean charged;
        boolean stunnedAt30;
        float sinceFx;
    }

    static final Map<UUID, Carrier> CARRIERS = new ConcurrentHashMap<>();

    private Hammer() {
    }

    static CombinedItemContainer inventory(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING);
    }

    /** Vrai si le joueur a le marteau quelque part dans son inventaire. */
    public static boolean carries(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return inventory(store, ref).canRemoveItemStack(new ItemStack(ID, 1));
    }

    /** Vrai si le joueur tient le marteau en main. */
    public static boolean holds(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        ItemStack held = InventoryComponent.getItemInHand(store, ref);
        return held != null && ID.equals(held.getItemId());
    }

    /** Retire tous les marteaux de l'inventaire ; vrai s'il y en avait. */
    public static boolean remove(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        CombinedItemContainer inventory = inventory(store, ref);
        boolean removed = false;
        for (int i = 0; i < 4 && inventory.removeItemStack(new ItemStack(ID, 1), true, true).succeeded(); i++) {
            removed = true;
        }
        return removed;
    }

    /** Donne le marteau au joueur (il tombe à ses pieds si l'inventaire est plein). */
    public static void give(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer.addOrDropItemStack(store, ref,
                InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK), new ItemStack(ID, 1));
    }

    /** Fait tomber un marteau au sol en `at` (ramassable au bout d'une seconde). */
    public static void drop(Store<EntityStore> store, Vector3d at) {
        Holder<EntityStore> holder = ItemComponent.generateItemDrop(store, new ItemStack(ID, 1), new Vector3d(at).add(0, 0.5, 0),
                new Rotation3f(), 0f, 2f, 0f);
        if (holder != null) {
            ItemComponent item = holder.getComponent(ItemComponent.getComponentType());
            if (item != null) {
                item.setPickupDelay(1f);
            }
            store.addEntity(holder, AddReason.SPAWN);
        }
    }

    public static boolean isCharged(UUID player) {
        Carrier carrier = CARRIERS.get(player);
        return carrier != null && carrier.carrying && carrier.charged;
    }

    /** Consomme la charge du marteau ; vrai s'il était chargé. */
    public static boolean consumeCharge(UUID player) {
        Carrier carrier = CARRIERS.get(player);
        if (carrier == null || !carrier.charged) {
            return false;
        }
        carrier.charged = false;
        return true;
    }

    /** Charges de Corruption du joueur (0 s'il n'a jamais porté le marteau). */
    public static float stacks(UUID player) {
        Carrier carrier = CARRIERS.get(player);
        return carrier == null ? 0f : carrier.stacks;
    }

    public static void clearAll() {
        CARRIERS.clear();
    }
}
