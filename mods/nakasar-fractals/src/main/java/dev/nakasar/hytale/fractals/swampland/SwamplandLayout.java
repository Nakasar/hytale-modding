package dev.nakasar.hytale.fractals.swampland;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions du Marais, écrites par tools/generate_swampland.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {x, y, z} : pieds ; blocs {x, y, z} : coins.
 */
public final class SwamplandLayout {

    public static final double[] SPAWN = {0.5, 100.0, 26.5};
    /** Le marais des feux-follets. */
    public static final Box SWAMP = new Box(-38, 38, 99, 108, -40, 38);
    /** Failles des feux-follets, au nord. */
    public static final int[][] CLEFTS = {{-10, 100, -35}, {0, 100, -37}, {10, 100, -35}};
    /** Places possibles des feux-follets : une par groupe, tirée à chaque essai (blocs et points). */
    public static final int[][][] WISP_SPOTS = {{{-33, 101, 27}, {-34, 101, -14}}, {{33, 101, 27}, {34, 101, -14}}, {{-13, 101, 34}, {13, 101, 34}}};
    public static final double[][][] WISP_POINTS = {{{-32.5, 101.0, 27.5}, {-33.5, 101.0, -13.5}}, {{33.5, 101.0, 27.5}, {34.5, 101.0, -13.5}}, {{-12.5, 101.0, 34.5}, {13.5, 101.0, 34.5}}};
    /** Murs qui surgissent dès qu'un feu-follet est pris : {x0, x1, y, z}, un bloc de haut. */
    public static final int[][] WALLS = {{-30, -6, 100, 20}, {6, 30, 100, 20}, {-20, 20, 100, 5}, {-34, -10, 100, -11}, {10, 34, 100, -11}, {-22, 22, 100, -24}};
    public static final int WALL_HEIGHT = 2;
    /** Pièges : {x, y, z, sorte} ; sortes : 0 fil tendu, 1 piège à loup, 2 plaque à piques, 3 œufs d'araignée. */
    public static final int[][] TRAPS = {{-27, 99, 8, 0}, {-19, 99, -7, 1}, {-16, 99, -23, 2}, {-26, 99, -20, 3}, {-22, 99, -26, 0}, {-14, 99, -31, 1}, {22, 99, 8, 2}, {16, 99, -8, 3}, {6, 99, -22, 0}, {25, 99, -21, 1}, {14, 99, -27, 2}, {8, 99, -32, 3}, {-7, 99, 13, 0}, {1, 99, -4, 1}, {4, 99, -21, 2}, {13, 99, 13, 3}, {10, 99, -4, 0}, {12, 99, -21, 1}};
    public static final int[][] RACKS = {{-17, 100, -34}, {17, 100, -34}};
    public static final int[][] GATE_SWAMP = {{-2, 100, -41}, {-2, 101, -41}, {-2, 102, -41}, {-2, 103, -41}, {-2, 104, -41}, {-1, 100, -41}, {-1, 101, -41}, {-1, 102, -41}, {-1, 103, -41}, {-1, 104, -41}, {0, 100, -41}, {0, 101, -41}, {0, 102, -41}, {0, 103, -41}, {0, 104, -41}, {1, 100, -41}, {1, 101, -41}, {1, 102, -41}, {1, 103, -41}, {1, 104, -41}, {2, 100, -41}, {2, 101, -41}, {2, 102, -41}, {2, 103, -41}, {2, 104, -41}};
    public static final double[] SWAMP_CHECKPOINT = {0.5, 100.0, -43.5};

    /** Salle de l'embuscade du Moussu. */
    public static final Box ROOM = new Box(-9, 9, 99, 108, -84, -60);
    public static final int[][] GATE_BEHIND = {{-2, 100, -51}, {-2, 101, -51}, {-2, 102, -51}, {-2, 103, -51}, {-2, 104, -51}, {-1, 100, -51}, {-1, 101, -51}, {-1, 102, -51}, {-1, 103, -51}, {-1, 104, -51}, {0, 100, -51}, {0, 101, -51}, {0, 102, -51}, {0, 103, -51}, {0, 104, -51}, {1, 100, -51}, {1, 101, -51}, {1, 102, -51}, {1, 103, -51}, {1, 104, -51}, {2, 100, -51}, {2, 101, -51}, {2, 102, -51}, {2, 103, -51}, {2, 104, -51}};
    public static final int[][] GATE_AHEAD = {{-2, 100, -86}, {-2, 101, -86}, {-2, 102, -86}, {-2, 103, -86}, {-2, 104, -86}, {-1, 100, -86}, {-1, 101, -86}, {-1, 102, -86}, {-1, 103, -86}, {-1, 104, -86}, {0, 100, -86}, {0, 101, -86}, {0, 102, -86}, {0, 103, -86}, {0, 104, -86}, {1, 100, -86}, {1, 101, -86}, {1, 102, -86}, {1, 103, -86}, {1, 104, -86}, {2, 100, -86}, {2, 101, -86}, {2, 102, -86}, {2, 103, -86}, {2, 104, -86}};
    public static final double[] MOSSMAN = {0.5, 100.0, -75.5};
    /** Cachette fermée où le Moussu attend pendant sa furtivité. */
    public static final double[] POCKET = {16.5, 86.0, -67.5};
    public static final double[] ROOM_CHECKPOINT = {0.5, 100.0, -55.5};

    /** Clairière de Carnasse. */
    public static final double[] CLEARING = {0.5, 100.0, -115.5};
    public static final double CLEARING_RADIUS = 20;
    /** Failles de la clairière, dans le sens horaire (N, E, S, O). */
    public static final int[][] CLEARING_CLEFTS = {{0, 100, -129}, {13, 100, -116}, {0, 100, -103}, {-13, 100, -116}};
    public static final int[] CLEARING_WISP = {3, 101, -99};
    public static final int[][] CORNER_WISPS = {{12, 101, -128}, {12, 101, -104}, {-12, 101, -104}, {-12, 101, -128}};
    public static final double[] CLEARING_CHECKPOINT = {0.5, 100.0, -94.5};
    public static final int[] REWARD = {-2, 100, -112};
    public static final int[] END_EXIT = {2, 100, -112};

    private SwamplandLayout() {
    }
}
