package dev.nakasar.hytale.fractals.solidocean;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.MovementStates;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.protocol.packets.inventory.SetActiveSlot;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.event.events.ecs.InventoryActiveSlotRequestEvent;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.modules.entity.item.PreventPickup;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le cristal réfléchissant de l'Abîme de Jade se porte comme le marteau de la Falaise, en plus strict :
 * <ul>
 *   <li>au sol, il ne se ramasse pas en passant dessus ({@link PreventPickup}, {@link Drops}) : on s'accroupit à moins
 *   de {@value #REACH} blocs ({@link Pickup}) ; un seul cristal par joueur ;</li>
 *   <li>ramassé (ou rendu après un lancer à vide), il va dans la barre d'inventaire et y est sélectionné ; la main
 *   secondaire est vidée (objet à deux mains) ;</li>
 *   <li>tant qu'on le porte, on ne change pas d'objet sélectionné : son interaction {@code SwapFrom} ne fait rien
 *   (côté client), les demandes de changement de case sont refusées ({@link Lock}) et, s'il sort de la main malgré
 *   tout (rangé à la main dans le sac), il y est remis ; un cristal en trop retombe au sol.</li>
 * </ul>
 */
public final class CrystalHold {

    public static final double REACH = 2.0;
    public static final double FORGET = 4.0;
    private static final float INTERVAL = 0.15f;
    private static final Map<World, Set<Ref<EntityStore>>> GROUND = new WeakHashMap<>();
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());
    private static final Map<World, Set<UUID>> HINTED = Collections.synchronizedMap(new WeakHashMap<>());

    private CrystalHold() {
    }

    static boolean isSolidOcean(World world) {
        return world != null && SolidOcean.FRACTAL.equals(FractalCatalog.fractalOf(world));
    }

    static synchronized Set<Ref<EntityStore>> onGround(World world) {
        return GROUND.computeIfAbsent(world, w -> ConcurrentHashMap.newKeySet());
    }

    static boolean isCrystal(ItemStack stack) {
        return stack != null && !stack.isEmpty() && SolidOcean.CRYSTAL.equals(stack.getItemId());
    }

    static int count(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING).countItemStacks(CrystalHold::isCrystal);
    }

    static boolean holds(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return isCrystal(InventoryComponent.getItemInHand(store, ref));
    }

    /** Retire tous les cristaux de l'inventaire ; rend combien de cases en tenaient. */
    static int removeAll(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING);
        List<Short> slots = new ArrayList<>();
        inventory.forEach((slot, stack) -> {
            if (isCrystal(stack)) {
                slots.add(slot);
            }
        });
        for (short slot : slots) {
            inventory.removeItemStackFromSlot(slot);
        }
        return slots.size();
    }

    /**
     * Met un cristal dans la barre d'inventaire et le sélectionne : la case active si elle est vide, sinon la première
     * case vide, sinon la case active dont l'objet part dans le sac. Vide la main secondaire.
     */
    static void give(Store<EntityStore> store, Ref<EntityStore> ref) {
        InventoryComponent.Hotbar hotbar = store.getComponent(ref, InventoryComponent.Hotbar.getComponentType());
        if (hotbar == null) {
            SimpleItemContainer.addOrDropItemStack(store, ref,
                    InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK),
                    new ItemStack(SolidOcean.CRYSTAL, 1));
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
        bar.setItemStackForSlot(slot, new ItemStack(SolidOcean.CRYSTAL, 1));
        select(store, ref, hotbar, (byte) slot);
        freeOffHand(store, ref);
    }

    private static boolean empty(ItemStack stack) {
        return stack == null || stack.isEmpty();
    }

    private static void select(Store<EntityStore> store, Ref<EntityStore> ref, InventoryComponent.Hotbar hotbar, byte slot) {
        if (hotbar.getActiveSlot() != slot) {
            hotbar.setActiveSlot(slot, ref, store);
        }
        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        if (player != null) {
            player.getPacketHandler().writeNoCache(new SetActiveSlot(InventoryComponent.HOTBAR_SECTION_ID, slot));
        }
    }

    /** Objet à deux mains : rien dans la main secondaire. */
    private static void freeOffHand(Store<EntityStore> store, Ref<EntityStore> ref) {
        InventoryComponent.Utility utility = store.getComponent(ref, InventoryComponent.Utility.getComponentType());
        if (utility == null || utility.getActiveSlot() == InventoryComponent.INACTIVE_SLOT_INDEX) {
            return;
        }
        utility.setActiveSlot(InventoryComponent.INACTIVE_SLOT_INDEX, ref, store);
        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        if (player != null) {
            player.getPacketHandler().writeNoCache(new SetActiveSlot(InventoryComponent.UTILITY_SECTION_ID,
                    InventoryComponent.INACTIVE_SLOT_INDEX));
        }
    }

    /** Le cristal reste en main : un seul, sélectionné, main secondaire vide. */
    private static void keep(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d at) {
        int n = count(store, ref);
        if (n == 0 || n == 1 && holds(store, ref) && offHandFree(store, ref)) {
            return;
        }
        removeAll(store, ref);
        give(store, ref);
        for (int i = 1; i < n; i++) {
            SolidOcean.dropCrystal(store, at);
        }
    }

    private static boolean offHandFree(Store<EntityStore> store, Ref<EntityStore> ref) {
        InventoryComponent.Utility utility = store.getComponent(ref, InventoryComponent.Utility.getComponentType());
        return utility == null || utility.getActiveSlot() == InventoryComponent.INACTIVE_SLOT_INDEX;
    }

    private static boolean crouching(Store<EntityStore> store, Ref<EntityStore> ref) {
        MovementStatesComponent movement = store.getComponent(ref, MovementStatesComponent.getComponentType());
        MovementStates states = movement == null ? null : movement.getMovementStates();
        return states != null && (states.crouching || states.forcedCrouching);
    }

    private static void step(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Set<Ref<EntityStore>> crystals = onGround(world);
        crystals.removeIf(ref -> !ref.isValid());
        Set<UUID> hinted = HINTED.computeIfAbsent(world, w -> new HashSet<>());
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                continue;
            }
            TransformComponent body = store.getComponent(ref, TransformComponent.getComponentType());
            if (body == null) {
                continue;
            }
            Vector3d at = body.getPosition();
            keep(store, ref, at);
            Ref<EntityStore> closest = null;
            double best = Double.MAX_VALUE;
            for (Ref<EntityStore> crystal : crystals) {
                TransformComponent t = store.getComponent(crystal, TransformComponent.getComponentType());
                if (t != null) {
                    double d = t.getPosition().distance(at);
                    if (d < best) {
                        best = d;
                        closest = crystal;
                    }
                }
            }
            if (closest == null || best > FORGET) {
                hinted.remove(player.getUuid());
                continue;
            }
            if (best > REACH) {
                continue;
            }
            boolean carrying = count(store, ref) > 0;
            if (crouching(store, ref) && !carrying) {
                crystals.remove(closest);
                store.removeEntity(closest, RemoveReason.REMOVE);
                give(store, ref);
                hinted.remove(player.getUuid());
            } else if (hinted.add(player.getUuid())) {
                NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(SolidOcean.MESSAGES
                        + (carrying ? "crystal.already" : "crystal.crouch")), NotificationStyle.Default);
            }
        }
    }

    /** Cristal au sol de l'Océan solide : pas de ramassage automatique, suivi pour {@link Pickup}. */
    public static final class Drops extends RefSystem<EntityStore> {

        @Override
        public Query<EntityStore> getQuery() {
            return ItemComponent.getComponentType();
        }

        @Override
        public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
            ItemComponent item = store.getComponent(ref, ItemComponent.getComponentType());
            World world = store.getExternalData().getWorld();
            if (item == null || !isCrystal(item.getItemStack()) || !isSolidOcean(world)) {
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

    /** Toutes les {@value #INTERVAL} s dans l'Océan solide : ramassage accroupi et cristal gardé en main. */
    public static final class Pickup extends TickingSystem<EntityStore> {

        @Override
        public void tick(float dt, int systemIndex, Store<EntityStore> store) {
            World world = store.getExternalData().getWorld();
            if (!isSolidOcean(world)) {
                return;
            }
            float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
            elapsed[0] += dt;
            if (elapsed[0] < INTERVAL) {
                return;
            }
            elapsed[0] = 0f;
            world.execute(() -> step(world));
        }
    }

    /** Cristal en main : les demandes de changement de case (barre ou main secondaire) sont refusées. */
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
            if (event.isCancelled() || !event.isClientRequest()) {
                return;
            }
            Ref<EntityStore> ref = chunk.getReferenceTo(index);
            if (holds(store, ref)) {
                event.setCancelled(true);
            }
        }
    }
}
