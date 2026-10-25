package dev.nakasar.hytale.fractals.uncategorized;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Box;
import dev.nakasar.hytale.fractals.arena.Consoles;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.SafeLandings;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.instability.Instabilities;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.stage.FractalStage;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * L'Inclassable (étape 6 du GDD), fidèle au déroulé de GW2 :
 * <ol>
 *   <li>{@link Step#PLATFORMS} : plates-formes des harpies (une chute ramène au départ, {@link SafeLandings}) ;</li>
 *   <li>{@link Step#YARD} : le générateur de la prison, puis les quatre prisonniers l'un après l'autre ;</li>
 *   <li>{@link Step#STAIRS} : l'escalier mortel, balayé par quatre tourelles, et les trois consoles du haut à activer
 *   ensemble ({@link Consoles#window}) ;</li>
 *   <li>{@link Step#TOM} : Vieux Tom, son gaz et son ventilateur ({@link OldTom}) ;</li>
 *   <li>{@link Step#GLIMMER} : les plates-formes de lueur ;</li>
 *   <li>{@link Step#ASURA} : l'Asura fou et ses golems de cristal ({@link MadAsura}) ; {@link Step#DONE} ensuite.</li>
 * </ol>
 * Tout ce que pose le Java est non sauvegardé : une instance rechargée repart du début.
 */
public final class Uncategorized implements FractalStage {

    public static final String FRACTAL = "Uncategorized";
    static final String MESSAGES = "nakasar_fractals_uncategorized.";
    static final String HARPY = "Nakasar_Fractal_Harpy";
    static final String GENERATOR = "Nakasar_Fractal_Prison_Generator";
    static final String TURRET = "Nakasar_Fractal_Turret";
    static final String TOM = "Nakasar_Fractal_Old_Tom";
    static final String ASURA = "Nakasar_Fractal_Mad_Asura";
    static final String CRYSTAL_GOLEM = "Nakasar_Fractal_Crystal_Golem";
    static final String TEAR = "Nakasar_Fractal_Mist_Tear";
    static final String HARRIED = "Nakasar_Fractal_Harried";
    static final String LEVER_ROOTED = "Nakasar_Fractal_Lever_Rooted";
    static final String TRAP_CAUSE = "Nakasar_Fractal_Spikes";
    /** Prisonniers, dans l'ordre de libération (mêmes index que {@link UncategorizedLayout#PRISONERS}). */
    static final String[] PRISONERS = {"Nakasar_Fractal_Rabid_Rabbit", "Nakasar_Fractal_Saboteur",
            "Nakasar_Fractal_Fire_Shaman", "Nakasar_Fractal_Ettin"};

    static final float HARPY_RESPAWN = 25f;
    static final double HARRIED_RANGE = 14;
    /** Tourelles : une voie toutes les {@value #TURRET_STAGGER} s, annonce de {@value #TURRET_WINDUP} s. */
    static final float TURRET_STAGGER = 1f;
    static final float TURRET_WINDUP = 1.4f;
    /** Demi-largeur d'une voie : les quatre voies (x = -3, -1, 1, 3) se touchent sans se chevaucher. */
    static final double TURRET_HALF_WIDTH = 1.0;
    static final float TURRET_PART = 0.25f;
    static final float CONSOLE_ROOT = 1.5f;

    enum Step { PLATFORMS, YARD, STAIRS, TOM, GLIMMER, ASURA, DONE }

    static final class State {
        Step step = Step.PLATFORMS;
        boolean started;
        final SafeLandings landings = new SafeLandings(UncategorizedLayout.JUMP_ZONES, MESSAGES + "landing.back");
        final List<Ref<EntityStore>> harpies = new ArrayList<>();
        float harpyClock;
        float harriedClock;
        Ref<EntityStore> generator;
        volatile boolean generatorDown;
        int prisoner = -1;
        Ref<EntityStore> prisonerRef;
        volatile boolean prisonerDown;
        final List<Ref<EntityStore>> turrets = new ArrayList<>();
        float turretClock;
        int lane;
        final Consoles consoles = new Consoles(UncategorizedLayout.CONSOLES.length);
        int litBefore;
        final OldTom tom = new OldTom();
        final MadAsura asura = new MadAsura();
        final Map<UUID, Long> throttle = new HashMap<>();
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Barres de boss de l'Inclassable et rôles fixes que les instabilités laissent tranquilles. */
    public static void register() {
        BossBarSystem.register(GENERATOR);
        BossBarSystem.register(TOM);
        BossBarSystem.register(CRYSTAL_GOLEM);
        for (String prisoner : PRISONERS) {
            BossBarSystem.register(prisoner);
        }
        Instabilities.exempt(GENERATOR, TURRET, ASURA);
    }

    @Override
    public String fractal() {
        return FRACTAL;
    }

    State state(World world) {
        return states.computeIfAbsent(world, w -> new State());
    }

    @Override
    public void clearAll() {
        states.clear();
    }

    // --- pas de jeu ---------------------------------------------------------------------------------

    @Override
    public void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        if (players.isEmpty()) {
            st.tom.idle(world, store, st, dt);
            st.asura.idle(world, store, dt);
            return;
        }
        if (!st.started) {
            st.started = true;
            Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
            spawnHarpies(world, store, st, UncategorizedLayout.HARPIES);
        }
        st.landings.step(world, store, players);
        harpies(world, store, st, players, dt);
        switch (st.step) {
            case PLATFORMS -> {
                if (Spawns.anyIn(store, players, UncategorizedLayout.YARD)) {
                    st.step = Step.YARD;
                    Gates.checkpoint(world, UncategorizedLayout.YARD_CHECKPOINT, MESSAGES + "checkpoint");
                    Spawns.tellAll(world, Message.translation(MESSAGES + "yard.enter"));
                }
            }
            case YARD -> yard(world, store, st);
            case STAIRS -> stairs(world, store, st, players, dt);
            case TOM -> {
                if (st.tom.step(world, store, st, players, dt)) {
                    st.step = Step.GLIMMER;
                    Gates.open(world, store, UncategorizedLayout.GATE_TOM, MESSAGES + "tom.victory");
                    Gates.checkpoint(world, UncategorizedLayout.PAD2_CHECKPOINT, MESSAGES + "checkpoint");
                    spawnHarpies(world, store, st, UncategorizedLayout.HARPIES_2);
                }
            }
            case GLIMMER -> {
                if (!MadAsura.inArena(store, players).isEmpty()) {
                    st.step = Step.ASURA;
                }
            }
            case ASURA -> {
                if (st.asura.step(world, store, players, dt)) {
                    st.step = Step.DONE;
                    Spawns.removeAll(store, st.harpies);
                    Gates.victory(world, UncategorizedLayout.REWARD, UncategorizedLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "asura.victory");
                }
            }
            default -> {
            }
        }
    }

    // --- harpies ------------------------------------------------------------------------------------

    private void spawnHarpies(World world, Store<EntityStore> store, State st, double[][] points) {
        st.harpies.removeIf(ref -> !Spawns.alive(store, ref));
        for (double[] at : points) {
            Ref<EntityStore> harpy = Spawns.spawnFoe(world, store, HARPY, at);
            if (harpy != null) {
                st.harpies.add(harpy);
            }
        }
        st.harpyClock = 0f;
    }

    /** Harcèlement près des harpies ; sur les plates-formes, les harpies tuées reviennent toutes les 25 s. */
    private void harpies(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        st.harpies.removeIf(ref -> !Spawns.alive(store, ref));
        if (st.step == Step.PLATFORMS || st.step == Step.GLIMMER) {
            double[][] points = st.step == Step.PLATFORMS ? UncategorizedLayout.HARPIES : UncategorizedLayout.HARPIES_2;
            st.harpyClock += dt;
            if (st.harpyClock >= HARPY_RESPAWN && st.harpies.size() < points.length) {
                st.harpyClock = 0f;
                double[] at = points[(int) (Math.random() * points.length)];
                Ref<EntityStore> harpy = Spawns.spawnFoe(world, store, HARPY, at);
                if (harpy != null) {
                    st.harpies.add(harpy);
                }
            }
        }
        st.harriedClock += dt;
        if (st.harriedClock < 1f || st.harpies.isEmpty()) {
            return;
        }
        st.harriedClock = 0f;
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at == null) {
                continue;
            }
            for (Ref<EntityStore> harpy : st.harpies) {
                Vector3d h = Telegraphs.position(store, harpy);
                if (h != null && h.distance(at) <= HARRIED_RANGE) {
                    Hurt.effect(store, player.getReference(), HARRIED, 1.5f);
                    break;
                }
            }
        }
    }

    // --- cour de la prison ----------------------------------------------------------------------------

    private void yard(World world, Store<EntityStore> store, State st) {
        if (!st.generatorDown) {
            if (st.generator == null || !st.generator.isValid()) {
                st.generator = Spawns.spawnFoe(world, store, GENERATOR, Spawns.point(UncategorizedLayout.GENERATOR), 0f);
                if (st.generator != null) {
                    store.ensureAndGetComponent(st.generator, Frozen.getComponentType());
                }
            }
            return;
        }
        if (st.prisoner >= 0 && !st.prisonerDown && st.prisonerRef != null && st.prisonerRef.isValid()) {
            return;
        }
        if (st.prisoner >= 0 && !st.prisonerDown) {
            // Le prisonnier a disparu sans mourir (déchargé) : il revient dans sa cellule.
            st.prisonerRef = Spawns.spawnFoe(world, store, PRISONERS[st.prisoner], UncategorizedLayout.PRISONERS[st.prisoner]);
            return;
        }
        st.prisoner++;
        st.prisonerDown = false;
        if (st.prisoner >= PRISONERS.length) {
            st.step = Step.STAIRS;
            Gates.open(world, store, UncategorizedLayout.GATE_YARD, MESSAGES + "yard.done");
            spawnTurrets(store, st);
            float window = Consoles.window(FractalRuns.partySize(world));
            Spawns.tellAll(world, Message.translation(MESSAGES + "stairs.enter").param("seconds", Math.round(window)));
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        for (int[] c : UncategorizedLayout.CELL_DOORS[st.prisoner]) {
            WorldBlocks.clear(chunks, c[0], c[1], c[2]);
        }
        String role = PRISONERS[st.prisoner];
        st.prisonerRef = Spawns.spawnFoe(world, store, role, UncategorizedLayout.PRISONERS[st.prisoner]);
        String name = "nakasar_fractals_uncategorized.npc." + role.substring("Nakasar_Fractal_".length()) + ".name";
        Spawns.tellAll(world, Message.translation(MESSAGES + "yard.release").param("name", Message.translation(name)));
    }

    // --- escalier mortel --------------------------------------------------------------------------------

    private void spawnTurrets(Store<EntityStore> store, State st) {
        for (int x : UncategorizedLayout.TURRETS_X) {
            Ref<EntityStore> turret = Spawns.spawn(store, TURRET,
                    new Vector3d(x + 0.5, UncategorizedLayout.TURRET_Y, UncategorizedLayout.TURRET_Z), (float) Math.PI);
            if (turret != null) {
                store.ensureAndGetComponent(turret, Frozen.getComponentType());
                store.ensureAndGetComponent(turret, Invulnerable.getComponentType());
                st.turrets.add(turret);
            }
        }
    }

    /** Hauteur (debout, monde) de l'escalier à la case z. */
    static double stairLevel(int z) {
        return UncategorizedLayout.TURRET_Y - 0.5 * (z - UncategorizedLayout.STAIRS_TOP_Z);
    }

    private void stairs(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        long now = System.nanoTime();
        float window = Consoles.window(FractalRuns.partySize(world));
        int lit = st.consoles.litCount(now, window);
        if (st.litBefore > 0 && lit == 0) {
            Spawns.tellAll(world, Message.translation(MESSAGES + "console.late"));
        }
        st.litBefore = lit;
        if (!Spawns.anyIn(store, players, UncategorizedLayout.STAIRS)) {
            return;
        }
        st.turretClock += dt;
        if (st.turretClock < TURRET_STAGGER) {
            return;
        }
        st.turretClock = 0f;
        int laneX = UncategorizedLayout.TURRETS_X[st.lane++ % UncategorizedLayout.TURRETS_X.length];
        fireLane(world, store, laneX + 0.5, FractalRuns.windupFactor(world));
    }

    /**
     * Une tourelle tire dans sa voie : bande rouge de la largeur exacte de la voie sur toute la longueur (une ligne par
     * marche, posée sur elle), puis la décharge.
     */
    private void fireLane(World world, Store<EntityStore> store, double x, float wf) {
        float seconds = TURRET_WINDUP * wf;
        long now = System.nanoTime();
        for (int z = UncategorizedLayout.STAIRS_TOP_Z; z <= UncategorizedLayout.STAIRS_BOTTOM_Z; z++) {
            Telegraphs.Strip step = new Telegraphs.Strip(new Vector3d(x, stairLevel(z), z), Math.PI / 2, 1,
                    2 * TURRET_HALF_WIDTH, now, seconds);
            TelegraphSystem.start(world, (w, s, t) -> step.step(s, t));
        }
        Delayed.later(world, seconds, s -> {
            State st = state(world);
            if (st.step != Step.STAIRS) {
                return;
            }
            for (PlayerRef player : Spawns.alivePlayers(world, s)) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d at = Telegraphs.position(s, ref);
                if (at == null || Math.abs(at.x() - x) > TURRET_HALF_WIDTH + Telegraphs.BODY || !UncategorizedLayout.STAIRS.contains(at.x(), at.y(), at.z())) {
                    continue;
                }
                double level = stairLevel((int) Math.floor(at.z()));
                if (at.y() < level - 1.5 || at.y() > level + 3.5) {
                    continue;
                }
                Telegraphs.particle(s, "Nakasar_Fractal_Lightning_Arc", new Vector3d(at).add(0, 1, 0), 1.2f);
                Hurt.percent(s, ref, TURRET_PART, TRAP_CAUSE);
                Hurt.effect(s, ref, "Hazard_Electric_Stun", 1.5f);
            }
        });
    }

    // --- blocs utilisés ---------------------------------------------------------------------------------

    @Override
    public void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                    int x, int y, int z) {
        State st = state(world);
        switch (action) {
            case "Uncategorized_Console" -> {
                int[] fan = UncategorizedLayout.FAN;
                if (x == fan[0] && y == fan[1] && z == fan[2]) {
                    st.tom.useFan(world, store, st, player);
                    return;
                }
                useConsole(world, store, st, ref, player, x, y, z);
            }
            case "Uncategorized_Battery" -> st.tom.useBattery(world, store, st, ref, player, x, y, z);
            default -> {
            }
        }
    }

    private void useConsole(World world, Store<EntityStore> store, State st, Ref<EntityStore> ref, PlayerRef player,
                            int x, int y, int z) {
        if (st.step != Step.STAIRS || st.consoles.done()) {
            return;
        }
        int index = -1;
        for (int i = 0; i < UncategorizedLayout.CONSOLES.length; i++) {
            int[] c = UncategorizedLayout.CONSOLES[i];
            if (c[0] == x && c[1] == y && c[2] == z) {
                index = i;
            }
        }
        if (index < 0) {
            return;
        }
        long now = System.nanoTime();
        float window = Consoles.window(FractalRuns.partySize(world));
        Hurt.effect(store, ref, LEVER_ROOTED, CONSOLE_ROOT);
        Telegraphs.particle(store, "Nakasar_Fractal_Battery_Charge", new Vector3d(x + 0.5, y + 1, z + 0.5), 0.8f);
        if (!st.consoles.activate(index, now, window)) {
            Spawns.tellAll(world, Message.translation(MESSAGES + "console.lit")
                    .param("count", st.consoles.litCount(now, window)).param("total", st.consoles.size()));
            return;
        }
        for (Ref<EntityStore> turret : st.turrets) {
            Vector3d at = Telegraphs.position(store, turret);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", at, 1f);
            }
        }
        Spawns.removeAll(store, st.turrets);
        st.step = Step.TOM;
        Gates.open(world, store, UncategorizedLayout.GATE_TOP, MESSAGES + "console.done");
        Gates.checkpoint(world, UncategorizedLayout.TOP_CHECKPOINT, MESSAGES + "checkpoint");
    }

    // --- coups et morts -----------------------------------------------------------------------------------

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        if (TURRET.equals(victimRole) || ASURA.equals(victimRole)) {
            damage.setCancelled(true);
            return;
        }
        if (CRYSTAL_GOLEM.equals(victimRole) && state(world).asura.dormant(victim)) {
            damage.setCancelled(true);
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        if (GENERATOR.equals(role)) {
            st.generatorDown = true;
            Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", at, 1.5f);
        } else if (st.prisoner >= 0 && st.prisoner < PRISONERS.length && PRISONERS[st.prisoner].equals(role)) {
            st.prisonerDown = true;
        } else if (TOM.equals(role)) {
            st.tom.down = true;
        } else if (CRYSTAL_GOLEM.equals(role)) {
            st.asura.golemDown();
        }
    }

    // --- outils ------------------------------------------------------------------------------------------

    static void tell(State st, PlayerRef player, String key) {
        long now = System.nanoTime();
        Long last = st.throttle.get(player.getUuid());
        if (last != null && now - last < Telegraphs.seconds(2f)) {
            return;
        }
        st.throttle.put(player.getUuid(), now);
        player.sendMessage(Message.translation(MESSAGES + key));
    }

    static List<PlayerRef> in(Store<EntityStore> store, List<PlayerRef> players, Box box) {
        return Spawns.in(store, players, box);
    }
}
