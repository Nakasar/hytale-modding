package dev.nakasar.hytale.fractals.cliffside;

import java.util.List;

/**
 * Positions de la Falaise, écrites par tools/generate_cliffside.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud ; y monde (le plateau du camp est debout à 100).
 * Les points {x, y, z} sont des pieds (centre du bloc) ; les blocs {x, y, z} des coins de bloc.
 */
public final class CliffsideLayout {

    public static final int GROUND_Y = 100;
    /** Hauteurs (debout) : passerelle des genoux, du torse, épaules, arène. */
    public static final int KNEES = 122;
    public static final int CHEST = 152;
    public static final int SHOULDERS = 172;
    public static final int ARENA = 190;

    public static final double[] SPAWN = {0.5, 100.0, 20.5};
    public static final double[] CAMP = {0.5, 100.0, -9.5};
    public static final double[] SEEKER = {3.5, 100.0, -27.5};
    public static final double[][] CAMP_WAVE = {{-5.5, 100.0, -13.5}, {6.5, 100.0, -13.5}, {-2.5, 100.0, -19.5}, {3.5, 100.0, -19.5}, {0.5, 100.0, -7.5}};

    /** Points de retour (pieds) : passerelle des genoux, du torse, épaules, palier de l'arène. */
    public static final double[] CHECKPOINT_KNEES = {1.5, 122.0, -35.5};
    public static final double[] CHECKPOINT_CHEST = {0.5, 152.0, -33.5};
    public static final double[] CHECKPOINT_SHOULDERS = {0.5, 172.0, -45.5};
    public static final double[] CHECKPOINT_ARENA = {-15.5, 190.0, -31.5};

    /** Zones où l'on déclenche une étape (pieds dedans). */
    public static final Box KNEES_DECK = new Box(-18, 20, 121, 125, -41, -33);
    public static final Box CHEST_DECK = new Box(-18, 18, 151, 155, -42, -31);
    public static final Box SHOULDERS_TOP = new Box(-52, 52, 171, 175, -56, -44);

    /** Sceaux (pieds du PNJ) : genou ouest, genou est, poitrine, poignet ouest, poignet est, cou. */
    public static final double[][] SEALS = {{-8.5, 122.0, -39.5}, {8.5, 122.0, -39.5}, {0.5, 152.0, -40.5},
            {-44.5, 172.0, -51.5}, {45.5, 172.0, -51.5}, {0.5, 190.0, -11.5}};
    /** Points d'apparition des vagues, par sceau (mêmes index que {@link #SEALS}, le cou n'en a pas). */
    public static final double[][][] WAVES = {
            {{-10.5, 122.0, -35.5}, {-5.5, 122.0, -35.5}, {-8.5, 122.0, -33.5}},
            {{11.5, 122.0, -35.5}, {6.5, 122.0, -35.5}, {9.5, 122.0, -33.5}},
            {{-7.5, 152.0, -32.5}, {8.5, 152.0, -32.5}, {-3.5, 152.0, -31.5}, {4.5, 152.0, -31.5}},
            {{-39.5, 172.0, -53.5}, {-37.5, 172.0, -49.5}, {-41.5, 172.0, -49.5}},
            {{41.5, 172.0, -53.5}, {39.5, 172.0, -49.5}, {43.5, 172.0, -49.5}}};

    /** Barrières de brume (blocs) : G1 après les genoux, G2 au pied de l'escalier du torse, G3 avant les rampes. */
    public static final int[][] GATE1 = {{-18, 122, -38}, {-18, 122, -37}, {-18, 122, -36}, {-18, 122, -35}, {-18, 123, -38}, {-18, 123, -37}, {-18, 123, -36}, {-18, 123, -35}, {-18, 124, -38}, {-18, 124, -37}, {-18, 124, -36}, {-18, 124, -35}, {-18, 125, -38}, {-18, 125, -37}, {-18, 125, -36}, {-18, 125, -35}};
    public static final int[][] GATE2 = {{-4, 152, -31}, {-4, 153, -31}, {-4, 154, -31}, {-3, 152, -31}, {-3, 153, -31}, {-3, 154, -31}, {-2, 152, -31}, {-2, 153, -31}, {-2, 154, -31}, {-1, 152, -31}, {-1, 153, -31}, {-1, 154, -31}, {0, 152, -31}, {0, 153, -31}, {0, 154, -31}, {1, 152, -31}, {1, 153, -31}, {1, 154, -31}, {2, 152, -31}, {2, 153, -31}, {2, 154, -31}, {3, 152, -31}, {3, 153, -31}, {3, 154, -31}, {4, 152, -31}, {4, 153, -31}, {4, 154, -31}};
    public static final int[][] GATE3 = {{-18, 172, -43}, {-18, 173, -43}, {-18, 174, -43}, {-17, 172, -43}, {-17, 173, -43}, {-17, 174, -43}, {-16, 172, -43}, {-16, 173, -43}, {-16, 174, -43}, {-15, 172, -43}, {-15, 173, -43}, {-15, 174, -43}, {-14, 172, -43}, {-14, 173, -43}, {-14, 174, -43}, {-13, 172, -43}, {-13, 173, -43}, {-13, 174, -43}, {-12, 172, -43}, {-12, 173, -43}, {-12, 174, -43}};

    /** Tunnel : plaques (x, z) au sol en y = 121, piégées ou non. */
    public static final int PLATE_Y = 121;
    public static final List<Plate> PLATES = List.of(
            new Plate(-41, -37, true),
            new Plate(-41, -36, true),
            new Plate(-40, -36, true),
            new Plate(-40, -35, true),
            new Plate(-39, -35, true),
            new Plate(-38, -38, false),
            new Plate(-37, -38, true),
            new Plate(-37, -37, false),
            new Plate(-36, -37, true),
            new Plate(-36, -36, false),
            new Plate(-35, -36, true),
            new Plate(-35, -35, false),
            new Plate(-34, -35, true),
            new Plate(-33, -38, true),
            new Plate(-32, -38, false),
            new Plate(-32, -37, true),
            new Plate(-31, -37, false),
            new Plate(-31, -36, true),
            new Plate(-30, -36, false),
            new Plate(-30, -35, true),
            new Plate(-29, -35, false),
            new Plate(-28, -38, true),
            new Plate(-27, -38, true),
            new Plate(-27, -37, true),
            new Plate(-26, -37, true),
            new Plate(-26, -36, true),
            new Plate(-25, -36, true),
            new Plate(-25, -35, true),
            new Plate(-24, -35, true),
            new Plate(-23, -38, false),
            new Plate(-22, -38, true),
            new Plate(-22, -37, false),
            new Plate(-21, -37, true),
            new Plate(-21, -36, false),
            new Plate(-20, -36, true),
            new Plate(-20, -35, false));

    /** Gargouilles (bloc de la statue), groupe (levier) et décalage de cycle (s). Souffle vers +z sur 13 blocs. */
    public static final int GUST_REACH = 13;
    public static final List<Gargoyle> GARGOYLES = List.of(
            new Gargoyle(-54, 124, -57, 0, 0.0f),
            new Gargoyle(-59, 126, -57, 0, 2.5f),
            new Gargoyle(-54, 131, -57, 0, 1.7f),
            new Gargoyle(-59, 130, -57, 0, 4.2f),
            new Gargoyle(-54, 134, -57, 1, 3.4f),
            new Gargoyle(-59, 136, -57, 1, 0.9f),
            new Gargoyle(-54, 141, -57, 1, 0.1f),
            new Gargoyle(-59, 140, -57, 1, 2.6f),
            new Gargoyle(-54, 144, -57, 2, 1.8f),
            new Gargoyle(-59, 146, -57, 2, 4.3f),
            new Gargoyle(-54, 151, -57, 2, 3.5f),
            new Gargoyle(-59, 150, -57, 2, 1.0f));
    /** Leviers (blocs) : trois du saut (un par groupe de gargouilles), puis R1 et R2. */
    public static final int[][] LEVERS = {{-49, 152, -56}, {-48, 152, -56}, {-47, 152, -56}, {-17, 190, -36}, {-15, 190, -36}};
    public static final int GARGOYLE_LEVERS = 3;

    /** Zones de saut : une chute à plus de 4 blocs sous la dernière plate-forme sûre y ramène. */
    public static final List<Box> JUMP_ZONES = List.of(
            new Box(-70, -40, 40, 160, -60, -44),
            new Box(-22, 22, 164, 196, -44, -26));

    /** Foyers de la passerelle du torse (centre, pieds) et leur rayon. */
    public static final double[][] FIRES = {{-8.5, 152.0, -36.5}, {0.5, 152.0, -34.5}, {9.5, 152.0, -36.5}};
    public static final double FIRE_RADIUS = 4.5;

    /** Rampes : cases du haut vers le bas, au milieu de la rampe (pieds) ; les bombes les descendent. */
    public static final double[][][] RAMPS = {
            {{14.5, 181.0, -37.5}, {13.5, 180.5, -37.5}, {12.5, 180.0, -37.5}, {11.5, 179.5, -37.5}, {10.5, 179.5, -37.5}, {9.5, 179.0, -37.5}, {8.5, 178.5, -37.5}, {7.5, 178.5, -37.5}, {6.5, 178.0, -37.5}, {5.5, 177.5, -37.5}, {4.5, 177.5, -37.5}, {3.5, 177.0, -37.5}, {2.5, 176.5, -37.5}, {1.5, 176.5, -37.5}, {0.5, 176.0, -37.5}, {-0.5, 175.5, -37.5}, {-1.5, 175.0, -37.5}, {-2.5, 175.0, -37.5}, {-3.5, 174.5, -37.5}, {-4.5, 174.0, -37.5}, {-5.5, 174.0, -37.5}, {-6.5, 173.5, -37.5}, {-7.5, 173.0, -37.5}, {-8.5, 173.0, -37.5}, {-9.5, 172.5, -37.5}, {-10.5, 172.0, -37.5}, {-11.5, 172.0, -37.5}},
            {{-12.5, 190.0, -33.5}, {-11.5, 189.5, -33.5}, {-10.5, 189.0, -33.5}, {-9.5, 189.0, -33.5}, {-8.5, 188.5, -33.5}, {-7.5, 188.0, -33.5}, {-6.5, 188.0, -33.5}, {-5.5, 187.5, -33.5}, {-4.5, 187.0, -33.5}, {-3.5, 187.0, -33.5}, {-2.5, 186.5, -33.5}, {-1.5, 186.0, -33.5}, {-0.5, 186.0, -33.5}, {0.5, 185.5, -33.5}, {1.5, 185.0, -33.5}, {2.5, 185.0, -33.5}, {3.5, 184.5, -33.5}, {4.5, 184.0, -33.5}, {5.5, 184.0, -33.5}, {6.5, 183.5, -33.5}, {7.5, 183.0, -33.5}, {8.5, 183.0, -33.5}, {9.5, 182.5, -33.5}, {10.5, 182.0, -33.5}, {11.5, 182.0, -33.5}, {12.5, 181.5, -33.5}, {13.5, 181.0, -33.5}, {14.5, 181.0, -33.5}}};

    /** Arène de l'Archidevin. */
    public static final double[] ARENA_CENTER = {0.5, 190.0, -11.5};
    public static final double ARENA_RADIUS = 16;
    public static final double[] BOSS_SPAWN = {0.5, 190.0, -2.5};
    public static final int[] REWARD = {-2, 190, -19};
    public static final int[] END_EXIT = {2, 190, -19};
    /** Cages : bloc de cage aux pieds (x, z, y = {@link #ARENA}) et côté de la porte (dx, dz). */
    public static final List<Cage> CAGES = List.of(
            new Cage(-3, -25, 0, 1),
            new Cage(9, -21, -1, 0),
            new Cage(13, -9, -1, 0),
            new Cage(3, 1, 0, -1),
            new Cage(-9, -3, 1, 0),
            new Cage(-13, -15, 1, 0));

    private CliffsideLayout() {
    }

    public record Plate(int x, int z, boolean trapped) {
    }

    public record Gargoyle(int x, int y, int z, int group, float offset) {
    }

    public record Cage(int x, int z, int doorX, int doorZ) {
    }

    /** Boîte de blocs, bornes comprises. */
    public record Box(int x0, int x1, int y0, int y1, int z0, int z1) {
        public boolean contains(double x, double y, double z) {
            return x >= x0 && x < x1 + 1 && y >= y0 && y < y1 + 1 && z >= z0 && z < z1 + 1;
        }
    }
}
