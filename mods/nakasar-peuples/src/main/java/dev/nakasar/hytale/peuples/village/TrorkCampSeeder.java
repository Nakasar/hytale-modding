package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Étape 7 : pose le camp trork de la zone 1 (plan {@code Trork_Camp}, prefabs vanilla Npc/Trork) à
 * {@value #MIN_DISTANCE} à {@value #MAX_DISTANCE} blocs du premier village kweebec, une fois celui-ci posé
 * ({@link VillageSeeder}). GDD, Progression des zones : la zone 1 offre deux routes, les Kweebecs ou le camp trork, et
 * les deux lieux se voient sur la carte. Mêmes règles de site que le village kweebec, herbe moins exigée (les camps
 * vanilla sont posés en lisière). Le monde garde la trace ({@link VillageRegistry#isSeeded(People)}).
 */
public final class TrorkCampSeeder extends TickingSystem<EntityStore> {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    public static final int MIN_DISTANCE = 220;
    public static final int MAX_DISTANCE = 450;
    private static final double MIN_GRASS = 0.6;
    private static final int RINGS = 4;
    private static final int PER_RING = 10;

    /** Laisse passer le semeur kweebec (15 s) et sa recherche avant le premier essai. */
    private static final float FIRST_DELAY = 40f;
    private static final float INTERVAL = 30f;

    private float wait = FIRST_DELAY;
    private volatile boolean searching;
    private volatile World handled;

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (world != Universe.get().getDefaultWorld() || world == handled || searching) {
            return;
        }
        wait -= dt;
        if (wait > 0f) {
            return;
        }
        wait = INTERVAL;
        world.execute(() -> start(world));
    }

    private void start(World world) {
        VillageRegistry registry = Villages.registry(world);
        if (registry.isSeeded(People.TRORK) || registry.all().stream().anyMatch(v -> v.isAuto() && v.people() == People.TRORK)) {
            handled = world;
            return;
        }
        Village kweebec = registry.all().stream().filter(v -> v.isAuto() && v.people() == People.KWEEBEC).findFirst().orElse(null);
        if (kweebec == null) {
            return; // le village kweebec n'est pas encore posé : on réessaie plus tard
        }
        VillageLayout layout = VillageLayout.get(People.TRORK.layout());
        handled = world;
        if (layout == null) {
            LOGGER.atWarning().log("Nakasar Peuples : plan %s absent, pas de camp trork automatique", People.TRORK.layout());
            return;
        }
        List<int[]> sites = sites(world, kweebec.x(), kweebec.z());
        LOGGER.atInfo().log("Nakasar Peuples : recherche d'un site de camp trork autour de %s (%d sites)", kweebec.name(), sites.size());
        searching = true;
        tryNext(world, layout, sites, 0);
    }

    /** Sites candidats : cercles autour du village kweebec, angles tirés du seed du monde. */
    static List<int[]> sites(World world, int x, int z) {
        Random random = new Random(world.getWorldConfig().getSeed() * 37L + 0x7120CL);
        List<int[]> sites = new ArrayList<>();
        for (int ring = 0; ring < RINGS; ring++) {
            double distance = MIN_DISTANCE + (MAX_DISTANCE - MIN_DISTANCE) * ring / (double) (RINGS - 1);
            double offset = random.nextDouble() * Math.PI * 2;
            for (int i = 0; i < PER_RING; i++) {
                double angle = offset + i * Math.PI * 2 / PER_RING;
                sites.add(new int[] {x + (int) Math.round(Math.cos(angle) * distance), z + (int) Math.round(Math.sin(angle) * distance)});
            }
        }
        return sites;
    }

    private void tryNext(World world, VillageLayout layout, List<int[]> sites, int index) {
        if (Villages.registry(world).isSeeded(People.TRORK)) {
            searching = false;
            return;
        }
        if (index >= sites.size()) {
            searching = false;
            LOGGER.atWarning().log("Nakasar Peuples : aucun site de camp trork ne convient (ou /village generer trork)");
            return;
        }
        int[] site = sites.get(index);
        if (VillageBuilder.tooClose(world, layout, site[0], site[1]) != null) {
            tryNext(world, layout, sites, index + 1);
            return;
        }
        int r = layout.radiusUpTo(0);
        Terrain.load(world, site[0] - r, site[0] + r, site[1] - r, site[1] + r).whenComplete((ignored, error) -> world.execute(() -> {
            if (error != null || !VillageSeeder.suitable(world, layout, site[0], site[1], MIN_GRASS)) {
                tryNext(world, layout, sites, index + 1);
                return;
            }
            String name = VillageNames.pick(world, People.TRORK);
            VillageBuilder.generate(world, layout, name, site[0], site[1], true, result -> {
                if (result.village() == null) {
                    tryNext(world, layout, sites, index + 1);
                    return;
                }
                Villages.registry(world).setSeeded(People.TRORK, true);
                searching = false;
                LOGGER.atInfo().log("Nakasar Peuples : camp trork %s posé en %d %d", name, site[0], site[1]);
            });
        }));
    }
}
