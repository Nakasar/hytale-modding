package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.BlockMaterial;
import com.hypixel.hytale.protocol.ClientCameraView;
import com.hypixel.hytale.protocol.Direction;
import com.hypixel.hytale.protocol.Position;
import com.hypixel.hytale.protocol.PositionType;
import com.hypixel.hytale.protocol.RotationType;
import com.hypixel.hytale.protocol.ServerCameraSettings;
import com.hypixel.hytale.protocol.packets.camera.SetServerCamera;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import org.joml.Vector3d;

/**
 * Caméra de dialogue : pendant la conversation, la caméra du client quitte la vue du joueur et se pose derrière son
 * épaule, cadrant le joueur et le PNJ (paquet serveur {@link SetServerCamera}, celui de la commande vanilla
 * {@code /camera topdown}). Elle revient à la vue normale ({@code SetServerCamera(Custom, false, null)}, comme
 * {@code /camera reset}) quand la fenêtre se ferme, quelle que soit la façon de la fermer.
 *
 * <p>Désactivable par joueur ({@code /village camera}, drapeau {@value #OFF_FLAG}). Placement : derrière l'épaule
 * droite, sinon la gauche, sinon plus près ; une position dont le bloc ou la ligne de vue vers la cible sont pleins est
 * écartée (pas de caméra dans un mur). Faute de place, pas de caméra.
 */
public final class DialogueCamera {

    /** Drapeau du joueur qui a coupé la caméra de dialogue. */
    public static final String OFF_FLAG = "option.dialogueCameraOff";

    /** Recul derrière le joueur, décalage d'épaule et hauteur au-dessus de ses pieds (blocs), du plus large au plus serré. */
    private static final double[][] PLACEMENTS = {
            {3.2, 2.1, 2.3},
            {3.2, -2.1, 2.3},
            {2.4, 1.5, 2.0},
            {2.4, -1.5, 2.0},
    };
    /** Hauteur du regard visé au-dessus du sol, entre les deux têtes. */
    private static final double LOOK_HEIGHT = 1.35;
    /** Part du chemin joueur → PNJ où la caméra vise : un peu côté PNJ, les deux personnages restent dans le cadre. */
    private static final double LOOK_TOWARD_NPC = 0.55;
    /** Au-delà, le PNJ est trop loin pour un cadrage à deux : pas de caméra. */
    private static final double MAX_DISTANCE = 9.0;
    private static final float LERP = 0.12f;

    private DialogueCamera() {
    }

    public static boolean enabled(Store<EntityStore> store, Ref<EntityStore> player) {
        PeuplesPlayer state = PeuplesPlayer.get(store, player);
        return state == null || !state.hasFlag(OFF_FLAG);
    }

    /** Pose la caméra de dialogue entre `player` et `npc`. Vrai si elle a été posée (à rendre avec {@link #reset}). */
    public static boolean frame(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        if (npc == null || !npc.isValid() || !player.isValid() || !enabled(store, player)) {
            return false;
        }
        TransformComponent pt = store.getComponent(player, TransformComponent.getComponentType());
        TransformComponent nt = store.getComponent(npc, TransformComponent.getComponentType());
        if (pt == null || nt == null) {
            return false;
        }
        Vector3d p = pt.getPosition();
        Vector3d n = nt.getPosition();
        double dx = n.x() - p.x();
        double dz = n.z() - p.z();
        double flat = Math.sqrt(dx * dx + dz * dz);
        if (flat < 0.3 || flat > MAX_DISTANCE) {
            return false;
        }
        double fx = dx / flat;
        double fz = dz / flat;
        // Visée : entre les deux têtes, plus près du PNJ.
        double tx = p.x() + dx * LOOK_TOWARD_NPC;
        double ty = Math.max(p.y(), n.y()) + LOOK_HEIGHT;
        double tz = p.z() + dz * LOOK_TOWARD_NPC;
        ChunkStore chunks = world.getChunkStore();
        for (double[] place : PLACEMENTS) {
            double back = place[0] + Math.max(0, flat - 3) * 0.35;
            // Côté : perpendiculaire à la direction joueur → PNJ.
            double cx = p.x() - fx * back - fz * place[1];
            double cy = p.y() + place[2];
            double cz = p.z() - fz * back + fx * place[1];
            if (!clear(chunks, cx, cy, cz, tx, ty, tz)) {
                continue;
            }
            send(playerRef, cx, cy, cz, tx, ty, tz);
            return true;
        }
        return false;
    }

    /** Rend au joueur sa caméra normale. */
    public static void reset(PlayerRef playerRef) {
        if (playerRef != null && playerRef.getPacketHandler() != null) {
            playerRef.getPacketHandler().writeNoCache(new SetServerCamera(ClientCameraView.Custom, false, null));
        }
    }

    private static void send(PlayerRef playerRef, double cx, double cy, double cz, double tx, double ty, double tz) {
        double vx = tx - cx;
        double vy = ty - cy;
        double vz = tz - cz;
        double h = Math.sqrt(vx * vx + vz * vz);
        // Convention du jeu : lacet atan2(-dx, -dz) pour regarder vers (dx, dz) ; tangage négatif vers le bas
        // (/camera topdown regarde à -π/2).
        float yaw = (float) Math.atan2(-vx, -vz);
        float pitch = (float) Math.atan2(vy, h);
        ServerCameraSettings s = new ServerCameraSettings();
        s.positionLerpSpeed = LERP;
        s.rotationLerpSpeed = LERP;
        s.isFirstPerson = false;
        s.displayCursor = true;
        s.displayReticle = false;
        s.positionType = PositionType.Custom;
        s.position = new Position(cx, cy, cz);
        s.rotationType = RotationType.Custom;
        s.rotation = new Direction(yaw, pitch, 0f);
        playerRef.getPacketHandler().writeNoCache(new SetServerCamera(ClientCameraView.Custom, true, s));
    }

    /** Vrai si le bloc de la caméra et la ligne de vue jusqu'à la cible ne traversent aucun bloc plein chargé. */
    private static boolean clear(ChunkStore chunks, double cx, double cy, double cz, double tx, double ty, double tz) {
        double len = Math.sqrt((tx - cx) * (tx - cx) + (ty - cy) * (ty - cy) + (tz - cz) * (tz - cz));
        int steps = Math.max(1, (int) Math.ceil(len / 0.25));
        for (int i = 0; i <= steps; i++) {
            double t = (double) i / steps;
            if (solid(chunks, cx + (tx - cx) * t, cy + (ty - cy) * t, cz + (tz - cz) * t)) {
                return false;
            }
        }
        return true;
    }

    private static boolean solid(ChunkStore chunks, double x, double y, double z) {
        int bx = (int) Math.floor(x);
        int by = (int) Math.floor(y);
        int bz = (int) Math.floor(z);
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(bx, by, bz);
        if (ref == null || !ref.isValid()) {
            return true; // section non chargée : on ne pose pas la caméra à l'aveugle
        }
        BlockSection section = chunks.getStore().getComponent(ref, BlockSection.getComponentType());
        if (section == null) {
            return true;
        }
        int id = section.get(bx, by, bz);
        if (id == BlockType.EMPTY_ID) {
            return false;
        }
        BlockType type = BlockType.getAssetMap().getAsset(id);
        return type != null && type.getMaterial() == BlockMaterial.Solid;
    }
}
