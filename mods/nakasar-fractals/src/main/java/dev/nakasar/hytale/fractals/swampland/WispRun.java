package dev.nakasar.hytale.fractals.swampland;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.progress.Agony;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Le marais des feux-follets, d'après GW2 : un feu-follet par groupe de places ({@link SwamplandLayout#WISP_SPOTS}),
 * tiré à chaque essai. Le premier pris lance le minuteur ({@link #timer}) et fait surgir les murs entre les arbres ;
 * les trois failles allumées à temps ouvrent le passage, sinon tout s'éteint et les feux-follets changent de place.
 * <ul>
 *   <li>pièges au sol, réarmés au bout de {@value #TRAP_REARM} s pour chaque joueur : fil tendu (renversé
 *   {@value #TRIP_STUN} s et estropié), piège à loup ({@value #BEAR_PART} des PV, immobile), plaque à piques (cycle de
 *   {@value #SPIKE_CYCLE} s, cercle rouge puis {@value #SPIKE_PART} des PV), œufs d'araignée (poison,
 *   {@value #EGG_PART} des PV) ;</li>
 *   <li>fusils revigorants : rapidité aux joueurs à moins de {@value #RACK_RANGE} blocs, ennemis estropiés,
 *   {@value #RACK_COOLDOWN} s de recharge.</li>
 * </ul>
 */
final class WispRun {

    static final float TRAP_REARM = 5f;
    static final float TRIP_STUN = 1.5f;
    static final float BEAR_PART = 0.15f;
    static final float SPIKE_CYCLE = 4f;
    static final float SPIKE_PART = 0.2f;
    static final float EGG_PART = 0.08f;
    static final double RACK_RANGE = 16;
    static final float RACK_COOLDOWN = 12f;
    static final String TRAP_CAUSE = "Nakasar_Fractal_Spikes";

    private final int[] spot = new int[SwamplandLayout.WISP_SPOTS.length];
    private final Map<Long, Float> rearm = new HashMap<>();
    private final float[] rackCooldown = new float[SwamplandLayout.RACKS.length];
    private boolean running;
    private boolean done;
    private float left;
    private int lastShown = -1;
    private int lit;
    private float spikeClock;
    private float glow;

    /** Minuteur des feux-follets selon le niveau : 64 s, puis 38 s dès le niveau 26, 30 s dès le 51. */
    static float timer(World world) {
        int level = FractalRuns.level(world);
        return level < Agony.FIRST_LEVEL ? 64f : level < 51 ? 38f : 30f;
    }

    boolean done() {
        return done;
    }

    /** Pose un feu-follet par groupe, à une place tirée au hasard. */
    void setup(World world) {
        ChunkStore chunks = world.getChunkStore();
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int g = 0; g < spot.length; g++) {
            spot[g] = random.nextInt(SwamplandLayout.WISP_SPOTS[g].length);
            place(chunks, SwamplandLayout.WISP_SPOTS[g][spot[g]]);
        }
    }

    /**
     * Pose un feu-follet ; faux (et une ligne de log) si la section n'est pas chargée. Kevin, 2026-10-24 : les
     * feux-follets du marais n'apparaissaient pas, d'où la repose dans {@link #glow} tant que la course n'a pas commencé.
     */
    static boolean place(ChunkStore chunks, int[] b) {
        boolean ok = WorldBlocks.set(chunks, b[0], b[1], b[2], Swampland.WISP_BLOCK, 0);
        if (!ok) {
            FractalsPlugin.get().getLogger().atInfo().log("Nakasar_Fractal_Wisp : pose impossible en %d %d %d (section non chargée)",
                    b[0], b[1], b[2]);
        }
        return ok;
    }

    // --- feux-follets, murs, minuteur ------------------------------------------------------------------

    /** Un feu-follet ramassé au sol : le premier lance le minuteur et lève les murs. */
    void taken(World world, Store<EntityStore> store, int x, int z) {
        if (running || done) {
            return;
        }
        running = true;
        left = timer(world);
        lastShown = -1;
        walls(world, store, true);
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "wisp.taken"));
    }

    /** Un feu-follet déposé dans une faille du marais. */
    void lit(World world) {
        if (done) {
            return;
        }
        lit++;
        int total = SwamplandLayout.CLEFTS.length;
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "cleft.lit").param("count", lit).param("total", total));
        if (lit >= total) {
            done = true;
            running = false;
            walls(world, world.getEntityStore().getStore(), false);
        }
    }

    private void walls(World world, Store<EntityStore> store, boolean up) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] w : SwamplandLayout.WALLS) {
            for (int x = w[0]; x <= w[1]; x++) {
                for (int y = w[2]; y < w[2] + Swampland.WALL_HEIGHT; y++) {
                    String here = WorldBlocks.name(chunks, x, y, w[3]);
                    if (up && !WorldBlocks.solid(chunks, x, y, w[3])) {
                        WorldBlocks.set(chunks, x, y, w[3], Swampland.WALL, 0);
                    } else if (!up && Swampland.WALL.equals(here)) {
                        WorldBlocks.clear(chunks, x, y, w[3]);
                    }
                }
            }
            if (up) {
                for (int x = w[0]; x <= w[1]; x += 4) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Wall_Rise", new Vector3d(x + 0.5, w[2], w[3] + 0.5), 1f);
                }
            }
        }
    }

    void step(World world, Store<EntityStore> store, Swampland.State st, List<PlayerRef> players, float dt) {
        for (int i = 0; i < rackCooldown.length; i++) {
            rackCooldown[i] = Math.max(0f, rackCooldown[i] - dt);
        }
        List<PlayerRef> inSwamp = Spawns.in(store, players, SwamplandLayout.SWAMP);
        if (inSwamp.isEmpty()) {
            return;
        }
        traps(world, store, inSwamp, dt);
        if (done) {
            return;
        }
        glow(world, store, dt);
        if (!running) {
            return;
        }
        left -= dt;
        int shown = (int) Math.ceil(left);
        if (shown != lastShown && (shown % 10 == 0 || shown <= 5) && shown > 0) {
            EventTitleUtil.showEventTitleToWorld(Message.translation(Swampland.MESSAGES + "timer.title"),
                    Message.translation(Swampland.MESSAGES + "timer").param("seconds", shown), EventTitleStyle.Default,
                    null, 1.2f, 0.1f, 0.2f, world);
        }
        lastShown = shown;
        if (left <= 0f) {
            fail(world, store);
        }
    }

    /** Lueur au-dessus des feux-follets encore au sol ; avant le premier pris, repose ceux qui manquent. */
    private void glow(World world, Store<EntityStore> store, float dt) {
        glow += dt;
        if (glow < 1f) {
            return;
        }
        glow = 0f;
        ChunkStore chunks = world.getChunkStore();
        for (int g = 0; g < spot.length; g++) {
            int[] b = SwamplandLayout.WISP_SPOTS[g][spot[g]];
            boolean there = Swampland.WISP_BLOCK.equals(WorldBlocks.name(chunks, b[0], b[1], b[2]));
            if (!there && !running) {
                FractalsPlugin.get().getLogger().atInfo().log("Nakasar_Fractal_Wisp : feu-follet absent en %d %d %d (%s), reposé",
                        b[0], b[1], b[2], WorldBlocks.name(chunks, b[0], b[1], b[2]));
                there = place(chunks, b);
            }
            if (there) {
                Telegraphs.particle(store, "Nakasar_Fractal_Wisp_Glow", new Vector3d(b[0] + 0.5, b[1] + 1, b[2] + 0.5), 1f);
            }
        }
    }

    /** Trop tard : feux-follets repris aux joueurs, failles éteintes, murs baissés, nouvelles places. */
    private void fail(World world, Store<EntityStore> store) {
        running = false;
        lit = 0;
        ChunkStore chunks = world.getChunkStore();
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            if (ref != null && ref.isValid()) {
                Carried.removeAll(store, ref, Swampland.WISP);
            }
        }
        for (int[][] group : SwamplandLayout.WISP_SPOTS) {
            for (int[] b : group) {
                if (Swampland.WISP_BLOCK.equals(WorldBlocks.name(chunks, b[0], b[1], b[2]))) {
                    WorldBlocks.clear(chunks, b[0], b[1], b[2]);
                }
            }
        }
        for (int[] c : SwamplandLayout.CLEFTS) {
            WorldBlocks.swap(chunks, c[0], c[1], c[2], Swampland.CLEFT);
        }
        walls(world, store, false);
        setup(world);
        Spawns.tellAll(world, Message.translation(Swampland.MESSAGES + "fail"));
    }

    // --- pièges ------------------------------------------------------------------------------------------

    private void traps(World world, Store<EntityStore> store, List<PlayerRef> inSwamp, float dt) {
        rearm.replaceAll((k, v) -> v - dt);
        rearm.values().removeIf(v -> v <= 0f);
        float before = spikeClock;
        spikeClock = (spikeClock + dt) % SPIKE_CYCLE;
        boolean warn = before < SPIKE_CYCLE / 2 - 1f && spikeClock >= SPIKE_CYCLE / 2 - 1f;
        boolean spikesUp = spikeClock >= SPIKE_CYCLE / 2;
        for (int t = 0; t < SwamplandLayout.TRAPS.length; t++) {
            int[] trap = SwamplandLayout.TRAPS[t];
            if (trap[3] == 2 && warn) {
                Telegraphs.circle(store, new Vector3d(trap[0] + 0.5, trap[1] + 1, trap[2] + 0.5), 1.0, 1f);
            }
            for (PlayerRef p : inSwamp) {
                Ref<EntityStore> ref = p.getReference();
                Vector3d at = Telegraphs.position(store, ref);
                if (at == null || (int) Math.floor(at.x()) != trap[0] || (int) Math.floor(at.z()) != trap[2]
                        || Math.abs(at.y() - (trap[1] + 1)) > 0.6) {
                    continue;
                }
                long key = ((long) t << 32) ^ p.getUuid().getLeastSignificantBits();
                if (rearm.containsKey(key) || trap[3] == 2 && !spikesUp) {
                    continue;
                }
                rearm.put(key, trap[3] == 2 ? SPIKE_CYCLE / 2 : TRAP_REARM);
                spring(store, p, ref, trap, at);
            }
        }
    }

    private static void spring(Store<EntityStore> store, PlayerRef p, Ref<EntityStore> ref, int[] trap, Vector3d at) {
        String key;
        switch (trap[3]) {
            case 0 -> {
                Hurt.effect(store, ref, "Hazard_Electric_Stun", TRIP_STUN);
                Hurt.effect(store, ref, Swampland.CRIPPLED, 4f);
                key = "trap.tripwire";
            }
            case 1 -> {
                Hurt.percent(store, ref, BEAR_PART, TRAP_CAUSE);
                Hurt.effect(store, ref, "Nakasar_Fractal_Bear_Trapped", 2.5f);
                key = "trap.bear";
            }
            case 2 -> {
                Hurt.percent(store, ref, SPIKE_PART, TRAP_CAUSE);
                key = "trap.spikes";
            }
            default -> {
                Hurt.percent(store, ref, EGG_PART, TRAP_CAUSE);
                Hurt.effect(store, ref, "Poison_T1", 6f);
                Telegraphs.particle(store, "Nakasar_Fractal_Egg_Burst", at, 1.2f);
                key = "trap.eggs";
            }
        }
        if (trap[3] != 3) {
            Telegraphs.particle(store, "Nakasar_Fractal_Trap_Snap", at, 1f);
        }
        Telegraphs.sound(store, "SFX_Mace_T2_Signature_Impact", at);
        p.sendMessage(Message.translation(Swampland.MESSAGES + key));
    }

    // --- fusils revigorants ---------------------------------------------------------------------------

    void rack(World world, Store<EntityStore> store, Swampland.State st, PlayerRef player, int x, int z) {
        int index = 0;
        for (int i = 0; i < SwamplandLayout.RACKS.length; i++) {
            if (SwamplandLayout.RACKS[i][0] == x && SwamplandLayout.RACKS[i][2] == z) {
                index = i;
            }
        }
        if (rackCooldown[index] > 0f) {
            Swampland.tell(st, player, "rack.cooldown");
            return;
        }
        rackCooldown[index] = RACK_COOLDOWN;
        Vector3d where = new Vector3d(x + 0.5, SwamplandLayout.RACKS[index][1], z + 0.5);
        Telegraphs.particle(store, "Nakasar_Fractal_Invigorate", where, 2f);
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.distance(where) <= RACK_RANGE) {
                Hurt.effect(store, p.getReference(), Swampland.SWIFTNESS, 8f);
            }
        }
        for (Ref<EntityStore> foe : st.mossman.foes()) {
            Vector3d at = Telegraphs.position(store, foe);
            if (at != null && at.distance(where) <= RACK_RANGE) {
                Hurt.effect(store, foe, Swampland.CRIPPLED, 4f);
            }
        }
        player.sendMessage(Message.translation(Swampland.MESSAGES + "rack.used"));
    }
}
