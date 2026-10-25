package dev.nakasar.hytale.fractals.observatory;

/**
 * Positions de l'île de l'Observatoire, écrites par tools/generate_observatory.py (ne pas modifier à la main : relancer
 * le générateur). Repère du monde : x vers l'est, z vers le sud ; le centre de l'Astrolabe est en (0, 100, 0).
 */
public final class ObservatoryLayout {

    /** Première couche d'air au-dessus du dallage de l'île. */
    public static final int GROUND_Y = 100;
    public static final int ISLAND_RADIUS = 22;
    /** Cercle d'harmonisation : distance horizontale au centre de l'Astrolabe (blocs), bords compris. */
    public static final double CIRCLE_INNER = 4.5;
    public static final double CIRCLE_OUTER = 8.5;
    /** Point d'arrivée (pieds) sur le parvis. */
    public static final double[] ARRIVAL = {0.5, 100.0, 23.5};
    /** Golem d'essai (pieds). */
    public static final double[] GOLEM = {-44.5, 100.0, 8.5};
    /** Bloc de la cage d'essai (Nakasar_Fractal_Cage_Cell, au niveau des pieds). */
    public static final int[] TRIAL_CAGE = {-50, 100, 14};
    /** Où revient le joueur à l'ouverture de la cage d'essai (pieds), près du pupitre. */
    public static final double[] TRIAL_RELEASE = {-37.5, 100.0, 8.5};
    /** L'Archiviste (pieds), derrière son comptoir, tourné vers l'ouest. */
    public static final double[] ARCHIVIST = {49.5, 100.0, 1.5};
    /** Préfixes des objets de sélection : noyau d'une fractale ({@code <préfixe><Id>}) et diapason d'un niveau. */
    public static final String CORE_PREFIX = "Nakasar_Fractal_Core_";
    public static final String LEVEL_PREFIX = "Nakasar_Fractal_Level_";

    private ObservatoryLayout() {
    }
}
