package dev.nakasar.hytale.fractals.combat;

/**
 * Formes d'annonce dont les particules existent (tools/generate_warnings.py, qui écrit ce fichier) : rapports
 * longueur/largeur des lignes en dixièmes ({@code Nakasar_Fractal_Line_<rapport>_<dixièmes>}) et angles des cônes en
 * degrés ({@code Nakasar_Fractal_Sector_<angle>_<dixièmes>}), pour des durées de {@link #MIN_TENTHS} à
 * {@link #MAX_TENTHS} dixièmes de seconde.
 */
final class WarningShapes {

    static final int[] LINE_ASPECTS = {5, 18, 25, 30, 40, 47, 53, 60, 80};
    static final int[] SECTOR_ANGLES = {70, 90, 100, 120};
    static final int MIN_TENTHS = 5;
    static final int MAX_TENTHS = 30;
    /** Échelle de particule d'une ligne par bloc de largeur (celle d'un secteur est {@link Telegraphs#WARNING_SCALE} par bloc de rayon). */
    static final float LINE_SCALE = 0.34f;

    private WarningShapes() {
    }
}
