package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Le sentier de lave (GW2 : les murs de roche gardés par des élémentaires de lave, et les tigres). Trois murs barrent le
 * sentier ; un joueur à moins de {@value #WAKE} blocs d'un mur réveille ses trois gardes. Un élémentaire de lave qui
 * meurt explose (cercle rouge de {@value #BURST_RADIUS} blocs) et se divise en {@value #SPLIT} petits élémentaires, qui
 * explosent à leur tour ({@value #EMBER_RADIUS} blocs). Gardes et divisions vaincus, le mur s'effondre (point de retour
 * devant lui). Personne près d'un mur réveillé pendant {@value SunquaPeak#RESET_SECONDS} s : ses gardes disparaissent
 * et reviendront neufs. Les tigres rôdent entre le deuxième et le troisième mur (avec butin, ils ne reviennent pas).
 */
final class LavaPath {

    static final double WAKE = 8;
    static final double BURST_RADIUS = 3;
    static final float BURST_WINDUP = 1f;
    static final float BURST_PART = 0.12f;
    static final double EMBER_RADIUS = 2;
    static final float EMBER_WINDUP = 0.8f;
    static final float EMBER_PART = 0.06f;
    static final int SPLIT = 2;

    private final boolean[] woken = new boolean[SunquaPeakLayout.LAVA_WALLS.length];
    private final boolean[] open = new boolean[SunquaPeakLayout.LAVA_WALLS.length];
    private final float[] idle = new float[SunquaPeakLayout.LAVA_WALLS.length];
    @SuppressWarnings("unchecked")
    private final List<Ref<EntityStore>>[] guards = new List[SunquaPeakLayout.LAVA_WALLS.length];
    /** Délai au-delà duquel une division attendue (mort sans {@code onFoeDeath}) ne retient plus le mur. */
    static final float OWED_SECONDS = 3f;

    /** Une division en attente : posée au pas suivant, hors de la mort de l'élémentaire. */
    private record Split(int wall, Vector3d at) {
    }

    private final List<Split> pending = new ArrayList<>();
    /** Grands élémentaires vivants : leur mort annonce une division. */
    private final Set<Ref<EntityStore>> bigs = new HashSet<>();
    /**
     * Divisions attendues par mur : la mort (DeathComponent) se voit avant {@code onFoeDeath}, qui arrive par un
     * {@code world.execute} différé ; le mur reste fermé tant qu'elles ne sont pas en attente (au plus
     * {@value #OWED_SECONDS} s).
     */
    private final int[] owed = new int[SunquaPeakLayout.LAVA_WALLS.length];
    private final long[] owedUntil = new long[SunquaPeakLayout.LAVA_WALLS.length];
    private int epoch;

    LavaPath() {
        for (int i = 0; i < guards.length; i++) {
            guards[i] = new ArrayList<>();
        }
    }

    void begin(World world, Store<EntityStore> store, SunquaPeak.State st) {
        for (double[] at : SunquaPeakLayout.TIGERS) {
            st.foe(world, store, SunquaPeak.TIGER, Spawns.point(at), null, true);
        }
    }

    /** Vrai quand les trois murs sont tombés. */
    boolean step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        long now = System.nanoTime();
        for (Split p : pending) {
            int wall = p.wall();
            Vector3d at = p.at();
            for (int k = 0; k < SPLIT; k++) {
                double a = Math.random() * Math.PI * 2;
                Vector3d where = SunquaPeak.ground(world, new Vector3d(at.x() + Math.cos(a) * 1.5, at.y(), at.z() + Math.sin(a) * 1.5));
                Ref<EntityStore> ref = st.foe(world, store, SunquaPeak.LAVA_EMBER, where, null, false);
                if (ref != null && wall >= 0) {
                    guards[wall].add(ref);
                }
            }
        }
        pending.clear();
        int fallen = 0;
        for (int i = 0; i < woken.length; i++) {
            if (open[i]) {
                fallen++;
                continue;
            }
            Vector3d wall = center(i);
            boolean near = !SunquaPeak.near(store, players, wall, WAKE).isEmpty();
            if (!woken[i]) {
                if (near) {
                    wake(world, store, st, i);
                }
                continue;
            }
            for (Ref<EntityStore> ref : guards[i]) {
                if (!Spawns.alive(store, ref) && bigs.remove(ref)) {
                    owed[i]++;
                    owedUntil[i] = now + Telegraphs.seconds(OWED_SECONDS);
                }
            }
            guards[i].removeIf(ref -> !Spawns.alive(store, ref));
            if (guards[i].isEmpty() && (owed[i] == 0 || now >= owedUntil[i])) {
                open[i] = true;
                fallen++;
                Gates.open(world, store, SunquaPeakLayout.LAVA_WALLS[i], SunquaPeak.MESSAGES + "lava.open");
                Gates.checkpoint(world, SunquaPeakLayout.WALL_GUARDS[i][0], SunquaPeak.MESSAGES + "checkpoint");
                continue;
            }
            if (SunquaPeak.near(store, players, wall, WAKE + 10).isEmpty()) {
                idle[i] += dt;
                if (idle[i] >= SunquaPeak.RESET_SECONDS) {
                    Spawns.removeAll(store, guards[i]);
                    bigs.removeAll(guards[i]);
                    guards[i].clear();
                    owed[i] = 0;
                    woken[i] = false;
                    epoch++;   // les explosions annoncées de ce mur ne partent pas
                }
            } else {
                idle[i] = 0f;
            }
        }
        return fallen == woken.length;
    }

    private void wake(World world, Store<EntityStore> store, SunquaPeak.State st, int i) {
        woken[i] = true;
        idle[i] = 0f;
        Vector3d wall = center(i);
        for (double[] at : SunquaPeakLayout.WALL_GUARDS[i]) {
            Ref<EntityStore> ref = st.foe(world, store, SunquaPeak.LAVA_ELEMENTAL, Spawns.point(at), wall, false);
            if (ref != null) {
                guards[i].add(ref);
                bigs.add(ref);
                Telegraphs.particle(store, "Nakasar_Fractal_Lava_Blast", Spawns.point(at), 0.8f);
            }
        }
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "lava.wall"));
    }

    /** Un élémentaire de lave (ou une division) vient de mourir en `at` : explosion, et division pour les grands. */
    void burst(World world, Store<EntityStore> store, SunquaPeak.State st, String role, Vector3d at) {
        boolean big = SunquaPeak.LAVA_ELEMENTAL.equals(role);
        double radius = big ? BURST_RADIUS : EMBER_RADIUS;
        float part = big ? BURST_PART : EMBER_PART;
        Telegraphs.Circle circle = new Telegraphs.Circle(at, radius, System.nanoTime(),
                (big ? BURST_WINDUP : EMBER_WINDUP) * FractalRuns.windupFactor(world));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (epoch != e) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Lava_Blast", circle.origin(), big ? 1.4f : 0.8f);
            Telegraphs.sound(s, "SFX_Staff_Flame_Fireball_Impact", circle.origin());
            SunquaPeak.strike(w, s, circle, part, SunquaPeak.BURNING, 3f);
            return true;
        });
        if (big) {
            int wall = wallOf(at);
            if (wall >= 0) {
                owed[wall] = Math.max(0, owed[wall] - 1);
            }
            pending.add(new Split(wall, new Vector3d(at)));
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "lava.split"));
        }
    }

    /** Le mur réveillé le plus proche de `at` (-1 : aucun). */
    private int wallOf(Vector3d at) {
        int best = -1;
        double bestD = Double.MAX_VALUE;
        for (int i = 0; i < woken.length; i++) {
            double d = Telegraphs.horizontal(at, center(i));
            if (woken[i] && !open[i] && d < bestD) {
                bestD = d;
                best = i;
            }
        }
        return best;
    }

    private static Vector3d center(int wall) {
        int[][] cells = SunquaPeakLayout.LAVA_WALLS[wall];
        double x = 0;
        double z = 0;
        int y = Integer.MAX_VALUE;
        for (int[] c : cells) {
            x += c[0] + 0.5;
            z += c[2] + 0.5;
            y = Math.min(y, c[1]);
        }
        return new Vector3d(x / cells.length, y, z / cells.length);
    }
}
