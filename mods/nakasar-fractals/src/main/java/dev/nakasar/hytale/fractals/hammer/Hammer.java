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
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import org.joml.Vector3d;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le marteau du culte de la Falaise ({@value #ID}) : seule arme qui brise les sceaux. Le tenir en main fait monter la
 * Corruption, cran par cran ({@link HammerSystem}) ; il se charge (Brise-sceau) quand son porteur frappe un ennemi
 * avec, quand un ennemi qu'il a frappé (n'importe quelle arme) meurt dans les {@value #CREDIT_SECONDS} s, ou quand un
 * ennemi meurt à moins de {@value #CHARGE_RADIUS} blocs de lui ({@link HammerDamageSystem}). Un coup chargé sur un
 * sceau le fissure et consomme la charge.
 *
 * <p>L'état de chaque porteur est gardé en mémoire par joueur ; il ne survit ni à la sortie de la Falaise ni au
 * redémarrage (le marteau est alors retiré).
 */
public final class Hammer {

    public static final String ID = "Nakasar_Fractal_Cult_Hammer";
    /** Marteau lâché au sol : bloc en modèle 3D, ramassé avec « Utiliser » ({@link HammerDropSystem}). */
    public static final String DROPPED_BLOCK = "Nakasar_Fractal_Hammer_Dropped";
    public static final double CHARGE_RADIUS = 10;
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

    /**
     * Fait tomber un marteau au sol en `at` : le bloc {@value #DROPPED_BLOCK}, ramassé avec « Utiliser »
     * ({@link HammerDropSystem}) ; sans sol libre, une entité d'objet ordinaire.
     */
    public static void drop(Store<EntityStore> store, Vector3d at) {
        World world = store.getExternalData().getWorld();
        if (world != null) {
            world.execute(() -> {
                if (!place(world, at)) {
                    Holder<EntityStore> holder = ItemComponent.generateItemDrop(world.getEntityStore().getStore(),
                            new ItemStack(ID, 1), new Vector3d(at).add(0, 0.5, 0), new Rotation3f(), 0f, 2f, 0f);
                    if (holder != null) {
                        world.getEntityStore().getStore().addEntity(holder, AddReason.SPAWN);
                    }
                }
            });
        }
    }

    /**
     * Pose {@value #DROPPED_BLOCK} sur le premier sol libre sous `at` (6 blocs au plus), sinon juste au-dessus
     * (3 blocs au plus). Faux s'il n'y a nulle part où le poser.
     */
    public static boolean place(World world, Vector3d at) {
        ChunkStore chunks = world.getChunkStore();
        int x = (int) Math.floor(at.x);
        int y = (int) Math.floor(at.y);
        int z = (int) Math.floor(at.z);
        for (int dy : new int[]{0, -1, -2, -3, -4, -5, -6, 1, 2, 3}) {
            int cy = y + dy;
            if (WorldBlocks.id(chunks, x, cy, z) == BlockType.EMPTY_ID && WorldBlocks.solid(chunks, x, cy - 1, z)) {
                return WorldBlocks.set(chunks, x, cy, z, DROPPED_BLOCK, 0);
            }
        }
        return false;
    }

    /** Ramasse le marteau posé en (x, y, z) ; faux si ce n'est pas (ou plus) un marteau au sol. */
    public static boolean pickUp(World world, Store<EntityStore> store, Ref<EntityStore> ref, int x, int y, int z) {
        ChunkStore chunks = world.getChunkStore();
        if (!DROPPED_BLOCK.equals(WorldBlocks.name(chunks, x, y, z)) || !WorldBlocks.clear(chunks, x, y, z)) {
            return false;
        }
        give(store, ref);
        return true;
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
