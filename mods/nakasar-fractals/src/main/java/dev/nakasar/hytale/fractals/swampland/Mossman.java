package dev.nakasar.hytale.fractals.swampland;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Box;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Le Moussu, d'après GW2 : il surgit quand on entre dans la salle de l'embuscade, qui se referme derrière.
 * <ul>
 *   <li>toutes les {@value #WOLF_EVERY} s, il appelle des loups (2 + 1 pour deux joueurs, {@value #WOLF_CAP} vivants
 *   au plus) ;</li>
 *   <li>toutes les {@value #STEALTH_EVERY} s, sous sa forme humaine, il disparaît ({@value #HIDE_SECONDS} s dans une
 *   cachette fermée, invulnérable), puis surgit près d'un joueur : ligne rouge de {@value #STRIKE_LENGTH} blocs,
 *   défiance ouverte ; brisée, l'attaque tombe à l'eau et il est étourdi, sinon {@value #STRIKE_PART} des PV et
 *   étourdissement ;</li>
 *   <li>sous {@value #BEAST_AT} de vie, il prend sa forme sauvage (bonds et griffes), sans plus se cacher.</li>
 * </ul>
 * Personne de vivant dans la salle pendant {@value #RESET_SECONDS} s : il se retire et la salle se rouvre.
 */
final class Mossman {

    enum Outcome { NONE, WON, RESET }

    static final float WOLF_EVERY = 18f;
    static final int WOLF_CAP = 6;
    static final float STEALTH_EVERY = 20f;
    static final float HIDE_SECONDS = 3f;
    static final float STRIKE_WINDUP = 1.6f;
    static final double STRIKE_LENGTH = 9;
    static final double STRIKE_WIDTH = 3;
    static final float STRIKE_PART = 0.35f;
    static final float BEAST_AT = 0.5f;
    static final float RESET_SECONDS = 20f;
    /** La salle et son entrée, jusqu'à la barrière de derrière. */
    static final Box ARENA = new Box(-10, 10, 95, 110, -86, -51);

    private Ref<EntityStore> boss;
    private final List<Ref<EntityStore>> wolves = new ArrayList<>();
    private boolean engaged;
    private boolean beast;
    private boolean hidden;
    private boolean striking;
    private volatile boolean dead;
    private float wolfClock;
    private float stealthClock;
    private float hideClock;
    private float idle;

    List<Ref<EntityStore>> foes() {
        List<Ref<EntityStore>> out = new ArrayList<>(wolves);
        if (boss != null) {
            out.add(boss);
        }
        return out;
    }

    void down() {
        dead = true;
    }

    void ambush(World world, Store<EntityStore> store) {
        Vector3d at = Spawns.point(SwamplandLayout.MOSSMAN);
        boss = Spawns.spawnBoss(world, store, Swampland.MOSSMAN, at, Telegraphs.yawToward(at, new Vector3d(at).add(0, 0, 1)));
        Telegraphs.particle(store, "Nakasar_Fractal_Stealth_Smoke", at, 2f);
        engaged = true;
        beast = false;
        hidden = false;
        striking = false;
        dead = false;
        wolfClock = WOLF_EVERY - 6f;
        stealthClock = 0f;
        idle = 0f;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "mossman.ambush"));
    }

    Outcome step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        if (!engaged) {
            return Outcome.NONE;
        }
        if (dead) {
            clear(store);
            engaged = false;
            return Outcome.WON;
        }
        List<PlayerRef> inside = Spawns.in(store, players, ARENA);
        if (inside.isEmpty()) {
            return idle(world, store, dt) ? Outcome.RESET : Outcome.NONE;
        }
        idle = 0f;
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        wolves(world, store, dt);
        if (!beast && !hidden && !striking && Hurt.healthFraction(store, boss) <= BEAST_AT) {
            swap(world, store);
            return Outcome.NONE;
        }
        if (beast) {
            return Outcome.NONE;
        }
        if (hidden) {
            hideClock -= dt;
            if (hideClock <= 0f) {
                emerge(world, store, inside);
            }
        } else if (!striking) {
            stealthClock += dt;
            if (stealthClock >= STEALTH_EVERY) {
                hide(world, store);
            }
        }
        return Outcome.NONE;
    }

    // --- loups -------------------------------------------------------------------------------------------

    private void wolves(World world, Store<EntityStore> store, float dt) {
        wolves.removeIf(ref -> !Spawns.alive(store, ref));
        wolfClock += dt;
        if (wolfClock < WOLF_EVERY || hidden) {
            return;
        }
        wolfClock = 0f;
        Vector3d at = Telegraphs.position(store, boss);
        if (at == null) {
            return;
        }
        int count = Math.min(WOLF_CAP - wolves.size(), 2 + FractalRuns.partySize(world) / 2);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int i = 0; i < count; i++) {
            double a = random.nextDouble(0, Math.PI * 2);
            double[] p = clamp(at.x() + Math.cos(a) * 2.5, at.y(), at.z() + Math.sin(a) * 2.5);
            Ref<EntityStore> wolf = Spawns.spawnFoe(world, store, Swampland.MOSS_WOLF, p);
            if (wolf != null) {
                wolves.add(wolf);
            }
        }
        if (count > 0) {
            Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "mossman.wolves"));
        }
    }

    // --- furtivité ---------------------------------------------------------------------------------------

    private void hide(World world, Store<EntityStore> store) {
        Vector3d at = Telegraphs.position(store, boss);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Stealth_Smoke", at, 2f);
        }
        BossStun.hold(world, store, boss);
        store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(Spawns.point(SwamplandLayout.POCKET), new Rotation3f()));
        hidden = true;
        hideClock = HIDE_SECONDS;
        stealthClock = 0f;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "mossman.stealth"));
    }

    /** Il surgit à quelques blocs d'un joueur, face à lui : ligne rouge, défiance ouverte pendant l'annonce. */
    private void emerge(World world, Store<EntityStore> store, List<PlayerRef> inside) {
        hidden = false;
        PlayerRef target = inside.get(ThreadLocalRandom.current().nextInt(inside.size()));
        Vector3d goal = Telegraphs.position(store, target.getReference());
        store.tryRemoveComponent(boss, Invulnerable.getComponentType());
        if (goal == null) {
            BossStun.release(store, boss);
            return;
        }
        double a = ThreadLocalRandom.current().nextDouble(0, Math.PI * 2);
        double[] p = clamp(goal.x() + Math.cos(a) * 5, goal.y(), goal.z() + Math.sin(a) * 5);
        Vector3d from = new Vector3d(p[0], p[1], p[2]);
        store.putComponent(boss, Teleport.getComponentType(),
                new Teleport(from, new Rotation3f(0f, Telegraphs.yawToward(from, goal), 0f)));
        Telegraphs.particle(store, "Nakasar_Fractal_Stealth_Smoke", from, 2f);
        float windup = STRIKE_WINDUP * FractalRuns.windupFactor(world);
        Defiance.open(world, boss, windup + 0.5f);
        double facing = Math.atan2(goal.z() - from.z(), goal.x() - from.x());
        Telegraphs.Strip strip = new Telegraphs.Strip(from, facing, STRIKE_LENGTH, STRIKE_WIDTH, System.nanoTime(), windup);
        Ref<EntityStore> caster = boss;
        striking = true;
        TelegraphSystem.start(world, (w, s, now) -> {
            if (!caster.isValid()) {
                striking = false;
                return true;
            }
            if (!strip.step(s, now)) {
                return false;
            }
            striking = false;
            BossStun.release(s, caster);
            if (!Defiance.isOpen(caster)) {   // défiance brisée pendant l'annonce : l'attaque tombe à l'eau
                BossStun.stun(w, s, caster, Defiance.STUN_SECONDS, BossStun.EFFECT);
                return true;
            }
            Defiance.forget(caster);
            for (PlayerRef p2 : Spawns.alivePlayers(w, s)) {
                Vector3d at = Telegraphs.position(s, p2.getReference());
                if (at != null && strip.contains(at)) {
                    Hurt.percent(s, p2.getReference(), STRIKE_PART, "Physical");
                    Hurt.effect(s, p2.getReference(), "Hazard_Electric_Stun", 1.5f);
                }
            }
            Telegraphs.particle(s, "Stick_Slam_Ground_Large", strip.at(STRIKE_LENGTH / 2, 0), 1.2f);
            Telegraphs.sound(s, "SFX_Mace_T2_Signature_Impact", strip.at(STRIKE_LENGTH / 2, 0));
            return true;
        });
    }

    /** Garde un point dans la salle. */
    private static double[] clamp(double x, double y, double z) {
        return new double[]{Math.max(-7.5, Math.min(8.5, x)), y, Math.max(-82.5, Math.min(-60.5, z))};
    }

    // --- forme sauvage -----------------------------------------------------------------------------------

    private void swap(World world, Store<EntityStore> store) {
        Vector3d at = Telegraphs.position(store, boss);
        float fraction = Hurt.healthFraction(store, boss);
        if (at == null) {
            return;
        }
        at = new Vector3d(at);
        float yaw = (float) ThreadLocalRandom.current().nextDouble(-Math.PI, Math.PI);
        Defiance.forget(boss);
        Spawns.remove(store, boss);
        boss = Spawns.spawnBoss(world, store, Swampland.MOSSMAN_BEAST, at, yaw);
        beast = true;
        EntityStatMap stats = boss == null ? null : store.getComponent(boss, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.max(1f, health.getMax() * fraction));
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Stealth_Smoke", at, 2.5f);
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "mossman.beast"));
    }

    // --- remise à zéro -----------------------------------------------------------------------------------

    /** Personne de vivant dans la salle : vrai au bout de {@value #RESET_SECONDS} s, une fois tout retiré. */
    boolean idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged) {
            return false;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return false;
        }
        clear(store);
        engaged = false;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "mossman.reset"));
        return true;
    }

    private void clear(Store<EntityStore> store) {
        if (boss != null) {
            Defiance.forget(boss);
            BossStun.release(store, boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        Spawns.removeAll(store, wolves);
        wolves.clear();
        hidden = false;
        striking = false;
        idle = 0f;
    }
}
