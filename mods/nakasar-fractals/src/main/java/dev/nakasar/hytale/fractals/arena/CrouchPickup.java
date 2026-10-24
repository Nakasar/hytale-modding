package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.MovementStates;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
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
import java.util.function.BiConsumer;

/**
 * Objets de mécanique qui se ramassent accroupi et se gardent en main (cristal réfléchissant de l'Océan solide, pierre
 * imprégnée du Volcanique), comme le marteau de la Falaise :
 * <ul>
 *   <li>au sol, ils ne se ramassent pas en passant dessus ({@link PreventPickup}, {@link Drops}) : on s'accroupit à
 *   moins de {@value #REACH} blocs ({@link Pickup}) ; un seul par joueur ;</li>
 *   <li>ramassé, l'objet va dans la barre d'inventaire et y est sélectionné, main secondaire vidée ({@link HandLock}) ;</li>
 *   <li>tant qu'on le porte, on ne change pas d'objet sélectionné ; un objet en trop retombe au sol.</li>
 * </ul>
 * Un seul couple de systèmes sert tous les objets déclarés par {@link #register}.
 */
public final class CrouchPickup {

    public static final double REACH = 2.0;
    public static final double FORGET = 4.0;
    private static final float INTERVAL = 0.15f;

    /**
     * Objet `id` de la fractale `fractal` : `crouchKey` / `alreadyKey` (clés de langue) s'affichent près d'un objet au
     * sol, selon qu'on en porte déjà un ; `drop` fait retomber un objet en trop.
     */
    public record Item(String id, String fractal, String crouchKey, String alreadyKey,
                       BiConsumer<Store<EntityStore>, Vector3d> drop) {
    }

    private static final Map<String, Item> ITEMS = new ConcurrentHashMap<>();
    /** Objets au sol suivis, par monde : référence → id. */
    private static final Map<World, Map<Ref<EntityStore>, String>> GROUND = new WeakHashMap<>();
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());
    private static final Map<World, Set<UUID>> HINTED = Collections.synchronizedMap(new WeakHashMap<>());

    private CrouchPickup() {
    }

    /** Déclare l'objet et le garde en main ({@link HandLock#lock}). */
    public static void register(Item item) {
        ITEMS.put(item.id(), item);
        HandLock.lock(item.id());
    }

    private static synchronized Map<Ref<EntityStore>, String> ground(World world) {
        return GROUND.computeIfAbsent(world, w -> new ConcurrentHashMap<>());
    }

    /** Les objets `id` au sol dans `world`. */
    public static List<Ref<EntityStore>> onGround(World world, String id) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        ground(world).forEach((ref, item) -> {
            if (item.equals(id)) {
                out.add(ref);
            }
        });
        return out;
    }

    private static boolean is(ItemStack stack, String id) {
        return stack != null && !stack.isEmpty() && id.equals(stack.getItemId());
    }

    public static int count(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING).countItemStacks(s -> is(s, id));
    }

    public static boolean holds(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        return is(InventoryComponent.getItemInHand(store, ref), id);
    }

    /** Retire tous les objets `id` de l'inventaire ; rend combien de cases en tenaient. */
    public static int removeAll(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String id) {
        CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING);
        List<Short> slots = new ArrayList<>();
        inventory.forEach((slot, stack) -> {
            if (is(stack, id)) {
                slots.add(slot);
            }
        });
        for (short slot : slots) {
            inventory.removeItemStackFromSlot(slot);
        }
        return slots.size();
    }

    /** Retire tous les objets `id` au sol dans `world`. */
    public static void removeGround(World world, Store<EntityStore> store, String id) {
        for (Ref<EntityStore> ref : onGround(world, id)) {
            ground(world).remove(ref);
            if (ref.isValid()) {
                store.removeEntity(ref, RemoveReason.REMOVE);
            }
        }
    }

    /** Met un objet `id` dans la barre d'inventaire et le sélectionne. */
    public static void give(Store<EntityStore> store, Ref<EntityStore> ref, String id) {
        HandLock.putInHand(store, ref, new ItemStack(id, 1));
    }

    /** L'objet reste en main ; un objet en trop retombe au sol. Vrai si le joueur en porte un. */
    private static boolean keep(Store<EntityStore> store, Ref<EntityStore> ref, Item item, Vector3d at) {
        int n = count(store, ref, item.id());
        if (n > 1) {
            removeAll(store, ref, item.id());
            give(store, ref, item.id());
            for (int i = 1; i < n; i++) {
                item.drop().accept(store, at);
            }
        } else if (n == 1) {
            HandLock.ensureHeld(store, ref, item.id());
        }
        return n > 0;
    }

    private static boolean crouching(Store<EntityStore> store, Ref<EntityStore> ref) {
        MovementStatesComponent movement = store.getComponent(ref, MovementStatesComponent.getComponentType());
        MovementStates states = movement == null ? null : movement.getMovementStates();
        return states != null && (states.crouching || states.forcedCrouching);
    }

    private static List<Item> itemsOf(World world) {
        String fractal = world == null ? null : FractalCatalog.fractalOf(world);
        List<Item> out = new ArrayList<>();
        if (fractal != null) {
            for (Item item : ITEMS.values()) {
                if (fractal.equals(item.fractal())) {
                    out.add(item);
                }
            }
        }
        return out;
    }

    private static void step(World world, List<Item> items) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Map<Ref<EntityStore>, String> ground = ground(world);
        ground.keySet().removeIf(ref -> !ref.isValid());
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
            boolean carrying = false;
            for (Item item : items) {
                carrying |= keep(store, ref, item, at);
            }
            Ref<EntityStore> closest = null;
            Item closestItem = null;
            double best = Double.MAX_VALUE;
            for (Map.Entry<Ref<EntityStore>, String> e : ground.entrySet()) {
                TransformComponent t = store.getComponent(e.getKey(), TransformComponent.getComponentType());
                Item item = ITEMS.get(e.getValue());
                if (t != null && item != null) {
                    double d = t.getPosition().distance(at);
                    if (d < best) {
                        best = d;
                        closest = e.getKey();
                        closestItem = item;
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
            if (crouching(store, ref) && !carrying) {
                ground.remove(closest);
                store.removeEntity(closest, RemoveReason.REMOVE);
                give(store, ref, closestItem.id());
                hinted.remove(player.getUuid());
            } else if (hinted.add(player.getUuid())) {
                NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(
                        carrying ? closestItem.alreadyKey() : closestItem.crouchKey()), NotificationStyle.Default);
            }
        }
    }

    /** Objet déclaré tombé au sol dans sa fractale : pas de ramassage automatique, suivi pour {@link Pickup}. */
    public static final class Drops extends RefSystem<EntityStore> {

        @Override
        public Query<EntityStore> getQuery() {
            return ItemComponent.getComponentType();
        }

        @Override
        public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
            ItemComponent component = store.getComponent(ref, ItemComponent.getComponentType());
            ItemStack stack = component == null ? null : component.getItemStack();
            Item item = stack == null || stack.isEmpty() ? null : ITEMS.get(stack.getItemId());
            World world = store.getExternalData().getWorld();
            if (item == null || world == null || !item.fractal().equals(FractalCatalog.fractalOf(world))) {
                return;
            }
            buffer.ensureComponent(ref, PreventPickup.getComponentType());
            ground(world).put(ref, item.id());
        }

        @Override
        public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
            World world = store.getExternalData().getWorld();
            if (world != null) {
                ground(world).remove(ref);
            }
        }
    }

    /** Toutes les {@value #INTERVAL} s dans une fractale qui a des objets déclarés : ramassage accroupi, objet gardé en main. */
    public static final class Pickup extends TickingSystem<EntityStore> {

        @Override
        public void tick(float dt, int systemIndex, Store<EntityStore> store) {
            World world = store.getExternalData().getWorld();
            List<Item> items = itemsOf(world);
            if (items.isEmpty()) {
                return;
            }
            float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
            elapsed[0] += dt;
            if (elapsed[0] < INTERVAL) {
                return;
            }
            elapsed[0] = 0f;
            world.execute(() -> step(world, items));
        }
    }
}
