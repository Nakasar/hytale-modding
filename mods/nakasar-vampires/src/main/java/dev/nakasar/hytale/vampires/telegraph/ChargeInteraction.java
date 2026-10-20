package dev.nakasar.hytale.vampires.telegraph;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.arena.BarnPosts;
import dev.nakasar.hytale.vampires.arena.WorldBlocks;
import dev.nakasar.hytale.vampires.elite.EliteStun;
import org.joml.Vector3d;

import java.util.HashSet;
import java.util.Set;

/**
 * {@code "Type": "Nakasar_Charge"} : charge annoncée de l'Abomination (Kevin, 20 octobre 2026). Une ligne rouge de
 * {@code Length} × {@code Width} blocs se trace de l'élite vers sa cible pendant {@code Seconds} secondes (elle baisse
 * la tête, la chaîne JSON la fige), puis elle fonce tout droit à {@code Speed} blocs par seconde jusqu'au bout de la
 * ligne. Les joueurs sur son passage prennent {@code Damage} dégâts et sont projetés sur le côté.
 *
 * <p>Si elle percute un mur ou un poteau, elle est étourdie {@code StunSeconds} secondes ({@code StunEffect} : dégâts
 * subis +50 %, son IA est gelée) ; un poteau de bois se fend, puis cède au second choc ({@link BarnPosts}). Pendant la
 * course, son IA est gelée et le Java la déplace ; un vide devant elle l'arrête sans l'étourdir.
 */
public class ChargeInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Charge";

    public static final BuilderCodec<ChargeInteraction> CODEC = BuilderCodec
            .builder(ChargeInteraction.class, ChargeInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Charge annoncee par une ligne rouge ; etourdit l'elite si elle percute un mur.")
            .append(new KeyedCodec<>("Length", Codec.FLOAT), (i, v) -> i.length = v, i -> i.length).add()
            .append(new KeyedCodec<>("Width", Codec.FLOAT), (i, v) -> i.width = v, i -> i.width).add()
            .append(new KeyedCodec<>("Seconds", Codec.FLOAT), (i, v) -> i.seconds = v, i -> i.seconds).add()
            .append(new KeyedCodec<>("Speed", Codec.FLOAT), (i, v) -> i.speed = v, i -> i.speed).add()
            .append(new KeyedCodec<>("Damage", Codec.FLOAT), (i, v) -> i.damage = v, i -> i.damage).add()
            .append(new KeyedCodec<>("Knockback", Codec.FLOAT), (i, v) -> i.knockback = v, i -> i.knockback).add()
            .append(new KeyedCodec<>("StunSeconds", Codec.FLOAT), (i, v) -> i.stunSeconds = v, i -> i.stunSeconds).add()
            .append(new KeyedCodec<>("StunEffect", Codec.STRING), (i, v) -> i.stunEffect = v, i -> i.stunEffect).add()
            .append(new KeyedCodec<>("ImpactSound", Codec.STRING), (i, v) -> i.impactSound = v, i -> i.impactSound).add()
            .build();

    /** Hauteur de l'Abomination testée contre les murs (blocs au-dessus des pieds). */
    private static final double BODY_HEIGHT = 3.2;
    /** Demi-largeur du corps et distance du front au centre (blocs). */
    private static final double HALF_WIDTH = 0.7;
    private static final double FRONT = 1.0;
    /** Plus grand pas de la course entre deux tests de mur et de joueurs (blocs). */
    private static final double MAX_STEP = 0.5;
    private static final String TRAIL_PARTICLE = "Stick_Slam_Ground_Large";

    protected float length = 12f;
    protected float width = 2.4f;
    protected float seconds = 1.5f;
    protected float speed = 16f;
    protected float damage = 40f;
    protected float knockback = 9f;
    protected float stunSeconds = 4f;
    protected String stunEffect = "Nakasar_Elite_Stunned";
    protected String impactSound = "SFX_Goblin_Mace_Club_Slam_Impact";

    public ChargeInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        Vector3d self = buffer == null ? null : Telegraphs.position(buffer, caster);
        Vector3d target = self == null ? null : Telegraphs.position(buffer, TelegraphInteraction.target(caster, context, buffer));
        if (self == null || target == null || Telegraphs.horizontal(self, target) < 0.5) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        double facing = Telegraphs.angle(self, target);
        long now = System.nanoTime();
        TelegraphSystem.start(buffer.getExternalData().getWorld(),
                new Run(this, caster, new Telegraphs.Strip(new Vector3d(self), facing, length, width, now, seconds), facing));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    private static final class Run implements TelegraphSystem.Task {
        private final ChargeInteraction config;
        private final Ref<EntityStore> caster;
        private final Telegraphs.Strip strip;
        private final double dx;
        private final double dz;
        private final float yaw;
        private final Set<Ref<EntityStore>> struck = new HashSet<>();
        private double travelled;
        private long last = -1;
        private boolean charging;

        Run(ChargeInteraction config, Ref<EntityStore> caster, Telegraphs.Strip strip, double facing) {
            this.config = config;
            this.caster = caster;
            this.strip = strip;
            this.dx = Math.cos(facing);
            this.dz = Math.sin(facing);
            this.yaw = (float) Math.atan2(-dx, -dz);
        }

        @Override
        public boolean step(World world, Store<EntityStore> store, long now) {
            Vector3d at = Telegraphs.position(store, caster);
            if (at == null) {
                return true;
            }
            if (!charging) {
                if (!strip.step(store, now)) {
                    return false;
                }
                charging = true;
                last = now;
                store.ensureAndGetComponent(caster, Frozen.getComponentType());
                Telegraphs.sound(store, config.impactSound, at);
                return false;
            }
            double move = Math.min(config.speed * (now - last) / 1e9, config.length - travelled);
            last = now;
            ChunkStore chunks = world.getChunkStore();
            // Par petits pas : un tick long ne doit faire traverser ni mur, ni poteau, ni joueur.
            int steps = Math.max(1, (int) Math.ceil(move / MAX_STEP));
            Vector3d current = at;
            for (int i = 0; i < steps; i++) {
                double step = move / steps;
                Vector3d next = new Vector3d(current.x() + dx * step, strip.origin().y(), current.z() + dz * step);
                int[] wall = wallAhead(chunks, next);
                if (wall != null) {
                    moveTo(store, current);
                    stop(world, store, current, wall);
                    return true;
                }
                if (!WorldBlocks.solid(chunks, (int) Math.floor(next.x()), (int) Math.floor(next.y() - 0.5), (int) Math.floor(next.z()))
                        && !WorldBlocks.solid(chunks, (int) Math.floor(next.x()), (int) Math.floor(next.y() - 1.5), (int) Math.floor(next.z()))) {
                    moveTo(store, current);
                    end(store);   // bord d'un vide : elle s'arrête net
                    return true;
                }
                travelled += step;
                trample(world, store, next);
                current = next;
            }
            moveTo(store, current);
            if (((int) (travelled * 2)) % 3 == 0) {
                Telegraphs.particle(store, TRAIL_PARTICLE, new Vector3d(current).add(0, 0.1, 0), 0.5f);
            }
            if (travelled >= config.length - 1e-3) {
                end(store);
                return true;
            }
            return false;
        }

        @Override
        public void abort(World world, Store<EntityStore> store) {
            // Tâche interrompue (exception) : l'élite ne doit jamais rester figée.
            if (charging) {
                end(store);
            }
        }

        private void moveTo(Store<EntityStore> store, Vector3d at) {
            store.putComponent(caster, Teleport.getComponentType(), new Teleport(at, new Rotation3f(0f, yaw, 0f)));
        }

        /** Premier bloc plein devant le corps (front, côtés, de la cheville au haut du corps), ou null. */
        private int[] wallAhead(ChunkStore chunks, Vector3d at) {
            for (double h = 0.5; h <= BODY_HEIGHT; h += 1.0) {
                for (double side : new double[]{0, -HALF_WIDTH, HALF_WIDTH}) {
                    int x = (int) Math.floor(at.x() + dx * FRONT - dz * side);
                    int y = (int) Math.floor(at.y() + h);
                    int z = (int) Math.floor(at.z() + dz * FRONT + dx * side);
                    if (WorldBlocks.solid(chunks, x, y, z)) {
                        return new int[]{x, y, z};
                    }
                }
            }
            return null;
        }

        private void trample(World world, Store<EntityStore> store, Vector3d at) {
            for (PlayerRef player : world.getPlayerRefs()) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d p = Telegraphs.position(store, ref);
                if (p == null || struck.contains(ref) || Telegraphs.horizontal(p, at) > config.width / 2 + 0.6
                        || p.y() - at.y() < -1 || p.y() - at.y() > 3) {
                    continue;
                }
                struck.add(ref);
                DamageCause cause = DamageCause.getAssetMap().getAsset("Physical");
                if (cause != null && config.damage > 0f) {
                    DamageSystems.executeDamage(ref, store, new Damage(new Damage.EntitySource(caster), cause, config.damage));
                }
                Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
                if (velocity != null && Telegraphs.position(store, ref) != null) {
                    // Projeté sur le côté où il se trouve, et un peu vers l'avant.
                    double side = Math.signum(-(p.x() - at.x()) * dz + (p.z() - at.z()) * dx);
                    side = side == 0 ? 1 : side;
                    velocity.addInstruction(new Vector3d((-dz * side + dx * 0.5) * config.knockback, 6,
                            (dx * side + dz * 0.5) * config.knockback), null, ChangeVelocityType.Set);
                }
            }
        }

        private void stop(World world, Store<EntityStore> store, Vector3d at, int[] wall) {
            BarnPosts.hit(world, store, wall[0], wall[1], wall[2]);
            Telegraphs.sound(store, config.impactSound, at);
            Telegraphs.particle(store, TRAIL_PARTICLE, new Vector3d(at).add(dx * FRONT, 0.1, dz * FRONT), 1.0f);
            // Le gel de la course devient l'étourdissement (relâché par EliteStun).
            EliteStun.stun(world, store, caster, config.stunSeconds, config.stunEffect);
        }

        private void end(Store<EntityStore> store) {
            if (!EliteStun.isStunned(caster)) {
                store.tryRemoveComponent(caster, Frozen.getComponentType());
            }
        }
    }
}
