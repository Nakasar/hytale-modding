package dev.nakasar.hytale.fractals.instability;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Instabilités suivies dans le temps, quatre fois par seconde dans chaque fractale qui en a :
 * <ul>
 *   <li>à l'arrivée, chaque joueur reçoit la liste du jour ;</li>
 *   <li>Traînée toxique : un joueur qui avance laisse une flaque toutes les {@value #PUDDLE_INTERVAL} s ; armée au
 *   bout de {@value #PUDDLE_ARM} s, elle empoisonne qui s'y tient pendant {@value #PUDDLE_LIFE} s ;</li>
 *   <li>Malaise social : chaque seconde, {@value #AWKWARD_PART} des PV max à qui a un allié à moins de
 *   {@value #AWKWARD_RADIUS} blocs ;</li>
 *   <li>Restez groupés : icône « ensemble » ou « isolé » sur chaque joueur (le bonus est compté au coup) ;</li>
 *   <li>Bombe de flux : toutes les {@value #FLUX_INTERVAL} s, un joueur au hasard est marqué et pulse
 *   {@value #FLUX_PULSES} fois (cercle rouge de {@value #FLUX_RADIUS} blocs posé sous lui, {@value #FLUX_PART} des PV
 *   à qui y est encore) ;</li>
 *   <li>Nuée : toutes les {@value #BIRD_INTERVAL} s de combat (un ennemi à moins de 16 blocs d'un joueur), 2 corbeaux
 *   (3 à partir de 3 joueurs) fondent sur un joueur, {@value #BIRD_CAP} au plus.</li>
 * </ul>
 */
public final class InstabilitySystem extends TickingSystem<EntityStore> {

    public static final String BIRD = "Nakasar_Fractal_Crow";
    public static final String FLUX_MARK = "Nakasar_Fractal_Flux_Bomb";
    public static final String TOGETHER = "Nakasar_Fractal_Together";
    public static final String ALONE = "Nakasar_Fractal_Alone";
    static final float INTERVAL = 0.25f;
    static final float PUDDLE_INTERVAL = 1.2f;
    static final float PUDDLE_ARM = 1.2f;
    static final float PUDDLE_LIFE = 6f;
    static final double PUDDLE_RADIUS = 1.3;
    static final int PUDDLE_CAP = 60;
    static final float AWKWARD_PART = 0.03f;
    static final double AWKWARD_RADIUS = 2;
    static final float FLUX_INTERVAL = 18f;
    static final int FLUX_PULSES = 4;
    static final float FLUX_RADIUS = 3f;
    static final float FLUX_PART = 0.04f;
    static final float BIRD_INTERVAL = 25f;
    static final int BIRD_CAP = 6;
    static final double COMBAT_RANGE = 16;

    private static final class Puddle {
        final Vector3d at;
        float age;
        float glow;

        Puddle(Vector3d at) {
            this.at = at;
        }
    }

    private static final class State {
        final Set<UUID> announced = new HashSet<>();
        final Map<UUID, Vector3d> lastDrop = new HashMap<>();
        final Map<UUID, Float> dropClock = new HashMap<>();
        final List<Puddle> puddles = new ArrayList<>();
        final List<Ref<EntityStore>> birds = new ArrayList<>();
        float second;
        float fluxClock = FLUX_INTERVAL / 2;
        float birdClock;
    }

    private static final Map<World, State> STATES = Collections.synchronizedMap(new WeakHashMap<>());
    private final Map<World, float[]> elapsed = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        FractalRuns.Run run = FractalRuns.of(world);
        if (run == null || run.instabilities().isEmpty()) {
            return;
        }
        float[] e = elapsed.computeIfAbsent(world, w -> new float[1]);
        e[0] += dt;
        if (e[0] < INTERVAL) {
            return;
        }
        float step = e[0];
        e[0] = 0f;
        world.execute(() -> step(world, run, step));
    }

    private static void step(World world, FractalRuns.Run run, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = STATES.computeIfAbsent(world, w -> new State());
        List<Instability> active = run.instabilities();
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        for (PlayerRef player : world.getPlayerRefs()) {
            if (st.announced.add(player.getUuid())) {
                player.sendMessage(Message.translation(Instability.LANG + "arrival"));
                player.sendMessage(Instabilities.describe(active));
            }
        }
        st.second += dt;
        boolean everySecond = st.second >= 1f;
        if (everySecond) {
            st.second = 0f;
        }
        if (active.contains(Instability.TOXIC_TRAIL)) {
            toxicTrail(world, store, st, players, dt);
        }
        if (everySecond && active.contains(Instability.SOCIAL_AWKWARDNESS)) {
            socialAwkwardness(store, players);
        }
        if (everySecond && active.contains(Instability.STICK_TOGETHER)) {
            stickTogether(world, store, players);
        }
        if (active.contains(Instability.FLUX_BOMB)) {
            st.fluxClock += dt;
            if (st.fluxClock >= FLUX_INTERVAL && !players.isEmpty()) {
                st.fluxClock = 0f;
                fluxBomb(world, store, players.get(ThreadLocalRandom.current().nextInt(players.size())));
            }
        }
        if (active.contains(Instability.BIRDS)) {
            birds(world, store, st, players, dt);
        }
    }

    // --- traînée toxique --------------------------------------------------------------------------------

    private static void toxicTrail(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at == null) {
                continue;
            }
            UUID id = player.getUuid();
            float clock = st.dropClock.getOrDefault(id, 0f) + dt;
            Vector3d last = st.lastDrop.get(id);
            if (clock >= PUDDLE_INTERVAL && (last == null || last.distance(at) >= 1.5) && st.puddles.size() < PUDDLE_CAP) {
                clock = 0f;
                Vector3d where = new Vector3d(at.x(), Math.floor(at.y() + 0.05), at.z());
                st.puddles.add(new Puddle(where));
                st.lastDrop.put(id, where);
                Telegraphs.particle(store, "Nakasar_Fractal_Toxic_Puddle", new Vector3d(where).add(0, 0.1, 0), 1f);
            }
            st.dropClock.put(id, clock);
        }
        for (Iterator<Puddle> it = st.puddles.iterator(); it.hasNext(); ) {
            Puddle puddle = it.next();
            puddle.age += dt;
            if (puddle.age >= PUDDLE_LIFE) {
                it.remove();
                continue;
            }
            puddle.glow += dt;
            if (puddle.glow >= 1f) {
                puddle.glow = 0f;
                Telegraphs.particle(store, "Nakasar_Fractal_Toxic_Puddle", new Vector3d(puddle.at).add(0, 0.1, 0), 1f);
            }
            if (puddle.age < PUDDLE_ARM) {
                continue;
            }
            for (PlayerRef player : players) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d at = Telegraphs.position(store, ref);
                if (at != null && Telegraphs.horizontal(at, puddle.at) <= PUDDLE_RADIUS && Math.abs(at.y() - puddle.at.y()) <= 1.5
                        && !Hurt.has(store, ref, "Poison_T1")) {
                    Hurt.effect(store, ref, "Poison_T1", 3f);
                }
            }
        }
    }

    // --- malaise social, restez groupés ------------------------------------------------------------------

    private static void socialAwkwardness(Store<EntityStore> store, List<PlayerRef> players) {
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            for (PlayerRef other : players) {
                Vector3d there = other == player ? null : Telegraphs.position(store, other.getReference());
                if (there != null && there.distance(at) <= AWKWARD_RADIUS) {
                    Hurt.percent(store, ref, AWKWARD_PART, Instabilities.CAUSE);
                    Telegraphs.particle(store, "Nakasar_Fractal_Flux_Pulse", new Vector3d(at).add(0, 1, 0), 0.4f);
                    break;
                }
            }
        }
    }

    private static void stickTogether(World world, Store<EntityStore> store, List<PlayerRef> players) {
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            boolean near = false;
            Vector3d at = Telegraphs.position(store, ref);
            for (PlayerRef other : players) {
                Vector3d there = other == player || at == null ? null : Telegraphs.position(store, other.getReference());
                if (there != null && there.distance(at) <= Instabilities.TOGETHER_RADIUS) {
                    near = true;
                    break;
                }
            }
            Hurt.effect(store, ref, near ? TOGETHER : ALONE, 1.5f);
        }
    }

    // --- bombe de flux ---------------------------------------------------------------------------------

    private static void fluxBomb(World world, Store<EntityStore> store, PlayerRef carrier) {
        Ref<EntityStore> ref = carrier.getReference();
        Hurt.effect(store, ref, FLUX_MARK, FLUX_PULSES + 1f);
        carrier.sendMessage(Message.translation(Instability.LANG + "flux.marked"));
        float fill = Math.max(0.6f, FractalRuns.windupFactor(world));
        for (int k = 0; k < FLUX_PULSES; k++) {
            Delayed.later(world, k * 1.0f, s -> {
                Vector3d at = Telegraphs.position(s, ref);
                if (at == null) {
                    return;
                }
                Vector3d center = new Vector3d(at);
                Telegraphs.circle(s, center, FLUX_RADIUS, fill);
                Telegraphs.particle(s, "Nakasar_Fractal_Flux_Mark", new Vector3d(center).add(0, 2.4, 0), 1f);
                Delayed.later(world, fill, s2 -> {
                    Telegraphs.particle(s2, "Nakasar_Fractal_Flux_Pulse", new Vector3d(center).add(0, 0.3, 0), 1.2f);
                    Telegraphs.sound(s2, "SFX_Emit_Goblin_Flame_Quadrant_Blast", center);
                    for (PlayerRef player : world.getPlayerRefs()) {
                        Ref<EntityStore> r = player.getReference();
                        Vector3d p = Telegraphs.position(s2, r);
                        if (p != null && Telegraphs.horizontal(p, center) <= FLUX_RADIUS + 0.3 && Math.abs(p.y() - center.y()) <= 3) {
                            Hurt.percent(s2, r, FLUX_PART, Instabilities.CAUSE);
                        }
                    }
                });
            });
        }
    }

    // --- nuée -----------------------------------------------------------------------------------------

    private static void birds(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        st.birds.removeIf(ref -> !Spawns.alive(store, ref));
        PlayerRef fighting = null;
        List<Vector3d> foes = foePositions(store);
        for (PlayerRef player : Spawns.pick(players, players.size())) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && foes.stream().anyMatch(f -> f.distance(at) <= COMBAT_RANGE)) {
                fighting = player;
                break;
            }
        }
        if (fighting == null) {
            return;
        }
        st.birdClock += dt;
        if (st.birdClock < BIRD_INTERVAL) {
            return;
        }
        st.birdClock = 0f;
        Vector3d at = Telegraphs.position(store, fighting.getReference());
        int count = players.size() >= 3 ? 3 : 2;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int k = 0; k < count && st.birds.size() < BIRD_CAP && at != null; k++) {
            double a = random.nextDouble(Math.PI * 2);
            Vector3d where = new Vector3d(at.x() + Math.cos(a) * 6, at.y() + 4, at.z() + Math.sin(a) * 6);
            Ref<EntityStore> bird = Spawns.spawnFoe(world, store, BIRD, where, Telegraphs.yawToward(where, at));
            if (bird != null) {
                st.birds.add(bird);
            }
        }
        if (at != null) {
            Telegraphs.sound(store, "SFX_Spirit_Root_Alerted", at);
        }
    }

    private static List<Vector3d> foePositions(Store<EntityStore> store) {
        List<Vector3d> out = new ArrayList<>();
        List<Ref<EntityStore>> refs = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
                if (npc != null && transform != null && !Instabilities.isExempt(npc.getRoleName()) && !BIRD.equals(npc.getRoleName())) {
                    refs.add(chunk.getReferenceTo(i));
                    out.add(new Vector3d(transform.getPosition()));
                }
            }
        });
        List<Vector3d> foes = new ArrayList<>();
        for (int i = 0; i < refs.size(); i++) {
            if (Foes.inGroup(refs.get(i), store)) {
                foes.add(out.get(i));
            }
        }
        return foes;
    }

    public static void clearAll() {
        STATES.clear();
    }
}
