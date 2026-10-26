package dev.nakasar.hytale.fractals.deepstone;

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
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * La Sentinelle de la Roche des Abysses, sur sa corniche ouverte au vide à l'ouest (GW2). Souffle glacé et coup de vent :
 * rôle JSON. En Java :
 * <ul>
 *   <li>toutes les {@value #SPIRAL_EVERY} s, une spirale de vent : {@value #SPIRAL_COUNT} cercles rouges de
 *   {@value #SPIRAL_RADIUS} blocs qui partent d'elle en tournant, l'un après l'autre ; touché : {@value #SPIRAL_PART}
 *   des PV et Hébété. Sous elle, on ne risque rien ;</li>
 *   <li>à 80, 50 et 20 % (et 65 et 35 % à partir du rang Expert), des esprits du vent : un cercle rouge de
 *   {@value #SPRITE_RADIUS} blocs sous un joueur ({@value #SPRITE_WINDUP} s) ; qui y est encore est emporté (Emporté :
 *   ni mouvement ni action) et l'esprit file vers le bout ouest de la corniche. Sa défiance brisée ou l'esprit tué, il se dissipe et
 *   relâche ses prises ; au bord, il les jette dans le vide (retour au point de retour par le filet anti-chute) ;</li>
 *   <li>personne sur la corniche pendant {@value #RESET_SECONDS} s : elle se fond dans le vent (pas de soin, AGENTS.md :
 *   elle revient neuve au prochain venu).</li>
 * </ul>
 */
final class Sentinel {

    static final float SPIRAL_FIRST = 10f;
    static final float SPIRAL_EVERY = 18f;
    static final int SPIRAL_COUNT = 12;
    static final double SPIRAL_RADIUS = 2.5;
    static final float SPIRAL_WINDUP = 1.8f;
    static final float SPIRAL_PART = 0.12f;
    static final double SAFE = 2.5;
    static final float[] SPRITES_AT = {0.8f, 0.5f, 0.2f};
    static final float[] SPRITES_HARD = {0.65f, 0.35f};
    static final double SPRITE_RADIUS = 2.5;
    static final float SPRITE_WINDUP = 1.8f;
    static final double SPRITE_SPEED = 1.4;
    static final float SPRITE_DEFIANCE = 60f;
    static final float RESET_SECONDS = 20f;
    static final String CAPTURED = "Nakasar_Fractal_Captured";

    private static final class Sprite {
        final Ref<EntityStore> ref;
        final List<PlayerRef> captives = new ArrayList<>();
        Vector3d at;

        Sprite(Ref<EntityStore> ref, Vector3d at) {
            this.ref = ref;
            this.at = new Vector3d(at);
        }
    }

    private Ref<EntityStore> boss;
    private boolean engaged;
    private boolean done;
    private final List<Sprite> sprites = new ArrayList<>();
    private final List<Float> thresholds = new ArrayList<>();
    private float spiral;
    private float idle;
    private long lastTick;
    private int epoch;

    boolean done() {
        return done;
    }

    private boolean live(int e) {
        return engaged && epoch == e;
    }

    void step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        if (done || !st.grid.solved()) {
            return;
        }
        Vector3d c = Spawns.point(DeepstoneLayout.SENTINEL);
        List<PlayerRef> here = Deepstone.near(store, players, c, DeepstoneLayout.SENTINEL_RADIUS + 3);
        if (!engaged) {
            if (!Deepstone.near(store, players, c, DeepstoneLayout.SENTINEL_RADIUS - 3).isEmpty()) {
                engage(world, store, st, c);
            }
            return;
        }
        if (boss == null || !boss.isValid() || !Spawns.alive(store, boss)) {
            win(world, store, st);
            return;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                clear(store);
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "sentinel.reset"));
                return;
            }
        } else {
            idle = 0f;
        }
        Leash.keepOnDisc(store, boss, c, DeepstoneLayout.SENTINEL_RADIUS - 3, 2, Deepstone.FALL_LIMIT);
        float health = Hurt.healthFraction(store, boss);
        if (!thresholds.isEmpty() && health <= thresholds.get(0) + 0.001f) {
            thresholds.remove(0);
            sprites(world, store, here);
        }
        spiral += dt;
        if (spiral >= SPIRAL_EVERY && !BossStun.isStunned(boss)) {
            spiral = 0f;
            spiral(world, store);
        }
    }

    private void engage(World world, Store<EntityStore> store, Deepstone.State st, Vector3d c) {
        boss = st.boss(world, store, Deepstone.SENTINEL, c, Spawns.point(DeepstoneLayout.GRID_END));
        if (boss == null) {
            return;
        }
        engaged = true;
        epoch++;
        spiral = SPIRAL_EVERY - SPIRAL_FIRST;
        idle = 0f;
        thresholds.clear();
        for (float f : SPRITES_AT) {
            thresholds.add(f);
        }
        if (Deepstone.rank(world) >= 2) {
            for (float f : SPRITES_HARD) {
                thresholds.add(f);
            }
        }
        thresholds.sort((a, b) -> Float.compare(b, a));
        Telegraphs.particle(store, "Nakasar_Fractal_Sentinel_Burst", c, 2f);
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "sentinel.enter"));
    }

    private void win(World world, Store<EntityStore> store, Deepstone.State st) {
        clear(store);
        done = true;
        Deepstone.dropOrb(world, st, 0);
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "sentinel.victory"));
    }

    /** Spirale : des cercles qui partent de la Sentinelle en tournant, l'un après l'autre. */
    private void spiral(World world, Store<EntityStore> store) {
        Vector3d c = Telegraphs.position(store, boss);
        if (c == null) {
            return;
        }
        Vector3d center = new Vector3d(c);
        float windup = SPIRAL_WINDUP * FractalRuns.windupFactor(world);
        double turn = Math.random() * Math.PI * 2;
        Vector3d[] points = new Vector3d[SPIRAL_COUNT];
        for (int i = 0; i < SPIRAL_COUNT; i++) {
            double a = turn + i * 0.9;
            double r = SAFE + SPIRAL_RADIUS + i * 0.85;
            points[i] = new Vector3d(center.x() + Math.cos(a) * r, center.y(), center.z() + Math.sin(a) * r);
        }
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "sentinel.spiral"));
        int e = epoch;
        long begin = System.nanoTime();
        Telegraphs.Circle[] circles = new Telegraphs.Circle[SPIRAL_COUNT];
        boolean[] fired = new boolean[SPIRAL_COUNT];
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            boolean all = true;
            for (int i = 0; i < SPIRAL_COUNT; i++) {
                if (fired[i]) {
                    continue;
                }
                all = false;
                if (circles[i] == null) {
                    if (t < begin + Telegraphs.seconds(0.25f * i)) {
                        continue;
                    }
                    circles[i] = new Telegraphs.Circle(points[i], SPIRAL_RADIUS, t, windup);
                }
                if (!circles[i].step(s, t)) {
                    continue;
                }
                fired[i] = true;
                Telegraphs.particle(s, "Nakasar_Fractal_Sentinel_Burst", points[i], 1f);
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d pos = Telegraphs.position(s, p.getReference());
                    if (pos != null && circles[i].contains(pos)) {
                        Hurt.percent(s, p.getReference(), SPIRAL_PART, Deepstone.CAUSE);
                        Hurt.effect(s, p.getReference(), "Nakasar_Fractal_Dazed", 2f);
                    }
                }
            }
            return all;
        });
    }

    /** Esprits du vent : un cercle sous des joueurs au hasard ; qui y reste est emporté. */
    private void sprites(World world, Store<EntityStore> store, List<PlayerRef> here) {
        if (here.isEmpty()) {
            return;
        }
        int count = Math.min(here.size(), 1 + (FractalRuns.partySize(world) + 1) / 2);
        List<PlayerRef> targets = Spawns.pick(here, count);
        float windup = SPRITE_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (PlayerRef p : targets) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                circles.add(new Telegraphs.Circle(at, SPRITE_RADIUS, now, windup));
            }
        }
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "sentinel.sprites"));
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
                Ref<EntityStore> ref = Spawns.spawnFoe(w, s, Deepstone.WIND_SPRITE, c.origin(), 0f);
                if (ref == null) {
                    continue;
                }
                Spawns.noLoot(s, ref);
                Defiance.open(w, ref, SPRITE_DEFIANCE);
                Sprite sprite = new Sprite(ref, c.origin());
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d pos = Telegraphs.position(s, p.getReference());
                    if (pos != null && c.contains(pos) && !captured(p.getUuid())) {
                        sprite.captives.add(p);
                        p.sendMessage(Message.translation(Deepstone.MESSAGES + "sprite.caught"));
                    }
                }
                sprites.add(sprite);
                Telegraphs.particle(s, "Nakasar_Fractal_Sprite_Whirl", c.origin(), 1.2f);
            }
            return true;
        });
    }

    private boolean captured(UUID uuid) {
        for (Sprite s : sprites) {
            for (PlayerRef p : s.captives) {
                if (p.getUuid().equals(uuid)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** À chaque tick : les esprits filent vers le bord, leurs prises avec eux. */
    void tick(World world, Store<EntityStore> store, Deepstone.State st, long now) {
        float dt = lastTick == 0 ? 0f : Math.min(0.2f, (now - lastTick) / 1e9f);
        lastTick = now;
        if (sprites.isEmpty()) {
            return;
        }
        for (int i = sprites.size() - 1; i >= 0; i--) {
            Sprite s = sprites.get(i);
            boolean dead = !Spawns.alive(store, s.ref);
            boolean broken = !dead && !Defiance.isOpen(s.ref);
            if (dead || broken) {
                release(store, s, false);
                Telegraphs.particle(store, "Nakasar_Fractal_Sentinel_Burst", s.at, 1f);
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "sprite.broken"));
                Defiance.forget(s.ref);
                Spawns.remove(store, s.ref);
                sprites.remove(i);
                continue;
            }
            // Vers la pointe ouest de la corniche : la ligne droite reste sur la corniche (disque).
            Vector3d edge = new Vector3d(DeepstoneLayout.SENTINEL_EDGE_X - 0.5, s.at.y(), DeepstoneLayout.SENTINEL[2]);
            double d = Telegraphs.horizontal(s.at, edge);
            if (d <= 0.6) {
                release(store, s, true);
                Defiance.forget(s.ref);
                Spawns.remove(store, s.ref);
                sprites.remove(i);
                continue;
            }
            double k = Math.min(1.0, SPRITE_SPEED * dt / d);
            s.at = new Vector3d(s.at.x() + (edge.x() - s.at.x()) * k, s.at.y(), s.at.z() + (edge.z() - s.at.z()) * k);
            Deepstone.move(store, s.ref, s.at, edge);
            for (PlayerRef p : s.captives) {
                Ref<EntityStore> ref = p.getReference();
                if (ref == null || !ref.isValid()) {
                    continue;
                }
                Hurt.effect(store, ref, CAPTURED, 0.6f);
                Moves.teleport(store, ref, new Vector3d(s.at.x() + 0.6, s.at.y() + 0.4, s.at.z()));
            }
            if ((now / 250_000_000L) % 2 == 0) {
                Telegraphs.particle(store, "Nakasar_Fractal_Sprite_Whirl", s.at, 0.8f);
            }
        }
    }

    private static void release(Store<EntityStore> store, Sprite s, boolean throwOff) {
        for (PlayerRef p : s.captives) {
            Ref<EntityStore> ref = p.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            Hurt.clear(store, ref, CAPTURED);
            if (throwOff) {
                Moves.velocity(store, ref, new Vector3d(-11, 6, 0));
                p.sendMessage(Message.translation(Deepstone.MESSAGES + "sprite.thrown"));
            }
        }
        s.captives.clear();
    }

    void clear(Store<EntityStore> store) {
        for (Sprite s : sprites) {
            release(store, s, false);
            Defiance.forget(s.ref);
            Spawns.remove(store, s.ref);
        }
        sprites.clear();
        if (boss != null) {
            BossStun.release(store, boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
        epoch++;
    }
}
