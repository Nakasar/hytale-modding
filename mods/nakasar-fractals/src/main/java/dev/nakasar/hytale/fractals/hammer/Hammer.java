package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.HandLock;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le marteau du culte de la Falaise ({@value #ID}) : seule arme qui brise les sceaux. Porté, il reste en main (on ne
 * change pas d'objet, {@link HandLock}) et fait monter la Corruption, cran par cran ({@link HammerSystem}) ; il se
 * charge (Brise-sceau) quand un ennemi que son porteur a frappé avec meurt dans les {@value #CREDIT_SECONDS} s
 * ({@link HammerDamageSystem}). Un coup chargé sur un sceau le fissure et consomme la charge.
 *
 * <p>L'état de chaque porteur est gardé en mémoire par joueur ; il ne survit ni à la sortie de la Falaise ni au
 * redémarrage (le marteau est alors retiré).
 */
public final class Hammer {

    public static final String ID = "Nakasar_Fractal_Cult_Hammer";
    public static final float CREDIT_SECONDS = 15f;

    /** Porteur : cran de Corruption (0 à 3) et temps restant du cran, marteau porté, marteau chargé. */
    static final class Carrier {
        int tier;
        float cycle;
        boolean carrying;
        boolean charged;
        float sinceFx;
    }

    static final Map<UUID, Carrier> CARRIERS = new ConcurrentHashMap<>();

    private Hammer() {
    }

    static CombinedItemContainer inventory(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING);
    }

    /**
     * Vrai si le joueur a le marteau quelque part dans son inventaire. On compare l'id seul : le marteau s'use à
     * chaque coup, et un {@code canRemoveItemStack(new ItemStack(ID, 1))} (qui compare aussi la durabilité) ne le
     * reconnaissait plus après le premier coup, ce qui effaçait la charge aussitôt gagnée.
     */
    public static boolean carries(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return inventory(store, ref).countItemStacks(Hammer::isHammer) > 0;
    }

    static boolean isHammer(ItemStack stack) {
        return stack != null && !stack.isEmpty() && ID.equals(stack.getItemId());
    }

    /** Vrai si le joueur tient le marteau en main. */
    public static boolean holds(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        ItemStack held = InventoryComponent.getItemInHand(store, ref);
        return held != null && ID.equals(held.getItemId());
    }

    /** Retire tous les marteaux de l'inventaire, usés ou non ; vrai s'il y en avait. */
    public static boolean remove(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        CombinedItemContainer inventory = inventory(store, ref);
        List<Short> slots = new ArrayList<>();
        inventory.forEach((slot, stack) -> {
            if (isHammer(stack)) {
                slots.add(slot);
            }
        });
        for (short slot : slots) {
            inventory.removeItemStackFromSlot(slot);
        }
        return !slots.isEmpty();
    }

    /** Donne le marteau au joueur, en main et sélectionné ({@link HandLock}). */
    public static void give(Store<EntityStore> store, Ref<EntityStore> ref) {
        HandLock.putInHand(store, ref, new ItemStack(ID, 1));
    }

    /** Fait tomber un marteau au sol en `at` ; on le ramasse en s'accroupissant tout près ({@link HammerPickupSystem}). */
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

    /**
     * L'Archidevin rappelle le marteau (dernier sceau des poignets brisé) : retiré de tous les inventaires et du sol,
     * avec une volute violette là où il était. Il le rendra pendant ses transitions.
     */
    public static void recallAll(World world, Store<EntityStore> store) {
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref != null && ref.isValid() && carries(store, ref)) {
                Vector3d at = Telegraphs.position(store, ref);
                if (at != null) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", new Vector3d(at).add(0, 1, 0), 0.8f);
                }
                remove(store, ref);
            }
        }
        for (Ref<EntityStore> item : List.copyOf(HammerDropSystem.onGround(world))) {
            if (item.isValid()) {
                store.removeEntity(item, RemoveReason.REMOVE);
            }
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

    /** Cran de Corruption du joueur (0 à 3 ; 0 s'il n'a jamais tenu le marteau). */
    public static int tier(UUID player) {
        Carrier carrier = CARRIERS.get(player);
        return carrier == null ? 0 : carrier.tier;
    }

    public static void clearAll() {
        CARRIERS.clear();
    }
}
