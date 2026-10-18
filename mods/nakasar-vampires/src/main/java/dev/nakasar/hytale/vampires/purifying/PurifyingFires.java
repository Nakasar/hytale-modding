package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.HashMap;
import java.util.Map;

/**
 * Feux purificateurs proches de chaque mort-vivant (x, z des centres des blocs, à plat), relevés par
 * {@link PurifyingFireSystem} et lus à chaque tick par {@link PurifyingSteeringSystem}. Les deux systèmes ne sont
 * pas parallèles et tournent sur le fil du monde.
 */
public final class PurifyingFires {

    private final Map<Ref<EntityStore>, double[]> nearby = new HashMap<>();

    boolean isEmpty() {
        return nearby.isEmpty();
    }

    double[] get(Ref<EntityStore> ref) {
        return nearby.get(ref);
    }

    void put(Ref<EntityStore> ref, double[] fires) {
        if (nearby.size() > 256) {
            nearby.keySet().removeIf(r -> !r.isValid());
        }
        nearby.put(ref, fires);
    }

    void remove(Ref<EntityStore> ref) {
        nearby.remove(ref);
    }
}
