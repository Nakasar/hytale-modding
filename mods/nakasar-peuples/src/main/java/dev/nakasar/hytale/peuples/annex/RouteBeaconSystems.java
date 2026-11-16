package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent;
import com.hypixel.hytale.server.core.event.events.ecs.PlaceBlockEvent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.village.VillageRegistry;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3i;

/** Pose et casse des balises de route ({@link Routes}) : la liste des balises du monde suit les blocs. */
public final class RouteBeaconSystems {

    private RouteBeaconSystems() {
    }

    /** Balise posée : ajoutée aux routes, le joueur voit à combien de balises elle est reliée. */
    public static final class Place extends EntityEventSystem<EntityStore, PlaceBlockEvent> {

        public Place() {
            super(PlaceBlockEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return PlayerRef.getComponentType();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                           PlaceBlockEvent event) {
            if (event.isCancelled()) {
                return;
            }
            ItemStack stack = event.getItemInHand();
            Vector3i at = event.getTargetBlock();
            PlayerRef player = chunk.getComponent(index, PlayerRef.getComponentType());
            if (stack == null || ItemStack.isEmpty(stack) || !Routes.isBeacon(stack.getItemId()) || at == null || player == null) {
                return;
            }
            World world = store.getExternalData().getWorld();
            VillageRegistry registry = Villages.registry(world);
            if (registry.beacons().size() >= Routes.MAX_BEACONS) {
                event.setCancelled(true);
                tell(player, Message.translation(Annexes.KEYS + "route.full").param("max", Routes.MAX_BEACONS), NotificationStyle.Danger);
                return;
            }
            int x = at.x;
            int y = at.y;
            int z = at.z;
            world.execute(() -> {
                Villages.registry(world).addBeacon(x, y, z);
                int links = Routes.links(world, x, z);
                tell(player, Message.translation(Annexes.KEYS + (links == 0 ? "route.alone" : "route.placed"))
                        .param("links", links).param("range", Routes.LINK), links == 0 ? NotificationStyle.Warning : NotificationStyle.Success);
            });
        }
    }

    /** Balise cassée : retirée des routes (on tolère la case du haut d'une balise haute). */
    public static final class Break extends EntityEventSystem<EntityStore, BreakBlockEvent> {

        public Break() {
            super(BreakBlockEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return PlayerRef.getComponentType();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                           BreakBlockEvent event) {
            Vector3i at = event.getTargetBlock();
            if (at == null || event.isCancelled()) {
                return;
            }
            World world = store.getExternalData().getWorld();
            VillageRegistry registry = Villages.registry(world);
            int found = Integer.MIN_VALUE;
            for (int dy = 0; dy <= 2 && found == Integer.MIN_VALUE; dy++) {
                if (registry.isBeacon(at.x, at.y - dy, at.z)) {
                    found = at.y - dy;
                }
            }
            if (found == Integer.MIN_VALUE) {
                return;
            }
            PlayerRef player = chunk.getComponent(index, PlayerRef.getComponentType());
            int x = at.x;
            int y = found;
            int z = at.z;
            world.execute(() -> {
                if (Villages.registry(world).removeBeacon(x, y, z) && player != null) {
                    tell(player, Message.translation(Annexes.KEYS + "route.removed"), NotificationStyle.Default);
                }
            });
        }
    }

    private static void tell(PlayerRef player, Message message, NotificationStyle style) {
        NotificationUtil.sendNotification(player.getPacketHandler(), message, style);
    }
}
