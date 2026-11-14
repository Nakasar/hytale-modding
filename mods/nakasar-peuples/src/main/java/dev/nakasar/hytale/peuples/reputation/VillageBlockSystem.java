package dev.nakasar.hytale.peuples.reputation;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3i;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Casser un bloc d'un bâtiment du village coûte de la réputation (GDD, Jauges : « casser un bloc du village ») :
 * {@value #PENALTY} par bloc cassé par un joueur dans l'emprise d'un bâtiment déjà collé du plan du village (au-dessus
 * du sol de la place), ou sur le dépôt, le tableau ou la bannière. Les potagers ne comptent pas (on y récolte), ni le
 * reste du terrain. La notification ne revient qu'une fois toutes les {@value #NOTIFY_SECONDS} s.
 */
public final class VillageBlockSystem extends EntityEventSystem<EntityStore, BreakBlockEvent> {

    public static final int PENALTY = -2;
    private static final int NOTIFY_SECONDS = 6;
    /** Le bâtiment commence à cette hauteur sous le cœur (fondations des prefabs). */
    private static final int BELOW_HEART = 2;

    private static final Map<UUID, Long> LAST_NOTICE = new ConcurrentHashMap<>();

    public VillageBlockSystem() {
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
        PlayerRef player = chunk.getComponent(index, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        World world = store.getExternalData().getWorld();
        Village village = villageAt(world, at.x, at.y, at.z);
        if (village == null) {
            return;
        }
        long now = System.currentTimeMillis();
        Long last = LAST_NOTICE.get(player.getUuid());
        boolean notify = last == null || now - last >= NOTIFY_SECONDS * 1000L;
        if (notify) {
            LAST_NOTICE.put(player.getUuid(), now);
        }
        world.execute(() -> {
            Ref<EntityStore> ref = player.getReference();
            if (ref != null && ref.isValid()) {
                Reputations.change(world, world.getEntityStore().getStore(), ref, player, village, PENALTY,
                        Reputations.KEYS + "reason.block", notify);
            }
        });
    }

    /** Village dont un bâtiment (ou le dépôt, le tableau, la bannière) occupe le bloc (x, y, z), ou null. */
    public static Village villageAt(World world, int x, int y, int z) {
        for (Village v : Villages.registry(world).all()) {
            if (same(v.deposit(), x, y, z) || same(v.board(), x, y, z) || (v.hasBanner() && same(v.banner(), x, y, z))) {
                return v;
            }
            VillageLayout layout = v.layout() == null ? null : VillageLayout.get(v.layout());
            if (layout == null || y < v.y() - BELOW_HEART) {
                continue;
            }
            List<String> built = Arrays.asList(v.built());
            for (VillageLayout.Building b : layout.buildings()) {
                if (!built.contains(b.id()) || b.prefab() == null || b.prefab().contains("/Garden/")) {
                    continue;
                }
                int[] r = b.rect();
                if (x >= v.x() + r[0] && x <= v.x() + r[1] && z >= v.z() + r[2] && z <= v.z() + r[3]) {
                    return v;
                }
            }
        }
        return null;
    }

    private static boolean same(int[] p, int x, int y, int z) {
        return p != null && p[0] == x && p[1] == y && p[2] == z;
    }

    public static void clearAll() {
        LAST_NOTICE.clear();
    }
}
