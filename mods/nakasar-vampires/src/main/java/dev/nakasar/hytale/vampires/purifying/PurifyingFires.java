package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * Feux purificateurs proches de chaque mort-vivant (x, z des centres des blocs, à plat), relevés par
 * {@link PurifyingFireSystem} et lus à chaque tick par {@link PurifyingSteeringSystem}. Les deux systèmes ne sont
 * pas parallèles et tournent sur le fil du monde.
 *
 * <p>Tient aussi les auras de lumière (rune Aura de lumière, {@link LightAuraSystem}) : position (x, y, z) de
 * chaque porteur, mise à jour à chaque tick. Une aura repousse comme un feu posé, centrée sur son porteur. Table
 * partagée par les fils des mondes, filtrée par monde à la lecture.
 */
public final class PurifyingFires {

    private final Map<Ref<EntityStore>, double[]> nearby = new HashMap<>();
    private final Map<Ref<EntityStore>, double[]> auras = new ConcurrentHashMap<>();

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

    void putAura(Ref<EntityStore> ref, double x, double y, double z) {
        auras.put(ref, new double[] {x, y, z});
    }

    void removeAura(Ref<EntityStore> ref) {
        auras.remove(ref);
    }

    /** Auras actives du monde de {@code store} (positions x, y, z de leurs porteurs), sauf celle d'{@code exclude}. */
    void forEachAura(Store<EntityStore> store, Ref<EntityStore> exclude, Consumer<double[]> out) {
        if (auras.isEmpty()) {
            return;
        }
        auras.entrySet().removeIf(e -> !e.getKey().isValid());
        auras.forEach((ref, position) -> {
            if (ref.getStore() == store && !ref.equals(exclude)) {
                out.accept(position);
            }
        });
    }
}
