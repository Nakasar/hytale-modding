package dev.nakasar.hytale.fractals.party;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.GlobalSpawnProvider;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Filet de sécurité de l'Observatoire et des fractales (copie de {@code TowerFallSystem} du mod Vampires) : un joueur
 * tombé sous {@value #RESCUE_Y} est ramené au point d'apparition du monde (le parvis de l'Observatoire, le départ ou
 * le dernier point de contrôle d'une fractale). Toutes les îles du mod restent au-dessus de cette hauteur.
 */
public final class FallRescueSystem extends EntityTickingSystem<EntityStore> {

    public static final double RESCUE_Y = 40;

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
        if (chunk.getComponent(index, TransformComponent.getComponentType()).getPosition().y() >= RESCUE_Y) {
            return;
        }
        World world = store.getExternalData().getWorld();
        if (!FractalCatalog.isObservatory(world) && FractalCatalog.fractalOf(world) == null) {
            return;
        }
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        if (buffer.getComponent(ref, Teleport.getComponentType()) != null) {
            return;   // déjà en route
        }
        if (!(world.getWorldConfig().getSpawnProvider() instanceof GlobalSpawnProvider global)
                || global.getGlobalSpawnPoint() == null) {
            return;
        }
        buffer.putComponent(ref, Teleport.getComponentType(), Teleport.createForPlayer(new Transform(global.getGlobalSpawnPoint())));
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef != null) {
            playerRef.sendMessage(Message.translation("nakasar_fractals.observatory.fallRescue"));
        }
    }
}
