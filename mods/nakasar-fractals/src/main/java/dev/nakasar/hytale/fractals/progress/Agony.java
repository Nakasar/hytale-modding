package dev.nakasar.hytale.fractals.progress;

import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import dev.nakasar.hytale.fractals.party.FractalRuns;

/**
 * Barème de l'agonie (GDD, étape 3). L'effet {@value #EFFECT}, posé par certaines attaques des fractales, retire
 * chaque seconde une part des PV maximum ({@link AgonySystem}) ; la résistance du joueur (ses infusions) la réduit
 * jusqu'à l'annuler à la résistance conseillée du niveau.
 *
 * <ul>
 *   <li>Initié (1-25) : pas d'agonie ;</li>
 *   <li>Adepte (26-50) : 4 % par seconde, résistance conseillée de 10 à 40 ;</li>
 *   <li>Expert (51-75) : 6 % par seconde, de 50 à 100 ;</li>
 *   <li>Maître (76-100) : 8 % par seconde, de 110 à 150.</li>
 * </ul>
 */
public final class Agony {

    public static final String EFFECT = "Nakasar_Fractal_Agony";
    public static final String DAMAGE_CAUSE = "Nakasar_Fractal_Agony";
    /** Premier niveau avec de l'agonie. */
    public static final int FIRST_LEVEL = Observatory.RANK_SIZE + 1;

    /** Par rang à partir d'Adepte : résistance conseillée au premier et au dernier niveau, part des PV par seconde. */
    private static final int[][] RECOMMENDED = {{10, 40}, {50, 100}, {110, 150}};
    private static final float[] PERCENT = {0.04f, 0.06f, 0.08f};

    private Agony() {
    }

    /** Rang à partir d'Adepte (0, 1, 2), ou -1 sans agonie. */
    private static int rank(int level) {
        if (level < FIRST_LEVEL) {
            return -1;
        }
        return Math.min(RECOMMENDED.length - 1, (Math.min(level, Observatory.MAX_LEVEL) - 1) / Observatory.RANK_SIZE - 1);
    }

    /** Résistance conseillée au niveau (0 sans agonie). */
    public static int recommended(int level) {
        int rank = rank(level);
        if (rank < 0) {
            return 0;
        }
        int first = (rank + 1) * Observatory.RANK_SIZE + 1;
        int[] range = RECOMMENDED[rank];
        double t = (Math.min(level, Observatory.MAX_LEVEL) - first) / (double) (Observatory.RANK_SIZE - 1);
        return (int) Math.round(range[0] + (range[1] - range[0]) * t);
    }

    /** Part des PV maximum retirée par seconde, sans résistance (0 sans agonie). */
    public static float percentPerSecond(int level) {
        int rank = rank(level);
        return rank < 0 ? 0f : PERCENT[rank];
    }

    /** Part des dégâts qui passe la résistance : 1 sans résistance, 0 à la résistance conseillée et au-delà. */
    public static float factor(int level, int resistance) {
        int recommended = recommended(level);
        return recommended <= 0 ? 0f : Math.max(0f, 1f - resistance / (float) recommended);
    }

    /** Niveau qui règle l'agonie dans ce monde : celui de la partie, ou celui de l'Astrolabe dans l'Observatoire. */
    public static int levelOf(World world) {
        FractalRuns.Run run = FractalRuns.of(world);
        if (run != null) {
            return run.level();
        }
        return FractalCatalog.isObservatory(world) ? Observatory.state(world).level() : Observatory.MIN_LEVEL;
    }
}
