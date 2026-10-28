package dev.nakasar.hytale.fractals.moltenboss;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions du Boss en fusion, écrites par tools/generate_molten_boss.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {x, y, z} : pieds ; blocs {x, y, z} : coins.
 */
public final class MoltenBossLayout {

    /** Une meute : centre (pieds), rôles et places de ses membres. */
    public record Pack(double[] center, String[] roles, double[][] at) {
    }

    public static final double[] SPAWN = {-20.5, 110.0, -1.5};
    public static final double[] BRAHAM = {-24.5, 110.0, -8.5};
    public static final double[] ROX = {-16.5, 110.0, -8.5};
    public static final double[] BRAHAM_END = {70.5, 100.0, -59.5};
    public static final double[] ROX_END = {80.5, 100.0, -59.5};

    /** Meutes 1 à 4 (atelier) puis groupes 5 à 8 (cour des wagonnets, passerelle des cuves). */
    public static final Pack[] PACKS = {new Pack(new double[]{-21.5, 100.0, 42.5}, new String[]{"Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Dredge_Sonic"}, new double[][]{{-23.5, 100.0, 42.5}, {-19.5, 100.0, 43.5}, {-21.5, 100.0, 39.5}}), new Pack(new double[]{-85.5, 100.0, 50.5}, new String[]{"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Legion_Shaman"}, new double[][]{{-87.5, 100.0, 50.5}, {-83.5, 100.0, 49.5}, {-85.5, 100.0, 53.5}}), new Pack(new double[]{-89.5, 100.0, 20.5}, new String[]{"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Dredge_Sonic", "Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Legion_Shaman"}, new double[][]{{-92.5, 100.0, 20.5}, {-87.5, 100.0, 22.5}, {-88.5, 100.0, 17.5}, {-90.5, 100.0, 24.5}}), new Pack(new double[]{-85.5, 100.0, -5.5}, new String[]{"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Dredge_Sonic"}, new double[][]{{-82.5, 100.0, -3.5}, {-88.5, 100.0, -2.5}}), new Pack(new double[]{-39.5, 100.0, -69.5}, new String[]{"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Legion_Shaman"}, new double[][]{{-41.5, 100.0, -69.5}, {-37.5, 100.0, -68.5}, {-39.5, 100.0, -72.5}}), new Pack(new double[]{-5.5, 100.0, -70.5}, new String[]{"Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Dredge_Sonic"}, new double[][]{{-7.5, 100.0, -69.5}, {-3.5, 100.0, -71.5}}), new Pack(new double[]{18.5, 100.0, -72.5}, new String[]{"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Legion_Shaman"}, new double[][]{{16.5, 100.0, -72.5}, {20.5, 100.0, -70.5}}), new Pack(new double[]{41.5, 100.0, -69.5}, new String[]{"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Dredge_Sonic"}, new double[][]{{39.5, 100.0, -70.5}, {43.5, 100.0, -68.5}, {41.5, 100.0, -66.5}})};
    /** La meute 4 garde aussi le résonateur et le chaman de la flamme d'élite. */
    public static final double[] RESONATOR_1 = {-77.5, 100.0, -9.5};
    public static final double[] ELITE_SHAMAN = {-89.5, 100.0, -3.5};
    /** Pont du canal de lave (tablier, garde-corps), posé quand la meute 4 tombe. */
    public static final int[][] BRIDGE_DECK = {{-90, 99, -31}, {-90, 99, -30}, {-90, 99, -29}, {-90, 99, -28}, {-90, 99, -27}, {-90, 99, -26}, {-90, 99, -25}, {-90, 99, -24}, {-90, 99, -23}, {-90, 99, -22}, {-90, 99, -21}, {-90, 99, -20}, {-90, 99, -19}, {-89, 99, -31}, {-89, 99, -30}, {-89, 99, -29}, {-89, 99, -28}, {-89, 99, -27}, {-89, 99, -26}, {-89, 99, -25}, {-89, 99, -24}, {-89, 99, -23}, {-89, 99, -22}, {-89, 99, -21}, {-89, 99, -20}, {-89, 99, -19}, {-88, 99, -31}, {-88, 99, -30}, {-88, 99, -29}, {-88, 99, -28}, {-88, 99, -27}, {-88, 99, -26}, {-88, 99, -25}, {-88, 99, -24}, {-88, 99, -23}, {-88, 99, -22}, {-88, 99, -21}, {-88, 99, -20}, {-88, 99, -19}, {-87, 99, -31}, {-87, 99, -30}, {-87, 99, -29}, {-87, 99, -28}, {-87, 99, -27}, {-87, 99, -26}, {-87, 99, -25}, {-87, 99, -24}, {-87, 99, -23}, {-87, 99, -22}, {-87, 99, -21}, {-87, 99, -20}, {-87, 99, -19}, {-86, 99, -31}, {-86, 99, -30}, {-86, 99, -29}, {-86, 99, -28}, {-86, 99, -27}, {-86, 99, -26}, {-86, 99, -25}, {-86, 99, -24}, {-86, 99, -23}, {-86, 99, -22}, {-86, 99, -21}, {-86, 99, -20}, {-86, 99, -19}, {-85, 99, -31}, {-85, 99, -30}, {-85, 99, -29}, {-85, 99, -28}, {-85, 99, -27}, {-85, 99, -26}, {-85, 99, -25}, {-85, 99, -24}, {-85, 99, -23}, {-85, 99, -22}, {-85, 99, -21}, {-85, 99, -20}, {-85, 99, -19}, {-84, 99, -31}, {-84, 99, -30}, {-84, 99, -29}, {-84, 99, -28}, {-84, 99, -27}, {-84, 99, -26}, {-84, 99, -25}, {-84, 99, -24}, {-84, 99, -23}, {-84, 99, -22}, {-84, 99, -21}, {-84, 99, -20}, {-84, 99, -19}};
    public static final int[][] BRIDGE_RAILS = {{-90, 100, -31}, {-90, 100, -30}, {-90, 100, -29}, {-90, 100, -28}, {-90, 100, -27}, {-90, 100, -26}, {-90, 100, -25}, {-90, 100, -24}, {-90, 100, -23}, {-90, 100, -22}, {-90, 100, -21}, {-90, 100, -20}, {-90, 100, -19}, {-84, 100, -31}, {-84, 100, -30}, {-84, 100, -29}, {-84, 100, -28}, {-84, 100, -27}, {-84, 100, -26}, {-84, 100, -25}, {-84, 100, -24}, {-84, 100, -23}, {-84, 100, -22}, {-84, 100, -21}, {-84, 100, -20}, {-84, 100, -19}};
    /** Canal de lave : qui y tombe brûle puis revient au point de retour. */
    public static final Box CHANNEL = new Box(-114, -60, 96, 99, -30, -20);
    /** Cases de lave des bassins et du creuset (x, z ; surface un bloc sous le sol) : la lave brûle qui s'y tient. */
    public static final int[][] LAVA_CELLS = {{-109, -78}, {-109, -77}, {-109, -76}, {-109, -75}, {-109, -74}, {-108, -79}, {-108, -78}, {-108, -77}, {-108, -76}, {-108, -75}, {-108, -74}, {-108, -73}, {-108, -72}, {-107, -80}, {-107, -79}, {-107, -78}, {-107, -77}, {-107, -76}, {-107, -75}, {-107, -74}, {-107, -73}, {-107, -72}, {-106, -81}, {-106, -80}, {-106, -79}, {-106, -78}, {-106, -77}, {-106, -76}, {-106, -75}, {-106, -74}, {-106, -73}, {-106, -72}, {-106, -71}, {-105, -81}, {-105, -80}, {-105, -79}, {-105, -78}, {-105, -77}, {-105, -76}, {-105, -75}, {-105, -74}, {-105, -73}, {-105, -72}, {-105, -71}, {-105, -70}, {-104, -82}, {-104, -81}, {-104, -80}, {-104, -79}, {-104, -78}, {-104, -77}, {-104, -76}, {-104, -75}, {-104, -74}, {-104, -73}, {-104, -72}, {-104, -71}, {-104, -70}, {-103, -81}, {-103, -80}, {-103, -79}, {-103, -78}, {-103, -77}, {-103, -76}, {-103, -75}, {-103, -74}, {-103, -73}, {-103, -72}, {-103, -71}, {-103, -70}, {-102, -81}, {-102, -80}, {-102, -79}, {-102, -78}, {-102, -77}, {-102, -76}, {-102, -75}, {-102, -74}, {-102, -73}, {-102, -72}, {-102, -71}, {-102, -45}, {-102, -44}, {-102, -43}, {-101, -81}, {-101, -80}, {-101, -79}, {-101, -78}, {-101, -77}, {-101, -76}, {-101, -75}, {-101, -74}, {-101, -73}, {-101, -72}, {-101, -46}, {-101, -45}, {-101, -44}, {-101, -43}, {-101, -42}, {-101, -41}, {-100, -80}, {-100, -79}, {-100, -78}, {-100, -77}, {-100, -76}, {-100, -75}, {-100, -74}, {-100, -73}, {-100, -47}, {-100, -46}, {-100, -45}, {-100, -44}, {-100, -43}, {-100, -42}, {-100, -41}, {-99, -79}, {-99, -78}, {-99, -77}, {-99, -76}, {-99, -75}, {-99, -74}, {-99, -47}, {-99, -46}, {-99, -45}, {-99, -44}, {-99, -43}, {-99, -42}, {-99, -41}, {-99, -40}, {-98, -48}, {-98, -47}, {-98, -46}, {-98, -45}, {-98, -44}, {-98, -43}, {-98, -42}, {-98, -41}, {-98, -40}, {-97, -48}, {-97, -47}, {-97, -46}, {-97, -45}, {-97, -44}, {-97, -43}, {-97, -42}, {-97, -41}, {-97, -40}, {-96, -47}, {-96, -46}, {-96, -45}, {-96, -44}, {-96, -43}, {-96, -42}, {-96, -41}, {-95, -47}, {-95, -46}, {-95, -45}, {-95, -44}, {-95, -43}, {-95, -42}, {-76, 56}, {-75, 54}, {-75, 55}, {-75, 56}, {-75, 57}, {-75, 58}, {-74, 53}, {-74, 54}, {-74, 55}, {-74, 56}, {-74, 57}, {-74, 58}, {-74, 59}, {-73, 52}, {-73, 53}, {-73, 54}, {-73, 55}, {-73, 56}, {-73, 57}, {-73, 58}, {-73, 59}, {-73, 60}, {-72, 52}, {-72, 53}, {-72, 54}, {-72, 55}, {-72, 56}, {-72, 57}, {-72, 58}, {-72, 59}, {-72, 60}, {-71, 52}, {-71, 53}, {-71, 54}, {-71, 55}, {-71, 56}, {-71, 57}, {-71, 58}, {-71, 59}, {-71, 60}, {-70, 53}, {-70, 54}, {-70, 55}, {-70, 56}, {-70, 57}, {-70, 58}, {-70, 59}, {-69, 54}, {-69, 55}, {-69, 56}, {-69, 57}, {-69, 58}, {-18, 49}, {-18, 50}, {-17, 46}, {-17, 47}, {-17, 48}, {-17, 49}, {-17, 50}, {-17, 51}, {-17, 52}, {-16, 45}, {-16, 46}, {-16, 47}, {-16, 48}, {-16, 49}, {-16, 50}, {-16, 51}, {-16, 52}, {-15, 45}, {-15, 46}, {-15, 47}, {-15, 48}, {-15, 49}, {-15, 50}, {-15, 51}, {-15, 52}, {-15, 53}, {-14, 45}, {-14, 46}, {-14, 47}, {-14, 48}, {-14, 49}, {-14, 50}, {-14, 51}, {-14, 52}, {-14, 53}, {-13, 45}, {-13, 46}, {-13, 47}, {-13, 48}, {-13, 49}, {-13, 50}, {-13, 51}, {-13, 52}, {-13, 53}, {-12, 46}, {-12, 47}, {-12, 48}, {-12, 49}, {-12, 50}, {-12, 51}, {-12, 52}, {-11, 47}, {-11, 48}, {-11, 49}, {-11, 50}, {-11, 51}, {-11, 52}, {-10, 49}, {-10, 50}, {65, -16}, {65, -15}, {65, -14}, {66, -18}, {66, -17}, {66, -16}, {66, -15}, {66, -14}, {66, -13}, {66, -12}, {67, -18}, {67, -17}, {67, -16}, {67, -15}, {67, -14}, {67, -13}, {67, -12}, {68, -19}, {68, -18}, {68, -17}, {68, -16}, {68, -15}, {68, -14}, {68, -13}, {68, -12}, {68, -11}, {69, -19}, {69, -18}, {69, -17}, {69, -16}, {69, -15}, {69, -14}, {69, -13}, {69, -12}, {69, -11}, {70, -19}, {70, -18}, {70, -17}, {70, -16}, {70, -15}, {70, -14}, {70, -13}, {70, -12}, {70, -11}, {71, -18}, {71, -17}, {71, -16}, {71, -15}, {71, -14}, {71, -13}, {71, -12}, {72, -18}, {72, -17}, {72, -16}, {72, -15}, {72, -14}, {72, -13}, {72, -12}, {73, -16}, {73, -15}, {73, -14}};
    public static final int LAVA_FLOOR_Y = 100;

    /** La fonderie : centre de l'Effigie, rayon du combat, Protecteur, second résonateur, renforts, porte est. */
    public static final double[] EFFIGY = {-81.5, 100.0, -57.5};
    public static final double EFFIGY_RADIUS = 18.0;
    public static final double[] PROTECTOR = {-81.5, 100.0, -65.5};
    public static final double[] RESONATOR_2 = {-69.5, 100.0, -71.5};
    public static final String[] EFFIGY_ADD_ROLES = {"Nakasar_Fractal_Molten_Legion_Warrior", "Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Dredge_Sonic", "Nakasar_Fractal_Molten_Legion_Shaman", "Nakasar_Fractal_Molten_Dredge_Miner", "Nakasar_Fractal_Molten_Legion_Warrior"};
    public static final double[][] EFFIGY_ADDS = {{-96.5, 100.0, -63.5}, {-94.5, 100.0, -62.5}, {-70.5, 100.0, -49.5}, {-68.5, 100.0, -48.5}, {-94.5, 100.0, -47.5}, {-92.5, 100.0, -46.5}};
    public static final int[][] FOUNDRY_GATE = {{-56, 100, -76}, {-56, 101, -76}, {-56, 102, -76}, {-56, 103, -76}, {-56, 104, -76}, {-56, 100, -75}, {-56, 101, -75}, {-56, 102, -75}, {-56, 103, -75}, {-56, 104, -75}, {-56, 100, -74}, {-56, 101, -74}, {-56, 102, -74}, {-56, 103, -74}, {-56, 104, -74}, {-56, 100, -73}, {-56, 101, -73}, {-56, 102, -73}, {-56, 103, -73}, {-56, 104, -73}, {-56, 100, -72}, {-56, 101, -72}, {-56, 102, -72}, {-56, 103, -72}, {-56, 104, -72}, {-56, 100, -71}, {-56, 101, -71}, {-56, 102, -71}, {-56, 103, -71}, {-56, 104, -71}, {-56, 100, -70}, {-56, 101, -70}, {-56, 102, -70}, {-56, 103, -70}, {-56, 104, -70}, {-56, 100, -69}, {-56, 101, -69}, {-56, 102, -69}, {-56, 103, -69}, {-56, 104, -69}, {-56, 100, -68}, {-56, 101, -68}, {-56, 102, -68}, {-56, 103, -68}, {-56, 104, -68}, {-56, 100, -67}, {-56, 101, -67}, {-56, 102, -67}, {-56, 103, -67}, {-56, 104, -67}, {-56, 100, -66}, {-56, 101, -66}, {-56, 102, -66}, {-56, 103, -66}, {-56, 104, -66}};
    public static final double[] CHECKPOINT_B = {-49.5, 100.0, -70.5};

    /** Salle des chaudières : barrière du pont du creuset, point de retour. */
    public static final int[][] BOILERS_GATE = {{72, 100, -54}, {72, 101, -54}, {72, 102, -54}, {72, 103, -54}, {72, 104, -54}, {73, 100, -54}, {73, 101, -54}, {73, 102, -54}, {73, 103, -54}, {73, 104, -54}, {74, 100, -54}, {74, 101, -54}, {74, 102, -54}, {74, 103, -54}, {74, 104, -54}, {75, 100, -54}, {75, 101, -54}, {75, 102, -54}, {75, 103, -54}, {75, 104, -54}, {76, 100, -54}, {76, 101, -54}, {76, 102, -54}, {76, 103, -54}, {76, 104, -54}, {77, 100, -54}, {77, 101, -54}, {77, 102, -54}, {77, 103, -54}, {77, 104, -54}, {78, 100, -54}, {78, 101, -54}, {78, 102, -54}, {78, 103, -54}, {78, 104, -54}};
    public static final double[] CHECKPOINT_D = {75.5, 100.0, -61.5};

    /** La plate-forme du creuset : centre, rayon, creuset de lave (muret compris). */
    public static final double[] ARENA = {75.5, 100.0, -9.5};
    public static final double ARENA_RADIUS = 26.0;
    public static final double[] PIT = {69.5, 100.0, -14.5};
    public static final double PIT_RADIUS = 5.3;
    /** Ondes de choc : vitesse, demi-épaisseur, hauteur de l'onde bleue. */
    public static final double SHOCK_SPEED = 8.0;
    public static final double SHOCK_BAND = 0.75;
    public static final double AIR_RING_HEIGHT = 1.6;
    public static final double SHOCK_REACH_EFFIGY = 22.0;
    public static final double SHOCK_REACH_DUO = 56.0;
    public static final double RING_SCALE = 0.68;
    /** Flammes de la Tempête (rayon, durée), débris, couronne de vent (24 bandes de 6.9 x 6.0 : JAVA_LINES). */
    public static final double FIRE_POOL_RADIUS = 3.0;
    public static final float FIRE_POOL_SECONDS = 8.0f;
    public static final double DEBRIS_RADIUS = 2.5;
    public static final double WIND_BAND = 6.0;
    public static final int WIND_SEGMENTS = 24;
    public static final double WIND_LENGTH = 6.9;
    public static final double FIRESTORM_ORBIT = 17.0;
    public static final double FIRESTORM_HOVER = 1.5;
    public static final int[] REWARD = {72, 100, -2};
    public static final int[] END_EXIT = {78, 100, -2};

    private MoltenBossLayout() {
    }
}
