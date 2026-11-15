package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.builtin.locate.SpiralSearchUtil;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.worldgen.chunk.ChunkGenerator;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageNames;
import dev.nakasar.hytale.peuples.village.VillageSeederAccess;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3i;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * Pose l'oasis feran (zone 2) et le hameau des Renoncés (zone 3) dans le monde par défaut (étape 8, GDD : « un village
 * par zone et par peuple », généré avec les prefabs vanilla). Même principe que le premier village kweebec
 * ({@code VillageSeeder}) :
 * <ol>
 *   <li>hors du thread du monde, recherche en spirale du premier point de {@code Zone<n>_Tier1} autour du point
 *   d'apparition (comme la commande vanilla {@code /locate zone}, {@value #SEARCH_RADIUS} blocs au plus) ;</li>
 *   <li>sites candidats au-delà de ce point, vers l'intérieur de la zone ({@value #MIN_DEPTH} à {@value #MAX_DEPTH}
 *   blocs), dont le centre et les quatre bords du campement sont dans la zone, hors rivage ;</li>
 *   <li>un site convient s'il est couvert du sol du peuple (sable, neige), sans eau, et assez plat.</li>
 * </ol>
 * Le premier qui convient reçoit le village ; le monde en garde la trace ({@code VillageRegistry.isSeeded(People)}).
 */
public final class ZoneSeeder extends TickingSystem<EntityStore> {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    public static final int SEARCH_RADIUS = 6000;
    public static final int MIN_DEPTH = 100;
    public static final int MAX_DEPTH = 500;
    public static final int MAX_RELIEF = 10;
    private static final double MIN_GROUND = 0.6;
    private static final int RINGS = 5;
    private static final int PER_RING = 9;
    /** Après le village kweebec (15 s), pour ne pas charger deux régions à la fois. */
    private static final float FIRST_DELAY = 45f;
    /** Étape 9 : la zone 4 est plus loin du point d'apparition, on y cherche plus large. */
    public static final int FAR_SEARCH_RADIUS = 12000;
    public static final People[] PEOPLES = {People.FERAN, People.RENONCE, People.SLOTHIAN};

    private float wait = FIRST_DELAY;
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
        handled = world;
        world.execute(() -> startAll(world, 0));
    }

    private static void startAll(World world, int index) {
        if (index >= PEOPLES.length) {
            return;
        }
        start(world, PEOPLES[index], false, result -> startAll(world, index + 1));
    }

    /**
     * Cherche un site et y pose le village du peuple (thread du monde). `force` : même si le monde en a déjà un
     * (commande d'essai). `done` reçoit le village posé, ou null.
     */
    public static void start(World world, People people, boolean force, Consumer<Village> done) {
        var registry = Villages.registry(world);
        if (!force && (registry.isSeeded(people) || registry.all().stream().anyMatch(v -> v.people() == people && v.isAuto()))) {
            done.accept(null);
            return;
        }
        VillageLayout layout = VillageLayout.get(people.layout());
        ChunkGenerator generator = Zones.generator(world);
        if (layout == null || generator == null) {
            LOGGER.atWarning().log("Nakasar Peuples : pas de village %s automatique (plan %s %s, générateur %s)", people.id(),
                    people.layout(), layout == null ? "absent" : "présent", generator == null ? "absent" : "vanilla");
            done.accept(null);
            return;
        }
        int[] spawn = VillageSeederAccess.spawn(world);
        int seed = Zones.seed(world);
        int zone = people.zone();
        int radius = zone >= 4 ? FAR_SEARCH_RADIUS : SEARCH_RADIUS;
        CompletableFuture.supplyAsync(() -> SpiralSearchUtil.search(generator, seed, spawn[0], spawn[1], radius,
                r -> r != null && r.getZoneResult() != null && r.getZoneResult().getZone() != null
                        && Zones.inland(r.getZoneResult().getZone().name(), zone)))
                .whenComplete((found, error) -> world.execute(() -> {
                    if (error != null || found == null) {
                        LOGGER.atWarning().log("Nakasar Peuples : zone %d introuvable à moins de %d blocs du point d'apparition (%s)",
                                zone, radius, error == null ? "aucun résultat" : error.getMessage());
                        done.accept(null);
                        return;
                    }
                    List<int[]> sites = sites(world, layout, people, spawn, found);
                    LOGGER.atInfo().log("Nakasar Peuples : zone %d trouvée en %d %d, %d sites candidats pour le village %s",
                            zone, found.x(), found.z(), sites.size(), people.id());
                    tryNext(world, layout, people, sites, 0, done);
                }));
    }

    /** Sites au-delà du premier point de la zone, vers l'intérieur, dont le campement tient dans la terre de la zone. */
    private static List<int[]> sites(World world, VillageLayout layout, People people, int[] spawn, Vector3i found) {
        double heading = Math.atan2(found.z() - spawn[1], found.x() - spawn[0]);
        Random random = new Random(world.getWorldConfig().getSeed() * 37L + people.ordinal() * 104729L + System.nanoTime() % 997);
        int r = layout.radiusUpTo(0);
        List<int[]> out = new ArrayList<>();
        for (int ring = 0; ring < RINGS; ring++) {
            double depth = MIN_DEPTH + (MAX_DEPTH - MIN_DEPTH) * ring / (double) (RINGS - 1);
            double offset = random.nextDouble() * 0.2;
            for (int i = 0; i < PER_RING; i++) {
                double angle = heading + offset + (i - PER_RING / 2) * (Math.PI / 2.2 / PER_RING) * 2;
                int x = found.x() + (int) Math.round(Math.cos(angle) * depth);
                int z = found.z() + (int) Math.round(Math.sin(angle) * depth);
                if (inZone(world, people.zone(), x, z, r)) {
                    out.add(new int[] {x, z});
                }
            }
        }
        return out;
    }

    static boolean inZone(World world, int zone, int x, int z, int r) {
        int[][] points = {{0, 0}, {r, 0}, {-r, 0}, {0, r}, {0, -r}};
        for (int[] p : points) {
            if (!Zones.inland(Zones.name(world, x + p[0], z + p[1]), zone)) {
                return false;
            }
        }
        return true;
    }

    private static void tryNext(World world, VillageLayout layout, People people, List<int[]> sites, int index, Consumer<Village> done) {
        if (index >= sites.size()) {
            LOGGER.atWarning().log("Nakasar Peuples : aucun site de village %s ne convient, nouvel essai au prochain démarrage"
                    + " (ou /village semer %s)", people.id(), people.id().toLowerCase());
            done.accept(null);
            return;
        }
        int[] site = sites.get(index);
        if (VillageBuilder.tooClose(world, layout, site[0], site[1]) != null) {
            tryNext(world, layout, people, sites, index + 1, done);
            return;
        }
        int r = layout.radiusUpTo(0);
        Terrain.load(world, site[0] - r, site[0] + r, site[1] - r, site[1] + r).whenComplete((ignored, error) -> world.execute(() -> {
            if (error != null || !suitable(world, layout, people, site[0], site[1])) {
                tryNext(world, layout, people, sites, index + 1, done);
                return;
            }
            String name = VillageNames.pick(world, people);
            VillageBuilder.generate(world, layout, name, site[0], site[1], true, result -> {
                if (result.village() == null) {
                    tryNext(world, layout, people, sites, index + 1, done);
                    return;
                }
                Villages.registry(world).setSeeded(people, true);
                done.accept(result.village());
            });
        }));
    }

    /** Vrai si le site convient au campement : sol du peuple, pas d'eau, relief modéré. */
    static boolean suitable(World world, VillageLayout layout, People people, int cx, int cz) {
        return suitable(world, layout, people, cx, cz, MIN_GROUND, MAX_RELIEF);
    }

    /** Comme ci-dessus, avec la part de sol du peuple `minGround` et le relief `maxRelief` voulus (villages suivants). */
    static boolean suitable(World world, VillageLayout layout, People people, int cx, int cz, double minGround, int maxRelief) {
        Terrain terrain = new Terrain(world);
        int r = layout.radiusUpTo(0);
        int samples = 0;
        int ground = 0;
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
                if (people.suitsSite(Blocks.name(world.getChunkStore(), x, h, z)) && !terrain.hasFluid(x, h + 1, z)) {
                    ground++;
                }
                min = Math.min(min, h);
                max = Math.max(max, h);
            }
        }
        return samples > 0 && ground >= minGround * samples && max - min <= maxRelief;
    }
}
