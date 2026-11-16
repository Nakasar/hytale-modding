package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.List;
import java.util.Random;

/**
 * Le pas du monde vivant, dans le monde par défaut, joueurs connectés : chaque seconde les jeux et les charges (à
 * l'heure près des annonces rouges), toutes les {@value #INTERVAL} s le reste ; au changement de jour de jeu (le
 * matin, {@value GameClock#MORNING} h), les départs et tirages du jour.
 */
public final class WorldLifeSystem extends TickingSystem<EntityStore> {

    private static final float FAST = 1f;
    private static final float INTERVAL = 2f;

    private float fast;
    private float slow;
    /** Une résolution de charge attend déjà son tour sur le fil du monde. */
    private final java.util.concurrent.atomic.AtomicBoolean charge = new java.util.concurrent.atomic.AtomicBoolean();

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (world != Universe.get().getDefaultWorld()) {
            return;
        }
        if (Calendar.charging() && charge.compareAndSet(false, true)) {
            // La ruée se résout à l'image près : les dégâts tombent à la fin exacte de la zone rouge.
            world.execute(() -> {
                charge.set(false);
                try {
                    Calendar.stepCharge(world, world.getEntityStore().getStore());
                } catch (RuntimeException e) {
                    PeuplesPlugin.get().getLogger().atWarning().withCause(e).log("Peuples (monde vivant) : erreur de la ruée");
                }
            });
        }
        fast += dt;
        slow += dt;
        if (fast < FAST) {
            return;
        }
        float fastDt = fast;
        fast = 0f;
        boolean full = slow >= INTERVAL;
        float slowDt = slow;
        if (full) {
            slow = 0f;
        }
        world.execute(() -> {
            Store<EntityStore> s = world.getEntityStore().getStore();
            if (Villages.registry(world).all().isEmpty() || world.getPlayerRefs().isEmpty()) {
                return;
            }
            try {
                Hunts.step(world, s);
                List<Vector3d> players = WorldLife.players(world, s);
                Calendar.step(world, s, players, fastDt);
                if (full) {
                    daily(world, s);
                    Travellers.step(world, s, players, slowDt);
                    Travellers.letters(world, s);
                    Surroundings.step(world, s, players);
                    Traces.step(world, s, players);
                    Inns.step(world, s, players);
                    Hamlets.step(world, s, players);
                    HamletTrips.step(world, s, players, slowDt);
                    Garrisons.step(world, s, players);
                    Banners.step(world, s, players);
                    Camps.step(world, s, players);
                    Relations.step(world, s, players);
                    Sites.retry(world);
                }
            } catch (RuntimeException e) {
                PeuplesPlugin.get().getLogger().atWarning().withCause(e).log("Peuples (monde vivant) : erreur du pas");
            }
        });
    }

    /** Une fois par jour de jeu : départs, campements, relations, auberges, vestiges. */
    private static void daily(World world, Store<EntityStore> store) {
        WorldLifeRegistry r = WorldLife.registry(world);
        long day = GameClock.day(store);
        if (r.getLong(WorldLifeRegistry.Part.CALENDAR, "day", Long.MIN_VALUE) == day) {
            return;
        }
        r.put(WorldLifeRegistry.Part.CALENDAR, "day", Long.toString(day));
        Random random = new Random();
        Traces.seed(world);
        Relations.morning(world, store, day, random);
        Travellers.morning(world, store, random);
        Camps.morning(world, store, day, random);
        Inns.morning(world, store, day);
        Hamlets.seed(world);
        HamletTrips.morning(world, store, random);
        Allegiance.morning(world, store, day, random);
    }
}
