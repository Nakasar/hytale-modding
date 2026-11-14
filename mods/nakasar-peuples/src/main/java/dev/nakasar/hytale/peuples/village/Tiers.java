package dev.nakasar.hytale.peuples.village;

/**
 * Les quatre paliers d'un village (GDD, section Paliers) : 0 campement, 1 hameau, 2 village, 3 bourg, et l'essor à
 * réunir pour passer au suivant. Les valeurs sont un premier jet, réglées à l'étape 3 quand les demandes rapportent de
 * l'essor.
 */
public final class Tiers {

    public static final int MAX = 3;

    /** Essor à réunir au palier i pour lancer le chantier du palier i + 1 (le bourg n'a plus de seuil). */
    private static final int[] THRESHOLDS = {100, 250, 500, 0};

    private Tiers() {
    }

    public static int clamp(Integer tier) {
        return tier == null ? 0 : Math.max(0, Math.min(MAX, tier));
    }

    /** Seuil d'essor du palier `tier` (0 pour le bourg, dernier palier). */
    public static int threshold(int tier) {
        return THRESHOLDS[clamp(tier)];
    }

    /** Clé de traduction du nom du palier. */
    public static String nameKey(int tier) {
        return "nakasar_peuples.tier." + clamp(tier);
    }
}
