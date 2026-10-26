package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
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
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * La Voix (GW2) : Torin consumé par les ombres, sur une arène de dalles au-dessus du vide. Coup d'ombre, vague d'ombre
 * et secousses : rôle JSON. En Java :
 * <ul>
 *   <li>les dalles : une chute est rattrapée par un Courant ascendant résiduel (au plus 4, 3, 2 ou 1 selon le rang),
 *   sans courant on tombe pour de bon. La Lumière de Deldrimor refait les dalles à moins de {@value #RESTORE_RADIUS}
 *   blocs et donne un courant ;</li>
 *   <li>toutes les {@value #ORB_EVERY} s, une orbe sur un joueur (cercle rouge de {@value #ORB_RADIUS} blocs) qui brise la
 *   dalle touchée et rebondit 1 à 3 fois selon le rang ;</li>
 *   <li>sous 75 %, toutes les {@value #BOMB_EVERY} s, une bombe d'ombre suit un joueur {@value #BOMB_TRACK} s puis tombe :
 *   cercle rouge de {@value #BOMB_RADIUS} blocs ({@value #BOMB_WINDUP} s), {@value #BOMB_PART} des PV, Hébété, dalles
 *   brisées ; qui est touché en reçoit aussitôt une autre ;</li>
 *   <li>à chaque tranche de 10 %, une chance sur deux de se déplacer dans les ombres ;</li>
 *   <li>à 80 et 40 %, le siphon spirituel : défiance ouverte {@value #SIPHON_SECONDS} s, chaque seconde
 *   {@value #SIPHON_PART} des PV de chacun, la dalle d'un siphonné s'effrite ; brisée, la Voix est étourdie ;</li>
 *   <li>à 70, 50 et 30 %, des ombres (elles effritent des dalles) ;</li>
 *   <li>à 60 et 20 %, la Voix se retire, invulnérable, au centre : {@value #FLAMES} flammes spectrales filent vers elle ;
 *   chaque flamme qui l'atteint déclenche une déflagration sur toute l'arène (cercle rouge de {@value #BLAST_RADIUS}
 *   blocs) ; les dix passées, elle redevient vulnérable. Jamais de soin (AGENTS.md).</li>
 * </ul>
 */
final class Voice {

    static final String UPDRAFT = "Nakasar_Fractal_Updraft_";
    static final double RESTORE_RADIUS = 4.5;
    static final float FALL_PART = 0.05f;
    static final float ORB_EVERY = 7f;
    static final double ORB_RADIUS = 2.5;
    static final float ORB_WINDUP = 1.6f;
    static final float ORB_PART = 0.15f;
    static final float BOMB_EVERY = 15f;
    static final float BOMB_TRACK = 2f;
    static final double BOMB_RADIUS = 3.5;
    static final float BOMB_WINDUP = 2f;
    static final float BOMB_PART = 0.3f;
    static final int BOMB_CHAIN = 3;
    static final float SIPHON_SECONDS = 13f;
    static final float SIPHON_PART = 0.04f;
    static final float[] SIPHON_AT = {0.8f, 0.4f};
    static final float[] SHADES_AT = {0.7f, 0.5f, 0.3f};
    static final float[] SPLIT_AT = {0.6f, 0.2f};
    static final int FLAMES = 10;
    static final float FLAME_EVERY = 1.5f;
    static final double FLAME_SPEED = 1.6;
    static final double FLAME_START = 20;
    static final double BLAST_RADIUS = 26;
    static final float BLAST_WINDUP = 2f;
    static final float BLAST_PART = 0.25f;
    static final float CRUMBLE_SECONDS = 1.5f;
    static final float SHADE_CRUMBLE_EVERY = 12f;
    static final float RESET_SECONDS = 30f;
    static final String VEIL = "Nakasar_Fractal_Shadow_Veil";

    private final Tiles tiles = new Tiles(DeepstoneLayout.ARENA_X0, DeepstoneLayout.ARENA_Z0, DeepstoneLayout.ARENA_COLS,
            DeepstoneLayout.ARENA_ROWS, DeepstoneLayout.ARENA_TILE, DeepstoneLayout.ARENA_FLOOR_Y);
    private final Map<UUID, Integer> updrafts = new HashMap<>();
    private Ref<EntityStore> boss;
    private boolean engaged;
    private final List<Ref<EntityStore>> shades = new ArrayList<>();
    private final List<Ref<EntityStore>> flames = new ArrayList<>();
    private int tens;
    private int siphons;
    private int shadeWaves;
    private int splits;
    private boolean split;
    private int flamesSent;
    private int flamesGone;
    private float flameClock;
    private float orbClock;
    private float bombClock;
    private float shadeClock;
    private long siphonUntil;
    private float siphonTick;
    private float idle;
    private long lastTick;
    private int epoch;

    boolean shielded() {
        return split;
    }

    private boolean live(int e) {
        return engaged && epoch == e;
    }

    private static boolean inArena(Vector3d at) {
        double size = DeepstoneLayout.ARENA_COLS * DeepstoneLayout.ARENA_TILE;
        return at.x() >= DeepstoneLayout.ARENA_X0 - 2 && at.x() <= DeepstoneLayout.ARENA_X0 + size + 2
                && at.z() >= DeepstoneLayout.ARENA_Z0 - 2 && at.z() <= DeepstoneLayout.ARENA_Z0 + size + 2;
    }

    private List<PlayerRef> inArena(Store<EntityStore> store, List<PlayerRef> players) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && inArena(at) && Math.abs(at.y() - (tiles.floorY + 1)) < 6) {
                out.add(p);
            }
        }
        return out;
    }

    /** Vrai une fois la Voix vaincue. */
    boolean step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        falls(world, store, st, players);
        List<PlayerRef> here = inArena(store, players);
        if (!engaged) {
            if (!here.isEmpty()) {
                engage(world, store, st);
            }
            return false;
        }
        shades.removeIf(ref -> !Spawns.alive(store, ref));
        if (!Spawns.alive(store, boss)) {
            clearAdds(store);
            BossStun.release(store, boss);
            Defiance.forget(boss);
            fill(world);
            engaged = false;
            epoch++;
            return true;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                reset(world, store);
            }
            return false;
        }
        idle = 0f;
        float health = Hurt.healthFraction(store, boss);
        if (split) {
            Hurt.effect(store, boss, VEIL, 1.5f);
            splitStep(world, store, st, dt);
            return false;
        }
        if (splits < SPLIT_AT.length && health <= SPLIT_AT[splits] + 0.001f) {
            splits++;
            beginSplit(world, store);
            return false;
        }
        if (siphons < SIPHON_AT.length && health <= SIPHON_AT[siphons] + 0.001f) {
            siphons++;
            beginSiphon(world, store);
        }
        if (shadeWaves < SHADES_AT.length && health <= SHADES_AT[shadeWaves] + 0.001f) {
            shadeWaves++;
            int n = 2 + (FractalRuns.partySize(world) >= 4 ? 1 : 0);
            for (int i = 0; i < n; i++) {
                Vector3d at = randomTile(null, 0);
                if (at != null) {
                    Ref<EntityStore> ref = st.foe(world, store, Deepstone.SHADE, at, true);
                    if (ref != null) {
                        shades.add(ref);
                    }
                }
            }
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.shades"));
        }
        if (tens < 9 && health <= 0.9f - 0.1f * tens + 0.001f) {
            tens++;
            if (Math.random() < 0.5 && System.nanoTime() > siphonUntil) {
                teleport(world, store, 8);
            }
        }
        siphonStep(world, store, here, dt);
        if (BossStun.isStunned(boss)) {
            return false;
        }
        orbClock += dt;
        if (orbClock >= ORB_EVERY) {
            orbClock = 0f;
            PlayerRef target = here.get((int) (Math.random() * here.size()));
            orb(world, store, target, Math.min(3, 1 + Deepstone.rank(world)));
        }
        if (health < 0.75f) {
            bombClock += dt;
            if (bombClock >= BOMB_EVERY) {
                bombClock = 0f;
                bomb(world, store, here.get((int) (Math.random() * here.size())), 0);
            }
        }
        shadeClock += dt;
        if (shadeClock >= SHADE_CRUMBLE_EVERY && !shades.isEmpty()) {
            shadeClock = 0f;
            Vector3d at = Telegraphs.position(store, shades.get((int) (Math.random() * shades.size())));
            int[] cell = at == null ? null : tiles.cellOf(at);
            if (cell != null) {
                crumble(world, cell[0], cell[1]);
            }
        }
        return false;
    }

    private void engage(World world, Store<EntityStore> store, Deepstone.State st) {
        fill(world);
        Vector3d c = Spawns.point(DeepstoneLayout.ARENA);
        boss = st.boss(world, store, Deepstone.VOICE, c, Spawns.point(DeepstoneLayout.WALKWAY_END));
        if (boss == null) {
            return;
        }
        Spawns.remove(store, st.torin);
        st.torin = null;
        engaged = true;
        epoch++;
        tens = 0;
        siphons = 0;
        shadeWaves = 0;
        splits = 0;
        split = false;
        orbClock = ORB_EVERY - 4f;
        bombClock = 0f;
        siphonUntil = 0;
        idle = 0f;
        Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", c, 3f);
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.enter"));
    }

    private void fill(World world) {
        for (int c = 0; c < tiles.cols; c++) {
            for (int r = 0; r < tiles.rows; r++) {
                if (!tiles.present(c, r) || tiles.red(c, r)) {
                    tiles.place(world, c, r);
                }
            }
        }
    }

    // --- chutes et courants ascendants -----------------------------------------------------------------------------

    private void falls(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players) {
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null || !inArena(at) || at.y() > tiles.floorY - 3 || at.y() < tiles.floorY - 30) {
                continue;
            }
            int stacks = updrafts.getOrDefault(p.getUuid(), 0);
            if (stacks <= 0) {
                Hurt.percent(store, p.getReference(), 1f, Deepstone.CAUSE);
                continue;
            }
            setUpdraft(store, p, stacks - 1);
            Vector3d back = nearestTile(at);
            Moves.teleport(store, p.getReference(), back == null ? Spawns.point(DeepstoneLayout.ARENA) : back);
            Hurt.percent(store, p.getReference(), FALL_PART, Deepstone.CAUSE);
            Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Glow", back == null ? at : back, 1f);
            Deepstone.tell(st, p, "voice.saved");
        }
    }

    private void setUpdraft(Store<EntityStore> store, PlayerRef p, int stacks) {
        updrafts.put(p.getUuid(), stacks);
        for (int n = 1; n <= 4; n++) {
            Hurt.clear(store, p.getReference(), UPDRAFT + n);
        }
        if (stacks > 0) {
            Hurt.effect(store, p.getReference(), UPDRAFT + Math.min(4, stacks), 600f);
        }
    }

    /** La Lumière libérée en `at` : dalles refaites autour, un courant ascendant de plus. */
    void light(World world, Store<EntityStore> store, Deepstone.State st, PlayerRef player, Vector3d at) {
        if (!inArena(at) || Math.abs(at.y() - (tiles.floorY + 1)) > 6) {
            return;
        }
        for (int c = 0; c < tiles.cols; c++) {
            for (int r = 0; r < tiles.rows; r++) {
                if ((!tiles.present(c, r) || tiles.red(c, r)) && Telegraphs.horizontal(tiles.center(c, r), at) <= RESTORE_RADIUS) {
                    tiles.place(world, c, r);
                    Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Glow", tiles.center(c, r), 0.8f);
                }
            }
        }
        int cap = Math.max(1, 4 - Deepstone.rank(world));
        int stacks = updrafts.getOrDefault(player.getUuid(), 0);
        if (stacks < cap) {
            setUpdraft(store, player, stacks + 1);
            player.sendMessage(Message.translation(Deepstone.MESSAGES + "voice.updraft").param("count", stacks + 1));
        }
    }

    private Vector3d nearestTile(Vector3d at) {
        Vector3d best = null;
        double bestD = Double.MAX_VALUE;
        for (int c = 0; c < tiles.cols; c++) {
            for (int r = 0; r < tiles.rows; r++) {
                if (tiles.present(c, r) && !tiles.red(c, r)) {
                    Vector3d p = tiles.center(c, r);
                    double d = Telegraphs.horizontal(p, at);
                    if (d < bestD) {
                        bestD = d;
                        best = p;
                    }
                }
            }
        }
        return best;
    }

    /** Une dalle présente au hasard, à plus de `min` blocs de `from` (null : n'importe où). */
    private Vector3d randomTile(Vector3d from, double min) {
        List<Vector3d> options = new ArrayList<>();
        for (int c = 1; c < tiles.cols - 1; c++) {
            for (int r = 1; r < tiles.rows - 1; r++) {
                Vector3d p = tiles.center(c, r);
                if (tiles.present(c, r) && !tiles.red(c, r) && (from == null || Telegraphs.horizontal(p, from) >= min)) {
                    options.add(p);
                }
            }
        }
        return options.isEmpty() ? null : options.get((int) (Math.random() * options.size()));
    }

    /** La dalle rougit {@value #CRUMBLE_SECONDS} s (la zone rouge est la dalle) puis tombe. */
    private void crumble(World world, int c, int r) {
        if (!tiles.present(c, r) || tiles.red(c, r)) {
            return;
        }
        tiles.redden(world, c, r);
        long end = System.nanoTime() + Telegraphs.seconds(CRUMBLE_SECONDS * FractalRuns.windupFactor(world));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (t < end) {
                return false;
            }
            if (tiles.red(c, r)) {
                tiles.drop(w, s, c, r);
            }
            return true;
        });
    }

    private void dropUnder(World world, Store<EntityStore> store, Vector3d center, double radius) {
        for (int c = 0; c < tiles.cols; c++) {
            for (int r = 0; r < tiles.rows; r++) {
                if (tiles.present(c, r) && Telegraphs.horizontal(tiles.center(c, r), center) <= radius) {
                    tiles.drop(world, store, c, r);
                }
            }
        }
    }

    // --- orbe, bombes, téléportation -------------------------------------------------------------------------------

    private void orb(World world, Store<EntityStore> store, PlayerRef target, int bounces) {
        Vector3d at = Telegraphs.position(store, target.getReference());
        if (at == null) {
            return;
        }
        float windup = ORB_WINDUP * FractalRuns.windupFactor(world);
        Telegraphs.Circle circle = new Telegraphs.Circle(at, ORB_RADIUS, System.nanoTime(), windup);
        Telegraphs.particle(store, "Nakasar_Fractal_Voice_Orb", new Vector3d(at).add(0, 3, 0), 1f);
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Bomb_Blast", circle.origin(), 0.8f);
            List<PlayerRef> players = Spawns.alivePlayers(w, s);
            for (PlayerRef p : players) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && circle.contains(pos)) {
                    Hurt.percent(s, p.getReference(), ORB_PART, Deepstone.CAUSE);
                }
            }
            int[] cell = tiles.cellOf(circle.origin());
            if (cell != null) {
                tiles.drop(w, s, cell[0], cell[1]);
            }
            if (bounces > 1) {
                List<PlayerRef> here = inArena(s, players);
                if (!here.isEmpty()) {
                    orb(w, s, here.get((int) (Math.random() * here.size())), bounces - 1);
                }
            }
            return true;
        });
    }

    private void bomb(World world, Store<EntityStore> store, PlayerRef target, int chain) {
        Ref<EntityStore> ref = target.getReference();
        if (Telegraphs.position(store, ref) == null) {
            return;
        }
        Hurt.effect(store, ref, "Nakasar_Fractal_Shadow_Bomb", BOMB_TRACK + BOMB_WINDUP);
        target.sendMessage(Message.translation(Deepstone.MESSAGES + "voice.bomb"));
        long drop = System.nanoTime() + Telegraphs.seconds(BOMB_TRACK);
        float windup = BOMB_WINDUP * FractalRuns.windupFactor(world);
        Telegraphs.Circle[] circle = new Telegraphs.Circle[1];
        long[] fx = {0};
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (circle[0] == null) {
                Vector3d at = Telegraphs.position(s, ref);
                if (at == null) {
                    return true;
                }
                if (t - fx[0] > Telegraphs.seconds(0.3f)) {
                    fx[0] = t;
                    Telegraphs.particle(s, "Nakasar_Fractal_Bomb_Mark", at, 0.8f);
                }
                if (t < drop) {
                    return false;
                }
                circle[0] = new Telegraphs.Circle(at, BOMB_RADIUS, t, windup);
            }
            if (!circle[0].step(s, t)) {
                return false;
            }
            Vector3d c = circle[0].origin();
            Telegraphs.particle(s, "Nakasar_Fractal_Bomb_Blast", c, 1.4f);
            Telegraphs.sound(s, "SFX_Explosion_Boomshroom", c);
            List<PlayerRef> hit = new ArrayList<>();
            for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && circle[0].contains(pos)) {
                    Hurt.percent(s, p.getReference(), BOMB_PART, Deepstone.CAUSE);
                    Hurt.effect(s, p.getReference(), "Nakasar_Fractal_Dazed", 2f);
                    hit.add(p);
                }
            }
            dropUnder(w, s, c, BOMB_RADIUS);
            if (!hit.isEmpty() && chain + 1 < BOMB_CHAIN) {
                bomb(w, s, hit.get((int) (Math.random() * hit.size())), chain + 1);
            }
            return true;
        });
    }

    private void teleport(World world, Store<EntityStore> store, double min) {
        Vector3d from = Telegraphs.position(store, boss);
        Vector3d to = from == null ? null : randomTile(from, min);
        if (to == null) {
            return;
        }
        BossStun.interrupt(world, store, boss);
        Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", from, 1.5f);
        Deepstone.move(store, boss, to, Spawns.point(DeepstoneLayout.ARENA));
        Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", to, 1.5f);
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.teleport"));
    }

    // --- siphon spirituel ------------------------------------------------------------------------------------------

    private void beginSiphon(World world, Store<EntityStore> store) {
        teleport(world, store, 10);
        Defiance.open(world, boss, SIPHON_SECONDS);
        siphonUntil = System.nanoTime() + Telegraphs.seconds(SIPHON_SECONDS);
        siphonTick = 0f;
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.siphon"));
    }

    private void siphonStep(World world, Store<EntityStore> store, List<PlayerRef> here, float dt) {
        if (siphonUntil == 0) {
            return;
        }
        long now = System.nanoTime();
        if (!Defiance.isOpen(boss) && now < siphonUntil - Telegraphs.seconds(0.15f)) {
            siphonUntil = 0;
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.siphon.broken"));
            return;
        }
        if (now >= siphonUntil) {
            siphonUntil = 0;
            Defiance.forget(boss);
            return;
        }
        siphonTick += dt;
        if (siphonTick < 1f) {
            return;
        }
        siphonTick = 0f;
        Vector3d b = Telegraphs.position(store, boss);
        boolean crumbleOne = Math.random() < 0.5;
        for (PlayerRef p : here) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null) {
                continue;
            }
            Hurt.percent(store, p.getReference(), SIPHON_PART, Deepstone.CAUSE);
            Hurt.effect(store, p.getReference(), "Nakasar_Fractal_Siphoned", 1.5f);
            if (b != null) {
                for (int k = 1; k < 8; k++) {
                    double f = k / 8.0;
                    Telegraphs.particle(store, "Nakasar_Fractal_Siphon_Beam", new Vector3d(b.x() + (at.x() - b.x()) * f,
                            b.y() + 1.5 + (at.y() - b.y()) * f, b.z() + (at.z() - b.z()) * f), 0.6f);
                }
            }
            if (crumbleOne) {
                crumbleOne = false;
                int[] cell = tiles.cellOf(at);
                if (cell != null) {
                    crumble(world, cell[0], cell[1]);
                }
            }
        }
    }

    // --- flammes spectrales ----------------------------------------------------------------------------------------

    private void beginSplit(World world, Store<EntityStore> store) {
        split = true;
        flamesSent = 0;
        flamesGone = 0;
        flameClock = FLAME_EVERY;
        siphonUntil = 0;
        Defiance.forget(boss);
        BossStun.interrupt(world, store, boss);
        Vector3d c = Spawns.point(DeepstoneLayout.ARENA);
        Deepstone.move(store, boss, c, Spawns.point(DeepstoneLayout.WALKWAY_END));
        Hurt.effect(store, boss, VEIL, 1.5f);
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.split"));
    }

    private void splitStep(World world, Store<EntityStore> store, Deepstone.State st, float dt) {
        BossStun.hold(world, store, boss);
        for (int i = flames.size() - 1; i >= 0; i--) {
            if (!Spawns.alive(store, flames.get(i))) {
                flames.remove(i);
                flamesGone++;
            }
        }
        flameClock += dt;
        if (flamesSent < FLAMES && flameClock >= FLAME_EVERY) {
            flameClock = 0f;
            double a = Math.random() * Math.PI * 2;
            Vector3d c = Spawns.point(DeepstoneLayout.ARENA);
            Vector3d at = new Vector3d(c.x() + Math.cos(a) * FLAME_START, c.y() + 1.5, c.z() + Math.sin(a) * FLAME_START);
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, Deepstone.FLAME, at, 0f);
            flamesSent++;
            if (ref != null) {
                Spawns.noLoot(store, ref);
                st.foes.add(ref);
                flames.add(ref);
                Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", at, 0.8f);
            } else {
                flamesGone++;
            }
        }
        if (flamesSent >= FLAMES && flamesGone >= FLAMES && flames.isEmpty()) {
            split = false;
            Hurt.clear(store, boss, VEIL);
            BossStun.release(store, boss);
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.back"));
        }
    }

    /** À chaque tick : les flammes filent vers la Voix ; qui l'atteint déclenche une déflagration. */
    void tick(World world, Store<EntityStore> store, Deepstone.State st, long now) {
        float dt = lastTick == 0 ? 0f : Math.min(0.2f, (now - lastTick) / 1e9f);
        lastTick = now;
        if (!engaged || flames.isEmpty()) {
            return;
        }
        Vector3d b = Telegraphs.position(store, boss);
        if (b == null) {
            return;
        }
        for (int i = flames.size() - 1; i >= 0; i--) {
            Ref<EntityStore> f = flames.get(i);
            Vector3d at = Telegraphs.position(store, f);
            if (at == null) {
                continue;
            }
            double d = Telegraphs.horizontal(at, b);
            if (d <= 1.8) {
                Spawns.remove(store, f);
                flames.remove(i);
                flamesGone++;
                blast(world, store, b);
                continue;
            }
            double k = Math.min(1.0, FLAME_SPEED * dt / d);
            Vector3d next = new Vector3d(at.x() + (b.x() - at.x()) * k, b.y() + 1.5, at.z() + (b.z() - at.z()) * k);
            Deepstone.move(store, f, next, b);
        }
    }

    private void blast(World world, Store<EntityStore> store, Vector3d at) {
        Vector3d c = new Vector3d(at);
        Telegraphs.Circle circle = new Telegraphs.Circle(c, BLAST_RADIUS, System.nanoTime(),
                BLAST_WINDUP * FractalRuns.windupFactor(world));
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.absorb"));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Flame_Absorb", c, 2f);
            for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && circle.contains(pos)) {
                    Hurt.percent(s, p.getReference(), BLAST_PART, Deepstone.CAUSE);
                }
            }
            return true;
        });
    }

    // --- remise à zéro ---------------------------------------------------------------------------------------------

    private void clearAdds(Store<EntityStore> store) {
        Spawns.removeAll(store, shades);
        Spawns.removeAll(store, flames);
    }

    private void reset(World world, Store<EntityStore> store) {
        clearAdds(store);
        if (boss != null) {
            BossStun.release(store, boss);
            Defiance.forget(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
        split = false;
        siphonUntil = 0;
        epoch++;
        fill(world);
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "voice.reset"));
    }
}
