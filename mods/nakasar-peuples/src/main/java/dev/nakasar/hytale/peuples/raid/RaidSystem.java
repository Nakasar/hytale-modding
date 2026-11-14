package dev.nakasar.hytale.peuples.raid;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Les raids (étape 6), toutes les {@value #INTERVAL} s et par monde, sur le thread du monde : tirage du matin, début à
 * la nuit prévue, annonce, vague, bilan ({@link Raids#step}).
 */
public final class RaidSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 1f;

    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        float step = elapsed[0];
        elapsed[0] = 0f;
        if (Villages.registry(world).all().isEmpty()) {
            return;
        }
        world.execute(() -> Raids.step(world, step));
    }
}
