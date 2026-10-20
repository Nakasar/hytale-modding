package dev.nakasar.hytale.fractals.uncategorized;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions de l'Inclassable, écrites par tools/generate_uncategorized.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {x, y, z} : pieds ; blocs {x, y, z} : coins.
 */
public final class UncategorizedLayout {

    public static final double[] SPAWN = {0.5, 100.0, 44.5};
    /** Harpies des premières et des secondes plates-formes. */
    public static final double[][] HARPIES = {{-1.0, 107.0, 23.0}, {14.0, 110.0, 16.0}, {-5.0, 113.0, 13.0}, {3.0, 116.0, 3.0}, {2.0, 119.0, -4.0}, {0.0, 122.0, -10.0}};
    public static final double[][] HARPIES_2 = {{8.0, 150.0, -151.0}, {3.0, 155.0, -164.0}, {1.0, 160.0, -176.0}, {8.0, 165.0, -189.0}};
    public static final List<Box> JUMP_ZONES = List.of(
            new Box(-12, 16, 84, 126, -22, 47),
            new Box(-12, 12, 130, 170, -197, -139));

    /** Cour de la prison. */
    public static final Box YARD = new Box(-12, 12, 119, 124, -40, -21);
    public static final double[] YARD_CHECKPOINT = {0.5, 120.0, -23.5};
    public static final double[] GENERATOR = {0.5, 120.0, -30.5};
    /** Prisonniers (pieds, dans leur cellule) et portes de barreaux, dans l'ordre de libération. */
    public static final double[][] PRISONERS = {
            {-15.5, 120.0, -25.5},
            {15.5, 120.0, -25.5},
            {-15.5, 120.0, -34.5},
            {15.5, 120.0, -34.5}};
    public static final int[][][] CELL_DOORS = {
            {{-13, 120, -27}, {-13, 120, -26}, {-13, 120, -25}, {-13, 121, -27}, {-13, 121, -26}, {-13, 121, -25}, {-13, 122, -27}, {-13, 122, -26}, {-13, 122, -25}, {-13, 123, -27}, {-13, 123, -26}, {-13, 123, -25}},
            {{13, 120, -27}, {13, 120, -26}, {13, 120, -25}, {13, 121, -27}, {13, 121, -26}, {13, 121, -25}, {13, 122, -27}, {13, 122, -26}, {13, 122, -25}, {13, 123, -27}, {13, 123, -26}, {13, 123, -25}},
            {{-13, 120, -36}, {-13, 120, -35}, {-13, 120, -34}, {-13, 121, -36}, {-13, 121, -35}, {-13, 121, -34}, {-13, 122, -36}, {-13, 122, -35}, {-13, 122, -34}, {-13, 123, -36}, {-13, 123, -35}, {-13, 123, -34}},
            {{13, 120, -36}, {13, 120, -35}, {13, 120, -34}, {13, 121, -36}, {13, 121, -35}, {13, 121, -34}, {13, 122, -36}, {13, 122, -35}, {13, 122, -34}, {13, 123, -36}, {13, 123, -35}, {13, 123, -34}}};
    public static final int[][] GATE_YARD = {{-3, 120, -41}, {-3, 121, -41}, {-3, 122, -41}, {-3, 123, -41}, {-3, 124, -41}, {-2, 120, -41}, {-2, 121, -41}, {-2, 122, -41}, {-2, 123, -41}, {-2, 124, -41}, {-1, 120, -41}, {-1, 121, -41}, {-1, 122, -41}, {-1, 123, -41}, {-1, 124, -41}, {0, 120, -41}, {0, 121, -41}, {0, 122, -41}, {0, 123, -41}, {0, 124, -41}, {1, 120, -41}, {1, 121, -41}, {1, 122, -41}, {1, 123, -41}, {1, 124, -41}, {2, 120, -41}, {2, 121, -41}, {2, 122, -41}, {2, 123, -41}, {2, 124, -41}, {3, 120, -41}, {3, 121, -41}, {3, 122, -41}, {3, 123, -41}, {3, 124, -41}};

    /** Escalier mortel : bas (z) et haut, x des voies des tourelles, hauteur debout d'une case. */
    public static final int STAIRS_BOTTOM_Z = -42;
    public static final int STAIRS_TOP_Z = -89;
    public static final int STAIRS_X0 = -3;
    public static final int STAIRS_X1 = 3;
    public static final int[] TURRETS_X = {-3, -1, 1, 3};
    public static final double TURRET_Y = 144.0;
    public static final double TURRET_Z = -90.5;
    public static final Box STAIRS = new Box(-4, 4, 119, 148, -89, -41);
    public static final Box LANDING_TOP = new Box(-7, 7, 143, 148, -100, -90);
    public static final int[][] CONSOLES = {{-5, 144, -99}, {0, 144, -99}, {5, 144, -99}};
    public static final int[][] GATE_TOP = {{-3, 144, -101}, {-3, 145, -101}, {-3, 146, -101}, {-3, 147, -101}, {-2, 144, -101}, {-2, 145, -101}, {-2, 146, -101}, {-2, 147, -101}, {-1, 144, -101}, {-1, 145, -101}, {-1, 146, -101}, {-1, 147, -101}, {0, 144, -101}, {0, 145, -101}, {0, 146, -101}, {0, 147, -101}, {1, 144, -101}, {1, 145, -101}, {1, 146, -101}, {1, 147, -101}, {2, 144, -101}, {2, 145, -101}, {2, 146, -101}, {2, 147, -101}, {3, 144, -101}, {3, 145, -101}, {3, 146, -101}, {3, 147, -101}};
    public static final double[] TOP_CHECKPOINT = {0.5, 144.0, -94.5};

    /** Salle de Vieux Tom. */
    public static final Box ROOM = new Box(-15, 15, 143, 152, -135, -105);
    public static final double[] TOM = {0.5, 144.0, -122.5};
    public static final int[] FAN = {6, 144, -134};
    public static final int[][] BATTERIES = {{13, 144, -133}, {-13, 144, -107}};
    public static final int[][] GATE_TOM = {{-3, 144, -136}, {-3, 145, -136}, {-3, 146, -136}, {-3, 147, -136}, {-2, 144, -136}, {-2, 145, -136}, {-2, 146, -136}, {-2, 147, -136}, {-1, 144, -136}, {-1, 145, -136}, {-1, 146, -136}, {-1, 147, -136}, {0, 144, -136}, {0, 145, -136}, {0, 146, -136}, {0, 147, -136}, {1, 144, -136}, {1, 145, -136}, {1, 146, -136}, {1, 147, -136}, {2, 144, -136}, {2, 145, -136}, {2, 146, -136}, {2, 147, -136}, {3, 144, -136}, {3, 145, -136}, {3, 146, -136}, {3, 147, -136}};
    public static final double[] VENT = {0.5, 149.0, -134.5};
    public static final double[] ROOM_CENTER = {0.5, 144.0, -119.5};

    /** Plates-formes de lueur et arène de l'Asura. */
    public static final double[] PAD2_CHECKPOINT = {0.5, 144.0, -140.5};
    public static final double[] ARENA_CENTER = {0.5, 164.0, -213.5};
    public static final double ARENA_RADIUS = 17;
    public static final double[] ASURA = {0.5, 166.0, -228.5};
    public static final double[][] GOLEMS = {{7.8, 164.0, -206.2}, {-7.8, 164.0, -206.2}, {-7.8, 164.0, -221.8}, {7.8, 164.0, -221.8}};
    /** Pylônes de charge (x, y, z, signe), actifs seulement quand on est seul. */
    public static final double[][] PYLONS = {{-5.5, 164.0, -217.5, 1}, {6.5, 164.0, -217.5, -1}};
    public static final int[] REWARD = {-2, 164, -212};
    public static final int[] END_EXIT = {2, 164, -212};

    private UncategorizedLayout() {
    }
}
