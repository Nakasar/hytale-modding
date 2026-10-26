package dev.nakasar.hytale.fractals.support;

import java.util.concurrent.ThreadLocalRandom;

/**
 * Échos des fractales : ingrédients des runes et armes de soutien, un par fractale
 * ({@code Nakasar_Fractal_Echo_<Fractale>}), donnés par le coffre de fin avec le sac du rang. Le noyau stable des runes
 * de rang Maître ne tombe qu'au rang Maître, une fois sur {@value #CORE_ONE_IN}.
 */
public final class Echoes {

    public static final String PREFIX = "Nakasar_Fractal_Echo_";
    public static final String STABLE_CORE = "Nakasar_Fractal_Stable_Core";
    /** Échos en plus la première fois du jour sur une fractale du jour. */
    public static final int DAILY_BONUS = 2;
    static final int CORE_ONE_IN = 3;

    private Echoes() {
    }

    public static String echo(String fractal) {
        return PREFIX + fractal;
    }

    /** Échos du coffre de fin pour un rang : Initié 1, Adepte 1-2, Expert 2, Maître 3. */
    public static int count(String rank) {
        return switch (rank) {
            case "Adept" -> 1 + ThreadLocalRandom.current().nextInt(2);
            case "Expert" -> 2;
            case "Master" -> 3;
            default -> 1;
        };
    }

    public static boolean stableCore(String rank) {
        return "Master".equals(rank) && ThreadLocalRandom.current().nextInt(CORE_ONE_IN) == 0;
    }
}
