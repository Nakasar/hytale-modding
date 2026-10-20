package dev.nakasar.hytale.fractals.volcanic;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions du Volcanique, écrites par tools/generate_volcanic.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {x, y, z} : pieds ; blocs {x, y, z} : coins.
 */
public final class VolcanicLayout {

    public static final double[] SPAWN = {0.5, 100.0, 26.5};
    /** Camp des grawls. */
    public static final Box CAMP = new Box(-20, 20, 99, 106, -20, 32);
    public static final double[] TOTEM = {0.5, 100.0, -5.5};
    public static final double[][] CAMP_SPAWNS = {{-13.5, 100.0, -11.5}, {14.5, 100.0, -11.5}, {-15.5, 100.0, 8.5}, {16.5, 100.0, 8.5}, {0.5, 100.0, -15.5}, {-7.5, 100.0, 0.5}, {8.5, 100.0, 0.5}};
    public static final int[][] GATE_CAMP = {{-3, 100, -21}, {-3, 101, -21}, {-3, 102, -21}, {-3, 103, -21}, {-3, 104, -21}, {-2, 100, -21}, {-2, 101, -21}, {-2, 102, -21}, {-2, 103, -21}, {-2, 104, -21}, {-1, 100, -21}, {-1, 101, -21}, {-1, 102, -21}, {-1, 103, -21}, {-1, 104, -21}, {0, 100, -21}, {0, 101, -21}, {0, 102, -21}, {0, 103, -21}, {0, 104, -21}, {1, 100, -21}, {1, 101, -21}, {1, 102, -21}, {1, 103, -21}, {1, 104, -21}, {2, 100, -21}, {2, 101, -21}, {2, 102, -21}, {2, 103, -21}, {2, 104, -21}, {3, 100, -21}, {3, 101, -21}, {3, 102, -21}, {3, 103, -21}, {3, 104, -21}};

    /** Couloir aux rochers : voie (x0..x1, z nord..sud), niches {z0, z1, côté}, palier nord, départ des rochers. */
    public static final Box CORRIDOR = new Box(-3, 3, 99, 105, -97, -22);
    public static final int CORRIDOR_X0 = -3;
    public static final int CORRIDOR_X1 = 3;
    public static final int[][] ALCOVES = {{-34, -32, 1}, {-46, -44, -1}, {-58, -56, 1}, {-70, -68, -1}, {-82, -80, 1}};
    public static final double[] BOULDER_START = {0.5, 100.0, -95.5};
    public static final double BOULDER_END_Z = -21.5;
    public static final double[] CORRIDOR_CHECKPOINT = {0.5, 100.0, -18.5};
    public static final double[] LANDING_CHECKPOINT = {-5.5, 100.0, -93.5};

    /** Arène du Champion chaman. */
    public static final double[] CHAMPION = {-33.5, 100.0, -93.5};
    public static final double CHAMPION_RADIUS = 14;
    public static final double[][] CAPTIVES = {{-25.5, 100.0, -85.5}, {-41.5, 100.0, -85.5}, {-41.5, 100.0, -101.5}, {-25.5, 100.0, -101.5}};
    public static final double[][] VETERAN_GATES = {{-33.5, 100.0, -80.5}, {-33.5, 100.0, -106.5}};
    public static final int[][] GATE_CHAMPION = {{-49, 100, -96}, {-49, 100, -95}, {-49, 100, -94}, {-49, 100, -93}, {-49, 100, -92}, {-49, 101, -96}, {-49, 101, -95}, {-49, 101, -94}, {-49, 101, -93}, {-49, 101, -92}, {-49, 102, -96}, {-49, 102, -95}, {-49, 102, -94}, {-49, 102, -93}, {-49, 102, -92}, {-49, 103, -96}, {-49, 103, -95}, {-49, 103, -94}, {-49, 103, -93}, {-49, 103, -92}, {-49, 104, -96}, {-49, 104, -95}, {-49, 104, -94}, {-49, 104, -93}, {-49, 104, -92}};

    /** Mine. */
    public static final Box MINE = new Box(-120, -48, 98, 108, -99, -89);
    public static final List<Box> JUMP_ZONES = List.of(
            new Box(-120, -48, 89, 114, -101, -87));
    public static final double[][] BATS = {{-61.5, 104.0, -93.5}, {-77.5, 104.0, -93.5}, {-93.5, 104.0, -93.5}, {-107.5, 104.0, -93.5}};
    public static final Box END_PAD = new Box(-124, -116, 101, 106, -98, -90);
    public static final double[] END_CHECKPOINT = {-116.5, 102.0, -93.5};

    /** Arène du Chamane imprégné. */
    public static final double[] ARENA_CENTER = {-139.5, 102.0, -93.5};
    public static final double ARENA_RADIUS = 16;
    public static final double[][] VILLAGERS = {{-127.5, 102.0, -86.5}, {-151.5, 102.0, -86.5}, {-151.5, 102.0, -100.5}, {-127.5, 102.0, -100.5}};
    public static final int[] REWARD = {-142, 102, -94};
    public static final int[] END_EXIT = {-138, 102, -94};

    private VolcanicLayout() {
    }
}
