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
            new Vector3d(-69.5, 100, -312.5),
            new Vector3d(16.5, 136, -463.5),
            new Vector3d(22.5, 184, -495.5),
            new Vector3d(1.5, 184, -516.5),
            new Vector3d(-8.5, 244, -511.5)
    };

    private TowerLayout() {
    }
}
