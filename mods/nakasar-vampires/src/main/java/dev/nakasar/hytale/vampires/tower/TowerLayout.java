package dev.nakasar.hytale.vampires.tower;

import org.joml.Vector3d;

/** Positions de la Tour de l'Alchimiste. Généré par tools/generate_alchemist_tower.py : ne pas modifier à la main. */
public final class TowerLayout {

    /** Première couche d'air au-dessus du sol des îles. */
    public static final double GROUND_Y = 100;
    /** Point d'apparition, sur le parvis d'arrivée. */
    public static final Vector3d ARRIVAL = new Vector3d(0.5, 100, 0.5);
    /** Points de contrôle, dans l'ordre du parcours : ruines du premier laboratoire, bibliothèque, Escalier des vents, antichambre. */
    public static final Vector3d[] CHECKPOINTS = {
            new Vector3d(-0.5, 105, -212.5),
            new Vector3d(25.5, 136, -412.5),
            new Vector3d(1.5, 184, -476.5),
            new Vector3d(-8.5, 244, -471.5)
    };

    /** Codex vivant : centre de la rotonde de la bibliothèque, au sol. */
    public static final Vector3d CODEX_CENTER = new Vector3d(0.5, 136, -439.5);
    /** Rayon de l'arène du Codex (intérieur de la tour). */
    public static final double CODEX_ARENA_RADIUS = 29.5;
    /** Dessus des trois pupitres où le Codex ouvre ses chapitres. */
    public static final Vector3d[] CODEX_LECTERNS = {
            new Vector3d(8.5, 137, -434.5),
            new Vector3d(-7.5, 137, -434.5),
            new Vector3d(0.5, 137, -449.5)
    };
    /** Volumes de l'arène (tools/alchemist_traps.py, Traps.codex) : sceau de la rampe (Codex=On), remise à zéro (Reset=On). */
    public static final String CODEX_SEAL = "1816a36c-8023-5278-9339-7f890a3bbcbd";
    public static final String CODEX_ARENA = "5db73ada-e251-5acd-a5b6-2e4205d9853d";
    /** Sorts des chapitres (Cast=On) : cercle de feu, pluie de livres, onde de givre de chaque pupitre. */
    public static final String CODEX_FIRE = "0aef35a7-5051-56e2-91e8-22a282c43e6c";
    public static final String CODEX_RAIN = "173c39a7-c79c-5281-911c-3a4fa7945a02";
    public static final String[] CODEX_FROST = {"74757796-2d48-5a90-bd46-438d4df92b2a", "c80345e6-188c-556a-9abd-fd25903252d6", "3f9bcf18-3622-53f0-a84c-6d3ddbbfae01"};
    /** Pans d'étagères qui s'effondrent (Collapse=On). */
    public static final String[] CODEX_COLLAPSE = {"00f64808-4e2c-5a2a-9ad9-582cfaf84967", "7d02473a-a339-5dd9-b38c-332bc146f65c", "11b6c4b0-f282-5f81-9450-bbc71005b7cc", "8f701448-8141-5268-b334-60a5f0d7124f", "d9cfadb3-7f39-5fa4-8be5-4a00213450b8"};

    /** Salle des Transmutations : centre (golem de cristal), au sol ; rayon de l'arène. */
    public static final Vector3d TRANS_CENTER = new Vector3d(0.5, 166, -439.5);
    public static final double TRANS_ARENA_RADIUS = 29.5;
    /** Hauteur des quadrants au-dessus du sol : plus haut (l'hélice), on est hors de l'arène. */
    public static final double TRANS_ARENA_HEIGHT = 6;
    /** Quadrants élémentaires dans l'ordre du tour (le répit passe à un voisin) : nom, volume (tools/alchemist_traps.py,
     * Traps.transmutation : State, Fx), rôle de l'esprit qui en sort, signes (x, z) du quadrant. */
    public static final String[] TRANS_QUADRANTS = {"Earth", "Air", "Ice", "Fire"};
    public static final String[] TRANS_ZONES = {"8d9af366-23f4-55e5-9e6c-f1772896e935", "32c5d148-cdbf-5f1b-93c9-a3394f87040f", "43e4e080-e174-5199-b49b-34705aa1a119", "9960f64e-5188-59be-907a-a94e76cfb047"};
    public static final String[] TRANS_SPIRITS = {"Nakasar_Elemental_Root", "Nakasar_Elemental_Thunder", "Nakasar_Elemental_Frost", "Nakasar_Elemental_Fire"};
    public static final int[][] TRANS_SIGNS = {{1, 1}, {-1, 1}, {-1, -1}, {1, -1}};
    /** Où les esprits de chaque quadrant apparaissent (une ligne par quadrant, dans l'ordre de TRANS_QUADRANTS). */
    public static final Vector3d[][] TRANS_SPIRIT_SPOTS = {
            {new Vector3d(10.5, 167, -432.5), new Vector3d(10.5, 167, -425.5), new Vector3d(19.5, 167, -430.5), new Vector3d(9.5, 167, -420.5)},
            {new Vector3d(-6.5, 167, -429.5), new Vector3d(-13.5, 167, -429.5), new Vector3d(-8.5, 167, -420.5), new Vector3d(-18.5, 167, -430.5)},
            {new Vector3d(-9.5, 167, -446.5), new Vector3d(-9.5, 167, -453.5), new Vector3d(-18.5, 167, -448.5), new Vector3d(-8.5, 167, -458.5)},
            {new Vector3d(7.5, 167, -449.5), new Vector3d(14.5, 167, -449.5), new Vector3d(9.5, 167, -458.5), new Vector3d(19.5, 167, -448.5)}
    };
    /** Sceau du pied de l'hélice (Golem=On à la mort du golem). */
    public static final String TRANS_SEAL = "fefcd8de-8af2-5fed-9e1c-c2ac424fa1b2";

    /** Chimère du laboratoire : centre de la cuve, au niveau du sol de la salle. */
    public static final Vector3d CHIMERA_VAT = new Vector3d(0.5, 184, -439.5);
    /** Rayon de l'arène de la Chimère (intérieur de la tour) et rayon intérieur de la margelle de la cuve. */
    public static final double CHIMERA_ARENA_RADIUS = 29.5;
    public static final double CHIMERA_VAT_RADIUS = 7.5;
    /** Bassins d'acide secondaires (centre, au sol) et, devant chacun, la case où un zombie remplit son seau. */
    public static final Vector3d[] CHIMERA_BASINS = {
            new Vector3d(21.5, 184, -439.5),
            new Vector3d(15.5, 184, -424.5),
            new Vector3d(-14.5, 184, -424.5),
            new Vector3d(-14.5, 184, -454.5)
    };
    public static final Vector3d[] CHIMERA_FILLS = {
            new Vector3d(17.5, 184, -439.5),
            new Vector3d(12.5, 184, -427.5),
            new Vector3d(-11.5, 184, -427.5),
            new Vector3d(-11.5, 184, -451.5)
    };
    /** Volumes (tools/alchemist_traps.py, Traps.chimera) : sceau de la porte nord (Chimera=On), acide de la cuve (Cast=On). */
    public static final String CHIMERA_SEAL = "ebf90f00-a380-54f6-8309-d361a492b8ee";
    public static final String CHIMERA_ACID = "72e78f01-8a21-5fd0-9ad7-435fd0d949e4";

    /** Alchimiste : centre de l'athanor, au sol de sa chambre (il s'y enferme au Grand Œuvre). */
    public static final Vector3d ALCHEMIST_CENTER = new Vector3d(0.5, 244, -439.5);
    /** Rayon de la terrasse de l'Observatoire. */
    public static final double ALCHEMIST_DECK_RADIUS = 45.5;
    /** Antichambre (hors de l'arène) : secteur en degrés (atan2(dz, dx), comme tools/alchemist_tower.py) au-delà du rayon. */
    public static final double[] ALCHEMIST_ANTECHAMBER_ARC = {200, 275};
    public static final double ALCHEMIST_ANTECHAMBER_RADIUS = 22;
    /** Bureau (hors de l'arène) : au-delà de cette coordonnée z du monde. */
    public static final double ALCHEMIST_STUDY_Z = -414;
    /** Pans du rebord qui s'effondrent au Grand Œuvre : secteurs en degrés, entre deux rayons. */
    public static final double[][] ALCHEMIST_COLLAPSE_ARCS = {{282, 322}, {346, 362}, {18, 52}};
    public static final double[] ALCHEMIST_COLLAPSE_RADII = {34.5, 41.4};
    /** Cases libres autour de l'athanor où il ressort. */
    public static final Vector3d[] ALCHEMIST_EXITS = {
            new Vector3d(7.5, 244, -439.5),
            new Vector3d(4.5, 244, -434.5),
            new Vector3d(0.5, 244, -432.5),
            new Vector3d(-4.5, 244, -435.5),
            new Vector3d(-6.5, 244, -439.5),
            new Vector3d(-4.5, 244, -443.5),
            new Vector3d(0.5, 244, -446.5),
            new Vector3d(4.5, 244, -444.5)
    };
    /** Piliers élémentaires de la Convergence (feu, givre, foudre, racines), au sol. */
    public static final Vector3d[] ALCHEMIST_PILLARS = {
            new Vector3d(16.5, 244, -433.5),
            new Vector3d(-14.5, 244, -431.5),
            new Vector3d(7.5, 244, -454.5),
            new Vector3d(16.5, 244, -445.5)
    };
    /** Points sûrs du bord intérieur où revient qui tombe d'un pan effondré. */
    public static final Vector3d[] ALCHEMIST_SAFE = {
            new Vector3d(28.5, 244, -439.5),
            new Vector3d(27.5, 244, -432.5),
            new Vector3d(24.5, 244, -425.5),
            new Vector3d(20.5, 244, -419.5),
            new Vector3d(-19.5, 244, -419.5),
            new Vector3d(-23.5, 244, -425.5),
            new Vector3d(-26.5, 244, -432.5),
            new Vector3d(-27.5, 244, -439.5),
            new Vector3d(-26.5, 244, -446.5),
            new Vector3d(7.5, 244, -466.5),
            new Vector3d(14.5, 244, -463.5),
            new Vector3d(20.5, 244, -459.5),
            new Vector3d(24.5, 244, -453.5),
            new Vector3d(27.5, 244, -446.5)
    };
    /** Volumes (tools/alchemist_traps.py, Traps.alchemist) : sceau du bureau (Alchemist=On), levier du mode difficile
     * (lu : Hard ; posé : Locked), remise à zéro (Reset=On), titres des phases (Cast=On), pans (Collapse=On), fioles de
     * soin (Pack=On, une par case de {@link #ALCHEMIST_HEALS}). */
    public static final String ALCHEMIST_SEAL = "11be98a7-c0d1-5d35-8504-167199e3a691";
    public static final String ALCHEMIST_LEVER = "f5885123-832d-59a5-a0cb-8b8cc3579904";
    public static final String ALCHEMIST_ARENA = "bf45f277-6bf0-5c21-8251-b365d4b829b8";
    public static final String ALCHEMIST_PHASE_2 = "22a699ed-6eb2-5c24-adcd-4616ece53eb2";
    public static final String ALCHEMIST_PHASE_3 = "2d3238e3-4c91-5fb4-bd07-35ba570415d6";
    public static final String[] ALCHEMIST_COLLAPSE = {"343d6b06-7fbd-5bac-924f-16ecc475defa", "012e652b-4b46-5ea3-b941-9ac66f64a26b", "a9c4b840-6f2e-5227-9b34-3059ec1996c6"};
    public static final String[] ALCHEMIST_HEAL = {"91aa9d85-efd6-57af-934e-353a85369349", "24015491-87d0-5ff0-ba66-dd2f1951e8fa", "caaa3ecc-e4c8-5e8f-b834-dd53b6db9d96", "7e703455-fde9-5d75-857d-c5b09cadd35c", "8529c35d-751c-5723-b783-51cd3a93dd3b", "85ce8128-39c6-5250-9707-4ef4d1f2b8c5"};
    public static final Vector3d[] ALCHEMIST_HEALS = {
            new Vector3d(26.5, 244, -439.5),
            new Vector3d(18.5, 244, -421.5),
            new Vector3d(-16.5, 244, -419.5),
            new Vector3d(-24.5, 244, -432.5),
            new Vector3d(13.5, 244, -462.5),
            new Vector3d(21.5, 244, -454.5)
    };

    /** Cour : les gardiens d'airain à abattre, et le volume des portes de la tour (tools/alchemist_traps.py,
     * Traps.court) qui tombent quand ils le sont tous (Guardians=On). */
    public static final int COURT_GUARDIANS = 4;
    public static final String COURT_DOOR = "fc473f7e-7642-5fb7-9bcb-908678463f56";

    /** Barrières des arènes (tools/alchemist_traps.py, Traps.arena_gate ; Gate=Close / Gate=Open, tower.ArenaGate). */
    public static final String CODEX_GATE = "f73442dd-e02a-55cc-84ab-10d60eea593c";
    public static final String CHIMERA_GATE = "5e7476ec-d34c-59ad-87c0-ee78dbf21849";
    public static final String ALCHEMIST_GATE = "d8542a1b-5d14-5e36-aaaa-d2ae0e1fcadc";

    private TowerLayout() {
    }
}
