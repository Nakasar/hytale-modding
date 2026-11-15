package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.Requests;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * La vie des villages (étape 5), toutes les {@value #INTERVAL} s et par monde, sur le thread du monde : un chantier
 * commence quand la jauge est pleine et que le dépôt contient ses matériaux, il se finit à son heure, et les villageois
 * à métier suivent leur routine ({@link Villagers}). Rien ne se passe dans un village sans joueur à moins de
 * {@value Chantiers#ANNOUNCE_RADIUS} blocs (ses chunks ne sont pas chargés pour rien).
 */
public final class VillageLifeSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 2f;

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
        world.execute(() -> step(world, step));
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Vector3d> players = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = ref == null || !ref.isValid() ? null : Requests.position(store, ref);
            if (at != null) {
                players.add(at);
            }
        }
        if (players.isEmpty()) {
            return;
        }
        for (Village village : new ArrayList<>(Villages.registry(world).all())) {
            if (Chantiers.layout(village) == null || !watched(village, players)) {
                continue;
            }
            if (village.chantier() == null) {
                if (village.tier() < Tiers.MAX && village.essor() >= Tiers.threshold(village.tier())) {
                    Chantiers.start(world, village, false, state -> Villagers.forgetGround());
                }
            } else if (Chantiers.due(store, village)) {
                Chantiers.finish(world, village, Villagers::forgetGround);
            } else {
                Chantiers.grow(world, village);
            }
            Plots.step(world, store, village);
        }
        Villagers.step(world, store, players, dt);
        dev.nakasar.hytale.peuples.workshop.Livestock.step(world, store, players);
    }

    private static boolean watched(Village village, List<Vector3d> players) {
        for (Vector3d p : players) {
            if (village.horizontalDistanceSquared(p.x(), p.z()) <= (double) Chantiers.ANNOUNCE_RADIUS * Chantiers.ANNOUNCE_RADIUS) {
                return true;
            }
        }
        return false;
    }
}
