package dev.nakasar.hytale.fractals.cliffside;

import dev.nakasar.hytale.fractals.FractalsPlugin;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.util.NotificationUtil;
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
    /** Sceau intact, fissuré, très fissuré : un modèle par état (tools/generate_cliffside.py). */
    public static final String[] SEAL_ROLES = {SEAL_ROLE, SEAL_ROLE + "_Cracked_1", SEAL_ROLE + "_Cracked_2"};
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
    /** Index des sceaux dans {@link CliffsideLayout#SEALS}. */
    static final int KNEE_W = 0, KNEE_E = 1, CHEST_SEAL = 2, WRIST_W = 3, WRIST_E = 4, NECK = 5;
    private static final int[] BREAKS = {KNEE_BREAKS, KNEE_BREAKS, CHEST_BREAKS, WRIST_BREAKS, WRIST_BREAKS, 1};
    private static final double SEAL_RESPAWN_RANGE = 80;
    static final double SHIELD_RADIUS = 2.2;
    /** Distance de l'incantateur au sceau qu'il répare (côté de sa vague). */
    static final double CHANNEL_DISTANCE = 2.5;
    static final double FALL_LIMIT = 3;

    public enum Stage { CAMP, KNEES, CLIMB, CHEST, ARMS, RAMPS, ARENA, DONE }

    /** Un sceau : son PNJ, les coups chargés qu'il lui faut encore, sa bulle. */
    static final class Seal {
        Ref<EntityStore> ref;
        /** Rôle posé (sceau intact ou fissuré) : il change avec les coups qui restent. */
        String shown;
        int left;
        boolean shielded;
        boolean broken;
        float mend;
        float glow;
        /** Incantateur figé devant le sceau qui le répare (null : aucun). */
        Ref<EntityStore> channeler;
        float channelFx;
        boolean swing;
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
        float markClock;

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

    /** Vrai pour un sceau, intact ou fissuré. */
    public static boolean isSeal(String role) {
        return role != null && role.startsWith(SEAL_ROLE);
    }

    /** Rôle du sceau selon les coups déjà portés (le sceau du cou, lui, ne se fissure pas). */
    static String sealRole(Seal seal, int index) {
        int cracks = index == NECK ? 0 : Math.min(SEAL_ROLES.length - 1, BREAKS[index] - seal.left);
        return SEAL_ROLES[Math.max(0, cracks)];
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
        for (String role : SEAL_ROLES) {
            BossBarSystem.register(role);
        }
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
        markChanters(store, st);
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
            String wanted = sealRole(seal, i);
            if (seal.ref != null && seal.ref.isValid() && !wanted.equals(seal.shown)) {
                // Fissuré (ou réparé) : le sceau change de modèle, reposé tout de suite à sa place.
                store.removeEntity(seal.ref, RemoveReason.REMOVE);
                seal.ref = null;
            }
            if (seal.ref == null || !seal.ref.isValid()) {
                if (nearest(store, players, where) > SEAL_RESPAWN_RANGE) {
                    continue;
                }
                seal.ref = spawn(store, wanted, where, (float) Math.PI);
                seal.shown = wanted;
                if (seal.ref != null) {
                    store.ensureAndGetComponent(seal.ref, Frozen.getComponentType());
                    showBreaks(store, seal, i);
                }
            }
            seal.glow += 0.25f;
            if (seal.shielded && seal.ref != null) {
                shield(store, where, st.clock);
                if (seal.glow >= 1f) {
                    seal.glow = 0f;
                    Telegraphs.particle(store, "Nakasar_Fractal_Shield_Glow", new Vector3d(where).add(0, 1.2, 0), 2.4f);
                }
            }
        }
    }

    /**
     * Bulle d'un sceau protégé : étincelles posées sur une sphère de {@value #SHIELD_RADIUS} blocs autour de lui
     * (douze par passage, quatre passages par seconde, qui tournent), assez denses pour dessiner un dôme.
     */
    private static void shield(Store<EntityStore> store, Vector3d where, float clock) {
        double golden = Math.PI * (3 - Math.sqrt(5));
        int n = 48;
        int offset = (int) (clock * 4) % 4;
        for (int k = offset; k < n; k += 4) {
            double y = 1 - (k + 0.5) / n * 1.6;   // du sommet à un peu sous l'équateur : un dôme posé au sol
            double r = Math.sqrt(Math.max(0, 1 - y * y));
            double a = golden * k + clock * 0.6;
            Telegraphs.particle(store, "Nakasar_Fractal_Shield_Spark", new Vector3d(where.x() + Math.cos(a) * r * SHIELD_RADIUS,
                    where.y() + 1.2 + y * SHIELD_RADIUS, where.z() + Math.sin(a) * r * SHIELD_RADIUS), 1f);
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
        FractalsPlugin.get().getLogger().atInfo().log("Nakasar_Fractal_Hammer : sceau %d frappé par %s (marteau en main %s, "
                + "chargé %s, bulle %s)", index, player.getUsername(), Hammer.holds(store, playerRef),
                Hammer.isCharged(player.getUuid()), seal.shielded);
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
        release(store, seal);
        // Le sceau vole en éclats : gerbe de pierre et de cristal, puis il disparaît.
        double[] at = CliffsideLayout.SEALS[index];
        Vector3d where = new Vector3d(at[0], at[1] + 1, at[2]);
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Shatter", where, 1.5f);
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", where, 2.2f);
        Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", where);
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
                    // L'Archidevin rappelle son marteau : il ne le rendra qu'au fil de ses transitions.
                    Hammer.recallAll(world, store);
                    for (PlayerRef p : world.getPlayerRefs()) {
                        p.sendMessage(Message.translation(MESSAGES + "hammer.recalled"));
                    }
                    openGate(world, store, CliffsideLayout.GATE3);
                    checkpoint(world, CliffsideLayout.CHECKPOINT_SHOULDERS);
                    st.stage = Stage.RAMPS;
                }
            }
            default -> {
            }
        }
    }

    /**
     * Réparation d'un sceau fissuré : un incantateur vivant de sa vague vient se placer devant lui (fumée, puis il
     * réapparaît à {@value #CHANNEL_DISTANCE} blocs, du côté de sa vague), y reste figé et incante — bâton levé, fil
     * violet vers le sceau — ; au bout de {@value #MEND_INTERVAL} s d'incantation, un coup est réparé. L'abattre
     * coupe la réparation ; le suivant prend sa place.
     */
    private static void mend(World world, Store<EntityStore> store, State st, int index, float dt) {
        Seal seal = st.seals[index];
        if (seal.broken || seal.left >= BREAKS[index]) {
            release(store, seal);
            seal.mend = 0f;
            return;
        }
        double[] at = CliffsideLayout.SEALS[index];
        Vector3d where = new Vector3d(at[0], at[1], at[2]);
        if (seal.channeler == null || !alive(store, seal.channeler)) {
            seal.channeler = null;
            seal.mend = 0f;
            Ref<EntityStore> chanter = st.waves[index].stream()
                    .filter(ref -> alive(store, ref) && CHANTER.equals(role(store, ref)))
                    .findFirst().orElse(null);
            Vector3d from = chanter == null ? null : Telegraphs.position(store, chanter);
            if (from == null) {
                return;
            }
            Vector3d spot = channelSpot(index, where);
            Telegraphs.particle(store, "Nakasar_Fractal_Stealth_Smoke", new Vector3d(from), 1.2f);
            Telegraphs.particle(store, "Nakasar_Fractal_Stealth_Smoke", spot, 1.2f);
            store.putComponent(chanter, Teleport.getComponentType(),
                    new Teleport(spot, new Rotation3f(0f, Telegraphs.yawToward(spot, where), 0f)));
            store.ensureAndGetComponent(chanter, Frozen.getComponentType());
            st.homes.put(chanter, spot);
            seal.channeler = chanter;
            seal.channelFx = 1f;
            for (PlayerRef p : world.getPlayerRefs()) {
                p.sendMessage(Message.translation(MESSAGES + "seal.channel"));
            }
        }
        Vector3d hands = Telegraphs.position(store, seal.channeler);
        if (hands == null) {
            return;
        }
        seal.channelFx += dt;
        if (seal.channelFx >= 1f) {
            seal.channelFx = 0f;
            seal.swing = !seal.swing;
            Chanting.cast(store, seal.channeler, seal.swing);
            Vector3d a = new Vector3d(hands).add(0, 1.5, 0);
            Vector3d b = new Vector3d(where).add(0, 1.4, 0);
            double length = a.distance(b);
            for (double d = 0.5; d < length; d += 0.5) {
                Telegraphs.particle(store, "Nakasar_Fractal_Mend_Beam", new Vector3d(a).lerp(b, d / length), 1f);
            }
            Telegraphs.particle(store, "Nakasar_Fractal_Seal_Mend", where, 1.2f);
        }
        seal.mend += dt;
        if (seal.mend < MEND_INTERVAL) {
            return;
        }
        seal.mend = 0f;
        seal.left++;
        showBreaks(store, seal, index);
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Mend", where, 2f);
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(MESSAGES + "seal.mended"));
        }
    }

    /** Place de l'incantateur : devant le sceau, du côté où arrive sa vague. */
    private static Vector3d channelSpot(int index, Vector3d seal) {
        double cx = 0;
        double cz = 0;
        double[][] points = CliffsideLayout.WAVES[index];
        for (double[] p : points) {
            cx += p[0] / points.length;
            cz += p[2] / points.length;
        }
        double dx = cx - seal.x();
        double dz = cz - seal.z();
        double d = Math.max(1e-6, Math.sqrt(dx * dx + dz * dz));
        return new Vector3d(seal.x() + dx / d * CHANNEL_DISTANCE, seal.y(), seal.z() + dz / d * CHANNEL_DISTANCE);
    }

    /** L'incantateur cesse d'incanter (sceau réparé ou brisé) : il reprend le combat. */
    private static void release(Store<EntityStore> store, Seal seal) {
        if (seal.channeler != null && seal.channeler.isValid()) {
            store.tryRemoveComponent(seal.channeler, Frozen.getComponentType());
        }
        seal.channeler = null;
    }

    /** Une rune violette au-dessus de chaque incantateur, chaque seconde : on les repère dans la mêlée. */
    private static void markChanters(Store<EntityStore> store, State st) {
        st.markClock += 0.25f;
        if (st.markClock < 1f) {
            return;
        }
        st.markClock = 0f;
        List<Ref<EntityStore>> all = new ArrayList<>(st.camp);
        for (List<Ref<EntityStore>> wave : st.waves) {
            all.addAll(wave);
        }
        all.addAll(st.boss.adds());
        for (Ref<EntityStore> ref : all) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at != null && CHANTER.equals(role(store, ref))) {
                Telegraphs.particle(store, "Nakasar_Fractal_Chanter_Mark", new Vector3d(at).add(0, 2.5, 0), 1f);
            }
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
        Ref<EntityStore> foe = Spawns.noLoot(store, spawnFoe(world, store, role, at));
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
        NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(MESSAGES + key), NotificationStyle.Default);
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
