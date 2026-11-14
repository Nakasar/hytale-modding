package dev.nakasar.hytale.peuples.klops;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/** Toutes les {@value #INTERVAL} s dans le monde par défaut : tournée du Klops errant et livraison des colis ({@link Klops}). */
public final class KlopsSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 2f;

    private float elapsed;

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (world != Universe.get().getDefaultWorld()) {
            return;
        }
        elapsed += dt;
        if (elapsed < INTERVAL) {
            return;
        }
        elapsed = 0f;
        world.execute(() -> {
            Store<EntityStore> s = world.getEntityStore().getStore();
            if (Villages.registry(world).all().isEmpty()) {
                return;
            }
            List<Vector3d> players = new ArrayList<>();
            for (PlayerRef p : world.getPlayerRefs()) {
                Vector3d at = Requests.position(s, p.getReference());
                if (at != null) {
                    players.add(at);
                }
            }
            Klops.step(world, s, players);
            Klops.deliveries(world, s);
        });
    }
}
