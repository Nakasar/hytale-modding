package dev.nakasar.hytale.fractals.solidocean;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions de l'Océan solide, écrites par tools/generate_solid_ocean.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {x, y, z} : pieds ; blocs {x, y, z} : coins.
 */
public final class SolidOceanLayout {

    public static final double[] SPAWN = {0.5, 100.0, 42.5};
    /** Les fragments de jade et l'arène : une chute y ramène au dernier fragment. */
    public static final List<Box> JUMP_ZONES = List.of(new Box(-30, 56, 28, 119, -159, 48));
    /** Irukandjis des grands fragments. */
    public static final double[][] PATH_IRUKANDJI = {{5.5, 102.0, 31.5}, {12.5, 103.0, 17.5}, {8.5, 104.0, 8.5}, {10.5, 104.0, 8.5}, {0.5, 104.0, -4.5}, {4.5, 104.0, -19.5}, {6.5, 104.0, -19.5}, {10.5, 105.0, -27.5}, {10.5, 106.0, -42.5}, {3.5, 105.0, -49.5}, {5.5, 105.0, -49.5}, {0.5, 107.0, -64.5}, {5.5, 106.0, -72.5}, {10.5, 107.0, -79.5}, {12.5, 107.0, -79.5}, {13.5, 107.0, -89.5}};
    /** Dernier fragment avant l'arène (point de retour). */
    public static final double[] ARENA_CHECKPOINT = {13.5, 105.0, -89.5};

    /** Arène de l'Abîme de Jade. */
    public static final double[] ARENA_CENTER = {13.5, 105.0, -123.5};
    public static final double ARENA_RADIUS = 27;
    public static final double[] MAW = {13.5, 105.0, -157.5};
    /** Points des tentacules : les deux premiers sont ceux de la phase 1. */
    public static final double[][] TENTACLES = {{5.5, 105.0, -138.5}, {21.5, 105.0, -138.5}, {-6.5, 105.0, -128.5}, {33.5, 105.0, -128.5}, {13.5, 105.0, -126.5}, {13.5, 105.0, -146.5}, {1.5, 105.0, -114.5}, {25.5, 105.0, -114.5}};
    public static final double[][] COLOSSI = {{3.5, 105.0, -117.5}, {23.5, 105.0, -117.5}, {13.5, 105.0, -135.5}, {13.5, 105.0, -111.5}};
    public static final double[][] ARENA_IRUKANDJI = {{-8.5, 107.0, -131.5}, {35.5, 107.0, -131.5}};
    public static final int[] REWARD = {11, 105, -118};
    public static final int[] END_EXIT = {15, 105, -118};

    private SolidOceanLayout() {
    }
}
