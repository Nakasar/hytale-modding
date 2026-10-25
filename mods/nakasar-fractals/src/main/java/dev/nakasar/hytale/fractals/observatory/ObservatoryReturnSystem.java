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
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
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
 *   <li>un joueur qui quitte un monde hors instance y laisse sa position (celle du portail franchi), reculée de
 *   {@value #BACK_OFF} blocs pour ne pas réapparaître dans le portail et y repartir aussitôt ;</li>
 *   <li>à son arrivée dans un Observatoire, si son point de retour vise ce même monde, il est remplacé par cette
 *   position (le moteur l'a posé juste avant, à l'ajout du joueur au monde).</li>
 * </ul>
 * Le retour d'une fractale vers l'Observatoire n'est pas touché : ce point vise l'Observatoire, pas le monde.
 */
public final class ObservatoryReturnSystem extends RefSystem<EntityStore> {

    /** Recul (blocs) depuis la position d'entrée, à l'opposé du regard : hors du voile du portail. */
    static final double BACK_OFF = 1.5;

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
            back.setReturnPoint(new Transform(left.at()));
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
        // Le regard pointe vers -Z à yaw 0 (rotation Y standard) : reculer, c'est aller vers +sin, +cos.
        Vector3d at = new Vector3d(transform.getPosition()).add(Math.sin(yaw) * BACK_OFF, 0, Math.cos(yaw) * BACK_OFF);
        LEFT.put(player.getUuid(), new Left(world.getWorldConfig().getUuid(), new Transform(at, new Rotation3f(0f, yaw, 0f))));
    }

    public static void clearAll() {
        LEFT.clear();
    }
}
