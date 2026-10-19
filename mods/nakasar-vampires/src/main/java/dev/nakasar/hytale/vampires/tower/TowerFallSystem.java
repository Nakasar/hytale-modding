package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.builtin.portals.resources.PortalWorld;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.GlobalSpawnProvider;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Filet de sécurité de la Tour de l'Alchimiste : un joueur tombé dans le vide est ramené au point d'apparition du monde,
 * c'est-à-dire au dernier point de contrôle allumé (les volumes Checkpoint_NN de l'instance, copiés de Deepworks, le
 * déplacent avec l'effet SetWorldSpawn), ou sur le parvis d'arrivée si aucun ne l'est.
 *
 * <p>Deepworks pose des volumes « Fall_Teleport » vers des points fixes sous son décor ; notre vide est partout et le
 * point de retour change avec les points de contrôle : ce système joue ce rôle.
 */
public final class TowerFallSystem extends EntityTickingSystem<EntityStore> {

    /** Type de portail de la tour (PortalTypes/Nakasar_Alchemist_Tower.json). */
    public static final String PORTAL_ID = "Nakasar_Alchemist_Tower";
    /**
     * Profondeur sous le sol de l'île de la tour à partir de laquelle un joueur est tombé (les îles font moins de 40 blocs
     * d'épaisseur ; le plus bas des îlots a son dessus 8 blocs plus bas que l'île).
     */
    static final double FALL_DEPTH = 60;

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
        if (position.y() >= TowerLayout.GROUND_Y - FALL_DEPTH || !isTower(store)) {
            return;
        }
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        if (buffer.getComponent(ref, Teleport.getComponentType()) != null) {
            return; // déjà en route
        }
        Transform target = spawn(store.getExternalData().getWorld());
        buffer.putComponent(ref, Teleport.getComponentType(),
                Teleport.createForPlayer(target));
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef != null) {
            playerRef.sendMessage(Message.translation("nakasar_alchemist.tower.fallRescue"));
        }
    }

    /** Point d'apparition du monde (déplacé par les points de contrôle), sinon le parvis d'arrivée. */
    private static Transform spawn(World world) {
        if (world.getWorldConfig().getSpawnProvider() instanceof GlobalSpawnProvider global
                && global.getGlobalSpawnPoint() != null) {
            return new Transform(global.getGlobalSpawnPoint());
        }
        return new Transform(new Vector3d(TowerLayout.ARRIVAL), new Rotation3f());
    }

    static boolean isTower(Store<EntityStore> store) {
        PortalWorld portal = store.getResource(PortalWorld.getResourceType());
        return portal != null && portal.exists() && portal.getPortalType() != null
                && PORTAL_ID.equals(portal.getPortalType().getId());
    }
}
