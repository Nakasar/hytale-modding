package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.data.PlayerRespawnPointData;
import com.hypixel.hytale.server.core.entity.entities.player.data.PlayerWorldData;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import org.joml.Vector3d;
import org.joml.Vector3i;

/**
 * Points de contrôle de la Tour de l'Alchimiste (statues de lumière, positions dans {@link TowerLayout}).
 *
 * <p>Le joueur qui s'arrête près d'un point de contrôle plus haut que le dernier atteint en fait son point de
 * réapparition dans l'instance (données du joueur pour ce monde, comme un lit), est soigné et voit un titre. À sa mort,
 * il réapparaît là ; s'il tombe dans le vide, {@link TowerFallSystem} l'y ramène. Chaque joueur a ses propres points :
 * un retardataire n'est pas téléporté avec le groupe.
 */
public final class TowerCheckpointSystem extends EntityTickingSystem<EntityStore> {

    /** Nom des points de réapparition posés par la tour, suivi du numéro du point de contrôle (1 = bibliothèque). */
    static final String RESPAWN_PREFIX = "nakasar_tower_checkpoint_";
    private static final double REACH = 2.5;

    private static final Query<EntityStore> QUERY = Query.and(Player.getComponentType(), TransformComponent.getComponentType());

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        int reached = near(position);
        if (reached < 0 || !TowerFallSystem.isTower(store)) {
            return;
        }
        Player player = chunk.getComponent(index, Player.getComponentType());
        PlayerWorldData data = player.getPlayerConfigData().getPerWorldData(store.getExternalData().getWorld().getName());
        if (reached <= checkpoint(data)) {
            return;
        }
        Vector3d spot = TowerLayout.CHECKPOINTS[reached];
        Vector3i block = new Vector3i((int) Math.floor(spot.x()), (int) Math.floor(spot.y()), (int) Math.floor(spot.z()));
        data.setRespawnPoints(new PlayerRespawnPointData[]{
                new PlayerRespawnPointData(block, new Vector3d(spot), RESPAWN_PREFIX + (reached + 1))});
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        EntityStatMap stats = buffer.getComponent(ref, EntityStatMap.getComponentType());
        if (stats != null) {
            stats.maximizeStatValue(DefaultEntityStatTypes.getHealth());
        }
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef != null) {
            EventTitleUtil.showEventTitleToPlayer(playerRef,
                    Message.translation("nakasar_alchemist.checkpoint.title"),
                    Message.translation("nakasar_alchemist.checkpoint." + (reached + 1)), EventTitleStyle.Default);
        }
    }

    /** Indice du point de contrôle tout proche de `position`, ou -1. */
    private static int near(Vector3d position) {
        for (int i = 0; i < TowerLayout.CHECKPOINTS.length; i++) {
            Vector3d spot = TowerLayout.CHECKPOINTS[i];
            double dy = position.y() - spot.y();
            if (dy > -0.5 && dy < 3 && Math.hypot(position.x() - spot.x(), position.z() - spot.z()) <= REACH) {
                return i;
            }
        }
        return -1;
    }

    /** Indice du dernier point de contrôle atteint dans ce monde, ou -1 (aucun : réapparition sur le parvis). */
    static int checkpoint(PlayerWorldData data) {
        PlayerRespawnPointData[] points = data.getRespawnPoints();
        if (points == null) {
            return -1;
        }
        int best = -1;
        for (PlayerRespawnPointData point : points) {
            String name = point.getName();
            if (name != null && name.startsWith(RESPAWN_PREFIX)) {
                try {
                    best = Math.max(best, Integer.parseInt(name.substring(RESPAWN_PREFIX.length())) - 1);
                } catch (NumberFormatException ignored) {
                    // point posé par autre chose que la tour
                }
            }
        }
        return best;
    }

    /** Position de réapparition du joueur dans la tour : son dernier point de contrôle, sinon le parvis. */
    static Vector3d respawn(PlayerWorldData data) {
        int i = checkpoint(data);
        return new Vector3d(i < 0 || i >= TowerLayout.CHECKPOINTS.length ? TowerLayout.ARRIVAL : TowerLayout.CHECKPOINTS[i]);
    }
}
