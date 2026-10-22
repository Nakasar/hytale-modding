package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/** Avance le déroulé de la fractale du monde ({@link FractalStage#step}) quatre fois par seconde. */
public final class StageSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.25f;
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        FractalStage stage = Stages.of(world);
        if (stage == null) {
            return;
        }
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        float step = elapsed[0];
        elapsed[0] = 0f;
        world.execute(() -> stage.step(world, step));
    }
}
