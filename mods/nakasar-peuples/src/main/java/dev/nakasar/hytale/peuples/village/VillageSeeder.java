package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.ISpawnProvider;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Pose le premier village kweebec du monde par défaut, près du point d'apparition (GDD : « un village par zone et par
 * peuple », généré par le mod avec les prefabs vanilla — recommandation retenue par Kevin).
 *
 * <p>Une fois le monde chargé, on essaie des sites sur des cercles de {@value #MIN_DISTANCE} à {@value #MAX_DISTANCE}
 * blocs autour du point d'apparition, dans un ordre tiré du seed du monde. Un site convient s'il est couvert d'herbe
 * (zone 1, forêts et plaines), sans eau, et assez plat ({@value #MAX_RELIEF} blocs d'écart au plus sur le campement).
 * Le premier qui convient reçoit le village ; le monde garde la trace ({@link VillageRegistry#isSeeded}). Si aucun ne
 * convient, on réessaie au prochain démarrage avec d'autres sites.
 */
public final class VillageSeeder extends TickingSystem<EntityStore> {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    public static final int MIN_DISTANCE = 280;
    public static final int MAX_DISTANCE = 700;
    /** Écart de hauteur maximal du sol sur l'emprise du campement. */
    public static final int MAX_RELIEF = 9;
    /** Part minimale des points sondés couverts d'herbe, sans eau. */
    private static final double MIN_GRASS = 0.8;
    private static final int RINGS = 5;
    private static final int PER_RING = 8;

    /** Laisse le monde et ses ressources se charger avant le premier essai. */
    private static final float FIRST_DELAY = 15f;
    private static final float INTERVAL = 10f;

    private float wait = FIRST_DELAY;
    /** Monde déjà traité depuis le démarrage (village posé, ou recherche lancée). */
    private volatile World handled;

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (world != Universe.get().getDefaultWorld() || world == handled) {
            return;
        }
        wait -= dt;
        if (wait > 0f) {
            return;
        }
        wait = INTERVAL;
        handled = world;
        world.execute(() -> start(world));
    }

    /** Lance la recherche de site (thread du monde) si le monde n'a pas encore son village automatique. */
    public static void start(World world) {
        VillageRegistry registry = Villages.registry(world);
        if (registry.isSeeded() || registry.all().stream().anyMatch(Village::isAuto)) {
            return;
        }
        VillageLayout layout = VillageLayout.get(People.KWEEBEC.layout());
        if (layout == null) {
            LOGGER.atWarning().log("Nakasar Peuples : plan %s absent, pas de village automatique", People.KWEEBEC.layout());
            return;
        }
        int[] spawn = spawn(world);
        List<int[]> sites = sites(world, spawn, registry.seedAttempts());
        registry.countSeedAttempt();
        LOGGER.atInfo().log("Nakasar Peuples : recherche d'un site de village kweebec autour de %d %d (%d sites, essai %d)",
                spawn[0], spawn[1], sites.size(), registry.seedAttempts());
        tryNext(world, layout, sites, 0);
    }

    /** Point d'apparition du monde (x, z), ou l'origine. */
    @SuppressWarnings("deprecation")
    static int[] spawn(World world) {
        try {
            ISpawnProvider provider = world.getWorldConfig().getSpawnProvider();
            Transform[] points = provider == null ? null : provider.getSpawnPoints();
            if (points != null && points.length > 0 && points[0] != null) {
                return new int[] {(int) Math.floor(points[0].getPosition().x()), (int) Math.floor(points[0].getPosition().z())};
            }
        } catch (RuntimeException e) {
            LOGGER.atWarning().withCause(e).log("Nakasar Peuples : point d'apparition illisible, recherche autour de 0 0");
        }
        return new int[] {0, 0};
    }

    /** Sites candidats : cercles concentriques, angles décalés par le seed du monde et le numéro d'essai. */
    static List<int[]> sites(World world, int[] spawn, int attempt) {
        Random random = new Random(world.getWorldConfig().getSeed() * 31L + attempt * 7919L + 0x5EEDL);
        List<int[]> sites = new ArrayList<>();
        for (int ring = 0; ring < RINGS; ring++) {
            double distance = MIN_DISTANCE + (MAX_DISTANCE - MIN_DISTANCE) * ring / (double) (RINGS - 1);
            double offset = random.nextDouble() * Math.PI * 2;
            for (int i = 0; i < PER_RING; i++) {
                double angle = offset + i * Math.PI * 2 / PER_RING;
                sites.add(new int[] {spawn[0] + (int) Math.round(Math.cos(angle) * distance),
                        spawn[1] + (int) Math.round(Math.sin(angle) * distance)});
            }
        }
        return sites;
    }

    private static void tryNext(World world, VillageLayout layout, List<int[]> sites, int index) {
        if (Villages.registry(world).isSeeded()) {
            return;
        }
        if (index >= sites.size()) {
            LOGGER.atWarning().log("Nakasar Peuples : aucun site de village kweebec ne convient, nouvel essai au prochain démarrage"
                    + " (ou /village generer)");
            return;
        }
        int[] site = sites.get(index);
        if (VillageBuilder.tooClose(world, layout, site[0], site[1]) != null) {
            tryNext(world, layout, sites, index + 1);
            return;
        }
        int r = layout.radiusUpTo(0);
        Terrain.load(world, site[0] - r, site[0] + r, site[1] - r, site[1] + r).whenComplete((ignored, error) -> world.execute(() -> {
            if (error != null || !suitable(world, layout, site[0], site[1])) {
                tryNext(world, layout, sites, index + 1);
                return;
            }
            String name = VillageNames.pick(world, People.KWEEBEC);
            VillageBuilder.generate(world, layout, name, site[0], site[1], true, result -> {
                if (result.village() == null) {
                    tryNext(world, layout, sites, index + 1);
                    return;
                }
                Villages.setSeeded(world, true);
            });
        }));
    }

    /** Vrai si le site (cx, cz) convient au campement du plan : herbe, pas d'eau, relief modéré. */
    static boolean suitable(World world, VillageLayout layout, int cx, int cz) {
        Terrain terrain = new Terrain(world);
        int r = layout.radiusUpTo(0);
        int samples = 0;
        int grass = 0;
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        for (int dx = -r; dx <= r; dx += 6) {
            for (int dz = -r; dz <= r; dz += 6) {
                if (dx * dx + dz * dz > r * r) {
                    continue;
                }
                samples++;
                int x = cx + dx;
                int z = cz + dz;
                int h = terrain.surface(x, z);
                if (h == Terrain.NONE) {
                    continue;
                }
                String block = Blocks.name(world.getChunkStore(), x, h, z);
                if (block != null && block.startsWith("Soil_Grass") && !terrain.hasFluid(x, h + 1, z)) {
                    grass++;
                }
                min = Math.min(min, h);
                max = Math.max(max, h);
            }
        }
        return samples > 0 && grass >= MIN_GRASS * samples && max - min <= MAX_RELIEF;
    }
}
