package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Chaque pas : climats des joueurs ({@link Climate}) ; toutes les 5 s : croissance du matin de la ruche ({@link Hive}). */
public final class ZoneSystem extends TickingSystem<EntityStore> {

    private float hiveClock;

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (world.getPlayerRefs().isEmpty()) {
            return;
        }
        Climate.step(world, store, dt);
        hiveClock += dt;
        if (hiveClock >= 5f && Zones.generator(world) != null) {
            hiveClock = 0f;
            Hive.morning(world, store);
        }
    }
}
