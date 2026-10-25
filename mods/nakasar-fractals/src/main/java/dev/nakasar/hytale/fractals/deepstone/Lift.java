package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * L'ascenseur de Pierre-Profonde (GW2) : tout le groupe vivant sur la plate-forme pendant {@value #BOARD_SECONDS} s,
 * elle descend d'un bloc toutes les {@value #STEP_SECONDS} s. À mi-chemin, elle s'arrête : une vague de diablotins des
 * ombres, puis une seconde menée par un écharpeur et un suceur de sang ; vidée, elle reprend jusqu'en bas. La rune de la
 * salle ramène un retardataire sur la plate-forme.
 */
final class Lift {

    static final float BOARD_SECONDS = 3f;
    static final float STEP_SECONDS = 0.4f;
    static final int WAVE_IMPS = 5;

    enum Mode { WAITING, BOARDING, DOWN, WAVE1, WAVE2, RESUME, BOTTOM }

    private Mode mode = Mode.WAITING;
    /** Y monde du sol de la plate-forme (on est debout un bloc au-dessus). */
    private int floor = DeepstoneLayout.LIFT_TOP - 1;
    private String[][] pattern;
    private float clock;
    private boolean told;
    private final List<Ref<EntityStore>> wave = new ArrayList<>();

    void begin(World world, Store<EntityStore> store) {
        int[] l = DeepstoneLayout.LIFT;
        ChunkStore chunks = world.getChunkStore();
        pattern = new String[l[1] - l[0] + 1][l[3] - l[2] + 1];
        for (int x = l[0]; x <= l[1]; x++) {
            for (int z = l[2]; z <= l[3]; z++) {
                String name = WorldBlocks.name(chunks, x, floor, z);
                pattern[x - l[0]][z - l[2]] = name == null || name.isEmpty() || "Empty".equals(name) ? Tiles.EDGE : name;
            }
        }
    }

    private static boolean on(Vector3d at, int floor) {
        int[] l = DeepstoneLayout.LIFT;
        return at.x() >= l[0] && at.x() <= l[1] + 1 && at.z() >= l[2] && at.z() <= l[3] + 1
                && at.y() >= floor + 0.5 && at.y() <= floor + 4;
    }

    /** Vrai une fois la plate-forme en bas. */
    boolean step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        if (pattern == null) {
            begin(world, store);
        }
        wave.removeIf(ref -> !Spawns.alive(store, ref));
        switch (mode) {
            case WAITING, BOARDING -> board(world, store, players, dt);
            case DOWN, RESUME -> descend(world, store, st, dt);
            case WAVE1 -> {
                if (wave.isEmpty()) {
                    spawnWave(world, store, st, true);
                    Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "lift.elite"));
                    mode = Mode.WAVE2;
                }
            }
            case WAVE2 -> {
                if (wave.isEmpty()) {
                    mode = Mode.RESUME;
                    clock = 0f;
                    Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "lift.resume"));
                }
            }
            case BOTTOM -> {
                return true;
            }
        }
        return false;
    }

    private void board(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        if (players.isEmpty()) {
            return;
        }
        boolean all = true;
        boolean any = false;
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            boolean here = at != null && on(at, floor);
            all &= here;
            any |= here;
        }
        if (any && !told) {
            told = true;
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "lift.intro"));
        }
        if (!all) {
            mode = Mode.WAITING;
            clock = 0f;
            return;
        }
        mode = Mode.BOARDING;
        clock += dt;
        if (clock >= BOARD_SECONDS) {
            clock = 0f;
            mode = Mode.DOWN;
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "lift.start"));
        }
    }

    private void descend(World world, Store<EntityStore> store, Deepstone.State st, float dt) {
        clock += dt;
        if (clock < STEP_SECONDS) {
            return;
        }
        clock = 0f;
        int target = (mode == Mode.DOWN ? DeepstoneLayout.LIFT_STOP : DeepstoneLayout.LIFT_BOTTOM) - 1;
        if (floor <= target) {
            if (mode == Mode.DOWN) {
                spawnWave(world, store, st, false);
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "lift.wave"));
                mode = Mode.WAVE1;
            } else {
                mode = Mode.BOTTOM;
                Gates.checkpoint(world, DeepstoneLayout.LIFT_LANDING, Deepstone.MESSAGES + "checkpoint");
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "lift.bottom"));
            }
            return;
        }
        int[] l = DeepstoneLayout.LIFT;
        ChunkStore chunks = world.getChunkStore();
        int next = floor - 1;
        for (int x = l[0]; x <= l[1]; x++) {
            for (int z = l[2]; z <= l[3]; z++) {
                WorldBlocks.set(chunks, x, next, z, pattern[x - l[0]][z - l[2]], 0);
            }
        }
        for (int x = l[0]; x <= l[1]; x++) {
            for (int z = l[2]; z <= l[3]; z++) {
                WorldBlocks.clear(chunks, x, floor, z);
            }
        }
        floor = next;
        if (floor % 3 == 0) {
            Telegraphs.particle(store, "Nakasar_Fractal_Lift_Dust", new Vector3d(DeepstoneLayout.LIFT_CENTER[0], floor,
                    DeepstoneLayout.LIFT_CENTER[2]), 1f);
        }
    }

    /** Vague sur les bords de la plate-forme (la seconde avec l'écharpeur et le suceur de sang). */
    private void spawnWave(World world, Store<EntityStore> store, Deepstone.State st, boolean elite) {
        int[] l = DeepstoneLayout.LIFT;
        int n = WAVE_IMPS + (FractalRuns.partySize(world) - 1) / 2;
        double y = floor + 1;
        for (int i = 0; i < n; i++) {
            double a = i * Math.PI * 2 / n;
            double x = (l[0] + l[1] + 1) / 2.0 + Math.cos(a) * 3.2;
            double z = (l[2] + l[3] + 1) / 2.0 + Math.sin(a) * 3.2;
            Ref<EntityStore> ref = st.foe(world, store, Deepstone.IMP, new Vector3d(x, y, z), true);
            if (ref != null) {
                wave.add(ref);
            }
        }
        if (elite) {
            for (String role : new String[]{Deepstone.MAULER, Deepstone.BLOODSUCKER}) {
                Vector3d at = new Vector3d(DeepstoneLayout.LIFT_CENTER[0] + (role.equals(Deepstone.MAULER) ? -2 : 2),
                        y + (role.equals(Deepstone.BLOODSUCKER) ? 2 : 0), DeepstoneLayout.LIFT_CENTER[2]);
                Ref<EntityStore> ref = st.foe(world, store, role, at, true);
                if (ref != null) {
                    wave.add(ref);
                }
            }
        }
    }

    /** La rune de la salle : un retardataire rejoint la plate-forme (où qu'elle soit). */
    void rune(World world, Store<EntityStore> store, Deepstone.State st, PlayerRef player) {
        if (st.phase != Deepstone.Phase.LIFT) {
            return;
        }
        Vector3d to = new Vector3d(DeepstoneLayout.LIFT_CENTER[0], floor + 1, DeepstoneLayout.LIFT_CENTER[2] + 2);
        Moves.teleport(store, player.getReference(), to);
        player.sendMessage(Message.translation(Deepstone.MESSAGES + "lift.rune"));
    }
}
