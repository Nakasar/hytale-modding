package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/** Mène la Falaise ({@link Cliffside#step}) quatre fois par seconde dans chaque instance de la Falaise. */
public final class CliffsideSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.25f;
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (!Cliffside.isCliffside(world)) {
            return;
        }
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        float step = elapsed[0];
        elapsed[0] = 0f;
        world.execute(() -> Cliffside.step(world, step));
    }
}
