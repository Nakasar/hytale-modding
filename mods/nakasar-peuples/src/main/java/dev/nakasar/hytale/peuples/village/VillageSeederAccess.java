package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.server.core.universe.world.World;

/** Accès public au point d'apparition lu par {@link VillageSeeder} (seeder des zones, étape 8). */
public final class VillageSeederAccess {

    private VillageSeederAccess() {
    }

    public static int[] spawn(World world) {
        return VillageSeeder.spawn(world);
    }
}
