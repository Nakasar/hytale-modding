package dev.nakasar.hytale.fractals.swampland;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.instability.Instabilities;
import dev.nakasar.hytale.fractals.stage.FractalStage;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Le Marais (étape 7 du GDD), fidèle au déroulé de GW2 :
 * <ol>
 *   <li>{@link Step#WISPS} : trois feux-follets à rapporter dans leurs failles avant la fin du minuteur, entre les murs
 *   qui surgissent, les pièges et les fusils revigorants ({@link WispRun}) ;</li>
 *   <li>{@link Step#PASSAGE} puis {@link Step#MOSSMAN} : l'embuscade du Moussu ({@link Mossman}) ;</li>
 *   <li>{@link Step#CLEARING} : un feu-follet à déposer dans une faille de la clairière réveille Carnasse ;</li>
 *   <li>{@link Step#BLOOM} : Carnasse ({@link Bloomhunger}) ; {@link Step#DONE} ensuite.</li>
 * </ol>
 * Tout ce que pose le Java est non sauvegardé : une instance rechargée repart du marais.
 */
public final class Swampland implements FractalStage {

    public static final String FRACTAL = "Swampland";
    static final String MESSAGES = "nakasar_fractals_swampland.";
    static final String MOSSMAN = "Nakasar_Fractal_Mossman";
    static final String MOSSMAN_BEAST = "Nakasar_Fractal_Mossman_Beast";
    static final String MOSS_WOLF = "Nakasar_Fractal_Moss_Wolf";
    static final String BLOOMHUNGER = "Nakasar_Fractal_Bloomhunger";
    static final String SPIRIT = "Nakasar_Fractal_Spirit_Animal";
    static final String BLOOM = "Nakasar_Fractal_Poison_Bloom";
    static final String WISP = "Nakasar_Fractal_Wisp";
    static final String WISP_BLOCK = "Nakasar_Fractal_Wisp_Light";
    static final String CLEFT = "Nakasar_Fractal_Wisp_Cleft";
    static final String CLEFT_LIT = "Nakasar_Fractal_Wisp_Cleft_Lit";
    static final String MIST = "Nakasar_Fractal_Mist_Barrier";
    static final String WALL = "Rock_Stone_Mossy";
    static final String SWIFTNESS = "Nakasar_Fractal_Swiftness";
    static final String CRIPPLED = "Nakasar_Fractal_Crippled";
    static final String PURGE_CAUSE = "Nakasar_Fractal_Purge";

    enum Step { WISPS, PASSAGE, MOSSMAN, CLEARING, BLOOM, DONE }

    static final class State {
        Step step = Step.WISPS;
        boolean started;
        final WispRun wisps = new WispRun();
        final Mossman mossman = new Mossman();
        final Bloomhunger bloom = new Bloomhunger();
        final Map<UUID, Long> throttle = new HashMap<>();
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Barres de boss du Moussu (ses deux formes) et de Carnasse, avec leur défiance ; la fleur ne bouge pas. */
    public static void register() {
        for (String role : new String[]{MOSSMAN, MOSSMAN_BEAST, BLOOMHUNGER}) {
            BossBarSystem.register(role);
            BossBarSystem.label(role, Defiance::label);
        }
        Instabilities.exempt(BLOOM);
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
            idle(world, store, st, dt);
            return;
        }
        if (!st.started) {
            st.started = true;
            st.wisps.setup(world);
            close(world, SwamplandLayout.GATE_AHEAD);
            Spawns.tellAll(world, Message.translation(MESSAGES + "intro").param("seconds", (int) WispRun.timer(world)));
        }
        st.wisps.step(world, store, st, players, dt);
        switch (st.step) {
            case WISPS -> {
                if (st.wisps.done()) {
                    st.step = Step.PASSAGE;
                    Gates.open(world, store, SwamplandLayout.GATE_SWAMP, MESSAGES + "wisps.done");
                    Gates.checkpoint(world, SwamplandLayout.SWAMP_CHECKPOINT, MESSAGES + "checkpoint");
                }
            }
            case PASSAGE -> {
                if (Spawns.anyIn(store, players, SwamplandLayout.ROOM)) {
                    st.step = Step.MOSSMAN;
                    close(world, SwamplandLayout.GATE_BEHIND);
                    Gates.checkpoint(world, SwamplandLayout.ROOM_CHECKPOINT, MESSAGES + "checkpoint");
                    st.mossman.ambush(world, store);
                }
            }
            case MOSSMAN -> {
                Mossman.Outcome outcome = st.mossman.step(world, store, players, dt);
                if (outcome == Mossman.Outcome.WON) {
                    st.step = Step.CLEARING;
                    Gates.open(world, store, SwamplandLayout.GATE_BEHIND, null);
                    Gates.open(world, store, SwamplandLayout.GATE_AHEAD, MESSAGES + "mossman.victory");
                    Gates.checkpoint(world, SwamplandLayout.CLEARING_CHECKPOINT, MESSAGES + "checkpoint");
                    st.bloom.prepare(world);
                    Spawns.tellAll(world, Message.translation(MESSAGES + "bloom.start"));
                } else if (outcome == Mossman.Outcome.RESET) {
                    st.step = Step.PASSAGE;
                    Gates.open(world, store, SwamplandLayout.GATE_BEHIND, null);
                }
            }
            case BLOOM -> {
                Bloomhunger.Outcome outcome = st.bloom.step(world, store, st, players, dt);
                if (outcome == Bloomhunger.Outcome.WON) {
                    st.step = Step.DONE;
                    Gates.victory(world, SwamplandLayout.REWARD, SwamplandLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "bloom.victory");
                } else if (outcome == Bloomhunger.Outcome.RESET) {
                    st.step = Step.CLEARING;
                    st.bloom.prepare(world);
                }
            }
            default -> {
            }
        }
    }

    /** Plus personne en vie : les boss en cours comptent jusqu'à leur remise à zéro. */
    private static void idle(World world, Store<EntityStore> store, State st, float dt) {
        if (st.step == Step.MOSSMAN && st.mossman.idle(world, store, dt)) {
            st.step = Step.PASSAGE;
            Gates.open(world, store, SwamplandLayout.GATE_BEHIND, null);
        }
        if (st.step == Step.BLOOM && st.bloom.idle(world, store, dt)) {
            st.step = Step.CLEARING;
            st.bloom.prepare(world);
        }
    }

    // --- blocs utilisés, coups, morts ------------------------------------------------------------------

    @Override
    public void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                    int x, int y, int z) {
        State st = state(world);
        ChunkStore chunks = world.getChunkStore();
        switch (action) {
            case "Swampland_Wisp" -> {
                if (!WISP_BLOCK.equals(WorldBlocks.name(chunks, x, y, z))) {
                    return;
                }
                if (Carried.count(store, ref, WISP) > 0) {
                    tell(st, player, "wisp.full");
                    return;
                }
                WorldBlocks.clear(chunks, x, y, z);
                Carried.give(store, ref, WISP);
                if (st.step == Step.WISPS) {
                    st.wisps.taken(world, store, x, z);
                }
            }
            case "Swampland_Cleft" -> {
                if (CLEFT_LIT.equals(WorldBlocks.name(chunks, x, y, z))) {
                    tell(st, player, "cleft.taken");
                    return;
                }
                if (!Carried.takeOne(store, ref, WISP)) {
                    tell(st, player, "wisp.none");
                    return;
                }
                WorldBlocks.swap(chunks, x, y, z, CLEFT_LIT);
                Telegraphs.particle(store, "Nakasar_Fractal_Wisp_Glow", new Vector3d(x + 0.5, y + 1, z + 0.5), 1.5f);
                if (z > SwamplandLayout.SWAMP.z0() - 2) {
                    st.wisps.lit(world);
                } else if (st.step == Step.CLEARING) {
                    st.step = Step.BLOOM;
                    st.bloom.wake(world, store, cleftIndex(x, z));
                } else if (st.step == Step.BLOOM) {
                    st.bloom.cleftLit(world, store);
                }
            }
            case "Swampland_Rack" -> st.wisps.rack(world, store, st, player, x, z);
            default -> {
            }
        }
    }

    private static int cleftIndex(int x, int z) {
        int[][] clefts = SwamplandLayout.CLEARING_CLEFTS;
        for (int i = 0; i < clefts.length; i++) {
            if (clefts[i][0] == x && clefts[i][2] == z) {
                return i;
            }
        }
        return 0;
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        if (victimRole == null) {
            return;
        }
        State st = state(world);
        if (BLOOMHUNGER.equals(victimRole) || SPIRIT.equals(victimRole) || BLOOM.equals(victimRole)) {
            st.bloom.filter(buffer, victim, victimRole, damage);
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        switch (role) {
            case MOSSMAN, MOSSMAN_BEAST -> st.mossman.down();
            case SPIRIT -> st.bloom.spiritDown();
            case BLOOMHUNGER -> st.bloom.down();
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
