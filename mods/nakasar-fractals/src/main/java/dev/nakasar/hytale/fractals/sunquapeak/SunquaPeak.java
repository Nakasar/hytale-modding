package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.FractalItemsSystem;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.instability.Instabilities;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.stage.FractalStage;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Pic de Sunqua (GW2) : le massif flottant où Ai, la gardienne, a laissé ses émotions. On monte de l'îlot de départ au
 * sommet :
 * <ol>
 *   <li>l'escalier brisé : des îlots qu'on ne franchit qu'avec le Bond chargé ({@link ChargedLeap}, orbes de foudre),
 *   gardés par trois élémentaires d'air ; vaincus, le socle refait l'escalier ({@link #stairs}) et une colonne de vent
 *   ({@link WindColumns}) mène au plateau ;</li>
 *   <li>la Voix de la montagne ({@link VoiceOfTheMountain}), puis une colonne de vent jusqu'à la corniche des cascades
 *   ({@link WaterPath}) ;</li>
 *   <li>les rochers flottants, la chute dans la terrasse de la Tristesse ({@link Sorrow}) ;</li>
 *   <li>le sentier de lave et ses murs ({@link LavaPath}), le cratère de la Fureur ({@link FuryOfTheMountain}) ;</li>
 *   <li>l'arène du sommet : Ai ({@link Ai}) ; au rang Maître, Ai assombrie ensuite.</li>
 * </ol>
 * Pas de soin nulle part (AGENTS.md) : un boss laissé seul {@value #RESET_SECONDS} s disparaît et revient neuf. Tout ce
 * que pose le Java (orbes, dalles, météores, PNJ) est non sauvegardé : une instance rechargée repart du départ.
 */
public final class SunquaPeak implements FractalStage {

    public static final String FRACTAL = "SunquaPeak";
    static final String MESSAGES = "nakasar_fractals_sunqua_peak.";
    static final String CAUSE = "Nakasar_Fractal_Sunqua";
    static final String ORB = "Nakasar_Fractal_Sunqua_Lightning_Orb";
    static final String SPIRIT = "Nakasar_Fractal_Spirit_Of_The_Mountain";
    static final String AIR_ELEMENTAL = "Nakasar_Fractal_Sunqua_Air_Elemental";
    static final String VOICE = "Nakasar_Fractal_Voice_Of_The_Mountain";
    static final String WATER_SPRITE = "Nakasar_Fractal_Enraged_Water_Sprite";
    static final String FRIGHTENED = "Nakasar_Fractal_Frightened_Water_Elemental";
    static final String SORROW = "Nakasar_Fractal_Sorrow_Of_The_Mountain";
    static final String BOULDER = "Nakasar_Fractal_Fallen_Boulder";
    static final String LAVA_ELEMENTAL = "Nakasar_Fractal_Sunqua_Lava_Elemental";
    static final String LAVA_EMBER = "Nakasar_Fractal_Sunqua_Lava_Ember";
    static final String TIGER = "Nakasar_Fractal_Sunqua_Tiger";
    static final String FURY = "Nakasar_Fractal_Fury_Of_The_Mountain";
    static final String AI = "Nakasar_Fractal_Ai_Keeper_Of_The_Peak";
    static final String AI_DARK = "Nakasar_Fractal_Ai_Dark";
    static final String FEAR = "Nakasar_Fractal_Sunqua_Fear";
    static final String BURNING = "Nakasar_Fractal_Sunqua_Burning";
    static final String KNOCKED_DOWN = "Nakasar_Fractal_Knocked_Down";
    static final String TIDAL = "Nakasar_Fractal_Tidal_Bargain_";
    /** Dalles de l'escalier refait. */
    static final String STAIR_BLOCK = "Rock_Marble_Brick_Smooth";
    /** Brûlure de la montagne : part des PV max par seconde. */
    static final float BURN_PART = 0.02f;
    /** Un boss sans joueur près de lui pendant ce temps disparaît (il reviendra neuf, sans soin). */
    static final float RESET_SECONDS = 20f;
    /** Un monstre tombé de plus de 4 blocs sous son point d'apparition y est ramené. */
    static final double FALL_LIMIT = 4;

    enum Phase { STAIRS, VOICE, WATER, SORROW, LAVA, FURY, AI, DONE }

    static final class State {
        boolean started;
        Phase phase = Phase.STAIRS;
        Ref<EntityStore> spirit;
        final List<Ref<EntityStore>> elementals = new ArrayList<>();
        final ChargedLeap leap = new ChargedLeap();
        final WindColumns columns = new WindColumns();
        final VoiceOfTheMountain voice = new VoiceOfTheMountain();
        final WaterPath water = new WaterPath();
        final Sorrow sorrow = new Sorrow();
        final LavaPath lava = new LavaPath();
        final FuryOfTheMountain fury = new FuryOfTheMountain();
        final Ai ai = new Ai();
        /** Pas de dégâts de chute jusqu'à cet instant (System.nanoTime) : colonnes, chute de la terrasse. */
        final Map<UUID, Long> safe = new HashMap<>();
        /** Dernier envoi de chaque message (joueur:clé). */
        final Map<String, Long> throttle = new HashMap<>();
        boolean ticking;
        /** Dernier tick du monde (System.nanoTime) : un seul pas de temps pour les tâches par tick. */
        long lastTick;

        void safe(UUID player, float seconds) {
            safe.merge(player, System.nanoTime() + Telegraphs.seconds(seconds), Math::max);
        }

        boolean isSafe(UUID player) {
            Long until = safe.get(player);
            return until != null && System.nanoTime() < until;
        }

        Ref<EntityStore> foe(World world, Store<EntityStore> store, String role, Vector3d where, Vector3d face, boolean loot) {
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, role, where,
                    face == null ? (float) (Math.random() * 2 * Math.PI - Math.PI) : Telegraphs.yawToward(where, face));
            if (ref != null && !loot) {
                Spawns.noLoot(store, ref);
            }
            return ref;
        }
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Charges et marques du Pic de Sunqua : perdues hors de la fractale. */
    public static FractalItemsSystem.Rule itemsRule() {
        List<String> effects = new ArrayList<>(List.of(BURNING, KNOCKED_DOWN, "Nakasar_Fractal_Storm_Marked",
                "Nakasar_Fractal_Meteor_Marked", "Nakasar_Fractal_Shared_Tide"));
        for (int n = 1; n <= ChargedLeap.FACTORS.length; n++) {
            effects.add(ChargedLeap.EFFECT + n);
        }
        for (int n = 1; n <= Tether.MAX_STACKS; n++) {
            effects.add(TIDAL + n);
        }
        return new FractalItemsSystem.Rule(FRACTAL, Set.of(), effects.toArray(new String[0]));
    }

    /** Barres de boss (défiance de la Fureur et d'Ai). */
    public static void register() {
        for (String role : new String[]{VOICE, FURY, AI, AI_DARK}) {
            BossBarSystem.register(role);
        }
        BossBarSystem.label(FURY, Defiance::label);
        BossBarSystem.label(AI, Defiance::label);
        Instabilities.exempt(SPIRIT, FRIGHTENED, SORROW, BOULDER);
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

    // --- pas de jeu ---------------------------------------------------------------------------------------------

    @Override
    public void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        if (!st.ticking) {
            st.ticking = true;
            // Colonnes de vent, météores qui suivent, lien de la marée : à chaque tick.
            TelegraphSystem.start(world, new TelegraphSystem.Task() {
                @Override
                public boolean step(World w, Store<EntityStore> s, long now) {
                    if (states.get(w) != st) {
                        return true;
                    }
                    float tickDt = st.lastTick == 0 ? 0f : Math.min(0.1f, (now - st.lastTick) / 1e9f);
                    st.lastTick = now;
                    st.columns.tick(w, s, st, tickDt);
                    st.fury.tick(w, s, tickDt);
                    st.ai.tick(w, s, tickDt);
                    return false;
                }

                @Override
                public void abort(World w, Store<EntityStore> s) {
                    st.ticking = false;
                }
            });
        }
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        if (!st.started) {
            if (players.isEmpty()) {
                return;
            }
            start(world, store, st);
        }
        st.leap.step(world, store, st, players, dt);
        burn(store, players, dt);
        switch (st.phase) {
            case STAIRS -> stairs(world, store, st, players);
            case VOICE -> {
                if (st.voice.step(world, store, st, players, dt)) {
                    st.columns.open(1);
                    Spawns.tellAll(world, Message.translation(MESSAGES + "voice.victory"));
                    st.phase = Phase.WATER;
                }
            }
            case WATER -> {
                if (st.water.step(world, store, st, players, dt)) {
                    Gates.open(world, store, SunquaPeakLayout.WATER_GATE, MESSAGES + "water.done");
                    st.phase = Phase.SORROW;
                }
            }
            case SORROW -> {
                if (st.sorrow.step(world, store, st, players, dt)) {
                    Gates.open(world, store, SunquaPeakLayout.SORROW_GATE, MESSAGES + "sorrow.victory");
                    st.lava.begin(world, store, st);
                    st.phase = Phase.LAVA;
                }
            }
            case LAVA -> {
                if (st.lava.step(world, store, st, players, dt)) {
                    st.phase = Phase.FURY;
                }
            }
            case FURY -> {
                if (st.fury.step(world, store, st, players, dt)) {
                    Gates.open(world, store, SunquaPeakLayout.CRATER_GATE, MESSAGES + "fury.victory");
                    st.phase = Phase.AI;
                }
            }
            case AI -> {
                if (st.ai.step(world, store, st, players, dt)) {
                    st.phase = Phase.DONE;
                    Gates.victory(world, SunquaPeakLayout.REWARD, SunquaPeakLayout.END_EXIT,
                            MESSAGES + "title.victory", MESSAGES + "ai.victory");
                }
            }
            default -> {
            }
        }
    }

    /** L'Esprit de la montagne, les orbes du départ, les élémentaires d'air de l'escalier. */
    private static void start(World world, Store<EntityStore> store, State st) {
        st.started = true;
        Vector3d spawn = Spawns.point(SunquaPeakLayout.SPAWN);
        Vector3d spirit = Spawns.point(SunquaPeakLayout.SPIRIT);
        st.spirit = Spawns.spawn(store, SPIRIT, spirit, Telegraphs.yawToward(spirit, spawn));
        if (st.spirit != null && st.spirit.isValid()) {
            store.ensureAndGetComponent(st.spirit, Invulnerable.getComponentType());
        }
        for (int[] at : SunquaPeakLayout.START_ORBS) {
            st.leap.site(world, at, true);
        }
        for (int i = 0; i < SunquaPeakLayout.AIR_ELEMENTALS.length; i++) {
            Ref<EntityStore> ref = st.foe(world, store, AIR_ELEMENTAL, Spawns.point(SunquaPeakLayout.AIR_ELEMENTALS[i]),
                    spawn, true);
            st.elementals.add(ref);
            st.leap.site(world, SunquaPeakLayout.STEP_ORBS[i], ref == null);   // sans gardien, l'orbe est déjà là
        }
        Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
        Spawns.tellAll(world, Message.translation(MESSAGES + "leap.intro"));
        Spawns.tellAll(world, Message.translation(MESSAGES + "stairs.elementals"));
    }

    /**
     * L'escalier brisé : l'orbe de l'îlot d'un élémentaire d'air s'allume quand il tombe ; les trois vaincus et un
     * joueur sur le socle, l'escalier se reforme (dalles posées seulement dans le vide) et la première colonne se lève.
     */
    private static void stairs(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        for (int i = 0; i < st.elementals.size(); i++) {
            Ref<EntityStore> ref = st.elementals.get(i);
            if (ref != null && !Spawns.alive(store, ref)) {
                st.elementals.set(i, null);
                st.leap.light(world, SunquaPeakLayout.STEP_ORBS[i]);
            }
        }
        List<PlayerRef> onPlinth = near(store, players, Spawns.point(SunquaPeakLayout.PLINTH), SunquaPeakLayout.PLINTH_RADIUS);
        if (onPlinth.isEmpty()) {
            return;
        }
        for (Ref<EntityStore> ref : st.elementals) {
            if (ref != null) {
                for (PlayerRef p : onPlinth) {
                    tell(st, p, "stairs.waiting");
                }
                return;
            }
        }
        var chunks = world.getChunkStore();
        for (int[] c : SunquaPeakLayout.STAIRS) {
            if (!WorldBlocks.solid(chunks, c[0], c[1], c[2])) {
                WorldBlocks.set(chunks, c[0], c[1], c[2], STAIR_BLOCK, 0);
            }
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Charged_Leap_Spark", Spawns.point(SunquaPeakLayout.PLINTH), 2f);
        Spawns.tellAll(world, Message.translation(MESSAGES + "stairs.mended"));
        Gates.checkpoint(world, SunquaPeakLayout.PLINTH, MESSAGES + "checkpoint");
        st.columns.open(0);
        Spawns.tellAll(world, Message.translation(MESSAGES + "column.open"));
        st.phase = Phase.VOICE;
    }

    /** Brûlure de la montagne (coups de la Fureur et des élémentaires de lave) : la vie s'en va tant qu'elle dure. */
    private static void burn(Store<EntityStore> store, List<PlayerRef> players, float dt) {
        for (PlayerRef p : players) {
            if (Hurt.has(store, p.getReference(), BURNING)) {
                Hurt.percent(store, p.getReference(), BURN_PART * dt, CAUSE);
            }
        }
    }

    // --- coups, morts ----------------------------------------------------------------------------------------------

    @Override
    public boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        State st = state(world);
        return switch (role) {
            case VOICE -> st.voice.shielded();
            case FURY -> st.fury.shielded();
            case AI, AI_DARK -> st.ai.shielded();
            default -> false;
        };
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        State st = state(world);
        if (victimRole == null) {
            fall(buffer, st, victim, damage);
            return;
        }
        switch (victimRole) {
            case SPIRIT, FRIGHTENED, SORROW -> {
                damage.setCancelled(true);
                return;
            }
            case VOICE -> {
                if (st.voice.shielded()) {
                    damage.setCancelled(true);
                    return;
                }
            }
            case FURY -> {
                if (st.fury.shielded()) {
                    damage.setCancelled(true);
                    return;
                }
            }
            case AI, AI_DARK -> {
                if (st.ai.shielded()) {
                    damage.setCancelled(true);
                    return;
                }
            }
            default -> {
            }
        }
        // Marché des marées : chaque charge du joueur qui frappe ajoute des dégâts.
        PlayerRef by = attacker == null ? null : buffer.getComponent(attacker, PlayerRef.getComponentType());
        if (by != null) {
            int stacks = Tether.stacksOf(st, by.getUuid());
            if (stacks > 0) {
                damage.setAmount(damage.getAmount() * (1f + Tether.MIGHT * stacks));
            }
        }
    }

    /** Pas de dégâts de chute sous Bond chargé, sur une colonne de vent ou en tombant dans la terrasse. */
    private static void fall(CommandBuffer<EntityStore> buffer, State st, Ref<EntityStore> victim, Damage damage) {
        int fall = DamageCause.getAssetMap().getIndexOrDefault("Fall", Integer.MIN_VALUE);
        if (damage.getDamageCauseIndex() != fall) {
            return;
        }
        PlayerRef player = buffer.getComponent(victim, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        if (st.isSafe(player.getUuid()) || st.leap.charged(player.getUuid())) {
            damage.setCancelled(true);
            return;
        }
        Vector3d at = Telegraphs.position(buffer, victim);
        if (at == null) {
            return;
        }
        for (double[] soft : SunquaPeakLayout.SOFT_LANDINGS) {
            if (Telegraphs.horizontal(at, new Vector3d(soft[0], soft[1], soft[2])) <= soft[3]
                    && Math.abs(at.y() - soft[1]) < 3) {
                damage.setCancelled(true);
                return;
            }
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        switch (role) {
            case LAVA_ELEMENTAL, LAVA_EMBER -> st.lava.burst(world, store, st, role, at);
            default -> {
            }
        }
    }

    // --- outils --------------------------------------------------------------------------------------------------

    /** Rang de la partie : 0 (niveaux 1-25) à 3 (76-100). */
    static int rank(World world) {
        return Math.min(3, (Math.max(1, FractalRuns.level(world)) - 1) / Observatory.RANK_SIZE);
    }

    /** Déplace un PNJ (téléportation), tourné vers `face`. */
    static void move(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d to, Vector3d face) {
        if (ref != null && ref.isValid()) {
            store.putComponent(ref, Teleport.getComponentType(),
                    new Teleport(new Vector3d(to), new Rotation3f(0f, Telegraphs.yawToward(to, face), 0f)));
        }
    }

    /** `home` s'il a encore un sol sous lui, sinon la case de sol la plus proche (à 12 blocs au plus). */
    static Vector3d ground(World world, Vector3d home) {
        ChunkStore chunks = world.getChunkStore();
        int bx = (int) Math.floor(home.x());
        int by = (int) Math.floor(home.y()) - 1;
        int bz = (int) Math.floor(home.z());
        for (int r = 0; r <= 12; r++) {
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    if (Math.max(Math.abs(dx), Math.abs(dz)) != r) {
                        continue;
                    }
                    for (int dy = 0; dy >= -2; dy--) {
                        if (WorldBlocks.solid(chunks, bx + dx, by + dy, bz + dz)
                                && !WorldBlocks.solid(chunks, bx + dx, by + dy + 1, bz + dz)
                                && !WorldBlocks.solid(chunks, bx + dx, by + dy + 2, bz + dz)) {
                            return new Vector3d(bx + dx + 0.5, by + dy + 1, bz + dz + 0.5);
                        }
                    }
                }
            }
        }
        return home;
    }

    /** Joueurs à moins de `radius` blocs (horizontalement, 5 blocs de haut) du point `c`. */
    static List<PlayerRef> near(Store<EntityStore> store, List<PlayerRef> players, Vector3d c, double radius) {
        return near(store, players, c, radius, 5);
    }

    /** Joueurs à moins de `radius` blocs (horizontalement) du point `c`, pieds de 5 blocs sous lui à `above` au-dessus. */
    static List<PlayerRef> near(Store<EntityStore> store, List<PlayerRef> players, Vector3d c, double radius,
                                double above) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && Telegraphs.horizontal(pos, c) <= radius && pos.y() - c.y() > -5 && pos.y() - c.y() < above) {
                out.add(p);
            }
        }
        return out;
    }

    /** Joueurs dans `shape` au moment du coup : part `part` des PV max, et l'effet `effect` (null : aucun). */
    static List<PlayerRef> strike(World world, Store<EntityStore> store, Telegraphs.Shape shape, float part, String effect,
                                  float seconds) {
        List<PlayerRef> hit = new ArrayList<>();
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && shape.contains(pos)) {
                Hurt.percent(store, p.getReference(), part, CAUSE);
                if (effect != null) {
                    Hurt.effect(store, p.getReference(), effect, seconds);
                }
                hit.add(p);
            }
        }
        return hit;
    }

    static void tell(State st, PlayerRef player, String key) {
        long now = System.nanoTime();
        String id = player.getUuid() + ":" + key;   // un message n'en masque pas un autre
        Long last = st.throttle.get(id);
        if (last != null && now - last < Telegraphs.seconds(2.5f)) {
            return;
        }
        st.throttle.put(id, now);
        player.sendMessage(Message.translation(MESSAGES + key));
    }
}
