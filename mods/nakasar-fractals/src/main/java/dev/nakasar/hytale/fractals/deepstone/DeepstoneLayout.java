package dev.nakasar.hytale.fractals.deepstone;

/**
 * Positions de la Roche des Abysses, écrites par tools/generate_deepstone.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {x, y, z} : pieds ; blocs {x, y, z} : coins.
 * Boîtes {x0, x1, z0, z1} en blocs.
 */
public final class DeepstoneLayout {

    public static final double[] SPAWN = {0.5, 124.0, 78.5};
    public static final double[] TORIN = {-2.5, 124.0, 72.5};
    public static final double[] KAY = {3.5, 124.0, 72.5};
    public static final double[][] BATS = {{13.5, 121.0, 60.5}, {14.5, 118.0, 48.5}, {2.5, 115.0, 42.5}, {-9.5, 112.0, 36.5}, {-13.5, 109.0, 28.5}};
    /** Sol des salles du caveau (y monde du dessus des dalles : on y est debout). */
    public static final double VAULT_Y = 100.0;

    /** La salle du cristal. */
    public static final int[] HALL = {-18, 18, -6, 18};
    public static final double[] HALL_CENTER = {0.5, 100.0, 5.5};
    public static final double[] TORIN_HALL = {-3.5, 100.0, 13.5};
    public static final double[] KAY_HALL = {4.5, 100.0, 13.5};
    public static final int[] CRYSTAL = {0, 100, 14};
    public static final double[] RETURN = {0.5, 100.0, 10.5};
    public static final double[] MINOTAUR = {0.5, 100.0, 0.5};
    public static final double[][] HALL_IMPS = {{-9.5, 100.0, -0.5}, {10.5, 100.0, -0.5}, {-9.5, 100.0, 11.5}, {10.5, 100.0, 11.5}, {0.5, 100.0, -1.5}, {0.5, 100.0, 12.5}};
    public static final int[][] NORTH_GATE = {{-3, 100, -7}, {-3, 101, -7}, {-3, 102, -7}, {-3, 103, -7}, {-3, 104, -7}, {-3, 105, -7}, {-3, 100, -6}, {-3, 101, -6}, {-3, 102, -6}, {-3, 103, -6}, {-3, 104, -6}, {-3, 105, -6}, {-2, 100, -7}, {-2, 101, -7}, {-2, 102, -7}, {-2, 103, -7}, {-2, 104, -7}, {-2, 105, -7}, {-2, 100, -6}, {-2, 101, -6}, {-2, 102, -6}, {-2, 103, -6}, {-2, 104, -6}, {-2, 105, -6}, {-1, 100, -7}, {-1, 101, -7}, {-1, 102, -7}, {-1, 103, -7}, {-1, 104, -7}, {-1, 105, -7}, {-1, 100, -6}, {-1, 101, -6}, {-1, 102, -6}, {-1, 103, -6}, {-1, 104, -6}, {-1, 105, -6}, {0, 100, -7}, {0, 101, -7}, {0, 102, -7}, {0, 103, -7}, {0, 104, -7}, {0, 105, -7}, {0, 100, -6}, {0, 101, -6}, {0, 102, -6}, {0, 103, -6}, {0, 104, -6}, {0, 105, -6}, {1, 100, -7}, {1, 101, -7}, {1, 102, -7}, {1, 103, -7}, {1, 104, -7}, {1, 105, -7}, {1, 100, -6}, {1, 101, -6}, {1, 102, -6}, {1, 103, -6}, {1, 104, -6}, {1, 105, -6}, {2, 100, -7}, {2, 101, -7}, {2, 102, -7}, {2, 103, -7}, {2, 104, -7}, {2, 105, -7}, {2, 100, -6}, {2, 101, -6}, {2, 102, -6}, {2, 103, -6}, {2, 104, -6}, {2, 105, -6}, {3, 100, -7}, {3, 101, -7}, {3, 102, -7}, {3, 103, -7}, {3, 104, -7}, {3, 105, -7}, {3, 100, -6}, {3, 101, -6}, {3, 102, -6}, {3, 103, -6}, {3, 104, -6}, {3, 105, -6}};

    /** L'ouest : grille de runes (dalles de 2 blocs, rangée 0 au nord), runes, barrière, corniche. */
    public static final int GRID_X0 = -38;
    public static final int GRID_Z0 = -38;
    public static final int GRID_COLS = 5;
    public static final int GRID_ROWS = 20;
    public static final int GRID_TILE = 2;
    public static final int FLOOR_Y = 99;
    public static final double[] GRID_START = {-33.5, 100.0, 5.5};
    public static final double[] GRID_END = {-33.5, 100.0, -42.5};
    public static final double[][] WEST_RUNES = {{-35.5, 100.0, -41.5}, {-30.5, 100.0, -41.5}};
    public static final int[][] WEST_GATE = {{-38, 100, -47}, {-38, 101, -47}, {-38, 102, -47}, {-38, 103, -47}, {-38, 104, -47}, {-38, 105, -47}, {-37, 100, -47}, {-37, 101, -47}, {-37, 102, -47}, {-37, 103, -47}, {-37, 104, -47}, {-37, 105, -47}, {-36, 100, -47}, {-36, 101, -47}, {-36, 102, -47}, {-36, 103, -47}, {-36, 104, -47}, {-36, 105, -47}, {-35, 100, -47}, {-35, 101, -47}, {-35, 102, -47}, {-35, 103, -47}, {-35, 104, -47}, {-35, 105, -47}, {-34, 100, -47}, {-34, 101, -47}, {-34, 102, -47}, {-34, 103, -47}, {-34, 104, -47}, {-34, 105, -47}, {-33, 100, -47}, {-33, 101, -47}, {-33, 102, -47}, {-33, 103, -47}, {-33, 104, -47}, {-33, 105, -47}, {-32, 100, -47}, {-32, 101, -47}, {-32, 102, -47}, {-32, 103, -47}, {-32, 104, -47}, {-32, 105, -47}, {-31, 100, -47}, {-31, 101, -47}, {-31, 102, -47}, {-31, 103, -47}, {-31, 104, -47}, {-31, 105, -47}, {-30, 100, -47}, {-30, 101, -47}, {-30, 102, -47}, {-30, 103, -47}, {-30, 104, -47}, {-30, 105, -47}, {-29, 100, -47}, {-29, 101, -47}, {-29, 102, -47}, {-29, 103, -47}, {-29, 104, -47}, {-29, 105, -47}};
    public static final double[] SENTINEL = {-47.5, 100.0, -60.5};
    public static final double SENTINEL_RADIUS = 13.0;
    /** Bord ouest de la corniche : au-delà (x plus petit), le vide. */
    public static final double SENTINEL_EDGE_X = -60.0;
    public static final int[] WEST_ORB = {-42, 100, -54};

    /** L'est : nids (œufs du Marais, bloc), pont, runes, barrière, antre de la Reine. */
    public static final int[] CORRIDOR_NEST = {30, 100, 2};
    public static final int[][] BRIDGE_NESTS = {{44, 100, 2}, {55, 100, 8}, {66, 100, 2}};
    public static final int[][] QUEEN_NESTS = {{82, 100, -4}, {94, 100, 14}};
    public static final int[] BRIDGE = {36, 74, 4, 6};
    /** Zone du vent et des chutes du pont (x0, x1, z0, z1), baies comprises. */
    public static final int[] BRIDGE_ZONE = {34, 76, 0, 10};
    public static final double[] BRIDGE_START = {34.5, 100.0, 5.5};
    public static final double[][] EAST_RUNES = {{54.5, 100.0, 1.5}, {54.5, 100.0, 9.5}};
    public static final int[][] EAST_GATE = {{73, 100, 3}, {73, 101, 3}, {73, 102, 3}, {73, 103, 3}, {73, 104, 3}, {73, 105, 3}, {73, 100, 4}, {73, 101, 4}, {73, 102, 4}, {73, 103, 4}, {73, 104, 4}, {73, 105, 4}, {73, 100, 5}, {73, 101, 5}, {73, 102, 5}, {73, 103, 5}, {73, 104, 5}, {73, 105, 5}, {73, 100, 6}, {73, 101, 6}, {73, 102, 6}, {73, 103, 6}, {73, 104, 6}, {73, 105, 6}, {73, 100, 7}, {73, 101, 7}, {73, 102, 7}, {73, 103, 7}, {73, 104, 7}, {73, 105, 7}};
    public static final double[] QUEEN = {88.5, 100.0, 5.5};
    public static final double QUEEN_RADIUS = 14.0;
    public static final double[][] MOTHERS = {{84.5, 100.0, 2.5}, {92.5, 100.0, 8.5}};
    public static final int[] EAST_ORB = {92, 100, -2};
    /** Vent du pont : bande de 11 x 5 blocs en travers (Telegraphs.Strip, JAVA_LINES). */
    public static final double WIND_LENGTH = 11.0;
    public static final double WIND_WIDTH = 5.0;

    /** Trésors cachés (Lumière de Deldrimor). */
    public static final double[][] TREASURES = {{9.5, 118.0, 50.5}, {-15.5, 109.0, 27.5}, {15.5, 100.0, 15.5}, {-33.5, 100.0, 7.5}, {-53.5, 100.0, -59.5}, {32.5, 100.0, 8.5}, {95.5, 100.0, 11.5}, {-14.5, 100.0, -27.5}, {8.5, 100.0, -97.5}, {2.5, 70.0, -109.5}};

    /** La salle du gouffre : dalles de 3 blocs (colonne 0 à l'ouest, rangée 0 au nord), orbes (case). */
    public static final int PIT_X0 = -16;
    public static final int PIT_Z0 = -67;
    public static final int PIT_COLS = 11;
    public static final int PIT_ROWS = 13;
    public static final int PIT_TILE = 3;
    public static final int[][] PIT_ORB_TILES = {{5, 12}, {0, 8}, {10, 4}, {1, 0}};
    public static final int[][] PIT_ORBS = {{0, 100, -30}, {-15, 100, -42}, {15, 100, -54}, {-12, 100, -66}};
    public static final double[] PIT_LEDGE = {0.0, 100.0, -27.5};
    public static final double[] PIT_EXIT = {0.0, 100.0, -70.0};
    /** La salle (avec ses paliers) : x0, x1, z0, z1. */
    public static final int[] PIT_ROOM = {-20, 20, -72, -26};

    /** L'ascenseur : plate-forme (x0, x1, z0, z1), debout en haut, à l'arrêt, en bas (y prefab + 100). */
    public static final int[] LIFT = {-4, 4, -96, -88};
    public static final int LIFT_TOP = 100;
    public static final int LIFT_STOP = 85;
    public static final int LIFT_BOTTOM = 70;
    public static final double[] LIFT_CENTER = {0.0, 100.0, -92.0};
    public static final int[] LIFT_RUNE = {7, 100, -92};
    public static final double[] LIFT_LANDING = {0.5, 70.0, -98.5};

    /** L'arène de la Voix : dalles de 3 blocs. */
    public static final int ARENA_X0 = -22;
    public static final int ARENA_Z0 = -173;
    public static final int ARENA_COLS = 15;
    public static final int ARENA_ROWS = 15;
    public static final int ARENA_TILE = 3;
    public static final int ARENA_FLOOR_Y = 69;
    public static final double[] ARENA = {0.5, 70.0, -149.5};
    public static final double[] WALKWAY_END = {0.5, 70.0, -127.5};
    public static final int[] REWARD = {-3, 70, -151};
    public static final int[] END_EXIT = {3, 70, -151};

    private DeepstoneLayout() {
    }
}
