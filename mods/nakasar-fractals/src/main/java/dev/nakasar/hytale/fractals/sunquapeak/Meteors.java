package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Météores de la Fureur de la montagne et d'Ai (phase de feu), d'après GW2 :
 * <ul>
 *   <li>appel : un cercle rouge de {@value #RADIUS} blocs sous chaque joueur ; à l'impact, {@value #PART} des PV et à
 *   terre ; chaque météore reste là, rocher qui sert d'abri ;</li>
 *   <li>frappe extrême : un cercle rouge sur toute l'arène ; qui voit le boss (aucun bloc entre ses yeux et la poitrine
 *   du joueur) perd {@value #EXTREME_PART} de ses PV ; caché derrière un météore, rien. Les météores s'effritent
 *   ensuite ;</li>
 *   <li>météores qui suivent : deux joueurs marqués ; un météore les suit ({@value #TRACK_SPEED} blocs/s) pendant
 *   {@value #TRACK_SECONDS} s puis éclate (cercle de {@value #RADIUS} blocs) ; s'ils se croisent (moins de
 *   {@value #SHATTER} blocs l'un de l'autre), ils se brisent l'un l'autre sans dégâts. Seul, il éclate toujours.</li>
 * </ul>
 * Les blocs posés ne remplacent rien (seulement l'air) et sont retirés à la fin de chaque rencontre.
 */
final class Meteors {

    static final double RADIUS = 4;
    static final float WINDUP = 2.5f;
    static final float PART = 0.15f;
    static final float EXTREME_WINDUP = 4f;
    static final float EXTREME_PART = 0.6f;
    static final float TRACK_SECONDS = 10f;
    static final double TRACK_SPEED = 3.6;
    static final double TRACK_START = 8;
    static final double SHATTER = 4;
    static final float TRACK_WINDUP = 1.5f;
    static final float TRACK_PART = 0.35f;
    static final String ROCK = "Rock_Volcanic";

    private static final class Tracker {
        final PlayerRef target;
        Vector3d at;
        final long until;

        Tracker(PlayerRef target, Vector3d at, long until) {
            this.target = target;
            this.at = at;
            this.until = until;
        }
    }

    private final List<int[]> rocks = new ArrayList<>();
    private final List<Tracker> trackers = new ArrayList<>();
    private long last;
    private int beat;
    private int epoch;

    /** Un météore sous chaque joueur de `here`. */
    void call(World world, Store<EntityStore> store, List<PlayerRef> here) {
        List<Vector3d> points = new ArrayList<>();
        for (PlayerRef p : here) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                points.add(at);
            }
        }
        rain(world, store, points, WINDUP, true);
    }

    /** Météores aux points `points` (cercles de {@value #RADIUS} blocs) ; `cover` : un rocher reste à chaque impact. */
    void rain(World world, Store<EntityStore> store, List<Vector3d> points, float windup, boolean cover) {
        long now = System.nanoTime();
        float w0 = windup * FractalRuns.windupFactor(world);
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (Vector3d at : points) {
            circles.add(new Telegraphs.Circle(at, RADIUS, now, w0));
            Telegraphs.particle(store, "Nakasar_Fractal_Meteor_Trail", new Vector3d(at).add(0, 12, 0), 1.2f);
        }
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (epoch != e) {
                return true;
            }
            boolean ready = true;
            for (Telegraphs.Circle c : circles) {
                ready &= c.step(s, t);
            }
            if (!ready) {
                return false;
            }
            for (Telegraphs.Circle c : circles) {
                Telegraphs.particle(s, "Explosion_Medium", c.origin(), 1.2f);
                Telegraphs.sound(s, "SFX_Explosion_Boomshroom", c.origin());
                for (PlayerRef p : SunquaPeak.strike(w, s, c, PART, SunquaPeak.KNOCKED_DOWN, 1.5f)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null) {
                        Vector3d away = new Vector3d(at.x() - c.origin().x(), 0, at.z() - c.origin().z());
                        if (away.lengthSquared() < 0.01) {
                            away.set(1, 0, 0);
                        }
                        Moves.velocity(s, p.getReference(), away.normalize().mul(6).add(0, 4, 0));
                    }
                }
                if (cover) {
                    rock(w, s, c.origin());
                }
            }
            return true;
        });
    }

    /** Un rocher (croix de 3 blocs de haut, coins de 2) au point d'impact, seulement dans l'air et hors des joueurs. */
    private void rock(World world, Store<EntityStore> store, Vector3d at) {
        ChunkStore chunks = world.getChunkStore();
        int bx = (int) Math.floor(at.x());
        int by = (int) Math.floor(at.y());
        int bz = (int) Math.floor(at.z());
        List<Vector3d> players = new ArrayList<>();
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null) {
                players.add(pos);
            }
        }
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                int height = dx == 0 || dz == 0 ? 3 : 2;
                for (int dy = 0; dy < height; dy++) {
                    int x = bx + dx;
                    int y = by + dy;
                    int z = bz + dz;
                    if (WorldBlocks.solid(chunks, x, y, z) || occupied(players, x, y, z)) {
                        continue;
                    }
                    if (WorldBlocks.set(chunks, x, y, z, ROCK, 0)) {
                        rocks.add(new int[]{x, y, z});
                    }
                }
            }
        }
    }

    private static boolean occupied(List<Vector3d> players, int x, int y, int z) {
        for (Vector3d p : players) {
            if (Math.abs(p.x() - (x + 0.5)) < 0.5 + Telegraphs.BODY && Math.abs(p.z() - (z + 0.5)) < 0.5 + Telegraphs.BODY
                    && p.y() < y + 1 && p.y() + 1.8 > y) {
                return true;
            }
        }
        return false;
    }

    /** Frappe extrême depuis `boss` sur le disque (`center`, `radius`) : seuls les joueurs à couvert y échappent. */
    void extreme(World world, Store<EntityStore> store, Ref<EntityStore> boss, Vector3d center, double radius,
                 String messageKey) {
        Telegraphs.Circle circle = new Telegraphs.Circle(center, radius, System.nanoTime(),
                EXTREME_WINDUP * FractalRuns.windupFactor(world));
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + messageKey));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (epoch != e) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Vector3d b = Telegraphs.position(s, boss);
            if (b != null) {
                Vector3d eye = new Vector3d(b).add(0, 2.5, 0);
                Telegraphs.particle(s, "Explosion_Big", b, 1.5f);
                Telegraphs.sound(s, "SFX_Gobliterator_Barrel_Explosion", b);
                ChunkStore chunks = w.getChunkStore();
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at == null || !circle.contains(at)) {
                        continue;
                    }
                    Vector3d chest = new Vector3d(at).add(0, 1.2, 0);
                    Vector3d dir = new Vector3d(chest).sub(eye);
                    double reach = dir.length();
                    boolean covered = reach > 0.5 && Moves.cast(chunks, eye, dir, reach - 0.3) != null;
                    if (!covered) {
                        Hurt.percent(s, p.getReference(), EXTREME_PART, SunquaPeak.CAUSE);
                        Hurt.effect(s, p.getReference(), SunquaPeak.BURNING, 3f);
                    }
                }
            }
            crumble(w, s);
            return true;
        });
    }

    /** Deux joueurs marqués (un seul s'il est seul) : leurs météores les suivent. */
    void track(World world, Store<EntityStore> store, List<PlayerRef> here) {
        List<PlayerRef> targets = Spawns.pick(here, Math.min(2, here.size()));
        long until = System.nanoTime() + Telegraphs.seconds(TRACK_SECONDS);
        for (PlayerRef p : targets) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null) {
                continue;
            }
            double a = Math.random() * Math.PI * 2;
            trackers.add(new Tracker(p, new Vector3d(at.x() + Math.cos(a) * TRACK_START, at.y(), at.z() + Math.sin(a) * TRACK_START),
                    until));
            Hurt.effect(store, p.getReference(), "Nakasar_Fractal_Meteor_Marked", TRACK_SECONDS);
        }
        if (targets.size() == 2) {
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.tracking")
                    .param("a", targets.get(0).getUsername()).param("b", targets.get(1).getUsername()));
        }
    }

    /** Un tick du monde : les météores suivent leur cible, se brisent l'un l'autre, ou éclatent au bout du temps. */
    void tick(World world, Store<EntityStore> store, long now) {
        float dt = last == 0 ? 0f : Math.min(0.2f, (now - last) / 1e9f);
        last = now;
        if (trackers.isEmpty()) {
            return;
        }
        boolean show = ++beat % 5 == 0;
        for (Tracker m : trackers) {
            Vector3d to = Telegraphs.position(store, m.target.getReference());
            if (to != null) {
                double d = Telegraphs.horizontal(m.at, to);
                double k = d < 1e-6 ? 0 : Math.min(1.0, TRACK_SPEED * dt / d);
                m.at = new Vector3d(m.at.x() + (to.x() - m.at.x()) * k, to.y(), m.at.z() + (to.z() - m.at.z()) * k);
            }
            if (show) {
                Telegraphs.particle(store, "Nakasar_Fractal_Meteor_Trail", new Vector3d(m.at).add(0, 1, 0), 1f);
            }
        }
        if (trackers.size() >= 2 && Telegraphs.horizontal(trackers.get(0).at, trackers.get(1).at) <= SHATTER) {
            for (Tracker m : trackers) {
                Telegraphs.particle(store, "Falling_Stalactite_Hit", m.at, 1.5f);
                Hurt.clear(store, m.target.getReference(), "Nakasar_Fractal_Meteor_Marked");
            }
            Telegraphs.sound(store, "SFX_Crystal_Break", trackers.get(0).at);
            trackers.clear();
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "fury.shattered"));
            return;
        }
        if (now < trackers.get(0).until) {
            return;
        }
        List<Vector3d> points = new ArrayList<>();
        for (Tracker m : trackers) {
            points.add(m.at);
        }
        trackers.clear();
        long t0 = System.nanoTime();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (Vector3d at : points) {
            circles.add(new Telegraphs.Circle(at, RADIUS, t0, TRACK_WINDUP * FractalRuns.windupFactor(world)));
        }
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (epoch != e) {
                return true;
            }
            boolean ready = true;
            for (Telegraphs.Circle c : circles) {
                ready &= c.step(s, t);
            }
            if (!ready) {
                return false;
            }
            for (Telegraphs.Circle c : circles) {
                Telegraphs.particle(s, "Explosion_Big", c.origin(), 1.2f);
                SunquaPeak.strike(w, s, c, TRACK_PART, SunquaPeak.BURNING, 3f);
            }
            return true;
        });
    }

    /** Les météores posés s'effritent. */
    void crumble(World world, Store<EntityStore> store) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] r : rocks) {
            if (ROCK.equals(WorldBlocks.name(chunks, r[0], r[1], r[2]))) {
                WorldBlocks.clear(chunks, r[0], r[1], r[2]);
            }
        }
        if (!rocks.isEmpty()) {
            int[] r = rocks.get(0);
            Telegraphs.particle(store, "Nakasar_Fractal_Boulder_Burst", new Vector3d(r[0] + 0.5, r[1], r[2] + 0.5), 1f);
        }
        rocks.clear();
    }

    /** Fin de rencontre : tout s'arrête, les rochers disparaissent. */
    void clear(World world, Store<EntityStore> store) {
        epoch++;
        for (Tracker m : trackers) {
            Hurt.clear(store, m.target.getReference(), "Nakasar_Fractal_Meteor_Marked");
        }
        trackers.clear();
        crumble(world, store);
    }
}
