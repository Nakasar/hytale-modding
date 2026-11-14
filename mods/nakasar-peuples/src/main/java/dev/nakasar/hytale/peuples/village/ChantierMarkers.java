package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.math.matrix.Matrix4dUtil;
import com.hypixel.hytale.protocol.DebugShape;
import com.hypixel.hytale.protocol.packets.player.ClearDebugShapes;
import com.hypixel.hytale.protocol.packets.player.DisplayDebug;
import com.hypixel.hytale.server.core.modules.debug.DebugUtils;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import org.joml.Matrix4d;
import org.joml.Vector3f;

/**
 * Repères en jeu des blocs qui gênent un chantier, montrés au seul joueur qui les demande ({@code /village genes}) : le
 * contour de la parcelle examinée (fil de fer jaune) et un cube rose sur chaque bloc gênant. Ce sont les formes de
 * débogage du moteur ({@link DisplayDebug}, celles de la commande vanilla {@code /debug shape}), envoyées au client du
 * joueur seulement (là où {@link DebugUtils} les envoie à tout le monde) et effacées d'elles-mêmes au bout de
 * {@value #SECONDS} s. Aucun bloc ni entité n'est posé dans le monde.
 */
public final class ChantierMarkers {

    public static final int SECONDS = 60;
    private static final Vector3f OUTLINE = new Vector3f(1f, 0.85f, 0.2f);
    private static final Vector3f BLOCK = new Vector3f(1f, 0.35f, 0.85f);
    /** Cube un peu plus grand que le bloc, pour qu'il se voie par-dessus. */
    private static final double BLOCK_SIZE = 1.06;

    private ChantierMarkers() {
    }

    /** Contour de la parcelle de `b` (à la hauteur `h`) et cubes sur les blocs gênants de `o`. */
    public static void show(PlayerRef player, Village village, VillageLayout.Building b, int h, Chantiers.Obstacles o) {
        int[] r = b.rect();
        double x0 = village.x() + r[0];
        double x1 = village.x() + r[1] + 1;
        double z0 = village.z() + r[2];
        double z1 = village.z() + r[3] + 1;
        double y0 = h + 1;
        double y1 = h + 1 + Chantiers.scanHeight(b);
        Matrix4d outline = new Matrix4d().translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2).scale(x1 - x0, y1 - y0, z1 - z0);
        send(player, outline, OUTLINE, DebugUtils.FLAG_NO_SOLID);
        for (Chantiers.Obstacle obstacle : o.sample()) {
            Matrix4d cube = new Matrix4d().translate(obstacle.x() + 0.5, obstacle.y() + 0.5, obstacle.z() + 0.5).scale(BLOCK_SIZE);
            send(player, cube, BLOCK, DebugUtils.FLAG_NONE);
        }
    }

    /** Efface tous les repères de débogage du joueur. */
    public static void clear(PlayerRef player) {
        player.getPacketHandler().write(new ClearDebugShapes());
    }

    private static void send(PlayerRef player, Matrix4d matrix, Vector3f color, int flags) {
        player.getPacketHandler().write(new DisplayDebug(DebugShape.Cube, Matrix4dUtil.asFloatData(matrix), color, SECONDS,
                (byte) flags, null, DebugUtils.DEFAULT_OPACITY));
    }
}
