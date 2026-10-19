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

    private TowerLayout() {
    }
}
