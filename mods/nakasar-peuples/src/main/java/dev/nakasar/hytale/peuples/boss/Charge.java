package dev.nakasar.hytale.peuples.boss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Blocks;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Set;

/**
 * Une charge après sa ligne rouge, comme {@code Nakasar_Fractal_Charge} (mod des fractales) : le PNJ, figé
 * ({@link Frozen}), est déplacé par le Java tout droit le long de la ligne annoncée, par petits pas. Il suit le relief
 * (un bloc en montée, deux en descente) et s'arrête net sur un mur ou au bord d'un vide. Les joueurs qu'il traverse,
 * dans la zone annoncée seulement (règle n° 3), prennent les dégâts une fois chacun et sont projetés sur le côté.
 * À appeler à chaque image (ou au moins tous les dixièmes de seconde) sur le fil du monde.
 */
public final class Charge {

    /** Fin de la course. */
    public enum Result { RUNNING, DONE, WALL }

    /** Plus grand pas entre deux tests (blocs) : un tick long ne doit traverser ni mur ni joueur. */
    private static final double STEP = 0.5;
    private static final String TRAIL_PARTICLE = "Stick_Slam_Ground_Large";

    private final Ref<EntityStore> src;
    private final Telegraphs.Strip strip;
    private final double speed;
    private final float damage;
    private final double knockback;
    private final double dx;
    private final double dz;
    private final float yaw;
    private final Set<Ref<EntityStore>> struck = Collections.newSetFromMap(new IdentityHashMap<>());
    private double travelled;
    private double y;
    private long last;

    /** Lance la course de `src` le long de `strip` (la ligne déjà annoncée) ; `src` est figé jusqu'à {@link #release}. */
    public Charge(Store<EntityStore> store, Ref<EntityStore> src, Telegraphs.Strip strip, double speed, float damage,
                  double knockback, long now) {
        this.src = src;
        this.strip = strip;
        this.speed = speed;
        this.damage = damage;
        this.knockback = knockback;
        this.dx = Math.cos(strip.facing());
        this.dz = Math.sin(strip.facing());
        this.yaw = (float) Math.atan2(-dx, -dz);
        this.y = strip.origin().y();
        this.last = now;
        store.ensureAndGetComponent(src, Frozen.getComponentType());
    }

    public Ref<EntityStore> source() {
        return src;
    }

    /** Un pas de la course. {@link Result#WALL} : arrêté par un mur ou un vide. */
    public Result step(World world, Store<EntityStore> store, long now) {
        Vector3d at = src.isValid() ? Requests.position(store, src) : null;
        if (at == null) {
            return Result.DONE;
        }
        double move = Math.min(speed * (now - last) / 1e9, strip.length - travelled);
        last = now;
        ChunkStore chunks = world.getChunkStore();
        int steps = Math.max(1, (int) Math.ceil(move / STEP));
        Vector3d current = new Vector3d(at.x(), y, at.z());
        Result result = Result.RUNNING;
        for (int i = 0; i < steps; i++) {
            double step = move / steps;
            double nx = current.x() + dx * step;
            double nz = current.z() + dz * step;
            Double ny = groundAhead(chunks, nx, y, nz);
            if (ny == null) {
                result = Result.WALL;
                break;
            }
            y = ny;
            current = new Vector3d(nx, ny, nz);
            travelled += step;
            trample(world, store, current);
        }
        store.putComponent(src, Teleport.getComponentType(), new Teleport(current, new Rotation3f(0f, yaw, 0f)));
        if (((int) (travelled * 2)) % 3 == 0) {
            Telegraphs.particle(store, TRAIL_PARTICLE, new Vector3d(current).add(0, 0.1, 0), 0.5f);
        }
        if (result == Result.RUNNING && travelled >= strip.length - 1e-3) {
            result = Result.DONE;
        }
        return result;
    }

    /** Le PNJ n'est plus figé (fin de course, ou d'étourdissement). */
    public void release(Store<EntityStore> store) {
        if (src.isValid()) {
            store.tryRemoveComponent(src, Frozen.getComponentType());
        }
    }

    /** Hauteur des pieds en (x, z) en partant de `y` : un bloc de montée, deux de descente ; null (mur, vide). */
    private static Double groundAhead(ChunkStore chunks, double x, double y, double z) {
        int bx = (int) Math.floor(x);
        int bz = (int) Math.floor(z);
        int by = (int) Math.floor(y);
        for (int dy : new int[] {0, 1, -1, -2}) {
            int feet = by + dy;
            if (Blocks.solid(chunks, bx, feet - 1, bz) && !Blocks.solid(chunks, bx, feet, bz) && !Blocks.solid(chunks, bx, feet + 1, bz)) {
                return (double) feet;
            }
        }
        return null;
    }

    private void trample(World world, Store<EntityStore> store, Vector3d at) {
        DamageCause cause = DamageCause.getAssetMap().getAsset("Physical");
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d p = ref == null || !ref.isValid() ? null : Requests.position(store, ref);
            if (p == null || struck.contains(ref) || !strip.contains(p)
                    || Telegraphs.horizontal(p, at) > strip.width / 2 + Telegraphs.BODY
                    || p.y() - at.y() < -1 || p.y() - at.y() > 3) {
                continue;
            }
            struck.add(ref);
            if (cause != null && damage > 0f) {
                DamageSystems.executeDamage(ref, store, new Damage(new Damage.EntitySource(src), cause, damage));
            }
            Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
            if (velocity != null && knockback > 0) {
                // Projeté sur le côté où il se trouve, et un peu vers l'avant.
                double side = Math.signum(-(p.x() - at.x()) * dz + (p.z() - at.z()) * dx);
                side = side == 0 ? 1 : side;
                velocity.addInstruction(new Vector3d((-dz * side + dx * 0.5) * knockback, 6,
                        (dx * side + dz * 0.5) * knockback), null, ChangeVelocityType.Set);
            }
        }
    }
}
