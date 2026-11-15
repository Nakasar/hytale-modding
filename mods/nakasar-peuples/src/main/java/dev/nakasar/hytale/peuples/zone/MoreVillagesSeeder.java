package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageNames;
import dev.nakasar.hytale.peuples.village.VillageRegistry;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.function.Consumer;

/**
 * Pose les villages suivants de chaque peuple dans le monde par défaut, une fois son premier lieu posé
 * ({@code VillageSeeder}, {@code TrorkCampSeeder}, {@link ZoneSeeder}), jusqu'à {@link People#naturalVillages()} en tout.
 *
 * <p>Espacement, choisi pour que chaque village garde son territoire :
 * <ul>
 *   <li>{@value #SAME_MIN} à {@value #SAME_MAX} blocs du village du même peuple le plus proche. Au-delà de 600 blocs,
 *   les terrains de chasse des demandes (220 blocs autour du cœur), la veille des raids et la vie du village
 *   (160 blocs) ne se chevauchent jamais, et la bannière (révélée à 300 blocs) ne se voit pas depuis l'autre village :
 *   on change vraiment de lieu, à deux ou trois minutes de marche. Au plus 1200 blocs, pour que les villages d'un
 *   peuple forment une région et restent à portée des caravanes (2400 blocs au plus) ;</li>
 *   <li>au moins {@value #OTHER_MIN} blocs de tout village d'un autre peuple (hors de sa bannière et de ses
 *   chasses) ;</li>
 *   <li>dans la terre ferme de la zone du peuple (centre et quatre bords du plan entier, pas le rivage ni l'océan), sur
 *   son sol (herbe pour les Kweebecs et les Trorks, sable, neige, cendre), sans eau, relief modéré, comme le premier.</li>
 * </ul>
 * Un village à la fois, puis le suivant : chaque essai charge et nivelle une région (nettoyage {@code Grading}). Une
 * recherche sans site compte un échec ; après {@value #MAX_FAILURES} échecs le peuple n'est plus cherché (la commande
 * {@code /village generer} reste possible).
 */
public final class MoreVillagesSeeder extends TickingSystem<EntityStore> {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    public static final int SAME_MIN = 600;
    public static final int SAME_MAX = 1200;
    public static final int OTHER_MIN = 300;
    public static final int MAX_FAILURES = 3;
    private static final int RINGS = 4;
    private static final int PER_RING = 12;
    /** Sites dont on charge le terrain au plus, par recherche. */
    private static final int MAX_SITES = 30;

    /** Après les premiers lieux (15 à 45 s, puis leur recherche), pour ne pas charger deux régions à la fois. */
    private static final float FIRST_DELAY = 150f;
    private static final float INTERVAL = 30f;

    public static final People[] ORDER = {People.KWEEBEC, People.TRORK, People.FERAN, People.RENONCE, People.SLOTHIAN};

    private float wait = FIRST_DELAY;
    private volatile boolean busy;
    private volatile World world;
    /** Peuples déjà cherchés sans succès depuis le démarrage. */
    private final Set<People> tried = EnumSet.noneOf(People.class);

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World w = store.getExternalData().getWorld();
        if (w != Universe.get().getDefaultWorld() || busy) {
            return;
        }
        wait -= dt;
        if (wait > 0f) {
            return;
        }
        wait = INTERVAL;
        if (world != w) {
            world = w;
            tried.clear();
        }
        busy = true;
        w.execute(() -> next(w));
    }

    private void next(World world) {
        VillageRegistry registry = Villages.registry(world);
        for (People people : ORDER) {
            if (tried.contains(people) || !wanted(registry, people)) {
                continue;
            }
            seedOne(world, people, village -> {
                if (village == null) {
                    tried.add(people);
                    Villages.registry(world).countMoreFailure(people);
                } else {
                    Villages.registry(world).countMoreSeeded(people);
                    Villages.registry(world).resetMoreFailures(people);
                    LOGGER.atInfo().log("Nakasar Peuples : village %s %s posé en %d %d (%d sur %d)", people.id(), village.name(),
                            village.x(), village.z(), 1 + Villages.registry(world).moreSeeded(people), people.naturalVillages());
                }
                busy = false;
            });
            return;
        }
        busy = false;
    }

    /** Vrai si le peuple a son premier lieu automatique et attend encore des villages suivants. */
    private static boolean wanted(VillageRegistry registry, People people) {
        return registry.isSeeded(people) && registry.moreFailures(people) < MAX_FAILURES
                && 1 + registry.moreSeeded(people) < people.naturalVillages();
    }

    /** Cherche un site et y pose un village suivant du peuple (thread du monde) ; `done` reçoit le village, ou null. */
    public static void seedOne(World world, People people, Consumer<Village> done) {
        VillageLayout layout = VillageLayout.get(people.layout());
        boolean zones = Zones.generator(world) != null;
        if (layout == null || !zones && people.zone() > 1) {
            done.accept(null);
            return;
        }
        List<int[]> sites = sites(world, layout, people, zones);
        LOGGER.atInfo().log("Nakasar Peuples : recherche d'un village %s suivant (%d sites candidats)", people.id(), sites.size());
        tryNext(world, layout, people, sites, 0, done);
    }

    /**
     * Sites candidats : cercles de {@value #SAME_MIN} à {@value #SAME_MAX} blocs autour de chaque village du peuple,
     * les plus proches d'abord, qui respectent les écarts et tiennent dans la zone du peuple.
     */
    static List<int[]> sites(World world, VillageLayout layout, People people, boolean zones) {
        List<Village> all = Villages.registry(world).all();
        List<Village> own = all.stream().filter(v -> v.people() == people).toList();
        Random random = new Random(world.getWorldConfig().getSeed() * 41L + people.ordinal() * 7727L + all.size() * 131L);
        int r = layout.radius();
        List<int[]> out = new ArrayList<>();
        for (int ring = 0; ring < RINGS && out.size() < MAX_SITES; ring++) {
            double distance = SAME_MIN + 40 + (SAME_MAX - SAME_MIN - 80) * ring / (double) (RINGS - 1);
            for (Village from : own) {
                double offset = random.nextDouble() * Math.PI * 2;
                for (int i = 0; i < PER_RING && out.size() < MAX_SITES; i++) {
                    double angle = offset + i * Math.PI * 2 / PER_RING;
                    int x = from.x() + (int) Math.round(Math.cos(angle) * distance);
                    int z = from.z() + (int) Math.round(Math.sin(angle) * distance);
                    if (spaced(all, people, x, z) && (!zones || ZoneSeeder.inZone(world, people.zone(), x, z, r))) {
                        out.add(new int[] {x, z});
                    }
                }
            }
        }
        return out;
    }

    /** Vrai si (x, z) est à bonne distance des autres villages (même peuple et autres peuples). */
    static boolean spaced(List<Village> all, People people, int x, int z) {
        for (Village v : all) {
            double min = v.people() == people ? SAME_MIN : OTHER_MIN;
            if (v.horizontalDistanceSquared(x, z) < min * min) {
                return false;
            }
        }
        return true;
    }

    private static void tryNext(World world, VillageLayout layout, People people, List<int[]> sites, int index, Consumer<Village> done) {
        if (index >= sites.size()) {
            LOGGER.atWarning().log("Nakasar Peuples : aucun site pour un village %s suivant (nouvel essai au prochain démarrage)",
                    people.id());
            done.accept(null);
            return;
        }
        int[] site = sites.get(index);
        // Un village a pu être posé entretemps (commande) : on revérifie les écarts.
        if (!spaced(Villages.registry(world).all(), people, site[0], site[1])
                || VillageBuilder.tooClose(world, layout, site[0], site[1]) != null) {
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
                done.accept(result.village());
            });
        }));
    }

    /** Mêmes exigences de site que le premier lieu du peuple (herbe à 80 % et 9 de relief pour les Kweebecs). */
    private static boolean suitable(World world, VillageLayout layout, People people, int cx, int cz) {
        return switch (people) {
            case KWEEBEC -> ZoneSeeder.suitable(world, layout, people, cx, cz, 0.8, 9);
            case TRORK -> ZoneSeeder.suitable(world, layout, people, cx, cz, 0.6, 9);
            default -> ZoneSeeder.suitable(world, layout, people, cx, cz);
        };
    }
}
