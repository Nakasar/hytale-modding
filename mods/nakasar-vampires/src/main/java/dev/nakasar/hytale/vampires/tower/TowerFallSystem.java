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
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Filet de sécurité de la Tour de l'Alchimiste : un joueur tombé dans le vide est ramené sur le parvis d'arrivée.
 *
 * <p>Les points de vue de la tour sont fermés par des murs trop hauts pour être sautés (tools/generate_alchemist_tower.py),
 * comme dans le donjon vanilla Deepworks, qui ajoute en plus des volumes « Fall_Teleport » sous son décor. Nos
 * instances sont générées, sans volumes déclencheurs : ce système joue ce rôle. Les points de contrôle de la tour
 * remplaceront le parvis comme point de retour.
 */
public final class TowerFallSystem extends EntityTickingSystem<EntityStore> {

    /** Type de portail de la tour (PortalTypes/Nakasar_Alchemist_Tower.json). */
    public static final String PORTAL_ID = "Nakasar_Alchemist_Tower";
    /** Première couche d'air au-dessus du sol des îles (GROUND_Y du générateur). */
    static final double GROUND_Y = 100;
    /** Profondeur sous le sol à partir de laquelle un joueur est tombé de l'île (l'île fait moins de 40 blocs d'épaisseur). */
    static final double FALL_DEPTH = 48;
    static final Vector3d ARRIVAL = new Vector3d(0.5, GROUND_Y, 0.5);

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
        if (position.y() >= GROUND_Y - FALL_DEPTH || !isTower(store)) {
            return;
        }
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        if (buffer.getComponent(ref, Teleport.getComponentType()) != null) {
            return; // déjà en route vers le parvis
        }
        buffer.putComponent(ref, Teleport.getComponentType(), Teleport.createForPlayer(new Vector3d(ARRIVAL), new Rotation3f()));
        PlayerRef player = chunk.getComponent(index, PlayerRef.getComponentType());
        if (player != null) {
            player.sendMessage(Message.translation("nakasar_alchemist.tower.fallRescue"));
        }
    }

    static boolean isTower(Store<EntityStore> store) {
        PortalWorld portal = store.getResource(PortalWorld.getResourceType());
        return portal != null && portal.exists() && portal.getPortalType() != null
                && PORTAL_ID.equals(portal.getPortalType().getId());
    }
}
