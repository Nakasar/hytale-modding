package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
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
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.prison.CagePlayerInteraction;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;

/**
 * {@code "Type": "Nakasar_Fractal_Telegraph"} : attaque annoncée d'un boss de fractale. Copie de
 * {@code Nakasar_Telegraph} du mod Vampires (pas de bibliothèque commune : un correctif se reporte à la main), sans
 * braseros ni Domination ; les cages remplacent les cellules du Capitaine. Codes de la Tour de l'Alchimiste
 * (Kevin, 20 octobre 2026). Une zone rouge de la taille exacte du coup se remplit au sol pendant {@code Seconds}
 * secondes, puis le coup tombe sur tout ce qui s'y trouve encore (calculé en Java : ce qu'on voit est ce qui touche).
 * L'interaction est instantanée : la chaîne JSON continue aussitôt (pose, animation de préparation de la même durée).
 *
 * <p>Formes ({@code Shape}) :
 * <ul>
 *   <li>{@code Circle} : cercle de {@code Radius} blocs ;</li>
 *   <li>{@code Cone} : cône de {@code Angle} degrés et {@code Radius} blocs, de l'élite vers sa cible ;</li>
 *   <li>{@code Line} : ligne de {@code Length} × {@code Width} blocs, de l'élite vers sa cible ;</li>
 *   <li>{@code Mark} : pas de zone au sol, la cible est marquée ({@code MarkParticle} au-dessus d'elle, qui la suit) ;
 *   le coup la touche où qu'elle soit (il ne s'esquive pas) ;</li>
 *   <li>{@code Column} : pas de zone, seulement {@code MarkParticle} au point visé (point d'arrivée d'un saut).</li>
 * </ul>
 *
 * <p>Centre ({@code Anchor}) : {@code Self} (l'élite), {@code Target} (sa cible, figé au début de l'annonce),
 * {@code Farthest} (vers le joueur le plus éloigné, à {@code OffsetMax} blocs de l'élite), {@code EachPlayer} (une zone
 * sous chaque joueur à moins de {@value #SEARCH_RADIUS} blocs, figée au début de l'annonce). {@code OffsetMin} /
 * {@code OffsetMax} décalent un centre {@code Target} au hasard autour de la cible (point d'arrivée d'un saut).
 *
 * <p>Le coup : {@code Damage} ({@code DamageCause}, défaut {@code Physical}), {@code Knockback} et {@code KnockUp}
 * (projection depuis le centre), {@code EffectId} pendant {@code EffectDuration} s, {@code HitParticle} sur chaque
 * touché, {@code ImpactParticle} / {@code ImpactSound} au centre, {@code Imprison} (cage la plus proche,
 * {@link CagePlayerInteraction#CAGE_BLOCK}, dans {@code CellRadius} blocs, effet {@code EffectId} : cage de
 * l'Archidevin), {@code TeleportCaster} (le boss surgit au centre juste avant le coup), {@code Cover} (un bloc plein
 * entre le centre et la victime la protège), {@code PlayersOnly}. Les alliés du boss ({@link Foes}) ne sont jamais
 * touchés.
 *
 * <p>{@code Delay} : la zone n'apparaît qu'au bout de ce nombre de secondes.
 */
public class TelegraphInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Telegraph";

    public static final BuilderCodec<TelegraphInteraction> CODEC = BuilderCodec
            .builder(TelegraphInteraction.class, TelegraphInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Attaque annoncee : zone rouge au sol puis coup sur ce qui s'y trouve.")
            .append(new KeyedCodec<>("Shape", Codec.STRING), (i, v) -> i.shape = v, i -> i.shape).add()
            .append(new KeyedCodec<>("Anchor", Codec.STRING), (i, v) -> i.anchor = v, i -> i.anchor).add()
            .append(new KeyedCodec<>("Radius", Codec.FLOAT), (i, v) -> i.radius = v, i -> i.radius).add()
            .append(new KeyedCodec<>("Angle", Codec.FLOAT), (i, v) -> i.angle = v, i -> i.angle).add()
            .append(new KeyedCodec<>("Length", Codec.FLOAT), (i, v) -> i.length = v, i -> i.length).add()
            .append(new KeyedCodec<>("Width", Codec.FLOAT), (i, v) -> i.width = v, i -> i.width).add()
            .append(new KeyedCodec<>("Seconds", Codec.FLOAT), (i, v) -> i.seconds = v, i -> i.seconds).add()
            .append(new KeyedCodec<>("Delay", Codec.FLOAT), (i, v) -> i.delay = v, i -> i.delay).add()
            .append(new KeyedCodec<>("OffsetMin", Codec.FLOAT), (i, v) -> i.offsetMin = v, i -> i.offsetMin).add()
            .append(new KeyedCodec<>("OffsetMax", Codec.FLOAT), (i, v) -> i.offsetMax = v, i -> i.offsetMax).add()
            .append(new KeyedCodec<>("Damage", Codec.FLOAT), (i, v) -> i.damage = v, i -> i.damage).add()
            .append(new KeyedCodec<>("DamageCause", Codec.STRING), (i, v) -> i.damageCause = v, i -> i.damageCause).add()
            .append(new KeyedCodec<>("Knockback", Codec.FLOAT), (i, v) -> i.knockback = v, i -> i.knockback).add()
            .append(new KeyedCodec<>("KnockUp", Codec.FLOAT), (i, v) -> i.knockUp = v, i -> i.knockUp).add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId).add()
            .append(new KeyedCodec<>("EffectDuration", Codec.FLOAT), (i, v) -> i.effectDuration = v, i -> i.effectDuration).add()
            .append(new KeyedCodec<>("PlayersOnly", Codec.BOOLEAN), (i, v) -> i.playersOnly = v, i -> i.playersOnly).add()
            .append(new KeyedCodec<>("Cover", Codec.BOOLEAN), (i, v) -> i.cover = v, i -> i.cover).add()
            .append(new KeyedCodec<>("Imprison", Codec.BOOLEAN), (i, v) -> i.imprison = v, i -> i.imprison).add()
            .append(new KeyedCodec<>("CellRadius", Codec.INTEGER), (i, v) -> i.cellRadius = v, i -> i.cellRadius).add()
            .append(new KeyedCodec<>("TeleportCaster", Codec.BOOLEAN), (i, v) -> i.teleportCaster = v, i -> i.teleportCaster).add()
            .append(new KeyedCodec<>("HitParticle", Codec.STRING), (i, v) -> i.hitParticle = v, i -> i.hitParticle).add()
            .append(new KeyedCodec<>("ImpactParticle", Codec.STRING), (i, v) -> i.impactParticle = v, i -> i.impactParticle).add()
            .append(new KeyedCodec<>("ImpactParticleScale", Codec.FLOAT), (i, v) -> i.impactScale = v, i -> i.impactScale).add()
            .append(new KeyedCodec<>("ImpactSound", Codec.STRING), (i, v) -> i.impactSound = v, i -> i.impactSound).add()
            .append(new KeyedCodec<>("MarkParticle", Codec.STRING), (i, v) -> i.markParticle = v, i -> i.markParticle).add()
            .append(new KeyedCodec<>("MarkParticleScale", Codec.FLOAT), (i, v) -> i.markScale = v, i -> i.markScale).add()
            .append(new KeyedCodec<>("MarkInterval", Codec.FLOAT), (i, v) -> i.markInterval = v, i -> i.markInterval).add()
            .append(new KeyedCodec<>("MarkHeight", Codec.FLOAT), (i, v) -> i.markHeight = v, i -> i.markHeight).add()
            .build();

    /** Rayon de recherche du joueur le plus éloigné ({@code Farthest}). */
    private static final int SEARCH_RADIUS = 24;

    protected String shape = "Circle";
    protected String anchor = "Self";
    protected float radius = 3f;
    protected float angle = 90f;
    protected float length = 10f;
    protected float width = 1.2f;
    protected float seconds = 1.2f;
    protected float delay = 0f;
    protected float offsetMin = 0f;
    protected float offsetMax = 0f;
    protected float damage = 0f;
    protected String damageCause = "Physical";
    protected float knockback = 0f;
    protected float knockUp = 0f;
    protected String effectId;
    protected float effectDuration = 3f;
    protected boolean playersOnly = false;
    protected boolean cover = false;
    protected boolean imprison = false;
    protected int cellRadius = 24;
    protected boolean teleportCaster = false;
    protected String hitParticle;
    protected String impactParticle;
    protected float impactScale = 1f;
    protected String impactSound;
    protected String markParticle;
    protected float markScale = 1f;
    protected float markInterval = 0.4f;
    protected float markHeight = 2.6f;

    public TelegraphInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        if (buffer == null || caster == null || !caster.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        Vector3d self = Telegraphs.position(buffer, caster);
        if (self == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        World world = buffer.getExternalData().getWorld();
        ChunkStore chunks = world.getChunkStore();
        Ref<EntityStore> target = target(caster, context, buffer);
        Vector3d targetAt = Telegraphs.position(buffer, target);

        if ("EachPlayer".equals(anchor)) {
            // Une zone sous chaque joueur à portée, figée au début de l'annonce.
            for (PlayerRef player : world.getPlayerRefs()) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d at = Telegraphs.position(buffer, ref);
                if (at != null && Telegraphs.horizontal(at, self) <= SEARCH_RADIUS && Math.abs(at.y() - self.y()) <= 8) {
                    TelegraphSystem.start(world, new Strike(this, caster, ref, new Vector3d(at), 0.0));
                }
            }
            return;
        }
        Vector3d center;
        switch (anchor) {
            case "Target" -> {
                if (targetAt == null) {
                    context.getState().state = InteractionState.Failed;
                    return;
                }
                center = new Vector3d(targetAt);
                if (offsetMax > 0f) {
                    double a = ThreadLocalRandom.current().nextDouble(Math.PI * 2);
                    double d = ThreadLocalRandom.current().nextDouble(offsetMin, Math.max(offsetMin + 0.01, offsetMax));
                    center.add(Math.cos(a) * d, 0, Math.sin(a) * d);
                    center.y = ground(chunks, center, targetAt.y());
                }
            }
            case "Farthest" -> {
                Vector3d far = farthestPlayer(world, buffer, self);
                center = new Vector3d(self);
                if (far != null && Telegraphs.horizontal(far, self) > 0.5) {
                    double d = Math.min(offsetMax, Telegraphs.horizontal(far, self));
                    double a = Telegraphs.angle(self, far);
                    center.add(Math.cos(a) * d, 0, Math.sin(a) * d);
                    center.y = ground(chunks, center, self.y());
                }
            }
            default -> center = new Vector3d(self);
        }
        // Direction des cônes et des lignes : vers la cible au début de l'annonce, sinon droit devant.
        double facing;
        if (targetAt != null && Telegraphs.horizontal(targetAt, self) > 0.3) {
            facing = Telegraphs.angle(self, targetAt);
        } else {
            TransformComponent transform = buffer.getComponent(caster, TransformComponent.getComponentType());
            float yaw = transform == null ? 0f : transform.getRotation().yaw();
            facing = Math.atan2(-Math.cos(yaw), -Math.sin(yaw));
        }
        Strike strike = new Strike(this, caster, target, center, facing);
        TelegraphSystem.start(world, strike);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement : les zones sont des particules envoyées aux joueurs proches.
    }

    /**
     * Annonce lancée depuis le code (pupitre du golem d'essai) : zone {@code shape} ({@code Circle}, {@code Cone} de
     * 90°, {@code Line} de 1,6 bloc de large) de taille {@code size} (rayon, ou longueur de la ligne) centrée sur
     * {@code center} et tournée vers {@code facing}, qui se remplit en {@code seconds} secondes après {@code delay}
     * secondes. Le coup ne fait pas de dégâts : il projette de {@code knockback}, ou envoie dans la cage la plus
     * proche du lanceur si {@code imprison}.
     */
    public static void demo(World world, Ref<EntityStore> caster, Ref<EntityStore> target, Vector3d center, double facing,
                            String shape, float size, float seconds, float delay, float knockback, boolean imprison) {
        demo(world, caster, target, center, facing, shape, size, seconds, delay, knockback, imprison, null, 0f);
    }

    /** Comme {@link #demo(World, Ref, Ref, Vector3d, double, String, float, float, float, float, boolean)}, l'effet {@code effectId} en plus sur qui est touché. */
    public static void demo(World world, Ref<EntityStore> caster, Ref<EntityStore> target, Vector3d center, double facing,
                            String shape, float size, float seconds, float delay, float knockback, boolean imprison,
                            String effectId, float effectDuration) {
        TelegraphInteraction config = new TelegraphInteraction();
        config.effectId = effectId;
        config.effectDuration = effectDuration;
        config.shape = shape;
        config.radius = size;
        config.length = size;
        config.width = 1.6f;
        config.seconds = seconds;
        config.delay = delay;
        config.knockback = knockback;
        config.knockUp = knockback > 0f ? 5f : 0f;
        config.imprison = imprison;
        config.playersOnly = true;
        TelegraphSystem.start(world, new Strike(config, caster, target, center, facing));
    }

    /**
     * Annonce lancée depuis le code (Archidevin, bombes des rampes) : forme {@code shape} remplie en {@code seconds}
     * secondes, réglée par les méthodes ci-dessous, puis {@link #launch}.
     */
    public static TelegraphInteraction spec(String shape, float seconds) {
        TelegraphInteraction config = new TelegraphInteraction();
        config.shape = shape;
        config.seconds = seconds;
        return config;
    }

    public TelegraphInteraction radius(float value) {
        radius = value;
        return this;
    }

    public TelegraphInteraction damage(float value, String cause) {
        damage = value;
        damageCause = cause;
        return this;
    }

    public TelegraphInteraction knockback(float horizontal, float up) {
        knockback = horizontal;
        knockUp = up;
        return this;
    }

    public TelegraphInteraction effect(String id, float duration) {
        effectId = id;
        effectDuration = duration;
        return this;
    }

    public TelegraphInteraction playersOnly() {
        playersOnly = true;
        return this;
    }

    public TelegraphInteraction teleportCaster() {
        teleportCaster = true;
        return this;
    }

    public TelegraphInteraction impact(String particle, String sound) {
        impactParticle = particle;
        impactSound = sound;
        return this;
    }

    public TelegraphInteraction hit(String particle) {
        hitParticle = particle;
        return this;
    }

    public TelegraphInteraction mark(String particle, float scale) {
        markParticle = particle;
        markScale = scale;
        return this;
    }

    /** Lance l'annonce : zone centrée sur {@code center} (Mark : sur {@code target}), tournée vers {@code facing}. */
    public void launch(World world, Ref<EntityStore> caster, Ref<EntityStore> target, Vector3d center, double facing) {
        TelegraphSystem.start(world, new Strike(this, caster, target, new Vector3d(center), facing));
    }

    /** Cible verrouillée de l'élite (sa cible de combat), sinon l'entité fournie par la chaîne. */
    static Ref<EntityStore> target(Ref<EntityStore> caster, InteractionContext context, CommandBuffer<EntityStore> buffer) {
        MarkedEntitySupport marked = buffer.getComponent(caster, MarkedEntitySupport.getComponentType());
        Ref<EntityStore> locked = marked == null ? null : marked.getMarkedEntityRef(MarkedEntitySupport.DEFAULT_TARGET_SLOT);
        if (locked != null && locked.isValid() && !locked.equals(caster)) {
            return locked;
        }
        Ref<EntityStore> chain = context.getTargetEntity();
        return chain != null && chain.isValid() && !chain.equals(caster) ? chain : null;
    }

    /** Hauteur du sol sous `at` (premier bloc plein en descendant depuis 3 blocs au-dessus de `reference`). */
    static double ground(ChunkStore chunks, Vector3d at, double reference) {
        int x = (int) Math.floor(at.x());
        int z = (int) Math.floor(at.z());
        int top = (int) Math.floor(reference) + 3;
        for (int y = top; y >= top - 8; y--) {
            if (WorldBlocks.solid(chunks, x, y, z) && !WorldBlocks.solid(chunks, x, y + 1, z) && !WorldBlocks.solid(chunks, x, y + 2, z)) {
                return y + 1;
            }
        }
        return reference;
    }

    private static Vector3d farthestPlayer(World world, CommandBuffer<EntityStore> buffer, Vector3d from) {
        Vector3d best = null;
        double bestDistance = -1;
        for (PlayerRef player : world.getPlayerRefs()) {
            Vector3d at = Telegraphs.position(buffer, player.getReference());
            if (at == null) {
                continue;
            }
            double d = Telegraphs.horizontal(at, from);
            if (d <= SEARCH_RADIUS && d > bestDistance) {
                bestDistance = d;
                best = new Vector3d(at);
            }
        }
        return best;
    }

    /** Une annonce en cours : attente ({@code Delay}), dessin de la zone, puis le coup. */
    private static final class Strike implements TelegraphSystem.Task {
        private final TelegraphInteraction config;
        private final Ref<EntityStore> caster;
        private final Ref<EntityStore> target;
        private final Vector3d center;
        private final double facing;
        private Telegraphs.Shape zone;
        private long start = -1;
        private long end;
        private long nextMark;

        Strike(TelegraphInteraction config, Ref<EntityStore> caster, Ref<EntityStore> target, Vector3d center,
               double facing) {
            this.config = config;
            this.caster = caster;
            this.target = target;
            this.center = center;
            this.facing = facing;
        }

        @Override
        public boolean step(World world, Store<EntityStore> store, long now) {
            if (start < 0) {
                start = now + Telegraphs.seconds(config.delay);
                end = start + Telegraphs.seconds(config.seconds);
            }
            if (Telegraphs.position(store, caster) == null) {
                return true;   // élite morte ou disparue : plus de coup
            }
            if (now < start) {
                return false;
            }
            if (zone == null) {
                zone = switch (config.shape) {
                    case "Cone" -> Telegraphs.Sweep.cone(center, facing, Math.toRadians(config.angle), config.radius, now, config.seconds);
                    case "Line" -> new Telegraphs.Strip(center, facing, config.length, config.width, now, config.seconds);
                    case "Circle" -> new Telegraphs.Circle(center, config.radius, now, config.seconds);
                    default -> null;
                };
            }
            if (zone != null) {
                zone.step(store, now);
            }
            mark(store, now);
            if (now < end) {
                return false;
            }
            hit(world, store);
            return true;
        }

        private void mark(Store<EntityStore> store, long now) {
            if (config.markParticle == null || config.markParticle.isBlank() || now < nextMark) {
                return;
            }
            nextMark = now + Telegraphs.seconds(Math.max(0.1f, config.markInterval));
            Vector3d at = "Mark".equals(config.shape) ? Telegraphs.position(store, target) : center;
            if (at != null) {
                Telegraphs.particle(store, config.markParticle, new Vector3d(at).add(0, config.markHeight, 0), config.markScale);
            }
        }

        private void hit(World world, Store<EntityStore> store) {
            ChunkStore chunks = world.getChunkStore();
            Vector3d casterAt = Telegraphs.position(store, caster);
            if (config.teleportCaster && casterAt != null) {
                Rotation3f rotation = new Rotation3f(0f, Telegraphs.yawToward(center, casterAt) + (float) Math.PI, 0f);
                Vector3d targetAt = Telegraphs.position(store, target);
                if (targetAt != null) {
                    rotation = new Rotation3f(0f, Telegraphs.yawToward(center, targetAt), 0f);
                }
                store.putComponent(caster, Teleport.getComponentType(), new Teleport(new Vector3d(center), rotation));
            }
            Vector3d impactAt = zone != null ? zone.origin() : center;
            if (config.impactParticle != null && !config.impactParticle.isBlank()) {
                Telegraphs.particle(store, config.impactParticle, new Vector3d(impactAt).add(0, 0.1, 0), config.impactScale);
            }
            Telegraphs.sound(store, config.impactSound, impactAt);

            for (Ref<EntityStore> victim : victims(world, store)) {
                Vector3d at = Telegraphs.position(store, victim);
                if (at == null) {
                    continue;
                }
                if (config.cover && !WorldBlocks.clearLine(chunks, new Vector3d(center).add(0, 1.2, 0), new Vector3d(at).add(0, 1.2, 0))) {
                    continue;   // à l'abri derrière un pilier
                }
                apply(world, store, chunks, victim, at);
            }
        }

        private Set<Ref<EntityStore>> victims(World world, Store<EntityStore> store) {
            Set<Ref<EntityStore>> out = new LinkedHashSet<>();
            if ("Mark".equals(config.shape)) {
                if (Telegraphs.position(store, target) != null) {
                    out.add(target);
                }
                return out;
            }
            if (zone == null) {
                return out;
            }
            for (PlayerRef player : world.getPlayerRefs()) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d at = Telegraphs.position(store, ref);
                if (at != null && zone.contains(at)) {
                    out.add(ref);
                }
            }
            if (!config.playersOnly) {
                List<Ref<EntityStore>> npcs = new ArrayList<>();
                store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
                    for (int i = 0; i < chunk.size(); i++) {
                        TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
                        if (transform != null && zone.contains(transform.getPosition())) {
                            npcs.add(chunk.getReferenceTo(i));
                        }
                    }
                });
                for (Ref<EntityStore> npc : npcs) {
                    if (!npc.equals(caster) && !Foes.allies(caster, npc, store)) {
                        out.add(npc);
                    }
                }
            }
            out.remove(caster);
            return out;
        }

        private void apply(World world, Store<EntityStore> store, ChunkStore chunks, Ref<EntityStore> victim, Vector3d at) {
            boolean player = store.getComponent(victim, Player.getComponentType()) != null;
            if (config.damage > 0f) {
                DamageCause cause = DamageCause.getAssetMap().getAsset(config.damageCause);
                if (cause != null) {
                    float amount = config.damage * (float) ThreadLocalRandom.current().nextDouble(0.92, 1.08);
                    DamageSystems.executeDamage(victim, store, new Damage(new Damage.EntitySource(caster), cause, amount));
                } else {
                    FractalsPlugin.get().getLogger().atWarning().log("%s : cause de dégâts '%s' introuvable", TYPE_ID, config.damageCause);
                }
            }
            if (Telegraphs.position(store, victim) == null) {
                return;   // achevé par le coup
            }
            if (config.knockback > 0f || config.knockUp > 0f) {
                Vector3d from = zone != null ? zone.origin() : center;
                double a = Telegraphs.horizontal(at, from) > 0.1 ? Telegraphs.angle(from, at) : facing;
                Velocity velocity = store.getComponent(victim, Velocity.getComponentType());
                if (velocity != null) {
                    velocity.addInstruction(new Vector3d(Math.cos(a) * config.knockback, config.knockUp, Math.sin(a) * config.knockback),
                            null, ChangeVelocityType.Set);
                }
            }
            if (config.effectId != null && !config.effectId.isBlank() && !config.imprison) {
                EntityEffect effect = EntityEffect.getAssetMap().getAsset(config.effectId);
                EffectControllerComponent effects = store.getComponent(victim, EffectControllerComponent.getComponentType());
                if (effect == null) {
                    FractalsPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, config.effectId);
                } else if (effects != null) {
                    effects.addEffect(victim, effect, config.effectDuration, OverlapBehavior.OVERWRITE, store, caster);
                }
            }
            if (config.imprison && player) {
                CagePlayerInteraction.imprison(store, chunks, caster, victim, CagePlayerInteraction.CAGE_BLOCK, config.cellRadius,
                        config.effectId, config.effectDuration);
            }
            if (config.hitParticle != null && !config.hitParticle.isBlank()) {
                Telegraphs.particle(store, config.hitParticle, new Vector3d(at).add(0, 1, 0), 1f);
            }
        }
    }
}
