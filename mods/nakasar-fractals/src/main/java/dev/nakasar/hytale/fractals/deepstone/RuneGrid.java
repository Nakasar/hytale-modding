package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.progress.Agony;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * La grille de runes de l'ouest (GW2) : des rangées de dalles vertes allumées glissent du nord vers le sud, une rangée toutes les
 * {@value #STEP_SECONDS} s ; chaque vague laisse {@value #GAPS_MIN} ou {@value #GAPS_MAX} colonnes éteintes où passer.
 * La dalle allumée est le danger même (sa zone exacte) : un corps qui mord sur une dalle verte prend {@value #HIT_PART} des PV, l'agonie
 * {@value #AGONY_SECONDS} s et un recul vers le sud. Au bout, deux runes à presser ensemble ({@link RunePair}) éteignent
 * la grille et ouvrent la barrière de la corniche de la Sentinelle.
 */
final class RuneGrid {

    static final float STEP_SECONDS = 0.6f;
    static final int WAVE_GAP = 4;
    static final int GAPS_MIN = 1;
    static final int GAPS_MAX = 2;
    static final float HIT_PART = 0.15f;
    static final float AGONY_SECONDS = 3f;
    static final float HIT_GRACE = 1.2f;
    /** La grille ne tourne que si un joueur est à moins de cette distance de ses bords. */
    static final double WAKE = 8;
    static final String RUNE_TILE = "Rock_Runic_Brick";

    private final RunePair runes = new RunePair(DeepstoneLayout.WEST_RUNES);
    /** Vagues : rangée atteinte, colonnes rouges. */
    private final List<int[]> waveRows = new ArrayList<>();
    private final List<boolean[]> waveLit = new ArrayList<>();
    private final boolean[] lit = new boolean[DeepstoneLayout.GRID_COLS * DeepstoneLayout.GRID_ROWS];
    private final Map<UUID, Long> hits = new HashMap<>();
    private final java.util.Set<UUID> hinted = new java.util.HashSet<>();
    private float clock;
    private int sinceWave = WAVE_GAP;
    private boolean told;
    private boolean solved;

    boolean solved() {
        return solved;
    }

    void step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        if (solved) {
            return;
        }
        if (runes.step(store, st, players)) {
            solved = true;
            waveRows.clear();
            waveLit.clear();
            paint(world, new boolean[lit.length]);
            Gates.open(world, store, DeepstoneLayout.WEST_GATE, Deepstone.MESSAGES + "grid.solved");
            Gates.checkpoint(world, DeepstoneLayout.GRID_END, Deepstone.MESSAGES + "checkpoint");
            return;
        }
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.z() <= DeepstoneLayout.GRID_END[2] + 3 && at.z() >= DeepstoneLayout.GRID_END[2] - 4
                    && Math.abs(at.x() - DeepstoneLayout.GRID_END[0]) <= 5 && Math.abs(at.y() - DeepstoneLayout.VAULT_Y) < 3
                    && hinted.add(p.getUuid())) {
                p.sendMessage(Message.translation(Deepstone.MESSAGES + "grid.runes"));
            }
        }
        List<PlayerRef> near = nearGrid(store, players);
        if (near.isEmpty()) {
            if (!waveRows.isEmpty()) {
                waveRows.clear();
                waveLit.clear();
                paint(world, new boolean[lit.length]);
            }
            return;
        }
        if (!told) {
            told = true;
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "grid.intro"));
        }
        clock += dt;
        float every = STEP_SECONDS * FractalRuns.windupFactor(world);
        if (clock >= every) {
            clock = 0f;
            advance();
            boolean[] next = new boolean[lit.length];
            for (int w = 0; w < waveRows.size(); w++) {
                int r = waveRows.get(w)[0];
                boolean[] cols = waveLit.get(w);
                for (int c = 0; c < cols.length; c++) {
                    if (cols[c] && r >= 0 && r < DeepstoneLayout.GRID_ROWS) {
                        next[r * DeepstoneLayout.GRID_COLS + c] = true;
                    }
                }
            }
            paint(world, next);
        }
        hurt(store, st, near);
    }

    /** Les vagues descendent d'une rangée ; une nouvelle part du nord toutes les {@value #WAVE_GAP} rangées. */
    private void advance() {
        for (int[] w : waveRows) {
            w[0]++;
        }
        for (int i = waveRows.size() - 1; i >= 0; i--) {
            if (waveRows.get(i)[0] >= DeepstoneLayout.GRID_ROWS) {
                waveRows.remove(i);
                waveLit.remove(i);
            }
        }
        sinceWave++;
        if (sinceWave >= WAVE_GAP) {
            sinceWave = 0;
            int cols = DeepstoneLayout.GRID_COLS;
            boolean[] row = new boolean[cols];
            java.util.Arrays.fill(row, true);
            int gaps = GAPS_MIN + (int) (Math.random() * (GAPS_MAX - GAPS_MIN + 1));
            int first = (int) (Math.random() * cols);
            for (int g = 0; g < gaps; g++) {
                // Brèches voisines une fois sur deux : il faut parfois changer de colonne.
                int c = Math.random() < 0.5 ? (first + g) % cols : (int) (Math.random() * cols);
                row[c] = false;
            }
            waveRows.add(new int[]{0});
            waveLit.add(row);
        }
    }

    /** Allume les dalles des vagues et éteint les autres (seulement ce qui change). */
    private void paint(World world, boolean[] next) {
        ChunkStore chunks = world.getChunkStore();
        int size = DeepstoneLayout.GRID_TILE;
        for (int i = 0; i < lit.length; i++) {
            if (lit[i] == next[i]) {
                continue;
            }
            lit[i] = next[i];
            int c = i % DeepstoneLayout.GRID_COLS;
            int r = i / DeepstoneLayout.GRID_COLS;
            for (int dx = 0; dx < size; dx++) {
                for (int dz = 0; dz < size; dz++) {
                    int x = DeepstoneLayout.GRID_X0 + c * size + dx;
                    int z = DeepstoneLayout.GRID_Z0 + r * size + dz;
                    boolean edge = dx == size - 1 || dz == size - 1;
                    String block = next[i] ? Tiles.GREEN : edge ? Tiles.EDGE : RUNE_TILE;
                    WorldBlocks.set(chunks, x, DeepstoneLayout.FLOOR_Y, z, block, 0);
                }
            }
        }
    }

    private void hurt(Store<EntityStore> store, Deepstone.State st, List<PlayerRef> near) {
        long now = System.nanoTime();
        int size = DeepstoneLayout.GRID_TILE;
        for (PlayerRef p : near) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null || at.y() > DeepstoneLayout.VAULT_Y + 1.2) {
                continue;
            }
            Long last = hits.get(p.getUuid());
            if (last != null && now - last < Telegraphs.seconds(HIT_GRACE)) {
                continue;
            }
            boolean touched = false;
            for (int i = 0; i < lit.length && !touched; i++) {
                if (!lit[i]) {
                    continue;
                }
                int c = i % DeepstoneLayout.GRID_COLS;
                int r = i / DeepstoneLayout.GRID_COLS;
                double x0 = DeepstoneLayout.GRID_X0 + c * size;
                double z0 = DeepstoneLayout.GRID_Z0 + r * size;
                double b = Telegraphs.BODY;
                touched = at.x() >= x0 - b && at.x() <= x0 + size + b && at.z() >= z0 - b && at.z() <= z0 + size + b;
            }
            if (!touched) {
                continue;
            }
            hits.put(p.getUuid(), now);
            Hurt.percent(store, p.getReference(), HIT_PART, Deepstone.CAUSE);
            Hurt.effect(store, p.getReference(), Agony.EFFECT, AGONY_SECONDS);
            Moves.velocity(store, p.getReference(), new Vector3d(0, 5, 7));
            Telegraphs.particle(store, "Nakasar_Fractal_Rune_Glow", at, 0.8f);
            Deepstone.tell(st, p, "grid.hit");
        }
    }

    private static List<PlayerRef> nearGrid(Store<EntityStore> store, List<PlayerRef> players) {
        List<PlayerRef> out = new ArrayList<>();
        double x0 = DeepstoneLayout.GRID_X0 - WAKE;
        double x1 = DeepstoneLayout.GRID_X0 + DeepstoneLayout.GRID_COLS * DeepstoneLayout.GRID_TILE + WAKE;
        double z0 = DeepstoneLayout.GRID_Z0 - WAKE;
        double z1 = DeepstoneLayout.GRID_Z0 + DeepstoneLayout.GRID_ROWS * DeepstoneLayout.GRID_TILE + WAKE;
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.x() >= x0 && at.x() <= x1 && at.z() >= z0 && at.z() <= z1
                    && Math.abs(at.y() - DeepstoneLayout.VAULT_Y) < 6) {
                out.add(p);
            }
        }
        return out;
    }
}
