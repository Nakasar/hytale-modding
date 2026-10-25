package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.builtin.instances.config.InstanceEntityConfig;
import com.hypixel.hytale.builtin.instances.config.InstanceWorldConfig;
import com.hypixel.hytale.builtin.instances.config.WorldReturnPoint;
import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import org.joml.Vector3d;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Sortir de l'Observatoire ramène là où l'on y est entré (Kevin, 25 octobre 2026). Le point de retour vanilla d'un
 * portail posé ({@code TeleportInstance}, {@code OriginSource} Block) se calcule depuis la boîte du bloc touché et
 * pouvait tomber dans le terrain. Ici :
 * <ul>
 *   <li>un joueur qui quitte un monde hors instance y laisse sa position (celle du portail franchi), décalée vers une
 *   place libre hors du portail ({@link #stepOut}) pour ne pas y repartir aussitôt ;</li>
 *   <li>à son arrivée dans un Observatoire, si son point de retour vise ce même monde, il est remplacé par cette
 *   position (le moteur l'a posé juste avant, à l'ajout du joueur au monde).</li>
 * </ul>
 * Le retour d'une fractale vers l'Observatoire n'est pas touché : ce point vise l'Observatoire, pas le monde.
 */
public final class ObservatoryReturnSystem extends RefSystem<EntityStore> {

    /** Recul (blocs) depuis la position d'entrée, à l'opposé du regard : hors du voile du portail. */
    static final double BACK_OFF = 1.5;
    /** Second essai, plus loin, si aucune place n'est libre à {@link #BACK_OFF}. */
    static final double FAR_OFF = 2.5;
    /** Blocs de portail à ne pas toucher en réapparaissant (Portail des Brumes et ses blocs de remplissage). */
    private static final String PORTAL_PREFIX = "Nakasar_Fractal_Mists_Portal";

    private record Left(UUID world, Transform at) {
    }

    private static final Map<UUID, Left> LEFT = new ConcurrentHashMap<>();

    @Override
    public Query<EntityStore> getQuery() {
        return PlayerRef.getComponentType();
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        if (world == null || player == null || !FractalCatalog.isObservatory(world)) {
            return;
        }
        Left left = LEFT.get(player.getUuid());
        InstanceEntityConfig config = store.getComponent(ref, InstanceEntityConfig.getComponentType());
        WorldReturnPoint back = config == null ? null : config.getReturnPoint();
        if (left != null && back != null && left.world().equals(back.getWorld())) {
            // Copie : le moteur peut avoir posé le point de retour commun de l'instance (partagé par tout le groupe).
            WorldReturnPoint own = back.clone();
            own.setReturnPoint(new Transform(left.at()));
            config.setReturnPoint(own);
        }
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
        if (world == null || player == null || transform == null || InstanceWorldConfig.get(world.getWorldConfig()) != null) {
            return;
        }
        float yaw = transform.getRotation().yaw();
        LEFT.put(player.getUuid(), new Left(world.getWorldConfig().getUuid(),
                stepOut(world.getChunkStore(), transform.getPosition(), yaw)));
    }

    /**
     * Où réapparaître : à {@value #BACK_OFF} puis {@value #FAR_OFF} blocs de la position d'entrée, d'abord à l'opposé
     * du regard (on entre en général face au portail), puis devant, puis sur les côtés ; la première place libre (pieds
     * et tête hors des blocs pleins et hors du portail) l'emporte, le joueur tourné dos au portail. Sans place libre, la
     * position d'entrée reculée.
     */
    static Transform stepOut(ChunkStore chunks, Vector3d entry, float yaw) {
        // Le regard pointe vers -Z à yaw 0 (rotation Y standard) : reculer, c'est aller vers +sin, +cos.
        double bx = Math.sin(yaw), bz = Math.cos(yaw);
        double[][] dirs = {{bx, bz}, {-bx, -bz}, {bz, -bx}, {-bz, bx}};
        for (double distance : new double[]{BACK_OFF, FAR_OFF}) {
            for (double[] d : dirs) {
                Vector3d at = new Vector3d(entry).add(d[0] * distance, 0, d[1] * distance);
                if (free(chunks, at)) {
                    // Dos au portail : regarder dans le sens du pas de côté (yaw de la direction (dx, dz) = atan2(-dx, -dz)).
                    return new Transform(at, new Rotation3f(0f, (float) Math.atan2(-d[0], -d[1]), 0f));
                }
            }
        }
        return new Transform(new Vector3d(entry).add(bx * BACK_OFF, 0, bz * BACK_OFF), new Rotation3f(0f, yaw, 0f));
    }

    private static boolean free(ChunkStore chunks, Vector3d at) {
        int x = (int) Math.floor(at.x()), y = (int) Math.floor(at.y()), z = (int) Math.floor(at.z());
        for (int h = 0; h < 2; h++) {
            String name = WorldBlocks.name(chunks, x, y + h, z);
            if (WorldBlocks.solid(chunks, x, y + h, z) || (name != null && name.startsWith(PORTAL_PREFIX))) {
                return false;
            }
        }
        return true;
    }

    public static void clearAll() {
        LEFT.clear();
    }
}
