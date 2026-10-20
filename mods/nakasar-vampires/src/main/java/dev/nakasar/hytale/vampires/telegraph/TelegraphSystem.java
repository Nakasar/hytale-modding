package dev.nakasar.hytale.vampires.telegraph;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.arena.Restores;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Fait avancer, à chaque tick du monde, les annonces et les actions en cours des élites ({@link TelegraphInteraction},
 * {@link ChargeInteraction}) et des décors ({@code arena}) : dessin des zones au fil de la charge, coup à la fin,
 * charge de l'Abomination, feux ; et la remise en place des blocs du décor ({@link Restores}).
 *
 * <p>Les tâches sont ajoutées et lues sur le thread du monde ({@link #start}).
 */
public final class TelegraphSystem extends TickingSystem<EntityStore> {

    /** Tâche d'un monde ; {@link #step} rend vrai quand elle est finie. */
    public interface Task {
        boolean step(World world, Store<EntityStore> store, long now);

        /** Appelé si {@link #step} lève une exception, avant que la tâche ne soit retirée : défaire ce qu'elle a posé. */
        default void abort(World world, Store<EntityStore> store) {
        }
    }

    /** Tâches en cours par monde (lues et modifiées sur le thread de ce monde). */
    private static final Map<World, List<Task>> TASKS = Collections.synchronizedMap(new WeakHashMap<>());

    /** Lance une tâche dans le monde, juste après le traitement en cours du store. */
    public static void start(World world, Task task) {
        world.execute(() -> TASKS.computeIfAbsent(world, w -> new ArrayList<>()).add(task));
    }

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Restores.tick(world);
        List<Task> tasks = TASKS.get(world);
        if (tasks == null || tasks.isEmpty()) {
            return;
        }
        // Le store est en plein traitement : on agit juste après.
        world.execute(() -> step(world));
    }

    private static void step(World world) {
        List<Task> tasks = TASKS.get(world);
        if (tasks == null || tasks.isEmpty()) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        long now = System.nanoTime();
        // Copie : une tâche peut en lancer une autre (feu d'une lanterne renversée).
        for (Task task : List.copyOf(tasks)) {
            boolean done;
            try {
                done = task.step(world, store, now);
            } catch (RuntimeException e) {
                VampiresPlugin.get().getLogger().atWarning().withCause(e).log("Annonce d'élite interrompue");
                try {
                    task.abort(world, store);
                } catch (RuntimeException ignored) {
                    // déjà signalé
                }
                done = true;
            }
            if (done) {
                tasks.remove(task);
            }
        }
    }

    /** Oublie les tâches (arrêt du plugin). */
    public static void clearAll() {
        TASKS.clear();
    }
}
