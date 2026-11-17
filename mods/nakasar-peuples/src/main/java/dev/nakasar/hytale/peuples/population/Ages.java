package dev.nakasar.hytale.peuples.population;

/**
 * Le rythme d'une vie (proposition validée par Kevin le 16 novembre 2026) : une « année du village » = {@value #YEAR}
 * jours de jeu ; enfant 0 à 14 jours, apprenti 14 à 28, adulte 28 à 112, ancien ensuite ; mort de vieillesse possible à
 * partir du jour {@value #DEATH_FROM} (une chance sur {@value #DEATH_CHANCE} chaque matin), sûre au jour
 * {@value #DEATH_SURE}. Tout se règle ici.
 */
public final class Ages {

    public static final int YEAR = 28;
    public static final int APPRENTICE = 14;
    public static final int ADULT = 28;
    public static final int ELDER = 112;
    public static final int DEATH_FROM = 140;
    public static final int DEATH_SURE = 168;
    public static final int DEATH_CHANCE = 14;

    public enum Stage {
        CHILD, APPRENTICE, ADULT, ELDER;

        public String key() {
            return name().toLowerCase(java.util.Locale.ROOT);
        }
    }

    private Ages() {
    }

    public static Stage stage(long age) {
        if (age < APPRENTICE) {
            return Stage.CHILD;
        }
        if (age < ADULT) {
            return Stage.APPRENTICE;
        }
        return age < ELDER ? Stage.ADULT : Stage.ELDER;
    }

    /** Âge en années du village (arrondi bas), pour l'affichage. */
    public static long years(long age) {
        return age / YEAR;
    }
}
