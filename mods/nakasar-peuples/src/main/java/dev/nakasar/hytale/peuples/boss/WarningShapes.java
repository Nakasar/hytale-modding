package dev.nakasar.hytale.peuples.boss;

/**
 * Formes d'annonce dont les particules existent (tools/generate_quests.py, qui écrit ce fichier) : rapports
 * longueur/largeur des lignes en dixièmes ({@code Nakasar_Peuples_Line_<rapport>_<dixièmes>}) et angles des cônes en
 * degrés ({@code Nakasar_Peuples_Sector_<angle>_<dixièmes>}), pour des durées de {@link #MIN_TENTHS} à
 * {@link #MAX_TENTHS} dixièmes de seconde.
 */
final class WarningShapes {

    static final int[] LINE_ASPECTS = {47};
    static final int[] SECTOR_ANGLES = {90};
    static final int MIN_TENTHS = 5;
    static final int MAX_TENTHS = 30;
    /** Échelle de particule d'une ligne par bloc de largeur. */
    static final float LINE_SCALE = 0.34f;

    private WarningShapes() {
    }
}
