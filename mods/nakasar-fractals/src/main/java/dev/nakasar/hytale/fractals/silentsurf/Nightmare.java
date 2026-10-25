package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les deux attaques du cauchemar que Dolus partage avec Kanaxai (GW2) :
 * <ul>
 *   <li>{@link #dread} Visage de l'effroi : un grand œil s'ouvre au-dessus du lanceur ; au bout de {@value #DREAD_WINDUP}
 *   s, qui le regarde encore (moins de {@value #DREAD_ANGLE}° entre son regard et le lanceur) perd
 *   {@value #DREAD_PART} de ses PV, prend Peur (repoussé, sans pouvoir agir) et Tourment ;</li>
 *   <li>{@link #speed} Vitesse effrayante : cinq marques numérotées I à V au sol ; le lanceur bondit de l'une à l'autre
 *   dans l'ordre (cercle rouge, {@value #DASH_PART} des PV et projection), puis revient à son point de départ.</li>
 * </ul>
 */
final class Nightmare {

    static final float DREAD_WINDUP = 2.6f;
    static final double DREAD_ANGLE = 60;
    static final double DREAD_RANGE = 45;
    static final float DREAD_PART = 0.25f;
    static final int MARKS = 5;
    static final float SPEED_WINDUP = 4f;
    static final float DASH_EVERY = 0.7f;
    static final double DASH_RADIUS = 3.5;
    static final float DASH_PART = 0.3f;

    private Nightmare() {
    }

    /** Visage de l'effroi de `caster` (nom `nameKey`). */
    static void dread(World world, Store<EntityStore> store, Ref<EntityStore> caster, String nameKey) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return;
        }
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "dread").param("name", Message.translation(nameKey)));
        Telegraphs.particle(store, "Nakasar_Fractal_Dread_Eye", new Vector3d(at).add(0, 4.5, 0), 1f);
        Telegraphs.sound(store, "SFX_Spear_Throw_Charge", at);
        float windup = DREAD_WINDUP * FractalRuns.windupFactor(world);
        long[] begin = {-1};
        TelegraphSystem.start(world, new TelegraphSystem.Task() {
            @Override
            public boolean step(World w, Store<EntityStore> s, long now) {
                if (begin[0] < 0) {
                    begin[0] = now;
                }
                if (now - begin[0] < Telegraphs.seconds(windup)) {
                    return false;
                }
                Vector3d from = Telegraphs.position(s, caster);
                if (from == null) {
                    return true;
                }
                Telegraphs.particle(s, "Nakasar_Fractal_Dread_Wave", from, 1.5f);
                double cos = Math.cos(Math.toRadians(DREAD_ANGLE));
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Ref<EntityStore> ref = p.getReference();
                    Vector3d pos = Telegraphs.position(s, ref);
                    Vector3d look = Moves.look(s, ref);
                    if (pos == null || look == null || pos.distance(from) > DREAD_RANGE) {
                        continue;
                    }
                    Vector3d eye = new Vector3d(pos).add(0, 1.6, 0);
                    Vector3d to = new Vector3d(from).add(0, 2.5, 0).sub(eye).normalize();
                    if (to.dot(look) < cos) {
                        continue;   // regard détourné
                    }
                    Hurt.percent(s, ref, DREAD_PART, SilentSurf.TORMENT_CAUSE);
                    Hurt.effect(s, ref, "Nakasar_Fractal_Fear", 2f);
                    Hurt.effect(s, ref, "Nakasar_Fractal_Torment", 6f);
                    Vector3d away = new Vector3d(pos).sub(from);
                    away.y = 0;
                    if (away.lengthSquared() < 1e-4) {
                        away.set(1, 0, 0);
                    }
                    Moves.velocity(s, ref, away.normalize().mul(9).add(0, 4, 0));
                    p.sendMessage(Message.translation(SilentSurf.MESSAGES + "dread.hit"));
                }
                return true;
            }

            @Override
            public Ref<EntityStore> caster() {
                return caster;
            }
        });
    }

    /**
     * Vitesse effrayante de `caster` autour de `center` (rayon `radius`) ; `done` est appelé quand il est revenu.
     * Le lanceur est figé ({@link BossStun#hold}) pendant toute la série.
     */
    static void speed(World world, Store<EntityStore> store, Ref<EntityStore> caster, String nameKey, Vector3d center,
                      double radius, Runnable done) {
        Vector3d home = Telegraphs.position(store, caster);
        if (home == null) {
            done.run();
            return;
        }
        home = new Vector3d(home);
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "speed").param("name", Message.translation(nameKey)));
        List<Vector3d> marks = new ArrayList<>();
        double start = ThreadLocalRandom.current().nextDouble(0, Math.PI * 2);
        int[] order = {0, 2, 4, 1, 3};      // une étoile : on traverse l'arène à chaque bond
        for (int i = 0; i < MARKS; i++) {
            double a = start + order[i] * Math.PI * 2 / MARKS;
            double r = radius * (0.55 + 0.4 * ThreadLocalRandom.current().nextDouble());
            marks.add(new Vector3d(center.x() + Math.cos(a) * r, center.y(), center.z() + Math.sin(a) * r));
        }
        BossStun.hold(world, store, caster);
        float windup = SPEED_WINDUP * FractalRuns.windupFactor(world);
        long now0 = System.nanoTime();
        // Un cercle rouge sous chaque numéro, de la taille exacte du coup d'arrivée (Kevin, 25 octobre 2026) : posé pour
        // se remplir pile à l'arrivée du lanceur (une annonce dure 6 s au plus : les dernières sont posées plus tard).
        Telegraphs.Circle[] circles = new Telegraphs.Circle[MARKS];
        Vector3d back = home;
        long[] shown = {0};
        int[] next = {0};
        TelegraphSystem.start(world, new TelegraphSystem.Task() {
            @Override
            public boolean step(World w, Store<EntityStore> s, long now) {
                if (!caster.isValid()) {
                    done.run();
                    return true;
                }
                for (int i = next[0]; i < MARKS; i++) {
                    long hit = now0 + Telegraphs.seconds(windup + i * DASH_EVERY);
                    if (circles[i] == null && hit - now <= Telegraphs.seconds(Telegraphs.WARNING_MAX_SECONDS)) {
                        circles[i] = new Telegraphs.Circle(marks.get(i), DASH_RADIUS, now, Math.max(0.5f, (hit - now) / 1e9f));
                    }
                    if (circles[i] != null) {
                        circles[i].step(s, now);
                    }
                }
                if (now - shown[0] > Telegraphs.seconds(1.8f)) {
                    shown[0] = now;
                    for (int i = next[0]; i < MARKS; i++) {
                        Telegraphs.particle(s, "Nakasar_Fractal_Numeral_" + (i + 1), marks.get(i), 1f);
                    }
                }
                long due = now0 + Telegraphs.seconds(windup + next[0] * DASH_EVERY);
                if (now < due) {
                    return false;
                }
                if (next[0] < MARKS) {
                    Vector3d mark = marks.get(next[0]);
                    Vector3d after = next[0] + 1 < MARKS ? marks.get(next[0] + 1) : back;
                    s.putComponent(caster, Teleport.getComponentType(),
                            new Teleport(mark, new Rotation3f(0f, Telegraphs.yawToward(mark, after), 0f)));
                    Telegraphs.particle(s, "Stick_Slam_Ground_Large", mark, 1.2f);
                    Telegraphs.sound(s, "SFX_Goblin_Feastmaster_Slam", mark);
                    for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                        Vector3d pos = Telegraphs.position(s, p.getReference());
                        if (pos != null && Telegraphs.inCircle(pos, mark, DASH_RADIUS)) {
                            Hurt.percent(s, p.getReference(), DASH_PART, "Physical");
                            Vector3d away = new Vector3d(pos).sub(mark);
                            away.y = 0;
                            Moves.velocity(s, p.getReference(), (away.lengthSquared() < 1e-4 ? new Vector3d(1, 0, 0)
                                    : away.normalize()).mul(10).add(0, 5, 0));
                        }
                    }
                    next[0]++;
                    return false;
                }
                s.putComponent(caster, Teleport.getComponentType(),
                        new Teleport(back, new Rotation3f(0f, Telegraphs.yawToward(back, center), 0f)));
                BossStun.release(s, caster);
                done.run();
                return true;
            }

            @Override
            public void abort(World w, Store<EntityStore> s) {
                BossStun.release(s, caster);
                done.run();
            }

            @Override
            public Ref<EntityStore> caster() {
                return caster;
            }
        });
    }
}
