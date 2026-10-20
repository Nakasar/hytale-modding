package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.builtin.triggervolumes.TriggerVolumesPlugin;
import com.hypixel.hytale.builtin.triggervolumes.manager.TriggerVolumeManager;
import com.hypixel.hytale.builtin.triggervolumes.manager.VolumeEntry;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.entitystats.modifier.Modifier;
import com.hypixel.hytale.server.core.modules.entitystats.modifier.StaticModifier;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Combat de l'Alchimiste, boss final de la Tour, sur la terrasse de l'Observatoire.
 *
 * <p>Ses coups de bâton sont dans son rôle ; ses fioles passent par {@link AlchemistFlaskInteraction}. Ce système mène
 * le reste :
 * <ul>
 *   <li><b>Engagement</b> : sa vie est multipliée par 1 + {@value #HP_PER_PLAYER} par joueur de plus dans l'arène, et
 *   par {@value #HARD_HP} si le levier de l'antichambre a été tiré (mode difficile, lu sur le volume
 *   {@link TowerLayout#ALCHEMIST_LEVER}, qu'on verrouille alors jusqu'à la remise à zéro).</li>
 *   <li><b>Transmutation</b> (100 à 67 %) : fioles, un seul élément par salve. Il lève une fiole de la couleur de
 *   l'élément ({@code Nakasar_Flask_*}) ; les cercles au sol restent rouges (effet négatif) et crépitent de l'élément
 *   ({@code Nakasar_Crackle_*}, tools/tower_fx.py ; Kevin, 20 octobre 2026).</li>
 *   <li><b>Grand Œuvre</b> (67 à 34 %) : chaque pan du rebord qui va tomber se couvre d'un cône rouge chargé de
 *   l'athanor vers le bord ({@link TowerFx.Sweep}), puis s'effondre (volumes {@link TowerLayout#ALCHEMIST_COLLAPSE}) ;
 *   il s'enferme dans l'athanor, gelé et invulnérable, et en fait sortir des homoncules ({@value #HOMUNCULUS_ROLE}).
 *   Tant qu'il y est, l'athanor déclenche toutes les {@value #RING_INTERVAL} s une transmutation en anneau, annoncée
 *   par un anneau rouge qui se remplit en {@value #RING_WARN} s (près de l'athanor, puis plus loin, en alternance).
 *   Le dernier homoncule tué, il ressort près d'un joueur, vulnérable {@value #VULNERABLE} s
 *   ({@value #VULNERABLE_HARD} s en mode difficile), puis s'y renferme. Qui tombe dans le vide d'un pan effondré revient
 *   sur le bord intérieur ({@link TowerLayout#ALCHEMIST_SAFE}), blessé.</li>
 *   <li><b>Convergence</b> (34 à 0 %) : quatre piliers élémentaires se dressent ; il prend l'élément d'un pilier encore
 *   debout toutes les {@value #ELEMENT_PERIOD} s (teinte et particules : effets {@value #ASPECT_PREFIX}*) et fait
 *   tomber cet élément sur chaque joueur toutes les {@value #HAZARD_INTERVAL} s : flammes qui restent au sol, givre
 *   qui ralentit, foudre qui étourdit, racines qui immobilisent. Les quatre piliers détruits, il s'effondre
 *   {@value #EXHAUSTED_SECONDS} s ({@value #EXHAUSTED}, dégâts subis +50 %). Ensuite les piliers renaissent à
 *   {@value #PILLAR_REBIRTH} de leur vie et le fléau reprend ; chaque nouvelle Convergence va plus vite (élément et
 *   fléau {@value #CYCLE_SPEEDUP} fois plus fréquents par cycle), jusqu'à sa mort.</li>
 *   <li><b>Fioles de soin</b> : à partir de {@value #HEAL_FIRST} s de combat, une fiole s'allume toutes les
 *   {@value #HEAL_INTERVAL} s sur un des socles de la terrasse.</li>
 *   <li><b>Remise à zéro</b> : plus aucun joueur dans l'arène pendant {@value #RESET_SECONDS} s : il sort de l'athanor,
 *   retrouve sa vie de départ, homoncules et piliers disparaissent, le rebord se reconstruit, le levier se déverrouille.</li>
 *   <li><b>Mort</b> : le sceau du bureau se dissout, le rebord se reconstruit, et chaque joueur de l'instance reçoit
 *   un sac de l'Alchimiste ({@value #BAG}, ou {@value #BAG_HARD} en mode difficile).</li>
 * </ul>
 */
public final class AlchemistSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Alchemist";
    static final String HOMUNCULUS_ROLE = "Nakasar_Athanor_Homunculus";
    static final String EXHAUSTED = "Nakasar_Alchemist_Exhausted";
    static final String ASPECT_PREFIX = "Nakasar_Alchemist_Aspect_";
    static final String HP_MODIFIER = "nakasar_alchemist_group";
    static final float HP_PER_PLAYER = GroupHealth.PER_PLAYER;
    static final float HARD_HP = 1.5f;
    static final float HARD_DAMAGE = 1.25f;
    static final float PHASE_2 = 0.67f;
    static final float PHASE_3 = 0.34f;
    static final float VULNERABLE = 30f;
    static final float VULNERABLE_HARD = 22f;
    static final int HOMUNCULI = 4;
    static final int HOMUNCULI_PER_PLAYER = 2;
    static final int HOMUNCULI_HARD = 2;
    static final float ELEMENT_PERIOD = 20f;
    static final float ELEMENT_PERIOD_HARD = 15f;
    static final float HAZARD_INTERVAL = 5f;
    static final float HAZARD_INTERVAL_HARD = 3.5f;
    static final float EXHAUSTED_SECONDS = 8f;
    static final float PILLAR_REBIRTH = 0.5f;
    static final float CYCLE_SPEEDUP = 1.2f;
    /** Au-delà, la cadence n'accélère plus (×1,2^4 ≈ ×2 : fléau toutes les 1,7 s en difficile, jamais à chaque tick). */
    static final int CYCLE_MAX = 4;
    /** Anneau de l'athanor au Grand Œuvre : cadence, annonce, part de la vie maximale, rayons des deux anneaux. */
    static final float RING_INTERVAL = 15f;
    static final float RING_WARN = 3f;
    private static final float RING_DAMAGE = 0.15f;
    private static final double RING_SPLIT = 17;
    private static final double RING_OUTER = 30;
    static final float HEAL_FIRST = 30f;
    static final float HEAL_INTERVAL = 40f;
    /** Une fiole de soin s'éteint seule au bout de 25 s (volume) : on ne rallume pas le même socle avant. */
    static final float HEAL_COOLDOWN = 27f;
    static final float RESET_SECONDS = 10f;
    static final float FLASK_RANGE = 30f;
    static final float FALL_DAMAGE = 0.1f;
    private static final float WARN = 2.5f;
    private static final float INTERVAL = 0.25f;
    private static final double ARENA_MARGIN = 1;
    private static final double ARENA_BELOW = 40;
    private static final double ARENA_ABOVE = 20;

    /** Zone rouge qui se remplit en {@link #WARN} s (tools/tower_warnings.py). */
    private static final String WARNING = "Nakasar_Warning_25";
    /** tools/tower_fx.py : fiole levée et crépitements de l'élément dans le cercle rouge. */
    private static final String FLASK = "Nakasar_Flask_";
    private static final String CRACKLE = "Nakasar_Crackle_";
    private static final String PARTICLE_ATHANOR = "Fire_Charge_Charging1";
    private static final String SOUND_ATHANOR = "SFX_Emit_Goblin_Pipes_Activate";
    private static final String SOUND_RING = "SFX_Emit_Goblin_Flame_Quadrant_Blast";

    /** Éléments des fioles et de la Convergence, dans l'ordre des piliers ({@link TowerLayout#ALCHEMIST_PILLARS}). */
    enum Element {
        FIRE("Fire", 3.0, 0.12f, "Fire", new String[]{"Fire_AoE"}, "SFX_Emit_Goblin_Flame_Quadrant_Blast",
                new String[]{"Burn"}, new float[]{4f}, 4f),
        FROST("Frost", 3.5, 0.10f, "Physical", new String[]{"Ice_Blast", "Ability_Ice_Explosion"},
                "SFX_Ice_Break", new String[]{"Slow"}, new float[]{4f}, 0f),
        THUNDER("Thunder", 2.5, 0.16f, "Physical", new String[]{"Lightning"},
                "SFX_Emit_Goblin_Electric_Fence_Zap", new String[]{"Hazard_Electric_Stun"}, new float[]{1f}, 0f),
        ROOT("Root", 3.0, 0.08f, "Physical", new String[]{"Impact_Poison", "Effect_Poison"},
                "SFX_Bramble_MoveIn", new String[]{"Root", "Poison_T1"}, new float[]{2.5f, 4f}, 0f);

        final String id;
        final double radius;
        final float damage;
        final String cause;
        final String[] hitParticles;
        final String sound;
        final String[] effects;
        final float[] effectSeconds;
        /** Secondes pendant lesquelles la zone reste dangereuse après l'éclat (flammes au sol). */
        final float linger;

        Element(String id, double radius, float damage, String cause, String[] hitParticles,
                String sound, String[] effects, float[] effectSeconds, float linger) {
            this.id = id;
            this.radius = radius;
            this.damage = damage;
            this.cause = cause;
            this.hitParticles = hitParticles;
            this.sound = sound;
            this.effects = effects;
            this.effectSeconds = effectSeconds;
            this.linger = linger;
        }
    }

    /** Zone annoncée au sol : éclate à {@code hit}, puis brûle encore jusqu'à {@code until} (flammes). */
    private static final class Strike {
        final Vector3d at;
        final Element element;
        final long hit;
        final long until;
        long nextBurn;
        boolean struck;

        Strike(Vector3d at, Element element, long hit) {
            this.at = at;
            this.element = element;
            this.hit = hit;
            this.until = hit + seconds(element.linger);
        }
    }

    /** État du combat par Alchimiste (le monde de l'instance n'en a qu'un). */
    private static final class Fight {
        boolean engaged;
        boolean hard;
        int players = 1;
        int phase = 1;
        long start;
        long nextHeal;
        long[] healReady = new long[TowerLayout.ALCHEMIST_HEALS.length];
        boolean collapsed;
        boolean enclosed;
        long vulnerableUntil;
        final List<Ref<EntityStore>> homunculi = new ArrayList<>();
        /** Pilier de chaque élément (null : détruit) ; null tant que la Convergence n'a pas commencé. */
        Ref<EntityStore>[] pillars;
        Element element;
        long nextElement;
        long nextHazard;
        boolean exhausted;
        long exhaustedUntil;
        /** Convergences recommencées (piliers renés) : chacune 20 % plus rapide. */
        int cycle;
        /** Cônes des pans du rebord, anneau de l'athanor en cours et le prochain (alterne près / loin). */
        final List<TowerFx.Sweep> cones = new ArrayList<>();
        TowerFx.Sweep ring;
        long nextRing;
        boolean ringFar;
        final List<Strike> strikes = new ArrayList<>();
        float absent;
        boolean sealed;
        /** Sacoches données (une seule fois, même sans volumes déclencheurs). */
        boolean rewarded;
    }

    /** Sacs de butin donnés à la mort du boss (tools/generate_alchemist_loot.py). */
    static final String BAG = "Nakasar_Alchemist_Bag";
    static final String BAG_HARD = "Nakasar_Alchemist_Bag_Hard";

    private static final Map<Ref<EntityStore>, Fight> FIGHTS = new ConcurrentHashMap<>();

    /** Système partagé par les mondes, chacun sur son thread : un compte à rebours par monde. */
    private final Map<World, Float> wait = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float left = wait.getOrDefault(world, 0f) - dt;
        if (left > 0f) {
            wait.put(world, left);
            return;
        }
        wait.put(world, INTERVAL);
        if (!TowerFallSystem.isTower(store)) {
            return;
        }
        // Le store est en plein traitement : on regarde et on agit juste après.
        world.execute(() -> step(world, INTERVAL));
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Ref<EntityStore>> bosses = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())) {
                    bosses.add(chunk.getReferenceTo(i));
                }
            }
        });
        // Alchimiste disparu du monde (chunk déchargé) : on retire ses homoncules et ses piliers.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            clearHelpers(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> boss : bosses) {
            update(world, store, boss, FIGHTS.computeIfAbsent(boss, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> boss, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        ArenaGate gate = ArenaGate.of(world, TowerLayout.ALCHEMIST_GATE, RESET_SECONDS, volumes);
        if (!alive(boss, store)) {
            clearHelpers(fight, store);
            gate.finish(volumes);
            fight.strikes.clear();
            if (!fight.rewarded) {
                fight.rewarded = true;
                VampiresPlugin.get().getLogger().atInfo().log("Alchimiste vaincu (mode difficile : %s, %d joueur(s))",
                        fight.hard, fight.players);
                giveBags(world, store, fight.hard);
            }
            if (!fight.sealed && volumes != null) {
                fight.sealed = true;
                tag(volumes, TowerLayout.ALCHEMIST_SEAL, "Alchemist", "On");
                tag(volumes, TowerLayout.ALCHEMIST_ARENA, "Reset", "On");
            }
            return;
        }
        EntityStatMap stats = store.getComponent(boss, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        List<Ref<EntityStore>> players = playersInArena(world, store);
        gate.update(volumes, !players.isEmpty(), dt);
        boolean engaged = fight.engaged || isEngaged(boss, store, health);

        // Remise à zéro : groupe mort ou sorti de l'arène.
        if (engaged && players.isEmpty()) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                reset(store, boss, fight, stats, volumes);
            }
            return;
        }
        fight.absent = 0f;
        if (!engaged) {
            return;
        }
        if (!fight.engaged) {
            engage(store, fight, stats, volumes, players.size(), now);
            health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        }

        rescueFallen(world, store, boss, fight);
        fight.cones.removeIf(cone -> cone.step(store, now));
        ring(world, store, fight, now);
        strikes(store, fight, now);
        heals(volumes, fight, now);

        float fraction = health == null ? 1f : health.get() / Math.max(1f, health.getMax());
        if (fight.phase == 1 && fraction <= PHASE_2) {
            fight.phase = 2;
            if (volumes != null) {
                tag(volumes, TowerLayout.ALCHEMIST_PHASE_2, "Cast", "On");
                for (String id : TowerLayout.ALCHEMIST_COLLAPSE) {
                    tag(volumes, id, "Collapse", "On");
                }
            }
            // Chaque pan qui va tomber : cône rouge chargé de l'athanor vers le bord, jusqu'à la chute.
            double[] radii = TowerLayout.ALCHEMIST_COLLAPSE_RADII;
            for (double[] arc : TowerLayout.ALCHEMIST_COLLAPSE_ARCS) {
                fight.cones.add(TowerFx.Sweep.arc(TowerLayout.ALCHEMIST_CENTER, arc[0], arc[1], radii[0], radii[1], now,
                        TowerLayout.ALCHEMIST_COLLAPSE_WARN));
            }
            fight.nextRing = now + seconds(RING_INTERVAL);
            fight.collapsed = true;
            enclose(store, boss, fight);
        } else if (fight.phase == 2) {
            greatWork(world, store, boss, fight, fraction, now);
        } else if (fight.phase == 3) {
            convergence(world, store, boss, fight, players, now);
        }
    }

    /** Début du combat : vie selon le groupe et le levier, levier verrouillé, premières fioles de soin. */
    private static void engage(Store<EntityStore> store, Fight fight, EntityStatMap stats, TriggerVolumeManager volumes,
                               int players, long now) {
        fight.engaged = true;
        fight.start = now;
        fight.players = Math.max(1, players);
        fight.nextHeal = now + seconds(HEAL_FIRST);
        if (volumes != null) {
            VolumeEntry lever = volumes.getVolume(TowerLayout.ALCHEMIST_LEVER);
            fight.hard = lever != null && "On".equals(lever.getRawTags().get("Hard"));
            tag(volumes, TowerLayout.ALCHEMIST_LEVER, "Locked", "On");
        }
        float multiplier = (1f + HP_PER_PLAYER * (fight.players - 1)) * (fight.hard ? HARD_HP : 1f);
        if (stats != null) {
            int healthIndex = DefaultEntityStatTypes.getHealth();
            stats.putModifier(healthIndex, HP_MODIFIER, new StaticModifier(Modifier.ModifierTarget.MAX,
                    StaticModifier.CalculationType.MULTIPLICATIVE, multiplier));
            stats.maximizeStatValue(healthIndex);
        }
    }

    // --- Grand Œuvre ----------------------------------------------------------------------------------------------

    private static void greatWork(World world, Store<EntityStore> store, Ref<EntityStore> boss, Fight fight, float fraction,
                                  long now) {
        if (fight.enclosed) {
            fight.homunculi.removeIf(homunculus -> !alive(homunculus, store));
            if (fight.homunculi.isEmpty()) {
                emerge(world, store, boss, fight);
                fight.vulnerableUntil = now + seconds(fight.hard ? VULNERABLE_HARD : VULNERABLE);
            }
            return;
        }
        if (fraction <= PHASE_3) {
            startConvergence(store, boss, fight, now);
        } else if (now >= fight.vulnerableUntil) {
            enclose(store, boss, fight);
        }
    }

    /** Il s'enferme dans l'athanor : gelé, invulnérable, et fait sortir ses homoncules. */
    private static void enclose(Store<EntityStore> store, Ref<EntityStore> boss, Fight fight) {
        fight.enclosed = true;
        store.ensureAndGetComponent(boss, Frozen.getComponentType());
        store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
        Vector3d center = new Vector3d(TowerLayout.ALCHEMIST_CENTER);
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(center, new Rotation3f()));
        puff(store, center);
        int count = HOMUNCULI + HOMUNCULI_PER_PLAYER * (fight.players - 1) + (fight.hard ? HOMUNCULI_HARD : 0);
        Vector3d[] exits = TowerLayout.ALCHEMIST_EXITS;
        int first = ThreadLocalRandom.current().nextInt(exits.length);
        for (int i = 0; i < count; i++) {
            Vector3d at = new Vector3d(exits[(first + i) % exits.length]);
            Ref<EntityStore> homunculus = spawn(store, HOMUNCULUS_ROLE, at, facing(TowerLayout.ALCHEMIST_CENTER, at));
            if (homunculus != null) {
                fight.homunculi.add(homunculus);
            }
        }
        if (fight.homunculi.isEmpty()) {
            fight.enclosed = false; // rien n'a pu apparaître : il ne reste pas enfermé pour toujours
            store.tryRemoveComponent(boss, Frozen.getComponentType());
            store.tryRemoveComponent(boss, Invulnerable.getComponentType());
        }
    }

    /** Il ressort de l'athanor, sur la case libre la plus proche d'un joueur. */
    private static void emerge(World world, Store<EntityStore> store, Ref<EntityStore> boss, Fight fight) {
        fight.enclosed = false;
        store.tryRemoveComponent(boss, Frozen.getComponentType());
        store.tryRemoveComponent(boss, Invulnerable.getComponentType());
        Vector3d exit = nearest(world, store, TowerLayout.ALCHEMIST_EXITS);
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(exit, new Rotation3f()));
        puff(store, TowerLayout.ALCHEMIST_CENTER);
        puff(store, exit);
    }

    /**
     * Transmutation en anneau de l'athanor, tant qu'il y est enfermé : un anneau rouge se remplit de l'intérieur vers
     * l'extérieur en {@link #RING_WARN} s, puis frappe qui s'y tient. Près de l'athanor, puis plus loin, en alternance :
     * on esquive en changeant d'anneau.
     */
    private static void ring(World world, Store<EntityStore> store, Fight fight, long now) {
        if (fight.ring != null) {
            if (!fight.ring.step(store, now)) {
                return;
            }
            TowerFx.Sweep ring = fight.ring;
            fight.ring = null;
            float damage = RING_DAMAGE * (fight.hard ? HARD_DAMAGE : 1f);
            for (Ref<EntityStore> player : playersInArena(world, store)) {
                Vector3d position = TowerFx.position(store, player);
                if (position != null && Math.abs(position.y() - ring.center.y()) < 3 && ring.contains(position)) {
                    damage(store, player, DamageCause.getAssetMap().getAsset("Physical"), damage);
                }
            }
            for (int k = 0; k < 8; k++) {
                double a = Math.PI * 2 * k / 8;
                double r = (ring.from + ring.to) / 2;
                Vector3d at = new Vector3d(ring.center).add(Math.cos(a) * r, 0.3, Math.sin(a) * r);
                ParticleUtil.spawnParticleEffect(PARTICLE_ATHANOR, at, 0f, 0f, 0f, 1.5f, 1f, store);
            }
            sound(SOUND_RING, ring.center, store);
            return;
        }
        if (fight.phase == 2 && !fight.enclosed) {
            // Vulnérable hors de l'athanor : le prochain anneau attend qu'il s'y renferme, et laisse souffler.
            fight.nextRing = now + seconds(RING_INTERVAL / 2);
            return;
        }
        if (fight.phase != 2 || now < fight.nextRing) {
            return;
        }
        fight.nextRing = now + seconds(RING_INTERVAL);
        double inner = TowerLayout.ALCHEMIST_ATHANOR_RADIUS + 1;
        fight.ring = fight.ringFar
                ? new TowerFx.Sweep(TowerLayout.ALCHEMIST_CENTER, 0, Math.PI * 2, RING_SPLIT, RING_OUTER, now, RING_WARN)
                : new TowerFx.Sweep(TowerLayout.ALCHEMIST_CENTER, 0, Math.PI * 2, inner, RING_SPLIT, now, RING_WARN);
        fight.ringFar = !fight.ringFar;
        puff(store, TowerLayout.ALCHEMIST_CENTER);
    }

    // --- Convergence ----------------------------------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private static void startConvergence(Store<EntityStore> store, Ref<EntityStore> boss, Fight fight, long now) {
        fight.phase = 3;
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        if (volumes != null) {
            tag(volumes, TowerLayout.ALCHEMIST_PHASE_3, "Cast", "On");
        }
        fight.pillars = new Ref[Element.values().length];
        raisePillars(store, fight, 1f);
        fight.nextHazard = now + seconds(3f);
        switchElement(store, boss, fight, now);
    }

    /** Dresse les quatre piliers (vie : part `health` de leur maximum). */
    private static void raisePillars(Store<EntityStore> store, Fight fight, float health) {
        Element[] elements = Element.values();
        for (int i = 0; i < elements.length; i++) {
            Vector3d at = new Vector3d(TowerLayout.ALCHEMIST_PILLARS[i]);
            Ref<EntityStore> pillar = spawn(store, "Nakasar_Alchemist_Pillar_" + elements[i].id, at,
                    facing(at, TowerLayout.ALCHEMIST_CENTER));
            if (pillar != null) {
                // Immobile : l'IA gelée ne le fait ni bouger ni tourner.
                store.ensureAndGetComponent(pillar, Frozen.getComponentType());
                ParticleUtil.spawnParticleEffect(elements[i].hitParticles[0], new Vector3d(at).add(0, 1, 0), 0f, 0f, 0f, 1.5f, 1f, store);
                EntityStatMap stats = store.getComponent(pillar, EntityStatMap.getComponentType());
                EntityStatValue value = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
                if (value != null && health < 1f) {
                    stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.max(1f, value.getMax() * health));
                }
            }
            fight.pillars[i] = pillar;
        }
    }

    /** Cadence d'un intervalle de la Convergence au cycle en cours (chaque cycle 20 % plus fréquent, jusqu'à CYCLE_MAX). */
    private static float paced(Fight fight, float seconds) {
        return (float) (seconds / Math.pow(CYCLE_SPEEDUP, Math.min(fight.cycle, CYCLE_MAX)));
    }

    private static void convergence(World world, Store<EntityStore> store, Ref<EntityStore> boss, Fight fight,
                                    List<Ref<EntityStore>> players, long now) {
        if (fight.exhausted) {
            if (now >= fight.exhaustedUntil) {
                // Pas de temps mort : les piliers renaissent à moitié, le fléau reprend, plus vite.
                fight.exhausted = false;
                fight.cycle++;
                store.tryRemoveComponent(boss, Frozen.getComponentType());
                raisePillars(store, fight, PILLAR_REBIRTH);
                fight.nextHazard = now + seconds(2f);
                switchElement(store, boss, fight, now);
                TowerFx.sound(store, "SFX_Emit_Dungeon_Goblin_Void_Thunder", TowerLayout.ALCHEMIST_CENTER);
            }
            return;
        }
        boolean lost = false;
        int standing = 0;
        for (int i = 0; i < fight.pillars.length; i++) {
            if (fight.pillars[i] != null && !alive(fight.pillars[i], store)) {
                fight.pillars[i] = null;
                lost |= fight.element == Element.values()[i];
            }
            if (fight.pillars[i] != null) {
                standing++;
            }
        }
        if (standing == 0) {
            exhaust(store, boss, fight, now);
            return;
        }
        if (lost || now >= fight.nextElement) {
            switchElement(store, boss, fight, now);
        }
        if (now >= fight.nextHazard && fight.element != null) {
            fight.nextHazard = now + seconds(paced(fight, fight.hard ? HAZARD_INTERVAL_HARD : HAZARD_INTERVAL));
            for (Ref<EntityStore> player : players) {
                Vector3d at = groundUnder(store, player);
                if (at != null) {
                    fight.strikes.add(strike(store, at, fight.element, now));
                }
            }
            if (fight.element == Element.FIRE) {
                // Les flammes gagnent aussi un point au hasard autour de l'athanor.
                Vector3d[] spots = TowerLayout.ALCHEMIST_EXITS;
                Vector3d at = new Vector3d(spots[ThreadLocalRandom.current().nextInt(spots.length)]);
                fight.strikes.add(strike(store, at, Element.FIRE, now));
            }
        }
    }

    /** Prend l'élément du pilier debout suivant (dans l'ordre des piliers), teinte et particules comprises. */
    private static void switchElement(Store<EntityStore> store, Ref<EntityStore> boss, Fight fight, long now) {
        Element[] elements = Element.values();
        int start = fight.element == null ? ThreadLocalRandom.current().nextInt(elements.length) : fight.element.ordinal() + 1;
        Element next = null;
        for (int k = 0; k < elements.length; k++) {
            int i = (start + k) % elements.length;
            if (fight.pillars[i] != null) {
                next = elements[i];
                break;
            }
        }
        if (fight.element != null) {
            removeEffect(boss, ASPECT_PREFIX + fight.element.id, store);
        }
        fight.element = next;
        fight.nextElement = now + seconds(paced(fight, fight.hard ? ELEMENT_PERIOD_HARD : ELEMENT_PERIOD));
        if (next != null) {
            applyEffect(boss, ASPECT_PREFIX + next.id, -1f, store);
            TransformComponent transform = store.getComponent(boss, TransformComponent.getComponentType());
            if (transform != null) {
                Vector3d at = new Vector3d(transform.getPosition()).add(0, 1, 0);
                ParticleUtil.spawnParticleEffect(next.hitParticles[0], at, 0f, 0f, 0f, 1.5f, 1f, store);
                sound(next.sound, at, store);
            }
        }
    }

    /** Les quatre piliers détruits : il s'effondre, gelé, et subit plus de dégâts. */
    private static void exhaust(Store<EntityStore> store, Ref<EntityStore> boss, Fight fight, long now) {
        fight.exhausted = true;
        if (fight.element != null) {
            removeEffect(boss, ASPECT_PREFIX + fight.element.id, store);
            fight.element = null;
        }
        applyEffect(boss, EXHAUSTED, EXHAUSTED_SECONDS, store);
        store.ensureAndGetComponent(boss, Frozen.getComponentType());
        fight.exhaustedUntil = now + seconds(EXHAUSTED_SECONDS);
        TransformComponent transform = store.getComponent(boss, TransformComponent.getComponentType());
        if (transform != null) {
            puff(store, transform.getPosition());
        }
    }

    // --- fioles et zones -------------------------------------------------------------------------------------------

    /** Appelé par {@link AlchemistFlaskInteraction} sur le thread du monde : une fiole vers chaque joueur à portée. */
    static void throwFlasks(World world, Ref<EntityStore> boss) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Fight fight = FIGHTS.get(boss);
        if (fight == null || !alive(boss, store) || fight.enclosed) {
            return;
        }
        TransformComponent self = store.getComponent(boss, TransformComponent.getComponentType());
        if (self == null) {
            return;
        }
        long now = System.nanoTime();
        Element[] elements = Element.values();
        ThreadLocalRandom random = ThreadLocalRandom.current();
        // Un seul élément par salve : il lève une fiole de sa couleur, les cercles crépitent de cet élément.
        Element element = fight.element != null ? fight.element : elements[random.nextInt(elements.length)];
        ParticleUtil.spawnParticleEffect(FLASK + element.id, new Vector3d(self.getPosition()).add(0, 2.4, 0), 0f, 0f, 0f,
                1f, 1f, store);
        for (Ref<EntityStore> player : playersInArena(world, store)) {
            Vector3d at = groundUnder(store, player);
            if (at == null || horizontal(at, self.getPosition()) > FLASK_RANGE) {
                continue;
            }
            fight.strikes.add(strike(store, at, element, now));
            if (fight.hard) {
                // Mode difficile : une seconde fiole à côté, pour qu'un pas de côté ne suffise pas toujours.
                double angle = random.nextDouble(Math.PI * 2);
                Vector3d near = new Vector3d(at).add(Math.cos(angle) * 3.5, 0, Math.sin(angle) * 3.5);
                fight.strikes.add(strike(store, near, element, now));
            }
        }
    }

    private static Strike strike(Store<EntityStore> store, Vector3d at, Element element, long now) {
        Vector3d ground = new Vector3d(at).add(0, 0.1, 0);
        ParticleUtil.spawnParticleEffect(WARNING, ground, 0f, 0f, 0f, (float) (0.68 * element.radius), 1f, store);
        ParticleUtil.spawnParticleEffect(CRACKLE + element.id, ground, 0f, 0f, 0f, (float) (0.68 * element.radius), 1f, store);
        return new Strike(new Vector3d(at), element, now + seconds(WARN));
    }

    private static void strikes(Store<EntityStore> store, Fight fight, long now) {
        fight.strikes.removeIf(strike -> {
            if (now < strike.hit) {
                return false;
            }
            if (!strike.struck) {
                strike.struck = true;
                strike.nextBurn = now + seconds(1f);
                for (String particle : strike.element.hitParticles) {
                    ParticleUtil.spawnParticleEffect(particle, new Vector3d(strike.at).add(0, 0.3, 0), 0f, 0f, 0f, 1.5f, 1f, store);
                }
                sound(strike.element.sound, strike.at, store);
                hit(store, fight, strike, true);
            } else if (now >= strike.nextBurn && now < strike.until) {
                strike.nextBurn = now + seconds(1f);
                ParticleUtil.spawnParticleEffect(strike.element.hitParticles[0], new Vector3d(strike.at).add(0, 0.3, 0), 0f, 0f, 0f, 1.2f, 1f, store);
                hit(store, fight, strike, false);
            }
            return now >= strike.until && strike.struck;
        });
    }

    /** Dégâts (part de la vie maximale) et effets de l'élément aux joueurs dans la zone. */
    private static void hit(Store<EntityStore> store, Fight fight, Strike strike, boolean effects) {
        World world = store.getExternalData().getWorld();
        DamageCause cause = DamageCause.getAssetMap().getAsset(strike.element.cause);
        float scale = (fight.hard ? HARD_DAMAGE : 1f) * (effects ? 1f : 0.4f);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            Vector3d position = transform.getPosition();
            double dy = position.y() - strike.at.y();
            if (horizontal(position, strike.at) > strike.element.radius || dy < -1 || dy > 3) {
                continue;
            }
            damage(store, ref, cause, strike.element.damage * scale);
            if (effects) {
                for (int i = 0; i < strike.element.effects.length; i++) {
                    applyEffect(ref, strike.element.effects[i], strike.element.effectSeconds[i], store);
                }
            }
        }
    }

    private static void damage(Store<EntityStore> store, Ref<EntityStore> ref, DamageCause cause, float fraction) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (cause == null || health == null) {
            return;
        }
        float amount = (float) Math.ceil(health.getMax() * fraction);
        DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource("Nakasar_Alchemist"), cause, amount));
    }

    // --- fioles de soin, chutes ------------------------------------------------------------------------------------

    private static void heals(TriggerVolumeManager volumes, Fight fight, long now) {
        if (volumes == null || now < fight.nextHeal) {
            return;
        }
        fight.nextHeal = now + seconds(HEAL_INTERVAL);
        List<Integer> free = new ArrayList<>();
        for (int i = 0; i < fight.healReady.length; i++) {
            if (now >= fight.healReady[i]) {
                free.add(i);
            }
        }
        if (free.isEmpty()) {
            return;
        }
        int i = free.get(ThreadLocalRandom.current().nextInt(free.size()));
        fight.healReady[i] = now + seconds(HEAL_COOLDOWN);
        tag(volumes, TowerLayout.ALCHEMIST_HEAL[i], "Pack", "On");
    }

    /**
     * Rebord effondré : qui tombe dans le vide d'un pan revient sur le bord intérieur le plus proche, blessé ; lui-même
     * revient près de l'athanor. Hors des pans, la chute relève de {@link TowerFallSystem}.
     */
    private static void rescueFallen(World world, Store<EntityStore> store, Ref<EntityStore> boss, Fight fight) {
        if (!fight.collapsed) {
            return;
        }
        DamageCause physical = DamageCause.getAssetMap().getAsset("Physical");
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store) || store.getComponent(ref, Teleport.getComponentType()) != null) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null || !fallen(transform.getPosition())) {
                continue;
            }
            Vector3d safe = nearestTo(transform.getPosition(), TowerLayout.ALCHEMIST_SAFE);
            store.putComponent(ref, Teleport.getComponentType(), Teleport.createForPlayer(safe, new Rotation3f()));
            damage(store, ref, physical, FALL_DAMAGE);
        }
        TransformComponent self = store.getComponent(boss, TransformComponent.getComponentType());
        if (self != null && self.getPosition().y() < TowerLayout.ALCHEMIST_CENTER.y() - 3
                && store.getComponent(boss, Teleport.getComponentType()) == null) {
            Vector3d exit = nearest(world, store, TowerLayout.ALCHEMIST_EXITS);
            store.putComponent(boss, Teleport.getComponentType(), new Teleport(exit, new Rotation3f()));
        }
    }

    /** Sous la terrasse, à l'aplomb d'un pan effondré. */
    private static boolean fallen(Vector3d position) {
        Vector3d center = TowerLayout.ALCHEMIST_CENTER;
        double dy = position.y() - center.y();
        if (dy > -2.5 || dy < -ARENA_BELOW) {
            return false;
        }
        double d = horizontal(position, center);
        double[] radii = TowerLayout.ALCHEMIST_COLLAPSE_RADII;
        if (d < radii[0] - 1.5 || d > radii[1] + 2) {
            return false;
        }
        double a = angle(position);
        for (double[] arc : TowerLayout.ALCHEMIST_COLLAPSE_ARCS) {
            if (inArc(a, arc[0] - 4, arc[1] + 4)) {
                return true;
            }
        }
        return false;
    }

    // --- remise à zéro ---------------------------------------------------------------------------------------------

    private static void reset(Store<EntityStore> store, Ref<EntityStore> boss, Fight fight, EntityStatMap stats,
                              TriggerVolumeManager volumes) {
        clearHelpers(fight, store);
        store.tryRemoveComponent(boss, Frozen.getComponentType());
        store.tryRemoveComponent(boss, Invulnerable.getComponentType());
        fight.strikes.clear();
        if (fight.element != null) {
            removeEffect(boss, ASPECT_PREFIX + fight.element.id, store);
        }
        removeEffect(boss, EXHAUSTED, store);
        if (fight.enclosed) {
            Vector3d exit = new Vector3d(TowerLayout.ALCHEMIST_EXITS[0]);
            store.putComponent(boss, Teleport.getComponentType(), new Teleport(exit, new Rotation3f()));
        }
        if (stats != null) {
            int healthIndex = DefaultEntityStatTypes.getHealth();
            stats.removeModifier(healthIndex, HP_MODIFIER);
            stats.maximizeStatValue(healthIndex);
        }
        if (volumes != null) {
            tag(volumes, TowerLayout.ALCHEMIST_ARENA, "Reset", "On");
            tag(volumes, TowerLayout.ALCHEMIST_LEVER, "Locked", "Off");
        }
        Fight fresh = new Fight();
        fresh.sealed = fight.sealed;
        FIGHTS.put(boss, fresh);
    }

    private static void clearHelpers(Fight fight, Store<EntityStore> store) {
        for (Ref<EntityStore> homunculus : fight.homunculi) {
            if (homunculus.isValid()) {
                store.removeEntity(homunculus, RemoveReason.REMOVE);
            }
        }
        fight.homunculi.clear();
        if (fight.pillars != null) {
            for (int i = 0; i < fight.pillars.length; i++) {
                Ref<EntityStore> pillar = fight.pillars[i];
                if (pillar != null && pillar.isValid()) {
                    store.removeEntity(pillar, RemoveReason.REMOVE);
                }
                fight.pillars[i] = null;
            }
        }
    }

    // --- outils ----------------------------------------------------------------------------------------------------

    private static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at, Rotation3f rotation) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, rotation);
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Alchimiste : impossible de faire apparaître '%s'", role);
            return null;
        }
        // Jamais sauvegardé : le combat repose tout au rechargement de l'instance.
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        return spawned.first();
    }

    /** Un sac de l'Alchimiste à chaque joueur de l'instance (le sac du mode difficile si le levier était tiré). */
    private static void giveBags(World world, Store<EntityStore> store, boolean hard) {
        String bag = hard ? BAG_HARD : BAG;
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            var inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
            SimpleItemContainer.addOrDropItemStack(store, ref, inventory, new ItemStack(bag, 1));
        }
    }

    private static List<Ref<EntityStore>> playersInArena(World world, Store<EntityStore> store) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform != null && inArena(transform.getPosition())) {
                out.add(ref);
            }
        }
        return out;
    }

    /** La terrasse, sans l'antichambre ni le bureau ; on compte aussi qui tombe d'un pan (il va revenir). */
    private static boolean inArena(Vector3d position) {
        Vector3d center = TowerLayout.ALCHEMIST_CENTER;
        double dy = position.y() - center.y();
        double d = horizontal(position, center);
        if (d > TowerLayout.ALCHEMIST_DECK_RADIUS + ARENA_MARGIN || dy < -ARENA_BELOW || dy > ARENA_ABOVE) {
            return false;
        }
        if (dy < -2.5 && !fallen(position)) {
            return false;
        }
        double[] antechamber = TowerLayout.ALCHEMIST_ANTECHAMBER_ARC;
        if (d >= TowerLayout.ALCHEMIST_ANTECHAMBER_RADIUS && inArc(angle(position), antechamber[0], antechamber[1])) {
            return false;
        }
        return position.z() < TowerLayout.ALCHEMIST_STUDY_Z;
    }

    /** Sol sous les pieds d'un joueur (sa position s'il est au niveau de la terrasse, sinon le niveau de la terrasse). */
    private static Vector3d groundUnder(Store<EntityStore> store, Ref<EntityStore> ref) {
        TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
        if (transform == null) {
            return null;
        }
        Vector3d at = new Vector3d(transform.getPosition());
        at.y = TowerLayout.ALCHEMIST_CENTER.y();
        return at;
    }

    private static Vector3d nearest(World world, Store<EntityStore> store, Vector3d[] points) {
        Vector3d best = points[ThreadLocalRandom.current().nextInt(points.length)];
        double bestDistance = Double.MAX_VALUE;
        for (Ref<EntityStore> ref : playersInArena(world, store)) {
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            Vector3d candidate = nearestTo(transform.getPosition(), points);
            double d = horizontal(candidate, transform.getPosition());
            if (d < bestDistance) {
                bestDistance = d;
                best = candidate;
            }
        }
        return new Vector3d(best);
    }

    private static Vector3d nearestTo(Vector3d from, Vector3d[] points) {
        Vector3d best = points[0];
        double bestDistance = Double.MAX_VALUE;
        for (Vector3d point : points) {
            double d = horizontal(point, from);
            if (d < bestDistance) {
                bestDistance = d;
                best = point;
            }
        }
        return new Vector3d(best);
    }

    private static double angle(Vector3d position) {
        Vector3d center = TowerLayout.ALCHEMIST_CENTER;
        double a = Math.toDegrees(Math.atan2(position.z() - center.z(), position.x() - center.x()));
        return (a % 360 + 360) % 360;
    }

    /** L'angle a est-il sur l'arc parcouru dans le sens positif de a0 à a1 (comme tools/alchemist_tower.in_arc) ? */
    private static boolean inArc(double a, double a0, double a1) {
        return ((a - a0) % 360 + 360) % 360 <= a1 - a0;
    }

    private static Rotation3f facing(Vector3d from, Vector3d to) {
        // Même convention que SummonMinionsInteraction.facing (tourné vers `to`).
        return new Rotation3f(0f, (float) Math.atan2(to.x() - from.x(), to.z() - from.z()), 0f);
    }

    private static void puff(Store<EntityStore> store, Vector3d at) {
        ParticleUtil.spawnParticleEffect(PARTICLE_ATHANOR, new Vector3d(at).add(0, 1, 0), 0f, 0f, 0f, 2f, 1f, store);
        sound(SOUND_ATHANOR, at, store);
    }

    private static void tag(TriggerVolumeManager volumes, String volume, String key, String value) {
        volumes.setTag(volume, key, value, null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
    }

    private static boolean applyEffect(Ref<EntityStore> ref, String effectId, float seconds, Store<EntityStore> store) {
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effect == null || effects == null) {
            if (effect == null) {
                VampiresPlugin.get().getLogger().atWarning().log("Alchimiste : effet '%s' introuvable", effectId);
            }
            return false;
        }
        if (seconds < 0f) {
            return effects.addInfiniteEffect(ref, EntityEffect.getAssetMap().getIndex(effectId), effect, store);
        }
        return effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, store);
    }

    private static void removeEffect(Ref<EntityStore> ref, String effectId, Store<EntityStore> store) {
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        if (effects != null && index >= 0 && effects.hasEffect(index)) {
            effects.removeEffect(ref, index, store);
        }
    }

    private static double horizontal(Vector3d a, Vector3d b) {
        double dx = a.x() - b.x();
        double dz = a.z() - b.z();
        return Math.sqrt(dx * dx + dz * dz);
    }

    private static boolean isEngaged(Ref<EntityStore> ref, Store<EntityStore> store, EntityStatValue health) {
        StateSupport state = StateSupport.get(ref, store);
        String name = state == null ? null : state.getStateName();
        if (name != null && name.startsWith("Combat")) {
            return true;
        }
        return health != null && health.get() < health.getMax() - 0.5f;
    }

    private static boolean alive(Ref<EntityStore> ref, Store<EntityStore> store) {
        if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return false;
        }
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        return health == null || health.get() > 0f;
    }

    private static void sound(String id, Vector3d position, Store<EntityStore> store) {
        int index = SoundEvent.getAssetMap().getIndexOrDefault(id, -1);
        if (index >= 0) {
            SoundUtil.playSoundEvent3d(index, SoundCategory.SFX, position.x(), position.y(), position.z(), store);
        }
    }

    private static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    /** Oublie les combats en cours (arrêt du plugin). Homoncules et piliers partent avec le monde. */
    public static void clearAll() {
        FIGHTS.clear();
    }
}
