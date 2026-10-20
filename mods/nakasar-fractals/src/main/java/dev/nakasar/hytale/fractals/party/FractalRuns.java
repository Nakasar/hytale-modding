package dev.nakasar.hytale.fractals.party;

import com.hypixel.hytale.builtin.instances.InstancesPlugin;
import com.hypixel.hytale.builtin.instances.config.InstanceWorldConfig;
import com.hypixel.hytale.builtin.instances.removal.RemovalCondition;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.observatory.ObservatoryLayout;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.CompletableFuture;

/**
 * Les parties en cours : une instance de fractale par groupe, ouverte depuis l'Observatoire.
 *
 * <p>Le retour se fait par le point de retour de l'instance (l'Observatoire du groupe, sur le parvis) :
 * {@code InstancesPlugin.exitInstance}. Un Observatoire vide est fermé aussitôt par le moteur (condition
 * {@code WorldEmpty} : il a eu des joueurs et n'en a plus) : tant qu'une fractale ouverte depuis lui vit, ses conditions
 * de fermeture sont donc mises de côté ({@link #hold}), puis rendues quand la dernière a fermé ({@link #releaseHolds},
 * appelé par {@code HarmonyCircleSystem}). Les Observatoires sont effacés au redémarrage du serveur (mondes de
 * portail) : rien ne reste ouvert pour toujours.
 *
 * <p>La partie (fractale, niveau, membres) est gardée en mémoire par monde : l'étape 3 y lira le niveau (agonie,
 * instabilités). Elle n'est pas sauvegardée : une instance rechargée après un redémarrage repart au niveau 1.
 */
public final class FractalRuns {

    /** Une partie : la fractale, son niveau et les joueurs partis ensemble. */
    public record Run(String fractal, int level, List<UUID> members) {
    }

    private static final Map<World, Run> RUNS = Collections.synchronizedMap(new WeakHashMap<>());
    /** Observatoires gardés ouverts, par monde (lus et modifiés sur le thread de cet Observatoire). */
    private static final Map<World, Hold> HOLDS = Collections.synchronizedMap(new WeakHashMap<>());

    /** Conditions de fermeture mises de côté et fractales ouvertes depuis cet Observatoire. */
    private static final class Hold {
        RemovalCondition[] saved;
        final List<CompletableFuture<World>> runs = new ArrayList<>();
    }

    private FractalRuns() {
    }

    /** Partie jouée dans ce monde, ou null (pas une fractale, ou partie oubliée au redémarrage). */
    public static Run of(World world) {
        return RUNS.get(world);
    }

    /**
     * Ouvre une instance de {@code fractal} pour le groupe et y envoie ses joueurs. À appeler sur le thread du monde
     * de l'Observatoire ({@code hub}).
     */
    public static void launch(World hub, Store<EntityStore> store, String fractal, int level, List<PlayerRef> players) {
        double[] arrival = ObservatoryLayout.ARRIVAL;
        // Retour sur le parvis, face à l'Astrolabe (vers le nord).
        Transform back = new Transform(new Vector3d(arrival[0], arrival[1], arrival[2]), new Rotation3f());
        List<UUID> members = players.stream().map(PlayerRef::getUuid).toList();
        CompletableFuture<World> instance = InstancesPlugin.get().spawnInstance(FractalCatalog.instance(fractal), hub, back);
        hold(hub, instance);
        instance.whenComplete((world, error) -> {
            if (error != null) {
                FractalsPlugin.get().getLogger().atWarning().withCause(error).log("Fractale %s : instance impossible à ouvrir", fractal);
            } else if (world != null) {
                RUNS.put(world, new Run(fractal, level, members));
            }
        });
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            if (ref != null && ref.isValid()) {
                InstancesPlugin.teleportPlayerToLoadingInstance(ref, store, instance, null);
            }
        }
    }

    /** Garde l'Observatoire ouvert tant que la fractale `run` n'a pas fermé. */
    private static void hold(World hub, CompletableFuture<World> run) {
        InstanceWorldConfig config = InstanceWorldConfig.get(hub.getWorldConfig());
        if (config == null) {
            return;
        }
        Hold hold = HOLDS.computeIfAbsent(hub, w -> new Hold());
        if (hold.saved == null) {
            hold.saved = config.getRemovalConditions();
            config.setRemovalConditions(new RemovalCondition[0]);
            hub.getWorldConfig().markChanged();
        }
        hold.runs.add(run);
    }

    /** Rend ses conditions de fermeture à l'Observatoire quand plus aucune de ses fractales n'est ouverte. */
    public static void releaseHolds(World hub) {
        Hold hold = HOLDS.get(hub);
        if (hold == null) {
            return;
        }
        hold.runs.removeIf(run -> run.isDone() && (run.isCompletedExceptionally() || run.getNow(null) == null
                || !run.getNow(null).isAlive()));
        if (!hold.runs.isEmpty()) {
            return;
        }
        InstanceWorldConfig config = InstanceWorldConfig.get(hub.getWorldConfig());
        if (config != null && hold.saved != null) {
            config.setRemovalConditions(hold.saved);
            hub.getWorldConfig().markChanged();
        }
        HOLDS.remove(hub);
    }

    /** Renvoie le joueur à l'Observatoire de son groupe. Faux s'il n'est pas dans une instance. */
    public static boolean leave(Ref<EntityStore> player, Store<EntityStore> store) {
        try {
            InstancesPlugin.exitInstance(player, store);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    public static void clearAll() {
        RUNS.clear();
        HOLDS.clear();
    }
}
