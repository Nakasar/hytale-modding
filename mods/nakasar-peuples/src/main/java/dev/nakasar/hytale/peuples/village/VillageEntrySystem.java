package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.data.PlayerWorldData;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.meta.state.BlockMapMarkersResource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Entrée dans un village (GDD, Exploration : « le village est repéré et nommé ») : quand un joueur passe à moins de
 * {@value #ENTER_RADIUS} blocs du cœur, un titre d'écran donne le nom du village, son peuple, le rang du joueur et
 * l'humeur du village. Il ne revient qu'après être ressorti au-delà de {@value #LEAVE_RADIUS} blocs.
 *
 * <p>La bannière du village est un marqueur de carte découvrable : on la révèle au joueur qui passe à moins de
 * {@value #REVEAL_RADIUS} blocs (elle reste ensuite sur sa carte).
 */
public final class VillageEntrySystem extends TickingSystem<EntityStore> {

    public static final int ENTER_RADIUS = 40;
    public static final int LEAVE_RADIUS = 52;
    public static final int REVEAL_RADIUS = 300;
    private static final float INTERVAL = 0.5f;

    private static final String MESSAGES = "nakasar_peuples.entry.";

    private static final class State {
        float elapsed;
        /** Joueur -> id du village où il se trouve. */
        final Map<UUID, String> inside = new HashMap<>();
    }

    private static final Map<World, State> STATES = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        State state = STATES.computeIfAbsent(world, w -> new State());
        state.elapsed += dt;
        if (state.elapsed < INTERVAL) {
            return;
        }
        state.elapsed = 0f;
        if (Villages.registry(world).all().isEmpty()) {
            state.inside.clear();
            return;
        }
        // Le store est en plein traitement : on regarde juste après.
        world.execute(() -> scan(world, state));
    }

    private static void scan(World world, State state) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        VillageRegistry registry = Villages.registry(world);
        Set<UUID> here = new HashSet<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            TransformComponent transform = ref == null || !ref.isValid() ? null
                    : store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            UUID id = player.getUuid();
            here.add(id);
            Vector3d pos = transform.getPosition();

            String currentId = state.inside.get(id);
            Village current = currentId == null ? null : registry.byId(currentId);
            if (current != null && current.horizontalDistanceSquared(pos.x(), pos.z()) > (double) LEAVE_RADIUS * LEAVE_RADIUS) {
                state.inside.remove(id);
                current = null;
            }
            Village nearest = null;
            double best = Double.MAX_VALUE;
            for (Village village : registry.all()) {
                double d = village.horizontalDistanceSquared(pos.x(), pos.z());
                if (village.hasBanner() && d <= (double) REVEAL_RADIUS * REVEAL_RADIUS) {
                    reveal(world, store, ref, village);
                }
                if (d < best) {
                    best = d;
                    nearest = village;
                }
            }
            if (current == null && nearest != null && best <= (double) ENTER_RADIUS * ENTER_RADIUS) {
                state.inside.put(id, nearest.id());
                showTitle(player, nearest);
            }
        }
        state.inside.keySet().retainAll(here);
    }

    /** Titre d'écran d'entrée : nom du village, puis peuple · rang · humeur. */
    public static void showTitle(PlayerRef player, Village village) {
        Message title = Message.raw(village.name());
        Message subtitle = Message.translation(MESSAGES + "subtitle")
                .param("people", Message.translation(village.people().nameKey()))
                .param("rank", Message.translation("nakasar_peuples.rank.stranger"))
                .param("mood", Message.translation(MESSAGES + "mood." + village.tier()));
        EventTitleUtil.showEventTitleToPlayer(player, title, subtitle, EventTitleStyle.Default, null, 3f, 0.5f, 1f);
    }

    private static void reveal(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        int[] b = village.banner();
        BlockMapMarkersResource.BlockMapMarkerData marker = BlockMapMarkersResource.of(world).getMarker(b[0], b[1], b[2]);
        if (marker == null || marker.getMarkerId() == null) {
            return;
        }
        Player player = store.getComponent(ref, Player.getComponentType());
        if (player == null) {
            return;
        }
        PlayerWorldData data = player.getPlayerConfigData().getPerWorldData(world.getName());
        if (data != null && !data.isMarkerRevealed(marker.getMarkerId())) {
            data.revealMarker(marker.getMarkerId());
        }
    }
}
