package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * La Fureur de la montagne, dans le cratère (GW2). Coups brûlants, bond et ruée : rôle JSON. En Java :
 * <ul>
 *   <li>toutes les {@value #METEOR_EVERY} s, des météores ({@link Meteors}) sous chaque joueur, puis la frappe extrême :
 *   il faut se cacher derrière un météore ;</li>
 *   <li>à 66 et 33 %, elle se divise : protégée et immobile tant que {@value #SPLITS} petits élémentaires de lave
 *   vivent ;</li>
 *   <li>sous 66 % : onde de choc toutes les {@value #SHOCK_EVERY} s (un anneau qui s'élargit au sol : on le saute) et
 *   défiance toutes les {@value #DEFIANCE_EVERY} s ({@value #DEFIANCE_SECONDS} s pour la briser, sinon un brasier frappe
 *   tout le cratère : {@value #INFERNO_PART} des PV) ;</li>
 *   <li>sous 33 % : deux météores qui suivent deux joueurs toutes les {@value #TRACK_EVERY} s.</li>
 * </ul>
 * Personne dans le cratère pendant {@value SunquaPeak#RESET_SECONDS} s : elle retourne au cratère (disparaît, sans
 * soin) et revient neuve au prochain venu.
 */
final class FuryOfTheMountain {

    static final float[] SPLITS_AT = {0.66f, 0.33f};
    static final int SPLITS = 3;
    static final float METEOR_FIRST = 8f;
    static final float METEOR_EVERY = 24f;
    /** La frappe extrême part ce temps après l'appel des météores (leur chute comprise). */
    static final float EXTREME_AFTER = Meteors.WINDUP + 2.5f;
    static final float SHOCK_EVERY = 16f;
    static final double SHOCK_SPEED = 7;
    static final double SHOCK_BAND = 0.75;
    static final float SHOCK_PART = 0.12f;
    static final float DEFIANCE_EVERY = 26f;
    static final float DEFIANCE_SECONDS = 8f;
    static final float INFERNO_PART = 0.4f;
    static final float TRACK_EVERY = 25f;

    private static final class Wave {
        final Vector3d center;
        double radius;
        final Set<UUID> hit = new HashSet<>();

        Wave(Vector3d center) {
            this.center = center;
        }
    }

    private final Meteors meteors = new Meteors();
    private Ref<EntityStore> boss;
    private boolean engaged;
    private final List<Float> thresholds = new ArrayList<>();
    private final List<Ref<EntityStore>> splits = new ArrayList<>();
    private final List<Wave> waves = new ArrayList<>();
    private float idle;
    private float meteor;
    private float extreme = -1f;
    private float shock;
    private float defiance;
    private long defianceUntil;
    private float track;
    private int beat;
    private boolean held;

    boolean shielded() {
        return !splits.isEmpty();
    }

    /** Vrai quand la Fureur est vaincue. */
    boolean step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(SunquaPeakLayout.CRATER);
        double radius = SunquaPeakLayout.CRATER_RADIUS;
        List<PlayerRef> here = SunquaPeak.near(store, players, c, radius + 3);
        if (!engaged) {
            if (!SunquaPeak.near(store, players, c, radius - 2).isEmpty()) {
                engage(world, store, c);
            }
            return false;
        }
        if (boss == null || !boss.isValid() || !Spawns.alive(store, boss)) {
            clear(world, store);
            return true;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= SunquaPeak.RESET_SECONDS) {
                clear(world, store);
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.reset"));
            }
            return false;
        }
        idle = 0f;
        Leash.keepOnDisc(store, boss, c, radius - 2, 2, SunquaPeak.FALL_LIMIT);
        splits.removeIf(ref -> !Spawns.alive(store, ref));
        if (shielded()) {
            BossStun.hold(world, store, boss);
            Vector3d at = Telegraphs.position(store, boss);
            if (++beat % 2 == 0 && at != null) {
                Telegraphs.particle(store, "Golem_Fire_Glow", at, 1.5f);
            }
            return false;
        }
        if (held) {
            held = false;
            BossStun.release(store, boss);
        }
        float health = Hurt.healthFraction(store, boss);
        if (!thresholds.isEmpty() && health <= thresholds.get(0) + 0.001f) {
            thresholds.remove(0);
            split(world, store, st, c);
            return false;
        }
        meteor += dt;
        if (meteor >= METEOR_EVERY) {
            meteor = 0f;
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.meteors"));
            meteors.call(world, store, here);
            extreme = EXTREME_AFTER;
        }
        if (extreme >= 0f) {
            extreme -= dt;
            if (extreme < 0f) {
                meteors.extreme(world, store, boss, c, radius + 2, "fury.extreme");
            }
        }
        if (health <= SPLITS_AT[0]) {
            shock += dt;
            if (shock >= SHOCK_EVERY) {
                shock = 0f;
                Vector3d at = Telegraphs.position(store, boss);
                if (at != null) {
                    waves.add(new Wave(at));
                    Telegraphs.particle(store, "Stick_Slam_Ground_Large", at, 1.5f);
                }
            }
            defianceStep(world, store, here, dt);
        }
        if (health <= SPLITS_AT[1]) {
            track += dt;
            if (track >= TRACK_EVERY) {
                track = 0f;
                meteors.track(world, store, here);
            }
        }
        return false;
    }

    private void defianceStep(World world, Store<EntityStore> store, List<PlayerRef> here, float dt) {
        long now = System.nanoTime();
        if (defianceUntil != 0) {
            if (!Defiance.isOpen(boss) && now < defianceUntil - Telegraphs.seconds(0.15f)) {
                defianceUntil = 0;   // brisée : la Fureur est étourdie (Defiance)
                return;
            }
            if (now >= defianceUntil) {
                defianceUntil = 0;
                Defiance.forget(boss);
                inferno(world, store, here);
            }
            return;
        }
        defiance += dt;
        if (defiance >= DEFIANCE_EVERY) {
            defiance = 0f;
            Defiance.open(world, boss, DEFIANCE_SECONDS);
            defianceUntil = now + Telegraphs.seconds(DEFIANCE_SECONDS);
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.defiance"));
        }
    }

    /** La défiance a tenu : un brasier frappe tout le cratère. */
    private void inferno(World world, Store<EntityStore> store, List<PlayerRef> here) {
        Vector3d at = Telegraphs.position(store, boss);
        if (at != null) {
            Telegraphs.particle(store, "Fire_AoE_Spawn", at, 3f);
            Telegraphs.sound(store, "SFX_Gobliterator_Barrel_Explosion", at);
        }
        for (PlayerRef p : here) {
            Hurt.percent(store, p.getReference(), INFERNO_PART, SunquaPeak.CAUSE);
            Hurt.effect(store, p.getReference(), SunquaPeak.BURNING, 4f);
        }
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.inferno"));
    }

    private void split(World world, Store<EntityStore> store, SunquaPeak.State st, Vector3d c) {
        BossStun.interrupt(world, store, boss);
        held = true;
        // Une défiance ouverte se ferme : son minuteur ne doit pas courir pendant la division (brasier sans annonce).
        defianceUntil = 0;
        defiance = 0f;
        Defiance.forget(boss);
        Vector3d at = Telegraphs.position(store, boss);
        Vector3d from = at == null ? c : at;
        for (int k = 0; k < SPLITS; k++) {
            double a = k * Math.PI * 2 / SPLITS;
            Vector3d where = SunquaPeak.ground(world, new Vector3d(from.x() + Math.cos(a) * 3, from.y(), from.z() + Math.sin(a) * 3));
            Ref<EntityStore> ref = st.foe(world, store, SunquaPeak.LAVA_EMBER, where, null, false);
            if (ref != null) {
                splits.add(ref);
            }
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Lava_Blast", from, 2f);
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "lava.split"));
    }

    /** Un tick du monde : ondes de choc et météores qui suivent. */
    void tick(World world, Store<EntityStore> store, float dt) {
        meteors.tick(world, store, dt);
        if (waves.isEmpty()) {
            return;
        }
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        for (int i = waves.size() - 1; i >= 0; i--) {
            Wave wv = waves.get(i);
            double before = wv.radius;
            wv.radius += SHOCK_SPEED * dt;
            if (wv.radius > SunquaPeakLayout.CRATER_RADIUS + 2) {
                waves.remove(i);
                continue;
            }
            if ((int) (before * 2) != (int) (wv.radius * 2)) {
                int n = Math.max(8, (int) (wv.radius * 2.5));
                for (int k = 0; k < n; k++) {
                    double a = k * Math.PI * 2 / n;
                    Telegraphs.particle(store, "Nakasar_Fractal_Shockwave", new Vector3d(wv.center.x() + Math.cos(a) * wv.radius,
                            wv.center.y(), wv.center.z() + Math.sin(a) * wv.radius), 0.6f);
                }
            }
            for (PlayerRef p : players) {
                if (wv.hit.contains(p.getUuid())) {
                    continue;
                }
                Ref<EntityStore> ref = p.getReference();
                Vector3d at = Telegraphs.position(store, ref);
                if (at == null || Math.abs(at.y() - wv.center.y()) > 1.5 || !Moves.onGround(store, ref)) {
                    continue;
                }
                double d = Telegraphs.horizontal(at, wv.center);
                if (Math.abs(d - wv.radius) <= SHOCK_BAND + Telegraphs.BODY) {
                    wv.hit.add(p.getUuid());
                    Hurt.percent(store, ref, SHOCK_PART, SunquaPeak.CAUSE);
                    Hurt.effect(store, ref, SunquaPeak.KNOCKED_DOWN, 1f);
                }
            }
        }
    }

    private void engage(World world, Store<EntityStore> store, Vector3d c) {
        boss = Spawns.spawnBoss(world, store, SunquaPeak.FURY, c, Telegraphs.yawToward(c,
                Spawns.point(SunquaPeakLayout.WALL_GUARDS[SunquaPeakLayout.WALL_GUARDS.length - 1][0])));
        if (boss == null) {
            return;
        }
        engaged = true;
        held = false;
        idle = 0f;
        meteor = METEOR_EVERY - METEOR_FIRST;
        extreme = -1f;
        shock = 0f;
        defiance = 0f;
        defianceUntil = 0;
        track = 0f;
        thresholds.clear();
        for (float f : SPLITS_AT) {
            thresholds.add(f);
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Lava_Blast", c, 2.5f);
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.enter"));
    }

    private void clear(World world, Store<EntityStore> store) {
        meteors.clear(world, store);
        waves.clear();
        Spawns.removeAll(store, splits);
        splits.clear();
        if (boss != null) {
            BossStun.release(store, boss);
            Defiance.forget(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
    }
}
