package dev.nakasar.hytale.peuples.trork;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;
import java.util.WeakHashMap;

/**
 * Toutes les {@value #INTERVAL} s : la teinte de la Peinture de guerre suit le drapeau du joueur ({@link WarPaint}) ;
 * elle revient après une reconnexion ou une mort (l'effet infini n'est pas gardé), et part si un opérateur ôte le
 * drapeau.
 */
public final class WarPaintSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 2f;

    private final Map<World, Float> elapsed = new WeakHashMap<>();

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float t = elapsed.getOrDefault(world, 0f) + dt;
        if (t < INTERVAL) {
            elapsed.put(world, t);
            return;
        }
        elapsed.put(world, 0f);
        world.execute(() -> {
            Store<EntityStore> s = world.getEntityStore().getStore();
            for (PlayerRef player : world.getPlayerRefs()) {
                Ref<EntityStore> ref = player.getReference();
                if (ref != null && ref.isValid()) {
                    WarPaint.sync(s, ref, WarPaint.worn(s, ref));
                }
            }
        });
    }
}
