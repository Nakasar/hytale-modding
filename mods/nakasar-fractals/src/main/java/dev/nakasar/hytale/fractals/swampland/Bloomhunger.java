package dev.nakasar.hytale.fractals.swampland;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.PinnedHealth;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Carnasse, d'après GW2. Lui et ses esprits ne sont vulnérables que dans le cercle vert, qui part de la faille
 * allumée au réveil, rétrécit de {@value #CIRCLE_MAX} à {@value #CIRCLE_MIN} blocs en {@value #CIRCLE_SECONDS} s puis
 * saute à la faille suivante, dans le sens horaire. Dans le cercle, l'endurance revient vite (vigueur).
 * <ul>
 *   <li>assauts à 75 % et 50 % : il se retire au centre, invulnérable ; il faut abattre 4 + 2 par joueur esprits
 *   animaux (dans le cercle), sous une pluie de poison ; ensuite poussent {@value #BLOOMS} fleurs de poison
 *   (poison à moins de {@value #BLOOM_RADIUS} blocs, et les ennemis proches ne prennent que {@value #BLOOM_SHIELD}
 *   des dégâts) ;</li>
 *   <li>à 25 % : il se charge au centre ({@value #CHARGE_SECONDS} s) ; quatre feux-follets apparaissent aux coins.
 *   Les quatre failles allumées à temps : grand cercle vert de {@value #BIG_RADIUS} blocs au centre et Carnasse
 *   étourdi {@value #BIG_STUN} s ; sinon purge corporelle ({@value #PURGE_PART} des PV, tous dès le niveau 76).</li>
 * </ul>
 * Sa vie ne descend pas sous le seuil suivant tant que l'étape qui y attend n'est pas passée. Personne de vivant dans
 * la clairière pendant {@value #RESET_SECONDS} s : tout recommence (le feu-follet de l'entrée revient).
 */
final class Bloomhunger {

    enum Outcome { NONE, WON, RESET }

    static final double CIRCLE_MAX = 7;
    static final double CIRCLE_MIN = 3;
    static final float CIRCLE_SECONDS = 25f;
    static final double BIG_RADIUS = 8;
    static final float BIG_SECONDS = 12f;
    static final float BIG_STUN = 6f;
    static final float CHARGE_SECONDS = 35f;
    static final float PURGE_PART = 0.6f;
    static final int BLOOMS = 3;
    static final double BLOOM_RADIUS = 3;
    static final double BLOOM_GUARD = 4;
    static final float BLOOM_SHIELD = 0.67f;
    static final int SPIRIT_CAP = 6;
    static final float RAIN_EVERY = 4f;
    static final int RAIN_DROPS = 5;
    static final double RAIN_RADIUS = 2.5;
    static final float RAIN_PART = 0.12f;
    static final float RESET_SECONDS = 20f;
    static final float[] THRESHOLDS = {0.75f, 0.5f, 0.25f};
    static final String VIGOR = "Nakasar_Fractal_Wisp_Vigor";
    static final String GREEN_ZONE = "Nakasar_Fractal_Green_Zone";

    private Ref<EntityStore> boss;
    private final List<Ref<EntityStore>> spirits = new ArrayList<>();
    private final List<Ref<EntityStore>> blooms = new ArrayList<>();
    private boolean engaged;
    private volatile boolean dead;
    /** Étapes passées : 0 aucune, 1 et 2 les assauts, 3 la charge. */
    private int stage;
    private boolean onslaught;
    private int spiritsNeeded;
    private int spiritsSpawned;
    private int spiritsDown;
    private float rainClock;
    private boolean charging;
    private float chargeLeft;
    private int chargeShown = -1;
    private int lit;
    private int cleft;
    private float circleClock;
    private float bigLeft;
    private float drawClock;
    private float pulseClock;
    private float idle;

    void spiritDown() {
        spiritsDown++;
    }

    void down() {
        dead = true;
    }

    // --- réveil ------------------------------------------------------------------------------------------

    /** Clairière prête : failles éteintes, feu-follet à l'entrée, plus rien aux coins. */
    void prepare(World world) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] c : SwamplandLayout.CLEARING_CLEFTS) {
            WorldBlocks.swap(chunks, c[0], c[1], c[2], Swampland.CLEFT);
        }
        clearCorners(chunks);
        WispRun.place(chunks, SwamplandLayout.CLEARING_WISP);
    }

    void wake(World world, Store<EntityStore> store, int cleftIndex) {
        Vector3d at = Spawns.point(SwamplandLayout.CLEARING);
        boss = Spawns.spawnBoss(world, store, Swampland.BLOOMHUNGER, at, Telegraphs.yawToward(at, new Vector3d(at).add(0, 0, 1)));
        PinnedHealth.noRegen(boss);   // invulnérable hors du cercle : il ne doit pas non plus se refaire une santé
        engaged = true;
        dead = false;
        stage = 0;
        onslaught = false;
        charging = false;
        cleft = cleftIndex;
        circleClock = 0f;
        bigLeft = 0f;
        idle = 0f;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.enter"));
    }

    // --- le cercle vert ------------------------------------------------------------------------------------

    private Vector3d circleCenter() {
        if (bigLeft > 0f) {
            return Spawns.point(SwamplandLayout.CLEARING);
        }
        int[] c = SwamplandLayout.CLEARING_CLEFTS[cleft];
        return new Vector3d(c[0] + 0.5, c[1], c[2] + 0.5);
    }

    private double circleRadius() {
        if (bigLeft > 0f) {
            return BIG_RADIUS;
        }
        return CIRCLE_MAX - (CIRCLE_MAX - CIRCLE_MIN) * Math.min(1f, circleClock / CIRCLE_SECONDS);
    }

    private boolean inCircle(Vector3d p) {
        return p != null && Telegraphs.horizontal(p, circleCenter()) <= circleRadius() + 0.5;
    }

    private void circle(Store<EntityStore> store, List<PlayerRef> inside, float dt) {
        if (bigLeft > 0f) {
            bigLeft -= dt;
        } else {
            circleClock += dt;
            if (circleClock >= CIRCLE_SECONDS) {
                circleClock = 0f;
                cleft = (cleft + 1) % SwamplandLayout.CLEARING_CLEFTS.length;
            }
        }
        Vector3d center = circleCenter();
        double radius = circleRadius();
        drawClock += dt;
        boolean draw = drawClock >= 0.5f;
        if (draw) {
            drawClock = 0f;
            // Disque et contour verts comme les zones rouges (bien lisibles), lueurs qui montent du bord.
            Telegraphs.particle(store, GREEN_ZONE, new Vector3d(center).add(0, 0.1, 0), (float) (Telegraphs.WARNING_SCALE * radius));
            int n = (int) Math.ceil(Math.PI * 2 * radius / 1.0);
            for (int i = 0; i < n; i++) {
                double a = Math.PI * 2 * i / n;
                Telegraphs.particle(store, "Nakasar_Fractal_Wisp_Ring",
                        new Vector3d(center.x() + Math.cos(a) * radius, center.y() + 0.1, center.z() + Math.sin(a) * radius), 1f);
            }
        }
        for (PlayerRef p : inside) {
            Ref<EntityStore> ref = p.getReference();
            if (!inCircle(Telegraphs.position(store, ref))) {
                continue;
            }
            EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
            if (stats != null) {
                stats.addStatValue(DefaultEntityStatTypes.getStamina(), 3f * dt);
            }
            if (draw) {
                Hurt.effect(store, ref, VIGOR, 1.5f);
            }
        }
    }

    // --- coups ---------------------------------------------------------------------------------------------

    /** Carnasse, ses esprits : vulnérables dans le cercle seulement ; près d'une fleur, dégâts réduits ; seuils. */
    void filter(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> victim, String role, Damage damage) {
        if (!engaged || Swampland.BLOOM.equals(role)) {
            return;
        }
        Vector3d at = Telegraphs.position(accessor, victim);
        boolean boss = Swampland.BLOOMHUNGER.equals(role);
        if (!inCircle(at) || boss && (onslaught || charging)) {
            damage.setCancelled(true);
            return;
        }
        for (Ref<EntityStore> bloom : blooms) {
            Vector3d b = Telegraphs.position(accessor, bloom);
            if (b != null && Telegraphs.horizontal(b, at) <= BLOOM_GUARD) {
                damage.setAmount(damage.getAmount() * BLOOM_SHIELD);
                break;
            }
        }
        if (!boss || stage >= THRESHOLDS.length) {
            return;
        }
        EntityStatMap stats = accessor.getComponent(victim, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            float floor = health.getMax() * THRESHOLDS[stage];
            damage.setAmount(Math.max(0f, Math.min(damage.getAmount(), health.get() - floor)));
        }
    }

    // --- pas de jeu ----------------------------------------------------------------------------------------

    Outcome step(World world, Store<EntityStore> store, Swampland.State st, List<PlayerRef> players, float dt) {
        if (!engaged) {
            return Outcome.NONE;
        }
        if (dead) {
            clear(world, store);
            engaged = false;
            return Outcome.WON;
        }
        List<PlayerRef> inside = inClearing(store, players);
        if (inside.isEmpty()) {
            return idle(world, store, dt) ? Outcome.RESET : Outcome.NONE;
        }
        idle = 0f;
        circle(store, inside, dt);
        blooms(store, inside, dt);
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        if (onslaught) {
            stayCentered(store);
            onslaught(world, store, inside, dt);
        } else if (charging) {
            stayCentered(store);
            charge(world, store, inside, dt);
        } else if (stage < THRESHOLDS.length && Hurt.healthFraction(store, boss) <= THRESHOLDS[stage] + 0.001f) {
            if (stage < 2) {
                startOnslaught(world, store);
            } else {
                startCharge(world, store);
            }
        }
        return Outcome.NONE;
    }

    private static List<PlayerRef> inClearing(Store<EntityStore> store, List<PlayerRef> players) {
        Vector3d c = Spawns.point(SwamplandLayout.CLEARING);
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.y() >= c.y() - 4 && at.y() <= c.y() + 10
                    && Telegraphs.horizontal(at, c) <= SwamplandLayout.CLEARING_RADIUS + 1) {
                out.add(p);
            }
        }
        return out;
    }

    /**
     * Le boss au centre, gelé et invulnérable (assaut, charge) : ses attaques en cours sont coupées net (une charge
     * partait au moment où il devenait invulnérable, retour du 2026-10-24).
     */
    private void retreat(World world, Store<EntityStore> store) {
        BossStun.interrupt(world, store, boss);
        Defiance.forget(boss);
        toCenter(store);
        BossStun.hold(world, store, boss);
        store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
    }

    private void toCenter(Store<EntityStore> store) {
        Vector3d c = Spawns.point(SwamplandLayout.CLEARING);
        store.putComponent(boss, Teleport.getComponentType(),
                new Teleport(c, new Rotation3f(0f, Telegraphs.yawToward(c, new Vector3d(c).add(0, 0, 1)), 0f)));
    }

    /** Pendant l'assaut et la charge : s'il a été déplacé (coup en vol, poussée), il revient au centre. */
    private void stayCentered(Store<EntityStore> store) {
        Vector3d at = Telegraphs.position(store, boss);
        if (at != null && Telegraphs.horizontal(at, Spawns.point(SwamplandLayout.CLEARING)) > 1.0) {
            toCenter(store);
        }
    }

    private void comeBack(Store<EntityStore> store) {
        BossStun.release(store, boss);
        store.tryRemoveComponent(boss, Invulnerable.getComponentType());
    }

    // --- assauts -------------------------------------------------------------------------------------------

    private void startOnslaught(World world, Store<EntityStore> store) {
        onslaught = true;
        retreat(world, store);
        spiritsNeeded = 4 + 2 * FractalRuns.partySize(world);
        spiritsSpawned = 0;
        spiritsDown = 0;
        rainClock = RAIN_EVERY - 1.5f;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.onslaught").param("count", spiritsNeeded));
    }

    private void onslaught(World world, Store<EntityStore> store, List<PlayerRef> inside, float dt) {
        spirits.removeIf(ref -> !Spawns.alive(store, ref));
        Vector3d c = Spawns.point(SwamplandLayout.CLEARING);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        while (spirits.size() < SPIRIT_CAP && spiritsSpawned < spiritsNeeded) {
            double a = random.nextDouble(0, Math.PI * 2);
            String animal = Swampland.SPIRITS.get(spiritsSpawned % Swampland.SPIRITS.size());
            Ref<EntityStore> spirit = Spawns.spawnFoe(world, store, animal,
                    new double[]{c.x() + Math.cos(a) * 14, c.y(), c.z() + Math.sin(a) * 14});
            spiritsSpawned++;
            if (spirit != null) {
                spirits.add(spirit);
            } else {
                spiritsDown++;   // refusé par le jeu : ne pas bloquer l'assaut
            }
        }
        rainClock += dt;
        if (rainClock >= RAIN_EVERY) {
            rainClock = 0f;
            rain(world, store);
        }
        if (spiritsDown < spiritsNeeded) {
            return;
        }
        onslaught = false;
        stage++;
        comeBack(store);
        Spawns.removeAll(store, blooms);
        blooms.clear();
        for (int i = 0; i < BLOOMS; i++) {
            double a = random.nextDouble(0, Math.PI * 2);
            double r = random.nextDouble(6, 14);
            Vector3d at = new Vector3d(c.x() + Math.cos(a) * r, c.y(), c.z() + Math.sin(a) * r);
            Ref<EntityStore> bloom = Spawns.spawnFoe(world, store, Swampland.BLOOM, at, 0f);
            if (bloom != null) {
                store.ensureAndGetComponent(bloom, Frozen.getComponentType());
                blooms.add(bloom);
            }
        }
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.back"));
    }

    /** Pluie de poison : {@value #RAIN_DROPS} cercles rouges au hasard dans la clairière. */
    private void rain(World world, Store<EntityStore> store) {
        Vector3d c = Spawns.point(SwamplandLayout.CLEARING);
        float windup = 1.6f * FractalRuns.windupFactor(world);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int i = 0; i < RAIN_DROPS; i++) {
            double a = random.nextDouble(0, Math.PI * 2);
            double r = random.nextDouble(2, 17);
            Vector3d drop = new Vector3d(c.x() + Math.cos(a) * r, c.y(), c.z() + Math.sin(a) * r);
            Telegraphs.circle(store, drop, RAIN_RADIUS, windup);
            Delayed.later(world, windup, s -> {
                Telegraphs.particle(s, "Nakasar_Fractal_Egg_Burst", drop, 1.2f);
                for (PlayerRef p : Spawns.alivePlayers(world, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && Telegraphs.horizontal(at, drop) <= RAIN_RADIUS && Math.abs(at.y() - drop.y()) <= 3) {
                        Hurt.percent(s, p.getReference(), RAIN_PART, "Physical");
                        Hurt.effect(s, p.getReference(), "Poison_T1", 4f);
                    }
                }
            });
        }
    }

    private void blooms(Store<EntityStore> store, List<PlayerRef> inside, float dt) {
        blooms.removeIf(ref -> !Spawns.alive(store, ref));
        pulseClock += dt;
        if (pulseClock < 1f || blooms.isEmpty()) {
            return;
        }
        pulseClock = 0f;
        for (Ref<EntityStore> bloom : blooms) {
            Vector3d b = Telegraphs.position(store, bloom);
            if (b == null) {
                continue;
            }
            Telegraphs.particle(store, "Nakasar_Fractal_Bloom_Pulse", b, 1f);
            for (PlayerRef p : inside) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, b) <= BLOOM_RADIUS) {
                    Hurt.effect(store, p.getReference(), "Poison_T1", 3f);
                }
            }
        }
    }

    // --- charge des feux-follets --------------------------------------------------------------------------

    private void startCharge(World world, Store<EntityStore> store) {
        charging = true;
        retreat(world, store);
        chargeLeft = CHARGE_SECONDS;
        chargeShown = -1;
        lit = 0;
        ChunkStore chunks = world.getChunkStore();
        for (int[] c : SwamplandLayout.CLEARING_CLEFTS) {
            WorldBlocks.swap(chunks, c[0], c[1], c[2], Swampland.CLEFT);
        }
        for (int[] w : SwamplandLayout.CORNER_WISPS) {
            WispRun.place(chunks, w);
        }
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.wisps").param("seconds", (int) CHARGE_SECONDS));
    }

    void cleftLit(World world, Store<EntityStore> store) {
        if (!charging) {
            return;
        }
        lit++;
        int total = SwamplandLayout.CLEARING_CLEFTS.length;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "cleft.lit").param("count", lit).param("total", total));
    }

    private void charge(World world, Store<EntityStore> store, List<PlayerRef> inside, float dt) {
        Vector3d c = Spawns.point(SwamplandLayout.CLEARING);
        chargeLeft -= dt;
        int shown = (int) Math.ceil(chargeLeft);
        if (shown != chargeShown) {
            chargeShown = shown;
            Telegraphs.particle(store, "Nakasar_Fractal_Bloom_Charge", c, 2f);
            if (shown > 0 && (shown % 5 == 0 || shown <= 5)) {
                EventTitleUtil.showEventTitleToWorld(Message.translation(Swampland.MESSAGES + "timer.title"),
                        Message.translation(Swampland.MESSAGES + "timer").param("seconds", shown), EventTitleStyle.Default,
                        null, 1.2f, 0.1f, 0.2f, world);
            }
        }
        if (lit >= SwamplandLayout.CLEARING_CLEFTS.length) {
            endCharge(world, store);
            bigLeft = BIG_SECONDS;
            BossStun.stun(world, store, boss, BIG_STUN, BossStun.EFFECT);
            Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.wisps.done"));
            return;
        }
        if (chargeLeft > 0f) {
            return;
        }
        endCharge(world, store);
        float part = FractalRuns.level(world) >= 76 ? 1f : PURGE_PART;
        Telegraphs.particle(store, "Nakasar_Fractal_Purge", c, 4f);
        for (PlayerRef p : inside) {
            Hurt.percent(store, p.getReference(), part, Swampland.PURGE_CAUSE);
        }
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.purge"));
    }

    private void endCharge(World world, Store<EntityStore> store) {
        charging = false;
        stage++;
        comeBack(store);
        clearCorners(world.getChunkStore());
        takeWisps(world, store);
    }

    // --- remise à zéro -----------------------------------------------------------------------------------

    /** Personne de vivant dans la clairière : vrai au bout de {@value #RESET_SECONDS} s, une fois tout retiré. */
    boolean idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged) {
            return false;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return false;
        }
        clear(world, store);
        engaged = false;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "bloom.reset"));
        return true;
    }

    private void clear(World world, Store<EntityStore> store) {
        if (boss != null) {
            Defiance.forget(boss);
            BossStun.release(store, boss);
            PinnedHealth.unpin(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        Spawns.removeAll(store, spirits);
        spirits.clear();
        Spawns.removeAll(store, blooms);
        blooms.clear();
        onslaught = false;
        charging = false;
        bigLeft = 0f;
        idle = 0f;
        clearCorners(world.getChunkStore());
        takeWisps(world, store);
    }

    private static void clearCorners(ChunkStore chunks) {
        for (int[] w : SwamplandLayout.CORNER_WISPS) {
            if (Swampland.WISP_BLOCK.equals(WorldBlocks.name(chunks, w[0], w[1], w[2]))) {
                WorldBlocks.clear(chunks, w[0], w[1], w[2]);
            }
        }
    }

    private static void takeWisps(World world, Store<EntityStore> store) {
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            if (ref != null && ref.isValid()) {
                Carried.removeAll(store, ref, Swampland.WISP);
            }
        }
    }
}
