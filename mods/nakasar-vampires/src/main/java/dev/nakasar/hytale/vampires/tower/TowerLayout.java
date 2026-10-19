package dev.nakasar.hytale.vampires.tower;

import org.joml.Vector3d;

/** Positions de la Tour de l'Alchimiste. Généré par tools/generate_alchemist_tower.py : ne pas modifier à la main. */
public final class TowerLayout {

    /** Première couche d'air au-dessus du sol des îles. */
    public static final double GROUND_Y = 100;
    /** Point d'apparition, sur le parvis d'arrivée. */
    public static final Vector3d ARRIVAL = new Vector3d(0.5, 100, 0.5);
    /** Points de contrôle, dans l'ordre du parcours : ruines du premier laboratoire, bibliothèque, laboratoire, Escalier des vents, antichambre. */
    public static final Vector3d[] CHECKPOINTS = {
            new Vector3d(8.5, 100, -215.5),
            new Vector3d(16.5, 136, -423.5),
            new Vector3d(22.5, 184, -455.5),
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

    private TowerLayout() {
    }
}
