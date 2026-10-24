package dev.nakasar.hytale.fractals.solidocean;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.CrouchPickup;

import java.util.List;

/**
 * Le cristal réfléchissant de l'Abîme de Jade se porte comme le marteau de la Falaise ({@link CrouchPickup}) : ramassé
 * accroupi, un seul par joueur, gardé en main.
 */
public final class CrystalHold {

    private CrystalHold() {
    }

    static void register() {
        CrouchPickup.register(new CrouchPickup.Item(SolidOcean.CRYSTAL, SolidOcean.FRACTAL,
                SolidOcean.MESSAGES + "crystal.crouch", SolidOcean.MESSAGES + "crystal.already", SolidOcean::dropCrystal));
    }

    static List<Ref<EntityStore>> onGround(World world) {
        return CrouchPickup.onGround(world, SolidOcean.CRYSTAL);
    }

    static boolean holds(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return CrouchPickup.holds(store, ref, SolidOcean.CRYSTAL);
    }

    static int removeAll(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        return CrouchPickup.removeAll(store, ref, SolidOcean.CRYSTAL);
    }

    static void give(Store<EntityStore> store, Ref<EntityStore> ref) {
        CrouchPickup.give(store, ref, SolidOcean.CRYSTAL);
    }
}
