package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.GlobalSpawnProvider;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import dev.nakasar.hytale.fractals.arena.Box;
import dev.nakasar.hytale.fractals.arena.SafeLandings;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.hammer.Hammer;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * La Falaise (étape 4 du GDD) : le déroulé d'une partie, monde par monde, mené par {@link CliffsideSystem} quatre fois
 * par seconde sur le thread du monde.
 *
 * <ol>
 *   <li>{@link Stage#CAMP} : le Chercheur et une vague de cultistes au camp ; le râtelier ne donne le marteau qu'une
 *   fois le camp nettoyé ;</li>
 *   <li>{@link Stage#KNEES} : deux sceaux aux genoux ({@value #KNEE_BREAKS} coups chargés chacun), vagues renouvelées
 *   toutes les {@value #KNEE_REFILL} s ; brisés, la barrière G1 s'ouvre ;</li>
 *   <li>{@link Stage#CLIMB} : tunnel aux plaques et saut des gargouilles ({@link Traps}, {@link SafeLandings}) ;</li>
 *   <li>{@link Stage#CHEST} : sceau de la poitrine ({@value #CHEST_BREAKS} coups), foyers, vagues toutes les
 *   {@value #CHEST_REFILL} s ; brisé, G2 s'ouvre ;</li>
 *   <li>{@link Stage#ARMS} : sceaux des poignets ({@value #WRIST_BREAKS} coups), protégés à tour de rôle par une bulle,
 *   réparés par les incantateurs proches, vagues sans fin ; brisés, G3 s'ouvre ;</li>
 *   <li>{@link Stage#RAMPS} : rampes aux bombes ;</li>
 *   <li>{@link Stage#ARENA} : l'Archidevin ({@link Archdiviner}) ; {@link Stage#DONE} une fois vaincu.</li>
 * </ol>
 *
 * <p>Les sceaux sont des PNJ fixes ({@value #SEAL_ROLE}) : le jeu refuse les coups sur les blocs dans nos instances
 * (ni casse ni modification de blocs), les PNJ, eux, reçoivent les coups. {@link CliffsideDamageFilter} annule tous
 * leurs dégâts et appelle {@link #onSealHit}. Tout ce que pose le Java est non sauvegardé : une instance rechargée
 * repart du camp.
 */
public final class Cliffside {

    public static final String FRACTAL = "Cliffside";
    public static final String SEAL_ROLE = "Nakasar_Fractal_Seal";
    public static final String FANATIC = "Nakasar_Fractal_Cultist_Fanatic";
    public static final String CHANTER = "Nakasar_Fractal_Cultist_Chanter";
    public static final String SEEKER = "Nakasar_Fractal_Seeker";
    public static final String DEVOURER = "Nakasar_Fractal_Devourer";
    static final String MESSAGES = "nakasar_fractals_cliffside.";

    static final int KNEE_BREAKS = 2;
    static final int CHEST_BREAKS = 3;
    static final int WRIST_BREAKS = 3;
    static final float KNEE_REFILL = 30f;
    static final float CHEST_REFILL = 20f;
    static final float ARM_REFILL = 12f;
    static final int WAVE_CAP = 4;
    static final float MEND_INTERVAL = 20f;
    static final double MEND_RANGE = 10;
    /** Index des sceaux dans {@link CliffsideLayout#SEALS}. */
    static final int KNEE_W = 0, KNEE_E = 1, CHEST_SEAL = 2, WRIST_W = 3, WRIST_E = 4, NECK = 5;
    private static final int[] BREAKS = {KNEE_BREAKS, KNEE_BREAKS, CHEST_BREAKS, WRIST_BREAKS, WRIST_BREAKS, 1};
    private static final double SEAL_RESPAWN_RANGE = 80;
    static final double FALL_LIMIT = 3;

    public enum Stage { CAMP, KNEES, CLIMB, CHEST, ARMS, RAMPS, ARENA, DONE }

    /** Un sceau : son PNJ, les coups chargés qu'il lui faut encore, sa bulle. */
    static final class Seal {
        Ref<EntityStore> ref;
        int left;
        boolean shielded;
        boolean broken;
        float mend;
        float glow;
    }

    /** Une partie de la Falaise. */
    static final class State {
        Stage stage = Stage.CAMP;
        float clock;
        boolean started;
        boolean campCleared;
        final List<Ref<EntityStore>> camp = new ArrayList<>();
        Ref<EntityStore> seeker;
        final Seal[] seals = new Seal[CliffsideLayout.SEALS.length];
        int broken;
        /** Cultistes de chaque vague (index des sceaux 0 à 4) et compte à rebours avant le prochain. */
        @SuppressWarnings("unchecked")
        final List<Ref<EntityStore>>[] waves = new List[5];
        final float[] refill = new float[5];
        final int[] spawned = new int[5];
        final Traps traps = new Traps();
        final SafeLandings landings = new SafeLandings(CliffsideLayout.JUMP_ZONES, MESSAGES + "landing.back");
        final Cages cages = new Cages();
        final Archdiviner boss = new Archdiviner();
        final Map<UUID, Long> throttle = new HashMap<>();
        /** Point d'apparition de chaque cultiste et dévoreur : ils ne tombent jamais des plates-formes. */
        final Map<Ref<EntityStore>, Vector3d> homes = new HashMap<>();

        State() {
            for (int i = 0; i < seals.length; i++) {
                seals[i] = new Seal();
                seals[i].left = BREAKS[i];
            }
            seals[WRIST_E].shielded = true;
            seals[NECK].shielded = true;
            for (int i = 0; i < waves.length; i++) {
                waves[i] = new ArrayList<>();
            }
        }
    }

    private static final Map<World, State> STATES = Collections.synchronizedMap(new WeakHashMap<>());

    private Cliffside() {
    }

    public static boolean isCliffside(World world) {
        return FRACTAL.equals(FractalCatalog.fractalOf(world));
    }

    static State state(World world) {
        return STATES.computeIfAbsent(world, w -> new State());
    }

    /** Barres de boss de la Falaise : l'Archidevin (avec sa défiance) et les sceaux, dès le premier coup reçu. */
    public static void registerBossBars() {
        BossBarSystem.register(Archdiviner.ROLE);
        BossBarSystem.label(Archdiviner.ROLE, Defiance::label);
        BossBarSystem.register(SEAL_ROLE);
    }

    public static void clearAll() {
        STATES.clear();
    }

    // --- pas de jeu -------------------------------------------------------------------------------

    static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        st.clock += dt;
        List<PlayerRef> players = alivePlayers(world, store);
        if (players.isEmpty()) {
            st.boss.idle(world, store, st, dt);
            return;
        }
        if (!st.started) {
            st.started = true;
            for (PlayerRef player : world.getPlayerRefs()) {
                player.sendMessage(Message.translation(MESSAGES + "camp.intro"));
            }
            for (int i = 0; i < CliffsideLayout.CAMP_WAVE.length; i++) {
                Ref<EntityStore> foe = spawnFoe(world, store, i < 3 ? FANATIC : CHANTER, CliffsideLayout.CAMP_WAVE[i]);
                if (foe != null) {
                    st.camp.add(foe);
                }
            }
        }
        keepSeeker(store, st);
        keepSeals(world, store, st, players);
        if (!st.campCleared && st.camp.stream().noneMatch(ref -> alive(store, ref))) {
            st.campCleared = true;
        }
        switch (st.stage) {
            case CAMP -> {
                if (anyIn(store, players, CliffsideLayout.KNEES_DECK)) {
                    enter(world, store, st, Stage.KNEES);
                }
            }
            case KNEES -> {
                refill(world, store, st, KNEE_W, KNEE_REFILL, dt);
                refill(world, store, st, KNEE_E, KNEE_REFILL, dt);
            }
            case CLIMB -> {
                if (anyIn(store, players, CliffsideLayout.CHEST_DECK)) {
                    enter(world, store, st, Stage.CHEST);
                }
            }
            case CHEST -> refill(world, store, st, CHEST_SEAL, CHEST_REFILL, dt);
            case ARMS -> {
                if (anyIn(store, players, CliffsideLayout.SHOULDERS_TOP)) {
                    refill(world, store, st, WRIST_W, ARM_REFILL, dt);
                    refill(world, store, st, WRIST_E, ARM_REFILL, dt);
                }
                mend(world, store, st, WRIST_W, dt);
                mend(world, store, st, WRIST_E, dt);
            }
            case RAMPS -> {
                if (anyInArena(store, players)) {
                    enter(world, store, st, Stage.ARENA);
                }
            }
            default -> {
            }
        }
        keepOnLedges(store, st);
        st.traps.step(world, store, st, players, dt);
        st.landings.step(world, store, players);
        st.cages.step(world, store, players, dt);
        if (st.stage == Stage.ARENA) {
            st.boss.step(world, store, st, players, dt);
        }
    }

    private static void enter(World world, Store<EntityStore> store, State st, Stage stage) {
        st.stage = stage;
        switch (stage) {
            case KNEES -> {
                wave(world, store, st, KNEE_W);
                wave(world, store, st, KNEE_E);
            }
            case CHEST -> wave(world, store, st, CHEST_SEAL);
            case ARMS -> {
                wave(world, store, st, WRIST_W);
                wave(world, store, st, WRIST_E);
            }
            case ARENA -> checkpoint(world, CliffsideLayout.CHECKPOINT_ARENA);
            default -> {
            }
        }
    }

    // --- sceaux ------------------------------------------------------------------------------------

    /** Pose les sceaux manquants (non brisés) quand un joueur est assez près ; montre la bulle des sceaux protégés. */
    private static void keepSeals(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        for (int i = 0; i < st.seals.length; i++) {
            Seal seal = st.seals[i];
            if (seal.broken) {
                continue;
            }
            double[] at = CliffsideLayout.SEALS[i];
            Vector3d where = new Vector3d(at[0], at[1], at[2]);
            if (seal.ref == null || !seal.ref.isValid()) {
                if (nearest(store, players, where) > SEAL_RESPAWN_RANGE) {
                    continue;
                }
                seal.ref = spawn(store, SEAL_ROLE, where, (float) Math.PI);
                if (seal.ref != null) {
                    store.ensureAndGetComponent(seal.ref, Frozen.getComponentType());
                    showBreaks(store, seal, i);
                }
            }
            seal.glow += 0.25f;
            if (seal.shielded && seal.glow >= 1f && seal.ref != null) {
                seal.glow = 0f;
                Telegraphs.particle(store, "Nakasar_Fractal_Shield_Glow", where, 1.6f);
            }
        }
    }

    /** La vie du sceau montre les coups qui restent (barre de boss dès le premier coup). */
    private static void showBreaks(Store<EntityStore> store, Seal seal, int index) {
        EntityStatMap stats = seal.ref == null ? null : store.getComponent(seal.ref, EntityStatMap.getComponentType());
        if (stats == null || index == NECK) {
            return;
        }
        int health = DefaultEntityStatTypes.getHealth();
        var value = stats.get(health);
        if (value != null) {
            stats.setStatValue(health, value.getMax() * seal.left / BREAKS[index]);
        }
    }

    /** Coup d'un joueur sur un sceau (thread du monde). */
    static void onSealHit(World world, Ref<EntityStore> sealRef, Ref<EntityStore> playerRef) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        PlayerRef player = playerRef.isValid() ? store.getComponent(playerRef, PlayerRef.getComponentType()) : null;
        int index = -1;
        for (int i = 0; i < st.seals.length; i++) {
            if (sealRef.equals(st.seals[i].ref)) {
                index = i;
            }
        }
        if (player == null || index < 0 || st.seals[index].broken) {
            return;
        }
        Seal seal = st.seals[index];
        if (!Hammer.holds(store, playerRef)) {
            tell(st, player, "seal.needHammer");
            return;
        }
        if (seal.shielded) {
            tell(st, player, "seal.shielded");
            return;
        }
        if (!Hammer.consumeCharge(player.getUuid())) {
            tell(st, player, "seal.needCharge");
            return;
        }
        double[] at = CliffsideLayout.SEALS[index];
        Vector3d where = new Vector3d(at[0], at[1], at[2]);
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", where, 1.2f);
        Telegraphs.sound(store, "SFX_Mace_T2_Signature_Impact", where);
        if (index == NECK) {
            st.boss.onNeckHit(world, store, st);
            return;
        }
        seal.left--;
        seal.mend = 0f;
        if (seal.left > 0) {
            showBreaks(store, seal, index);
            for (PlayerRef p : world.getPlayerRefs()) {
                p.sendMessage(Message.translation(MESSAGES + "seal.cracked").param("left", seal.left));
            }
            alternate(st, index);
            return;
        }
        breakSeal(world, store, st, index);
    }

    /** Bulle alternée des poignets : frapper l'un le protège et découvre l'autre. */
    private static void alternate(State st, int index) {
        if (index != WRIST_W && index != WRIST_E) {
            return;
        }
        int other = index == WRIST_W ? WRIST_E : WRIST_W;
        if (!st.seals[other].broken) {
            st.seals[index].shielded = true;
            st.seals[other].shielded = false;
        }
    }

    private static void breakSeal(World world, Store<EntityStore> store, State st, int index) {
        Seal seal = st.seals[index];
        seal.broken = true;
        seal.shielded = false;
        if (seal.ref != null && seal.ref.isValid()) {
            store.removeEntity(seal.ref, RemoveReason.REMOVE);
        }
        seal.ref = null;
        st.broken++;
        EventTitleUtil.showEventTitleToWorld(Message.translation(MESSAGES + "title.seal"),
                Message.translation(MESSAGES + "seal.broken").param("count", st.broken), EventTitleStyle.Major, null,
                3f, 0.3f, 0.8f, world);
        if (index == WRIST_W || index == WRIST_E) {
            int other = index == WRIST_W ? WRIST_E : WRIST_W;
            st.seals[other].shielded = false;
        }
        switch (index) {
            case KNEE_W, KNEE_E -> {
                if (st.seals[KNEE_W].broken && st.seals[KNEE_E].broken) {
                    openGate(world, store, CliffsideLayout.GATE1);
                    checkpoint(world, CliffsideLayout.CHECKPOINT_KNEES);
                    st.stage = Stage.CLIMB;
                }
            }
            case CHEST_SEAL -> {
                openGate(world, store, CliffsideLayout.GATE2);
                checkpoint(world, CliffsideLayout.CHECKPOINT_CHEST);
                enter(world, store, st, Stage.ARMS);
            }
            case WRIST_W, WRIST_E -> {
                if (st.seals[WRIST_W].broken && st.seals[WRIST_E].broken) {
                    openGate(world, store, CliffsideLayout.GATE3);
                    checkpoint(world, CliffsideLayout.CHECKPOINT_SHOULDERS);
                    st.stage = Stage.RAMPS;
                }
            }
            default -> {
            }
        }
    }

    /** Incantateurs à moins de {@value #MEND_RANGE} blocs d'un sceau fissuré : un coup réparé toutes les {@value #MEND_INTERVAL} s. */
    private static void mend(World world, Store<EntityStore> store, State st, int index, float dt) {
        Seal seal = st.seals[index];
        if (seal.broken || seal.left >= BREAKS[index]) {
            seal.mend = 0f;
            return;
        }
        double[] at = CliffsideLayout.SEALS[index];
        Vector3d where = new Vector3d(at[0], at[1], at[2]);
        boolean chanter = st.waves[index].stream().anyMatch(ref -> {
            Vector3d p = Telegraphs.position(store, ref);
            return p != null && p.distance(where) <= MEND_RANGE && CHANTER.equals(role(store, ref));
        });
        if (!chanter) {
            seal.mend = 0f;
            return;
        }
        seal.mend += dt;
        if (seal.mend < MEND_INTERVAL) {
            return;
        }
        seal.mend = 0f;
        seal.left++;
        showBreaks(store, seal, index);
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Mend", where, 1.2f);
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(MESSAGES + "seal.mended"));
        }
    }

    // --- vagues ------------------------------------------------------------------------------------

    /** Première vague d'un sceau : trois fanatiques et un incantateur. */
    private static void wave(World world, Store<EntityStore> store, State st, int index) {
        for (int k = 0; k < 4; k++) {
            spawnWave(world, store, st, index, k == 3 ? CHANTER : FANATIC);
        }
        st.refill[index] = 0f;
    }

    /** Tant que le sceau tient : un cultiste de plus toutes les `interval` s, {@value #WAVE_CAP} vivants au plus. */
    private static void refill(World world, Store<EntityStore> store, State st, int index, float interval, float dt) {
        if (st.seals[index].broken) {
            return;
        }
        st.waves[index].removeIf(ref -> !alive(store, ref));
        st.refill[index] += dt;
        if (st.refill[index] < interval || st.waves[index].size() >= WAVE_CAP) {
            return;
        }
        st.refill[index] = 0f;
        spawnWave(world, store, st, index, st.spawned[index] % 3 == 2 ? CHANTER : FANATIC);
    }

    private static void spawnWave(World world, Store<EntityStore> store, State st, int index, String role) {
        double[][] points = CliffsideLayout.WAVES[index];
        double[] at = points[st.spawned[index] % points.length];
        st.spawned[index]++;
        Ref<EntityStore> foe = spawnFoe(world, store, role, at);
        if (foe != null) {
            st.waves[index].add(foe);
        }
    }

    /**
     * Un ennemi des fractales en `at`, non sauvegardé, vie selon le groupe et le niveau ({@link Spawns#spawnFoe}) ;
     * {@link #keepOnLedges} le ramène là s'il tombe.
     */
    static Ref<EntityStore> spawnFoe(World world, Store<EntityStore> store, String role, double[] at) {
        Ref<EntityStore> ref = Spawns.spawnFoe(world, store, role, at);
        if (ref != null) {
            state(world).homes.put(ref, new Vector3d(at[0], at[1], at[2]));
        }
        return ref;
    }

    /** Un cultiste tombé de plus de {@value #FALL_LIMIT} blocs sous son point d'apparition y est ramené. */
    private static void keepOnLedges(Store<EntityStore> store, State st) {
        st.homes.entrySet().removeIf(e -> !Spawns.alive(store, e.getKey()));
        for (Map.Entry<Ref<EntityStore>, Vector3d> e : st.homes.entrySet()) {
            Vector3d at = Telegraphs.position(store, e.getKey());
            Vector3d home = e.getValue();
            if (at != null && at.y() < home.y() - FALL_LIMIT) {
                store.putComponent(e.getKey(), Teleport.getComponentType(),
                        new Teleport(new Vector3d(home), new Rotation3f(0f, Telegraphs.yawToward(home, at), 0f)));
            }
        }
    }

    /** Pose le PNJ `role` (non sauvegardé), tourné de `yaw` ; null si le jeu refuse. */
    static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at, float yaw) {
        return Spawns.spawn(store, role, at, yaw);
    }

    private static void keepSeeker(Store<EntityStore> store, State st) {
        if (st.seeker != null && st.seeker.isValid()) {
            return;
        }
        double[] at = CliffsideLayout.SEEKER;
        st.seeker = spawn(store, SEEKER, new Vector3d(at[0], at[1], at[2]), (float) Math.PI);
        if (st.seeker != null) {
            store.ensureAndGetComponent(st.seeker, Invulnerable.getComponentType());
        }
    }

    // --- barrières, points de retour, râtelier ---------------------------------------------------------

    private static void openGate(World world, Store<EntityStore> store, int[][] cells) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] c : cells) {
            WorldBlocks.clear(chunks, c[0], c[1], c[2]);
        }
        int[] mid = cells[cells.length / 2];
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", new Vector3d(mid[0] + 0.5, mid[1], mid[2] + 0.5), 1.5f);
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(MESSAGES + "gate.open"));
        }
    }

    /** Déplace le point d'apparition du monde (réapparition, filet anti-chute) ; regard vers le nord (le colosse). */
    static void checkpoint(World world, double[] at) {
        world.getWorldConfig().setSpawnProvider(new GlobalSpawnProvider(new Transform(new Vector3d(at[0], at[1], at[2]), new Rotation3f())));
        world.getWorldConfig().markChanged();
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(MESSAGES + "checkpoint"));
        }
    }

    /** Râtelier du camp : le marteau, une fois le camp nettoyé, s'il n'est entre les mains de personne. */
    static void takeHammer(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player) {
        State st = state(world);
        if (!st.campCleared) {
            player.sendMessage(Message.translation(MESSAGES + "camp.guarded"));
            return;
        }
        if (Hammer.carries(store, ref)) {
            player.sendMessage(Message.translation(MESSAGES + "hammer.have"));
            return;
        }
        for (PlayerRef other : world.getPlayerRefs()) {
            Ref<EntityStore> otherRef = other.getReference();
            if (otherRef != null && otherRef.isValid() && !otherRef.equals(ref) && Hammer.carries(store, otherRef)) {
                player.sendMessage(Message.translation(MESSAGES + "hammer.already").param("name", other.getUsername()));
                return;
            }
        }
        Hammer.give(store, ref);
    }

    // --- outils ---------------------------------------------------------------------------------------

    static void tell(State st, PlayerRef player, String key) {
        long now = System.nanoTime();
        Long last = st.throttle.get(player.getUuid());
        if (last != null && now - last < Telegraphs.seconds(2.5f)) {
            return;
        }
        st.throttle.put(player.getUuid(), now);
        player.sendMessage(Message.translation(MESSAGES + key));
    }

    static List<PlayerRef> alivePlayers(World world, Store<EntityStore> store) {
        return Spawns.alivePlayers(world, store);
    }

    static boolean alive(Store<EntityStore> store, Ref<EntityStore> ref) {
        return Spawns.alive(store, ref);
    }

    static String role(Store<EntityStore> store, Ref<EntityStore> ref) {
        return Spawns.role(store, ref);
    }

    static boolean anyIn(Store<EntityStore> store, List<PlayerRef> players, Box box) {
        return Spawns.anyIn(store, players, box);
    }

    static boolean inArena(Vector3d at) {
        double[] c = CliffsideLayout.ARENA_CENTER;
        return at.y() >= c[1] - 4 && at.y() <= c[1] + 8
                && Math.hypot(at.x() - c[0], at.z() - c[2]) <= CliffsideLayout.ARENA_RADIUS + 0.5;
    }

    static boolean anyInArena(Store<EntityStore> store, List<PlayerRef> players) {
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && inArena(at)) {
                return true;
            }
        }
        return false;
    }

    static double nearest(Store<EntityStore> store, List<PlayerRef> players, Vector3d where) {
        return Spawns.nearest(store, players, where);
    }
}
