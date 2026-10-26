package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * L'est de Pierre-Profonde (GW2) :
 * <ul>
 *   <li>les nids (sur les œufs vanilla du Marais) pondent une araignée toutes les {@value #BROOD_EVERY} s tant qu'un
 *   joueur est à moins de {@value #BROOD_RANGE} blocs (au plus {@value #BROOD_MAX} vivantes, sans butin) ; détruit, le nid
 *   éclate et ses œufs disparaissent ;</li>
 *   <li>le pont : toutes les {@value #WIND_EVERY} s, des bandes rouges en travers ({@code WIND_LENGTH} x
 *   {@code WIND_WIDTH} blocs, {@value #WIND_WINDUP} s) ; qui y est encore est jeté dans le gouffre et revient au début du
 *   pont. Deux runes au milieu ({@link RunePair}) arrêtent le vent et ouvrent la barrière du bout ;</li>
 *   <li>l'antre : deux mères de couvée, puis la Reine de la couvée. À 50 %, elle est invulnérable {@value #SHIELD_SECONDS}
 *   s, se protège et appelle diablotins et araignées ; toutes les {@value #QUEEN_BROOD_EVERY} s, des araignées. Personne
 *   dans l'antre pendant {@value #RESET_SECONDS} s : la couvée se retire (pas de soin : tout revient neuf).</li>
 * </ul>
 */
final class EastPath {

    static final float BROOD_EVERY = 7f;
    static final double BROOD_RANGE = 18;
    static final int BROOD_MAX = 3;
    static final double NEST_WAKE = 40;
    static final float WIND_EVERY = 6.5f;
    static final float WIND_WINDUP = 2.0f;
    static final int WIND_STRIPS = 3;
    static final float FALL_PART = 0.08f;
    static final float SHIELD_SECONDS = 5f;
    static final float QUEEN_BROOD_EVERY = 20f;
    static final float RESET_SECONDS = 25f;
    static final String PROTECTION = "Nakasar_Fractal_Brood_Protection";

    private static final class Nest {
        final int[] block;
        Ref<EntityStore> ref;
        boolean spawned;
        boolean dead;
        float clock;
        final List<Ref<EntityStore>> brood = new ArrayList<>();

        Nest(int[] block) {
            this.block = block;
        }

        Vector3d at() {
            return new Vector3d(block[0] + 0.5, block[1], block[2] + 0.5);
        }
    }

    enum Den { WAITING, MOTHERS, QUEEN, DONE }

    private final List<Nest> nests = new ArrayList<>();
    private final RunePair runes = new RunePair(DeepstoneLayout.EAST_RUNES);
    private boolean bridgeOpen;
    private boolean bridgeTold;
    private float wind;
    private Den den = Den.WAITING;
    private final List<Ref<EntityStore>> mothers = new ArrayList<>();
    private final List<Ref<EntityStore>> adds = new ArrayList<>();
    private Ref<EntityStore> queen;
    private boolean halved;
    private long shieldUntil;
    private float queenBrood;
    private float idle;
    private int epoch;

    EastPath() {
        nests.add(new Nest(DeepstoneLayout.CORRIDOR_NEST));
        for (int[] b : DeepstoneLayout.BRIDGE_NESTS) {
            nests.add(new Nest(b));
        }
        for (int[] b : DeepstoneLayout.QUEEN_NESTS) {
            nests.add(new Nest(b));
        }
    }

    boolean queenShielded() {
        return System.nanoTime() < shieldUntil;
    }

    void step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        if (den == Den.DONE) {
            return;
        }
        nests(world, store, st, players, dt);
        falls(store, st, players);
        if (!bridgeOpen) {
            bridge(world, store, st, players, dt);
        } else {
            den(world, store, st, players, dt);
        }
    }

    // --- nids ----------------------------------------------------------------------------------------------------

    private void nests(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        for (int i = 0; i < nests.size(); i++) {
            Nest n = nests.get(i);
            if (n.dead) {
                continue;
            }
            // Les nids de l'antre ne s'éveillent qu'avec les mères.
            boolean denNest = i > DeepstoneLayout.BRIDGE_NESTS.length;
            if (denNest && den == Den.WAITING) {
                continue;
            }
            if (!n.spawned) {
                if (Deepstone.near(store, players, n.at(), NEST_WAKE).isEmpty()) {
                    continue;
                }
                n.ref = st.foe(world, store, Deepstone.NEST, n.at(), true);
                n.spawned = n.ref != null;
                continue;
            }
            if (!Spawns.alive(store, n.ref)) {
                n.dead = true;
                WorldBlocks.clear(world.getChunkStore(), n.block[0], n.block[1], n.block[2]);
                Telegraphs.particle(store, "Nakasar_Fractal_Nest_Burst", n.at(), 1f);
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "nest.down"));
                continue;
            }
            n.brood.removeIf(ref -> !Spawns.alive(store, ref));
            n.clock += dt;
            if (n.clock >= BROOD_EVERY && n.brood.size() < BROOD_MAX
                    && !Deepstone.near(store, players, n.at(), BROOD_RANGE).isEmpty()) {
                n.clock = 0f;
                Ref<EntityStore> ref = st.foe(world, store, Deepstone.SPIDERLING, n.at(), false);
                if (ref != null) {
                    n.brood.add(ref);
                }
            }
        }
    }

    // --- le pont du vent -----------------------------------------------------------------------------------------

    private static boolean onBridge(Vector3d p) {
        int[] z = DeepstoneLayout.BRIDGE_ZONE;
        return p.x() >= z[0] && p.x() <= z[1] + 1 && p.z() >= z[2] && p.z() <= z[3] + 1
                && Math.abs(p.y() - DeepstoneLayout.VAULT_Y) < 4;
    }

    private void bridge(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        if (runes.step(store, st, players)) {
            bridgeOpen = true;
            Gates.open(world, store, DeepstoneLayout.EAST_GATE, Deepstone.MESSAGES + "bridge.solved");
            return;
        }
        boolean anyone = false;
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            anyone |= at != null && onBridge(at);
        }
        if (!anyone) {
            wind = 0f;
            return;
        }
        if (!bridgeTold) {
            bridgeTold = true;
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "bridge.intro"));
        }
        wind += dt;
        if (wind < WIND_EVERY) {
            return;
        }
        wind = 0f;
        int[] b = DeepstoneLayout.BRIDGE;
        int[] zone = DeepstoneLayout.BRIDGE_ZONE;
        double w = DeepstoneLayout.WIND_WIDTH;
        List<Double> centers = new ArrayList<>();
        for (double x = b[0] + w / 2; x <= b[1] + 1 - w / 2 + 0.01; x += w) {
            centers.add(x);
        }
        Collections.shuffle(centers);
        float windup = WIND_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Strip> strips = new ArrayList<>();
        for (int i = 0; i < Math.min(WIND_STRIPS, centers.size()); i++) {
            Vector3d start = new Vector3d(centers.get(i), DeepstoneLayout.VAULT_Y, zone[2]);
            strips.add(new Telegraphs.Strip(start, Math.PI / 2, DeepstoneLayout.WIND_LENGTH, w, now, windup));
        }
        int e = epoch;
        TelegraphSystem.start(world, (wo, s, t) -> {
            if (e != epoch || bridgeOpen) {
                return true;
            }
            boolean done = true;
            for (Telegraphs.Strip strip : strips) {
                done &= strip.step(s, t);
            }
            if (!done) {
                return false;
            }
            double mid = (zone[2] + zone[3] + 1) / 2.0;
            for (Telegraphs.Strip strip : strips) {
                Telegraphs.particle(s, "Nakasar_Fractal_Wind_Gust", strip.at(DeepstoneLayout.WIND_LENGTH / 2, 0), 1f);
                for (PlayerRef p : Spawns.alivePlayers(wo, s)) {
                    Vector3d pos = Telegraphs.position(s, p.getReference());
                    if (pos != null && strip.contains(pos)) {
                        double side = pos.z() < mid ? -1 : 1;
                        Moves.velocity(s, p.getReference(), new Vector3d(0, 6, 13 * side));
                        p.sendMessage(Message.translation(Deepstone.MESSAGES + "bridge.blown"));
                    }
                }
            }
            return true;
        });
    }

    /** Tombé dans le gouffre de l'est : retour au début du pont. */
    private static void falls(Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players) {
        int[] zone = DeepstoneLayout.BRIDGE_ZONE;
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null || at.y() > DeepstoneLayout.VAULT_Y - 6 || at.x() < zone[0] - 2 || at.x() > zone[1] + 6
                    || at.z() < -24 || at.z() > 34) {
                continue;
            }
            Moves.teleport(store, p.getReference(), Spawns.point(DeepstoneLayout.BRIDGE_START));
            Hurt.percent(store, p.getReference(), FALL_PART, Deepstone.CAUSE);
            Deepstone.tell(st, p, "bridge.fall");
        }
    }

    // --- l'antre de la Reine -------------------------------------------------------------------------------------

    private void den(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(DeepstoneLayout.QUEEN);
        List<PlayerRef> here = Deepstone.near(store, players, c, DeepstoneLayout.QUEEN_RADIUS + 4);
        if (den == Den.WAITING) {
            if (!Deepstone.near(store, players, c, DeepstoneLayout.QUEEN_RADIUS - 2).isEmpty()) {
                Gates.checkpoint(world, DeepstoneLayout.QUEEN, Deepstone.MESSAGES + "checkpoint");
                for (double[] at : DeepstoneLayout.MOTHERS) {
                    Ref<EntityStore> ref = st.boss(world, store, Deepstone.BROOD_MOTHER, Spawns.point(at), c);
                    if (ref != null) {
                        mothers.add(ref);
                    }
                }
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "queen.mothers"));
                den = Den.MOTHERS;
                idle = 0f;
            }
            return;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                reset(world, store);
                return;
            }
        } else {
            idle = 0f;
        }
        adds.removeIf(ref -> !Spawns.alive(store, ref));
        if (den == Den.MOTHERS) {
            mothers.removeIf(ref -> !Spawns.alive(store, ref));
            for (Ref<EntityStore> m : mothers) {
                Leash.keepOnDisc(store, m, c, DeepstoneLayout.QUEEN_RADIUS - 1, 2, Deepstone.FALL_LIMIT);
            }
            if (mothers.isEmpty()) {
                queen = st.boss(world, store, Deepstone.QUEEN, c, Spawns.point(DeepstoneLayout.BRIDGE_START));
                if (queen != null) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Nest_Burst", c, 2f);
                    Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "queen.enter"));
                    den = Den.QUEEN;
                    halved = false;
                    queenBrood = 0f;
                }
            }
            return;
        }
        if (!Spawns.alive(store, queen)) {
            Spawns.removeAll(store, adds);
            den = Den.DONE;
            Deepstone.dropOrb(world, st, 1);
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "queen.victory"));
            return;
        }
        Leash.keepOnDisc(store, queen, c, DeepstoneLayout.QUEEN_RADIUS - 1, 2, Deepstone.FALL_LIMIT);
        if (!halved && Hurt.healthFraction(store, queen) <= 0.5f) {
            halved = true;
            shieldUntil = System.nanoTime() + Telegraphs.seconds(SHIELD_SECONDS);
            Hurt.effect(store, queen, PROTECTION, 15f);
            Hurt.effect(store, queen, "Nakasar_Fractal_Shadow_Veil", SHIELD_SECONDS);
            for (int i = 0; i < 2; i++) {
                spawnAdd(world, store, st, Deepstone.IMP, c, true);
            }
            for (int i = 0; i < 3; i++) {
                spawnAdd(world, store, st, Deepstone.SPIDERLING, c, false);
            }
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "queen.protect"));
        }
        queenBrood += dt;
        if (queenBrood >= QUEEN_BROOD_EVERY) {
            queenBrood = 0f;
            for (int i = 0; i < 3; i++) {
                spawnAdd(world, store, st, Deepstone.SPIDERLING, c, false);
            }
        }
    }

    private void spawnAdd(World world, Store<EntityStore> store, Deepstone.State st, String role, Vector3d c, boolean loot) {
        double a = Math.random() * Math.PI * 2;
        double r = 5 + Math.random() * 5;
        Vector3d at = new Vector3d(c.x() + Math.cos(a) * r, c.y(), c.z() + Math.sin(a) * r);
        Ref<EntityStore> ref = st.foe(world, store, role, at, loot);
        if (ref != null) {
            adds.add(ref);
        }
    }

    private void reset(World world, Store<EntityStore> store) {
        Spawns.removeAll(store, mothers);
        Spawns.removeAll(store, adds);
        Spawns.remove(store, queen);
        queen = null;
        shieldUntil = 0;
        den = Den.WAITING;
        epoch++;
        Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "queen.reset"));
    }
}
