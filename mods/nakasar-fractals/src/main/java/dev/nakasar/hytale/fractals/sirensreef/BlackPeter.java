package dev.nakasar.hytale.fractals.sirensreef;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
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

/**
 * Black Peter la Mèche, dans son fort englouti (GW2). Tromblon et bombes : rôle JSON. En Java :
 * <ul>
 *   <li>toutes les {@value #MINE_EVERY} s, une mine sous chaque joueur du fort : cercle rouge de {@value #MINE_RADIUS}
 *   blocs ({@value #MINE_WINDUP} s), puis {@value #MINE_PART} des PV et projection ;</li>
 *   <li>à 75, 50 et 25 % il sème les mines du fort ({@link ReefMines}, à faire sauter en marchant dessus ou au canon
 *   du rempart) ; au bout de {@value #SWALLOW_FIRST} s, puis toutes les {@value #SWALLOW_EVERY} s, il bondit sur la
 *   plus proche et l'avale : poudre noire (dégâts subis divisés par deux) et défiance ouverte {@value #POWDER_WINDOW} s.
 *   Brisée (coups lourds, boulets du canon), il est étourdi et la poudre se disperse ; sinon il explose : cercle rouge
 *   de {@value #POWDER_RADIUS} blocs ({@value #POWDER_WINDUP} s), {@value #POWDER_PART} des PV ;</li>
 *   <li>à chaque tranche de 10 %, deux fantômes de l'équipage (sans butin) ;</li>
 *   <li>Cyclone de cendres : qui sort du fort pendant le combat brûle ({@value #CINDERS_PART} des PV par seconde) ;</li>
 *   <li>personne dans le fort pendant {@value #RESET_SECONDS} s : il disparaît dans la fumée (pas de soin, AGENTS.md :
 *   il revient neuf au prochain venu, comme Kanaxai).</li>
 * </ul>
 */
final class BlackPeter {

    enum Outcome { NONE, WON, RESET }

    static final float MINE_EVERY = 12f;
    static final float MINE_WINDUP = 2.5f;
    static final double MINE_RADIUS = 3;
    static final float MINE_PART = 0.15f;
    static final float[] SEED_AT = {0.75f, 0.5f, 0.25f};
    static final float SWALLOW_FIRST = 8f;
    static final float SWALLOW_EVERY = 7f;
    static final float POWDER_WINDOW = 20f;
    static final String POWDER_EFFECT = "Nakasar_Fractal_Gunpowder";
    static final double POWDER_RADIUS = 10;
    static final float POWDER_WINDUP = 3f;
    static final float POWDER_PART = 0.35f;
    static final int GHOSTS = 2;
    static final float CINDERS_PART = 0.03f;
    static final float RESET_SECONDS = 20f;

    private Ref<EntityStore> boss;
    private boolean engaged;
    private volatile boolean dead;
    private final List<Ref<EntityStore>> crew = new ArrayList<>();
    private float mineClock;
    private float swallowClock;
    private int seeds;
    private int ghosts;
    private long powderUntil;
    private boolean blowing;
    private float idle;
    private float cindersFx;
    private int epoch;

    boolean engaged() {
        return engaged;
    }

    void down() {
        dead = true;
    }

    boolean engage(World world, Store<EntityStore> store, SirensReef.State st) {
        boss = st.boss(world, store, SirensReef.PETER, SirensReefLayout.PETER, SirensReefLayout.FORT);
        if (boss == null) {
            return false;
        }
        engaged = true;
        dead = false;
        epoch++;
        mineClock = MINE_EVERY - 5f;
        swallowClock = 0f;
        seeds = 0;
        ghosts = 0;
        powderUntil = 0;
        blowing = false;
        idle = 0f;
        Telegraphs.particle(store, "Nakasar_Fractal_Cannon_Smoke", Spawns.point(SirensReefLayout.PETER), 2f);
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "peter.enter"));
        return true;
    }

    private boolean live(int e) {
        return engaged && !dead && epoch == e;
    }

    Outcome step(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        if (!engaged) {
            return Outcome.NONE;
        }
        if (dead) {
            clear(world, store, st);
            return Outcome.WON;
        }
        Vector3d fort = Spawns.point(SirensReefLayout.FORT);
        List<PlayerRef> inside = new ArrayList<>();
        List<PlayerRef> outside = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null) {
                continue;
            }
            double d = Telegraphs.horizontal(at, fort);
            if (d <= SirensReefLayout.FORT_RADIUS) {
                inside.add(p);
            } else if (d <= SirensReefLayout.FORT_RADIUS + 30) {
                outside.add(p);
            }
        }
        if (inside.isEmpty()) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                clear(world, store, st);
                Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "peter.reset"));
                return Outcome.RESET;
            }
        } else {
            idle = 0f;
        }
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        crew.removeIf(ref -> !Spawns.alive(store, ref));
        Leash.keepOnDisc(store, boss, fort, SirensReefLayout.FORT_RADIUS - 1, 3, SirensReef.FALL_LIMIT);
        cinders(store, outside, dt);
        float health = Hurt.healthFraction(store, boss);
        if (ghosts < 9 && health <= 0.9f - 0.1f * ghosts + 0.001f) {
            ghosts++;
            callCrew(world, store, st);
        }
        if (seeds < SEED_AT.length && health <= SEED_AT[seeds] + 0.001f) {
            seeds++;
            seed(world, store, st);
        }
        powder(world, store, st);
        if (blowing || BossStun.isStunned(boss)) {
            return Outcome.NONE;
        }
        mineClock += dt;
        if (mineClock >= MINE_EVERY && !inside.isEmpty()) {
            mineClock = 0f;
            minesUnder(world, store, inside);
        }
        if (st.mines.count(ReefMines.FORT) > 0 && powderUntil == 0) {
            swallowClock += dt;
            if (swallowClock >= SWALLOW_FIRST) {
                swallowClock = SWALLOW_FIRST - SWALLOW_EVERY;
                swallow(world, store, st);
            }
        } else {
            swallowClock = 0f;
        }
        return Outcome.NONE;
    }

    /** Cyclone de cendres : qui combat hors du fort brûle. */
    private void cinders(Store<EntityStore> store, List<PlayerRef> outside, float dt) {
        cindersFx += dt;
        boolean fx = cindersFx >= 1f;
        if (fx) {
            cindersFx = 0f;
        }
        for (PlayerRef p : outside) {
            Ref<EntityStore> ref = p.getReference();
            if (!Hurt.has(store, ref, "Nakasar_Fractal_Cinders")) {
                p.sendMessage(Message.translation(SirensReef.MESSAGES + "peter.cinders"));
            }
            Hurt.effect(store, ref, "Nakasar_Fractal_Cinders", 1.5f);
            Hurt.percent(store, ref, CINDERS_PART * dt, SirensReef.REEF_CAUSE);
            Vector3d at = fx ? Telegraphs.position(store, ref) : null;
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Peter_Bomb", at, 0.4f);
            }
        }
    }

    private void callCrew(World world, Store<EntityStore> store, SirensReef.State st) {
        double[][] spots = SirensReefLayout.FORT_GHOSTS;
        int first = (int) (Math.random() * spots.length);
        for (int i = 0; i < GHOSTS; i++) {
            double[] at = spots[(first + i * 3) % spots.length];
            Ref<EntityStore> ref = st.foe(world, store, SirensReef.GHOST, at, false);
            if (ref != null) {
                crew.add(ref);
                Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", Spawns.point(at), 1f);
            }
        }
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "peter.ghosts"));
    }

    /** Une mine sous chaque joueur du fort. */
    private void minesUnder(World world, Store<EntityStore> store, List<PlayerRef> inside) {
        float windup = MINE_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (PlayerRef p : inside) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                circles.add(new Telegraphs.Circle(at, MINE_RADIUS, now, windup));
                Telegraphs.particle(store, "Nakasar_Fractal_Mine_Fuse", at, 1f);
            }
        }
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            boolean done = true;
            for (Telegraphs.Circle c : circles) {
                done &= c.step(s, t);
            }
            if (!done) {
                return false;
            }
            for (Telegraphs.Circle c : circles) {
                Telegraphs.particle(s, "Nakasar_Fractal_Mine_Blast", c.origin(), 1.2f);
                Telegraphs.sound(s, "SFX_Explosion_Boomshroom", c.origin());
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && c.contains(at)) {
                        Hurt.percent(s, p.getReference(), MINE_PART, SirensReef.REEF_CAUSE);
                        Moves.velocity(s, p.getReference(), new Vector3d(0, 9, 0));
                    }
                }
            }
            return true;
        });
    }

    /** Les mines du fort : à faire sauter avant qu'il ne les avale. */
    private void seed(World world, Store<EntityStore> store, SirensReef.State st) {
        for (double[] at : SirensReefLayout.FORT_MINES) {
            int[] cell = {(int) Math.floor(at[0]), (int) Math.floor(at[1]), (int) Math.floor(at[2])};
            st.mines.add(world, cell, ReefMines.FORT, false);
            Telegraphs.particle(store, "Nakasar_Fractal_Mine_Fuse", Spawns.point(at), 0.6f);
        }
        swallowClock = 0f;
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "peter.mines"));
    }

    /** Il bondit sur la mine la plus proche et l'avale : poudre noire, défiance ouverte. */
    private void swallow(World world, Store<EntityStore> store, SirensReef.State st) {
        Vector3d at = Telegraphs.position(store, boss);
        ReefMines.Mine mine = at == null ? null : st.mines.nearest(ReefMines.FORT, at);
        if (mine == null) {
            return;
        }
        BossStun.interrupt(world, store, boss);
        Vector3d to = mine.center();
        Telegraphs.particle(store, "Nakasar_Fractal_Cannon_Smoke", at, 1f);
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(to, new Rotation3f(0f, Telegraphs.yawToward(at, to), 0f)));
        st.mines.swallow(world, mine);
        Telegraphs.particle(store, "Nakasar_Fractal_Mine_Blast", to, 0.6f);
        Hurt.effect(store, boss, POWDER_EFFECT, POWDER_WINDOW);
        Defiance.open(world, boss, POWDER_WINDOW);
        powderUntil = System.nanoTime() + Telegraphs.seconds(POWDER_WINDOW);
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "peter.powder"));
    }

    /** Défiance brisée : la poudre se disperse ; tenue jusqu'au bout : il explose. */
    private void powder(World world, Store<EntityStore> store, SirensReef.State st) {
        if (powderUntil == 0 || blowing) {
            return;
        }
        long now = System.nanoTime();
        if (!Defiance.isOpen(boss) && now < powderUntil - Telegraphs.seconds(0.15f)) {
            powderUntil = 0;
            Hurt.clear(store, boss, POWDER_EFFECT);
            Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "peter.broken"));
            return;
        }
        if (now < powderUntil - Telegraphs.seconds(POWDER_WINDUP)) {
            return;
        }
        Vector3d at = Telegraphs.position(store, boss);
        if (at == null) {
            return;                     // on réessaie au tick suivant
        }
        blowing = true;
        Vector3d c = new Vector3d(at);
        BossStun.interrupt(world, store, boss);
        BossStun.stun(world, store, boss, POWDER_WINDUP, null);
        Telegraphs.Circle circle = new Telegraphs.Circle(c, POWDER_RADIUS, now, POWDER_WINDUP);
        Telegraphs.particle(store, "Nakasar_Fractal_Mine_Fuse", c, 2f);
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Mine_Blast", c, 3f);
            Telegraphs.sound(s, "SFX_Gobliterator_Self_Destruct_Explosion", c);
            for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && circle.contains(pos)) {
                    Hurt.percent(s, p.getReference(), POWDER_PART, SirensReef.REEF_CAUSE);
                }
            }
            Defiance.forget(boss);
            Hurt.clear(s, boss, POWDER_EFFECT);
            powderUntil = 0;
            blowing = false;
            return true;
        });
    }

    void clear(World world, Store<EntityStore> store, SirensReef.State st) {
        if (boss != null) {
            BossStun.release(store, boss);
            Defiance.forget(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        Spawns.removeAll(store, crew);
        crew.clear();
        st.mines.clear(world, ReefMines.FORT);
        engaged = false;
        epoch++;
        powderUntil = 0;
        blowing = false;
        idle = 0f;
    }
}
