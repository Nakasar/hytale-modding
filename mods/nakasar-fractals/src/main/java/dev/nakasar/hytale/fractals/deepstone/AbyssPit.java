package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * La salle du gouffre (GW2 : « unveiling room ») : des dalles de 3 blocs au-dessus du vide, d'orbe en orbe. Le chemin,
 * tiré au hasard à chaque partie, n'existe qu'à la Lumière de Deldrimor : libérée à moins de {@value #REVEAL_REACH}
 * blocs de la dernière dalle posée, elle pose les {@value #REVEAL_COUNT} suivantes. Une orbe s'allume à la Lumière (à
 * moins de {@value #ORB_REACH} blocs) quand le chemin y mène : elle devient le point de retour, et une chute ramène à
 * elle. Dès la deuxième orbe, des ombres rôdent et des flammes spectrales flottent au-dessus du chemin : au bout de
 * {@value #FLAME_FUSE} s, la dalle sous une flamme rougit ({@value #DOOM_SECONDS} s : la zone rouge est la dalle même)
 * puis tombe, sauf si la Lumière la sauve. Les quatre orbes allumées, le chemin de la sortie se pose.
 */
final class AbyssPit {

    static final double REVEAL_REACH = 6.5;
    static final int REVEAL_COUNT = 3;
    static final double ORB_REACH = 5;
    static final float FLAME_EVERY = 9f;
    static final float FLAME_FUSE = 3f;
    static final float DOOM_SECONDS = 4f;
    static final int FLAMES_MAX = 3;
    static final float FALL_PART = 0.1f;
    static final String LIT = "Nakasar_Fractal_Deepstone_Pit_Orb_Lit";

    private static final class Flame {
        final Ref<EntityStore> ref;
        final int c;
        final int r;
        float clock;
        boolean dooming;

        Flame(Ref<EntityStore> ref, int c, int r) {
            this.ref = ref;
            this.c = c;
            this.r = r;
        }
    }

    private final Tiles tiles = new Tiles(DeepstoneLayout.PIT_X0, DeepstoneLayout.PIT_Z0, DeepstoneLayout.PIT_COLS,
            DeepstoneLayout.PIT_ROWS, DeepstoneLayout.PIT_TILE, DeepstoneLayout.FLOOR_Y);
    /** Chemin de chaque tronçon (orbe i vers orbe i + 1, puis la dernière vers la sortie) : cases {c, r}. */
    private final List<List<int[]>> segments = new ArrayList<>();
    private final int[] revealed = new int[DeepstoneLayout.PIT_ORB_TILES.length];
    private final boolean[] lit = new boolean[DeepstoneLayout.PIT_ORB_TILES.length];
    private final List<Flame> flames = new ArrayList<>();
    private final List<Ref<EntityStore>> shades = new ArrayList<>();
    private final List<int[]> safe = new ArrayList<>();
    private int count;
    private boolean begun;
    private boolean finished;
    private boolean shadesUp;
    private float flameClock;
    private float hint;

    void begin(World world, Store<EntityStore> store, Deepstone.State st) {
        begun = true;
        int[][] orbs = DeepstoneLayout.PIT_ORB_TILES;
        for (int[] o : orbs) {
            for (int dc = -1; dc <= 1; dc++) {
                for (int dr = -1; dr <= 1; dr++) {
                    if (tiles.inside(o[0] + dc, o[1] + dr)) {
                        tiles.mark(o[0] + dc, o[1] + dr);
                        safe.add(new int[]{o[0] + dc, o[1] + dr});
                    }
                }
            }
        }
        for (int i = 0; i + 1 < orbs.length; i++) {
            segments.add(path(orbs[i], orbs[i + 1]));
        }
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "pit.intro"));
    }

    /** Un chemin de cases de l'orbe `a` à l'orbe `b` : pas horizontaux et verticaux mêlés au hasard. */
    private List<int[]> path(int[] a, int[] b) {
        List<Integer> moves = new ArrayList<>();
        int dc = Integer.signum(b[0] - a[0]);
        int dr = Integer.signum(b[1] - a[1]);
        for (int i = 0; i < Math.abs(b[0] - a[0]); i++) {
            moves.add(0);
        }
        for (int i = 0; i < Math.abs(b[1] - a[1]); i++) {
            moves.add(1);
        }
        Collections.shuffle(moves);
        List<int[]> out = new ArrayList<>();
        int c = a[0];
        int r = a[1];
        for (int m : moves) {
            if (m == 0) {
                c += dc;
            } else {
                r += dr;
            }
            if (!isSafe(c, r)) {
                out.add(new int[]{c, r});
            }
        }
        return out;
    }

    private boolean isSafe(int c, int r) {
        for (int[] s : safe) {
            if (s[0] == c && s[1] == r) {
                return true;
            }
        }
        return false;
    }

    /** Vrai une fois les quatre orbes allumées. */
    boolean step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        if (!begun) {
            return false;
        }
        if (finished) {
            return true;
        }
        falls(store, st, players);
        shades.removeIf(ref -> !Spawns.alive(store, ref));
        if (count >= 2) {
            flames(world, store, st, players, dt);
        }
        hint += dt;
        if (hint >= 12f && count > 0 && count < lit.length) {
            hint = 0f;
            for (PlayerRef p : players) {
                if (inRoom(store, p)) {
                    Deepstone.tell(st, p, "pit.dark");
                }
            }
        }
        return false;
    }

    /** La Lumière libérée en `at` : orbe à allumer, ou dalles suivantes du chemin. */
    void light(World world, Store<EntityStore> store, Deepstone.State st, Vector3d at) {
        if (!begun || finished) {
            return;
        }
        // flammes : la dalle condamnée est sauvée
        for (Flame f : flames) {
            if (f.dooming && Telegraphs.horizontal(tiles.center(f.c, f.r), at) <= DeepLight.RADIUS) {
                tiles.place(world, f.c, f.r);
                f.dooming = false;
                f.clock = -FLAME_FUSE;
            }
        }
        // une dalle du chemin déjà révélée puis tombée (flamme) revient à la Lumière, même si son tronçon est complet
        for (int s = 0; s < segments.size(); s++) {
            for (int i = 0; i < revealed[s]; i++) {
                int[] cell = segments.get(s).get(i);
                if (!tiles.present(cell[0], cell[1])
                        && Telegraphs.horizontal(tiles.center(cell[0], cell[1]), at) <= REVEAL_REACH) {
                    tiles.place(world, cell[0], cell[1]);
                    Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Glow", tiles.center(cell[0], cell[1]), 1f);
                }
            }
        }
        if (count < lit.length) {
            int[] o = DeepstoneLayout.PIT_ORB_TILES[count];
            boolean reached = count == 0 || revealed[count - 1] >= segments.get(count - 1).size();
            if (reached && Telegraphs.horizontal(tiles.center(o[0], o[1]), at) <= ORB_REACH) {
                lightOrb(world, store, st);
                return;
            }
        }
        if (count == 0 || count > segments.size()) {
            return;
        }
        int seg = count - 1;
        List<int[]> path = segments.get(seg);
        int from = revealed[seg];
        if (from >= path.size()) {
            return;
        }
        // la dernière dalle posée (ou l'orbe) doit être à portée
        int[] last = from == 0 ? DeepstoneLayout.PIT_ORB_TILES[seg] : path.get(from - 1);
        if (Telegraphs.horizontal(tiles.center(last[0], last[1]), at) > REVEAL_REACH) {
            return;
        }
        for (int i = from; i < Math.min(path.size(), from + REVEAL_COUNT); i++) {
            int[] cell = path.get(i);
            tiles.place(world, cell[0], cell[1]);
            Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Glow", tiles.center(cell[0], cell[1]), 1f);
            revealed[seg] = i + 1;
        }
    }

    private void lightOrb(World world, Store<EntityStore> store, Deepstone.State st) {
        int[] block = DeepstoneLayout.PIT_ORBS[count];
        WorldBlocks.set(world.getChunkStore(), block[0], block[1], block[2], LIT, 0);
        lit[count] = true;
        count++;
        Vector3d at = new Vector3d(block[0] + 0.5, block[1], block[2] + 0.5);
        Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Flash", at, 1.5f);
        Gates.checkpoint(world, new double[]{at.x() + 1, at.y(), at.z()}, Deepstone.MESSAGES + "checkpoint");
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "pit.orb").param("count", count)
                .param("total", lit.length));
        if (count == 2 && !shadesUp) {
            shadesUp = true;
            int n = 2 + (FractalRuns.partySize(world) - 1) / 2;
            int[][] orbs = DeepstoneLayout.PIT_ORB_TILES;
            for (int i = 0; i < n; i++) {
                int[] o = orbs[1 + i % (orbs.length - 1)];
                int side = i % 2 == 0 ? 1 : -1;
                int c = tiles.inside(o[0] + side, o[1]) ? o[0] + side : o[0] - side;   // dalles sûres autour de l'orbe
                Ref<EntityStore> ref = st.foe(world, store, Deepstone.SHADE, tiles.center(c, o[1]), true);
                if (ref != null) {
                    shades.add(ref);
                }
            }
        }
        if (count == lit.length) {
            finish(world, store);
        }
    }

    /** La dernière orbe allumée : la rangée du nord jusqu'à la sortie se pose, les flammes s'éteignent. */
    private void finish(World world, Store<EntityStore> store) {
        finished = true;
        for (Flame f : flames) {
            Spawns.remove(store, f.ref);
            if (f.dooming) {
                tiles.place(world, f.c, f.r);
            }
        }
        flames.clear();
        int[] last = DeepstoneLayout.PIT_ORB_TILES[lit.length - 1];
        int exitC = (int) Math.floor((DeepstoneLayout.PIT_EXIT[0] - DeepstoneLayout.PIT_X0) / DeepstoneLayout.PIT_TILE);
        int step = Integer.signum(exitC - last[0]);
        for (int c = last[0]; step != 0 && c != exitC + step; c += step) {
            if (!tiles.present(c, 0)) {
                tiles.place(world, c, 0);
            }
        }
        if (!tiles.present(exitC, 0)) {
            tiles.place(world, exitC, 0);
        }
        Gates.checkpoint(world, DeepstoneLayout.PIT_EXIT, Deepstone.MESSAGES + "checkpoint");
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "pit.done"));
    }

    private void flames(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        for (int i = flames.size() - 1; i >= 0; i--) {
            Flame f = flames.get(i);
            if (!Spawns.alive(store, f.ref)) {
                if (f.dooming) {
                    tiles.place(world, f.c, f.r);
                }
                flames.remove(i);
                continue;
            }
            f.clock += dt;
            if (!f.dooming && f.clock >= FLAME_FUSE && tiles.present(f.c, f.r)) {
                f.dooming = true;
                f.clock = 0f;
                tiles.redden(world, f.c, f.r);
            } else if (f.dooming && f.clock >= DOOM_SECONDS * FractalRuns.windupFactor(world)) {
                tiles.drop(world, store, f.c, f.r);
                Spawns.remove(store, f.ref);
                flames.remove(i);
            }
        }
        flameClock += dt;
        if (flameClock < FLAME_EVERY || flames.size() >= FLAMES_MAX) {
            return;
        }
        flameClock = 0f;
        // une dalle du chemin déjà posée, hors des orbes, pas déjà visée
        List<int[]> options = new ArrayList<>();
        for (int s = 0; s < segments.size(); s++) {
            for (int i = 0; i < revealed[s]; i++) {
                int[] cell = segments.get(s).get(i);
                if (tiles.present(cell[0], cell[1]) && !tiles.red(cell[0], cell[1]) && !targeted(cell)) {
                    options.add(cell);
                }
            }
        }
        if (options.isEmpty()) {
            return;
        }
        int[] cell = options.get((int) (Math.random() * options.size()));
        Vector3d at = tiles.center(cell[0], cell[1]).add(0, 2, 0);
        Ref<EntityStore> ref = Spawns.spawnFoe(world, store, Deepstone.FLAME, at, 0f);
        if (ref != null) {
            Spawns.noLoot(store, ref);
            st.foes.add(ref);
            flames.add(new Flame(ref, cell[0], cell[1]));
            Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", at, 0.8f);
            for (PlayerRef p : players) {
                if (inRoom(store, p)) {
                    Deepstone.tell(st, p, "pit.flame");
                }
            }
        }
    }

    private boolean targeted(int[] cell) {
        for (Flame f : flames) {
            if (f.c == cell[0] && f.r == cell[1]) {
                return true;
            }
        }
        return false;
    }

    private static boolean inRoom(Store<EntityStore> store, PlayerRef p) {
        Vector3d at = Telegraphs.position(store, p.getReference());
        int[] room = DeepstoneLayout.PIT_ROOM;
        return at != null && at.x() >= room[0] && at.x() <= room[1] + 1 && at.z() >= room[2] && at.z() <= room[3] + 1;
    }

    /** Tombé dans le gouffre : retour à la dernière orbe allumée (ou au palier). */
    private void falls(Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players) {
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null || !inRoom(store, p) || at.y() > DeepstoneLayout.VAULT_Y - 5) {
                continue;
            }
            Vector3d back;
            if (count == 0) {
                back = Spawns.point(DeepstoneLayout.PIT_LEDGE);
            } else {
                int[] b = DeepstoneLayout.PIT_ORBS[count - 1];
                back = new Vector3d(b[0] + 1.5, b[1], b[2] + 0.5);
            }
            Moves.teleport(store, p.getReference(), back);
            Hurt.percent(store, p.getReference(), FALL_PART, Deepstone.CAUSE);
            Deepstone.tell(st, p, "pit.fall");
        }
    }
}
