package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.function.Consumer;

/** Actions différées des fractales (coup qui tombe après son annonce, porte qui se referme), menées par {@link TelegraphSystem}. */
public final class Delayed {

    private Delayed() {
    }

    /** Lance `action` dans `seconds` secondes sur le thread du monde. */
    public static void later(World world, float seconds, Consumer<Store<EntityStore>> action) {
        long[] due = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (due[0] < 0) {
                due[0] = now + Telegraphs.seconds(seconds);
            }
            if (now < due[0]) {
                return false;
            }
            action.accept(s);
            return true;
        });
    }
}
