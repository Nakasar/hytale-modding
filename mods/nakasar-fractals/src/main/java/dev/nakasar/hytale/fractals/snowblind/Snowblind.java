package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.FractalItemsSystem;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.HandLock;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.instability.Instabilities;
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
 * La Tempête de neige (étape 8 du GDD), d'après GW2. Jusqu'à la chute de la Source, l'Hypothermie ({@link Frost}) monte
 * loin des feux ; ensuite le froid ne mord plus.
 * <ol>
 *   <li>{@link Step#CAMP} : le grand feu fait fondre le mur de glace, harcelé par les élémentaires ({@link Campfire}) ;</li>
 *   <li>{@link Step#SOURCE} : la Source élémentaire et ses cinq foyers ({@link Source}) ;</li>
 *   <li>{@link Step#FOREST} : la forêt, en suivant les traces ; cinq groupes de Svanir et de loups autour de leurs feux
 *   s'éveillent à l'approche, mais rien n'oblige à les battre ;</li>
 *   <li>{@link Step#VILLAGE} : le Chaman légendaire dans la grotte de glace ({@link Shaman}) ; {@link Step#DONE}
 *   ensuite.</li>
 * </ol>
 * Les tas de fagots repoussent {@value #PILE_REGROW} s après qu'on s'y est servi. Tout ce que pose le Java est non
 * sauvegardé : une instance rechargée repart du camp.
 */
public final class Snowblind implements FractalStage {

    public static final String FRACTAL = "Snowblind";
    static final String MESSAGES = "nakasar_fractals_snowblind.";
    static final String ELEMENTAL = "Nakasar_Fractal_Ice_Elemental";
    static final String WOLF = "Nakasar_Fractal_Frost_Wolf";
    static final String CULTIST = "Nakasar_Fractal_Frost_Cultist";
    static final String ICE_CASTER = "Nakasar_Fractal_Frost_Caster";
    static final String SOURCE = "Nakasar_Fractal_Elemental_Source";
    static final String SHAMAN = "Nakasar_Fractal_Legendary_Shaman";
    static final String BEAR = "Nakasar_Fractal_Shaman_Bear";
    static final String EFFIGY = "Nakasar_Fractal_Ice_Effigy";
    static final String CRYSTAL = "Nakasar_Fractal_Corrupted_Crystal";
    static final String SHARD = "Nakasar_Fractal_Ice_Shard";
    static final String FIREWOOD = "Nakasar_Fractal_Firewood";
    static final String TORCH = "Nakasar_Fractal_Torch";
    static final String BONFIRE = "Nakasar_Fractal_Bonfire";
    static final String BONFIRE_OUT = "Nakasar_Fractal_Bonfire_Out";
    static final String BRAZIER = "Nakasar_Fractal_Frost_Brazier";
    static final String BRAZIER_OUT = "Nakasar_Fractal_Frost_Brazier_Out";
    static final String PILE = "Nakasar_Fractal_Firewood_Pile";
    static final String MIST = "Nakasar_Fractal_Mist_Barrier";
    static final String WEATHER = "Nakasar_Fractal_Weather_Snowblind";
    static final String BLIZZARD_WEATHER = "Nakasar_Fractal_Weather_Snowblind_Blizzard";
    static final int MAX_FIREWOOD = 3;
    static final float PILE_REGROW = 20f;
    static final float SNOW_EVERY = 2f;
    static final double VILLAGE_FIRE_HEAT = 6;

    enum Step { CAMP, SOURCE, FOREST, VILLAGE, DONE }

    static final class State {
        Step step = Step.CAMP;
        boolean started;
        final Frost frost = new Frost();
        final Campfire camp = new Campfire();
        final Source source = new Source();
        final Shaman shaman = new Shaman();
        final boolean[] packs = new boolean[SnowblindLayout.PACK_CENTERS.length];
        boolean plateau;
        final Map<UUID, Long> throttle = new HashMap<>();
        float snowClock;
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** L'étape enregistrée, pour la fiole de purge des objets de soutien. */
    private static volatile Snowblind instance;

    public Snowblind() {
        instance = this;
    }

    /** Fiole de purge : retire `n` piles d'Hypothermie au joueur (rien hors de la Tempête de neige). */
    public static void relieveCold(World world, Ref<EntityStore> ref, int n) {
        Snowblind self = instance;
        PlayerRef player = ref == null || !ref.isValid() ? null
                : world.getEntityStore().getStore().getComponent(ref, PlayerRef.getComponentType());
        State st = self == null || player == null ? null : self.states.get(world);
        if (st != null) {
            st.frost.relieve(player.getUuid(), n);
        }
    }

    /** La torche et les fagots se perdent hors de la fractale. */
    public static FractalItemsSystem.Rule itemsRule() {
        return new FractalItemsSystem.Rule(FRACTAL, Set.of(TORCH, FIREWOOD));
    }

    /** Barres de boss de la Source (bouclier de givre), du Chaman (ses deux formes) et de l'Effigie (défiance). */
    public static void register() {
        BossBarSystem.register(SOURCE);
        BossBarSystem.label(SOURCE, Source::label);
        for (String role : new String[]{SHAMAN, BEAR, EFFIGY}) {
            BossBarSystem.register(role);
            BossBarSystem.label(role, Defiance::label);
        }
        Instabilities.exempt(EFFIGY, CRYSTAL, SHARD);
        HandLock.lock(FIREWOOD);
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
        Source.forgetAll();
    }

    // --- pas de jeu ---------------------------------------------------------------------------------

    @Override
    public void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        if (players.isEmpty()) {
            idle(world, store, st, dt);
            return;
        }
        if (!st.started) {
            st.started = true;
            Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
        }
        boolean blizzard = st.step == Step.SOURCE && st.source.blizzard();
        if (st.step == Step.CAMP || st.step == Step.SOURCE) {
            st.frost.step(world, store, players, heats(st), blizzard, dt);
        } else {
            st.frost.thaw(store, players);   // la Source tombée, le froid ne mord plus
        }
        snow(store, st, players, blizzard, dt);
        // Un fagot porté reste en main (Kevin, 25 octobre 2026), comme le marteau ou les cristaux : rangé dans le sac,
        // il revient dans la main.
        for (PlayerRef p : players) {
            HandLock.ensureHeld(store, p.getReference(), FIREWOOD);
        }
        switch (st.step) {
            case CAMP -> {
                if (st.camp.step(world, store, dt)) {
                    st.step = Step.SOURCE;
                    Gates.checkpoint(world, SnowblindLayout.WALL_CHECKPOINT, MESSAGES + "checkpoint");
                }
            }
            case SOURCE -> {
                Source.Outcome outcome = st.source.step(world, store, players, st.frost, dt);
                if (outcome == Source.Outcome.WON) {
                    st.step = Step.FOREST;
                    Gates.open(world, store, SnowblindLayout.GATE_SOURCE, MESSAGES + "source.victory");
                    Gates.checkpoint(world, SnowblindLayout.FOREST_CHECKPOINT, MESSAGES + "checkpoint");
                }
            }
            case FOREST -> {
                packs(world, store, st, players);
                plateau(world, store, st, players);
                if (Spawns.anyIn(store, players, SnowblindLayout.VILLAGE)) {
                    st.step = Step.VILLAGE;
                    st.plateau = true;
                    Gates.checkpoint(world, SnowblindLayout.VILLAGE_CHECKPOINT, MESSAGES + "checkpoint");
                    st.shaman.engage(world, store);
                }
            }
            case VILLAGE -> {
                Shaman.Outcome outcome = st.shaman.step(world, store, st, players, dt);
                if (outcome == Shaman.Outcome.WON) {
                    st.step = Step.DONE;
                    Gates.victory(world, SnowblindLayout.REWARD, SnowblindLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "shaman.victory");
                } else if (outcome == Shaman.Outcome.RESET) {
                    reopenVillage(world, store, st);
                }
            }
            default -> {
            }
        }
    }

    /** Plus personne en vie : les boss en cours comptent jusqu'à leur remise à zéro. */
    private static void idle(World world, Store<EntityStore> store, State st, float dt) {
        if (st.step == Step.SOURCE) {
            st.source.idle(world, store, dt);
        }
        if (st.step == Step.VILLAGE && st.shaman.idle(world, store, dt)) {
            reopenVillage(world, store, st);
        }
    }

    private static void reopenVillage(World world, Store<EntityStore> store, State st) {
        st.step = Step.FOREST;
        Gates.checkpoint(world, SnowblindLayout.VILLAGE_CHECKPOINT, MESSAGES + "checkpoint");
    }

    /** Feux allumés : grand feu, foyers de la Source, feux de la forêt et de la grotte (toujours allumés). */
    private static List<Frost.Heat> heats(State st) {
        List<Frost.Heat> out = new ArrayList<>();
        if (st.camp.lit()) {
            out.add(new Frost.Heat(Campfire.center(), SnowblindLayout.BONFIRE_HEAT));
        }
        st.source.heats(out);
        for (int[] f : SnowblindLayout.VILLAGE_FIRES) {
            out.add(new Frost.Heat(new Vector3d(f[0] + 0.5, f[1], f[2] + 0.5), VILLAGE_FIRE_HEAT));
        }
        for (int[] f : SnowblindLayout.FOREST_FIRES) {
            out.add(new Frost.Heat(new Vector3d(f[0] + 0.5, f[1], f[2] + 0.5), SnowblindLayout.FOREST_FIRE_HEAT));
        }
        return out;
    }

    /** Neige qui tombe autour de chaque joueur (le blizzard, plus dense, pendant la Source sans foyer). */
    private static void snow(Store<EntityStore> store, State st, List<PlayerRef> players, boolean blizzard, float dt) {
        st.snowClock += dt;
        if (st.snowClock < SNOW_EVERY) {
            return;
        }
        st.snowClock = 0f;
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                Telegraphs.particle(store, blizzard ? "Nakasar_Fractal_Blizzard" : "Nakasar_Fractal_Snowfall",
                        new Vector3d(at).add(0, 6, 0), 1f);
            }
        }
    }

    /** Un joueur approche d'un groupe de la forêt : ses Svanir et ses loups se lèvent autour de leur feu. */
    private static void packs(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        double[][] centers = SnowblindLayout.PACK_CENTERS;
        for (int i = 0; i < centers.length; i++) {
            if (st.packs[i]) {
                continue;
            }
            Vector3d c = Spawns.point(centers[i]);
            if (Spawns.nearest(store, players, c) > SnowblindLayout.PACK_TRIGGER) {
                continue;
            }
            st.packs[i] = true;
            double[][] spawns = SnowblindLayout.PACK_SPAWNS[i];
            String[] roles = SnowblindLayout.PACK_ROLES[i];
            for (int k = 0; k < spawns.length; k++) {
                Vector3d s = Spawns.point(spawns[k]);
                Spawns.spawnFoe(world, store, roles[k], s, Telegraphs.yawToward(s, c) + (float) Math.PI);
            }
            // Un loup de plus par paire de joueurs en plus du premier.
            for (int k = 0; k < (FractalRuns.partySize(world) - 1) / 2; k++) {
                Vector3d s = Spawns.point(spawns[k % spawns.length]).add(1.2, 0, 1.2);
                Spawns.spawnFoe(world, store, WOLF, s, Telegraphs.yawToward(s, c) + (float) Math.PI);
            }
        }
    }

    /** Le plateau de l'est : point de retour à mi-forêt. */
    private static void plateau(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        if (!st.plateau && Spawns.nearest(store, players, Spawns.point(SnowblindLayout.PLATEAU_CHECKPOINT)) < 8) {
            st.plateau = true;
            Gates.checkpoint(world, SnowblindLayout.PLATEAU_CHECKPOINT, MESSAGES + "checkpoint");
        }
    }

    // --- blocs utilisés, coups, morts ------------------------------------------------------------------

    @Override
    public void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                    int x, int y, int z) {
        State st = state(world);
        ChunkStore chunks = world.getChunkStore();
        switch (action) {
            case "Snowblind_Firewood" -> {
                if (!PILE.equals(WorldBlocks.name(chunks, x, y, z))) {
                    return;
                }
                int carried = Carried.count(store, ref, FIREWOOD);
                if (carried >= MAX_FIREWOOD) {
                    tell(st, player, "wood.full");
                    return;
                }
                WorldBlocks.clear(chunks, x, y, z);
                Carried.give(store, ref, FIREWOOD);
                HandLock.ensureHeld(store, ref, FIREWOOD);
                player.sendMessage(Message.translation(MESSAGES + "wood.taken").param("count", carried + 1));
                Delayed.later(world, PILE_REGROW, s -> {
                    if (WorldBlocks.name(world.getChunkStore(), x, y, z) == null) {
                        WorldBlocks.setFacingOpen(world.getChunkStore(), x, y, z, PILE);
                    }
                });
            }
            case "Snowblind_Torch" -> {
                if (Carried.count(store, ref, TORCH) > 0) {
                    tell(st, player, "torch.has");
                    return;
                }
                Carried.give(store, ref, TORCH);
                player.sendMessage(Message.translation(MESSAGES + "torch.taken"));
            }
            case "Snowblind_Bonfire" -> {
                int[] b = SnowblindLayout.BONFIRE;
                if (st.step == Step.CAMP && x == b[0] && y == b[1] && z == b[2]) {
                    st.camp.use(world, store, ref, player, st);
                }
            }
            case "Snowblind_Brazier" -> {
                if (SnowblindLayout.SOURCE_ARENA.contains(x, y, z)) {
                    st.source.use(world, store, ref, player, st, x, z);
                }
            }
            default -> {
            }
        }
    }

    @Override
    public boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        return SHAMAN.equals(role) && state(world).shaman.shielded(ref);
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        State st = state(world);
        if (victimRole == null) {
            slash(buffer, st, victim, attacker, damage);
            return;
        }
        switch (victimRole) {
            case SHARD -> {
                if (attacker != null && attacker.equals(st.frost.prisoner(victim))) {
                    damage.setCancelled(true);   // le prisonnier ne brise pas lui-même sa glace
                }
            }
            case SOURCE -> st.source.filter(buffer, victim, damage);
            case SHAMAN -> st.shaman.filter(buffer, victim, damage);
            default -> {
            }
        }
    }

    /** Coup d'épée du Chaman (cause physique ; ses attaques annoncées ont la cause Frost) : +2 piles d'hypothermie. */
    private static void slash(CommandBuffer<EntityStore> buffer, State st, Ref<EntityStore> victim,
                              Ref<EntityStore> attacker, Damage damage) {
        if (attacker == null) {
            return;
        }
        NPCEntity npc = buffer.getComponent(attacker, NPCEntity.getComponentType());
        int physical = DamageCause.getAssetMap().getIndexOrDefault("Physical", Integer.MIN_VALUE);
        if (npc == null || !SHAMAN.equals(npc.getRoleName()) || damage.getDamageCauseIndex() != physical) {
            return;
        }
        PlayerRef player = buffer.getComponent(victim, PlayerRef.getComponentType());
        if (player != null) {
            st.frost.add(player.getUuid(), Shaman.SLASH_STACKS);
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        switch (role) {
            case SOURCE -> st.source.down();
            case SHAMAN, BEAR -> st.shaman.down();
            default -> {
            }
        }
    }

    // --- outils ------------------------------------------------------------------------------------------

    /** Ferme une barrière de brume (blocs `cells`). */
    static void close(World world, int[][] cells) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] c : cells) {
            WorldBlocks.set(chunks, c[0], c[1], c[2], MIST, 0);
        }
    }

    static void tell(State st, PlayerRef player, String key) {
        long now = System.nanoTime();
        Long last = st.throttle.get(player.getUuid());
        if (last != null && now - last < Telegraphs.seconds(2.5f)) {
            return;
        }
        st.throttle.put(player.getUuid(), now);
        player.sendMessage(Message.translation(MESSAGES + key));
    }
}
