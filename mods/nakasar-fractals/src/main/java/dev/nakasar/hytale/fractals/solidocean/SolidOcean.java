package dev.nakasar.hytale.fractals.solidocean;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.SafeLandings;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.instability.Instabilities;
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
 * L'Océan solide (étape 7 du GDD), fidèle au déroulé de GW2 :
 * <ol>
 *   <li>{@link Step#PATH} : les fragments de jade ({@link SafeLandings} : une chute ramène au fragment d'avant), des
 *   irukandjis sur les grands fragments, qu'on peut combattre ou éviter ;</li>
 *   <li>{@link Step#MAW} : l'Abîme de Jade et ses trois phases ({@link JadeMaw}) ; {@link Step#DONE} ensuite.</li>
 * </ol>
 * Tout ce que pose le Java est non sauvegardé : une instance rechargée repart du départ.
 */
public final class SolidOcean implements FractalStage {

    public static final String FRACTAL = "SolidOcean";
    static final String MESSAGES = "nakasar_fractals_solid_ocean.";
    static final String MAW = "Nakasar_Fractal_Jade_Maw";
    static final String TENTACLE = "Nakasar_Fractal_Jade_Tentacle";
    static final String COLOSSUS = "Nakasar_Fractal_Jade_Colossus";
    static final String IRUKANDJI = "Nakasar_Fractal_Irukandji";
    static final String CRYSTAL = "Nakasar_Fractal_Reflecting_Crystal";
    static final String JADE_LANDING = "Nakasar_Fractal_Jade_Landing";
    static final String BEAM_CAUSE = "Nakasar_Fractal_Jade_Beam";

    enum Step { PATH, MAW, DONE }

    static final class State {
        Step step = Step.PATH;
        boolean started;
        final List<Ref<EntityStore>> pathFoes = new ArrayList<>();
        final SafeLandings landings = new SafeLandings(SolidOceanLayout.JUMP_ZONES, MESSAGES + "landing.back",
                Set.of(SafeLandings.LANDING, JADE_LANDING));
        final JadeMaw maw = new JadeMaw();
        final Map<UUID, Long> throttle = new HashMap<>();
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Barre de boss de l'Abîme (sa vie, la phase et les colosses), rôles fixes que les instabilités laissent tranquilles. */
    public static void register() {
        BossBarSystem.register(MAW);
        BossBarSystem.label(MAW, JadeMaw::label);
        Instabilities.exempt(MAW, TENTACLE);
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
        JadeMaw.clearLabels();
    }

    // --- pas de jeu ---------------------------------------------------------------------------------

    @Override
    public void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        if (players.isEmpty()) {
            st.maw.idle(world, store, dt);
            return;
        }
        if (!st.started) {
            st.started = true;
            Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
            for (double[] at : SolidOceanLayout.PATH_IRUKANDJI) {
                Ref<EntityStore> foe = Spawns.spawnFoe(world, store, IRUKANDJI, at);
                if (foe != null) {
                    st.pathFoes.add(foe);
                }
            }
        }
        st.landings.step(world, store, players);
        switch (st.step) {
            case PATH -> {
                if (!JadeMaw.inArena(store, players).isEmpty()) {
                    st.step = Step.MAW;
                    Gates.checkpoint(world, SolidOceanLayout.ARENA_CHECKPOINT, MESSAGES + "checkpoint");
                    st.maw.step(world, store, st, players, dt);
                }
            }
            case MAW -> {
                if (st.maw.step(world, store, st, players, dt)) {
                    st.step = Step.DONE;
                    Spawns.removeAll(store, st.pathFoes);
                    Gates.victory(world, SolidOceanLayout.REWARD, SolidOceanLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "victory");
                }
            }
            default -> {
            }
        }
    }

    // --- coups, objets lancés, morts ---------------------------------------------------------------------

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        if (MAW.equals(victimRole)) {
            damage.setCancelled(true);   // écailles denses : seuls les cristaux et les tentacules le blessent (Java)
            return;
        }
        if (COLOSSUS.equals(victimRole) && damage.getSource() instanceof Damage.ProjectileSource) {
            State st = state(world);
            st.maw.reflect(world, st, victim, attacker, damage);
        }
    }

    @Override
    public void thrown(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                       Ref<EntityStore> target) {
        if ("Crystal".equals(action)) {
            state(world).maw.crystal(world, store, ref, player);
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        if (TENTACLE.equals(role)) {
            st.maw.tentacleDown(at);
        } else if (COLOSSUS.equals(role)) {
            st.maw.colossusDown(at);
        }
    }

    /** Fait tomber un cristal réfléchissant en `at` ; il se ramasse accroupi ({@link CrystalHold}). */
    static void dropCrystal(Store<EntityStore> store, Vector3d at) {
        Carried.drop(store, CRYSTAL, at);
        Telegraphs.particle(store, "Nakasar_Fractal_Crystal_Glow", at, 1f);
    }

    static void tell(State st, PlayerRef player, String key) {
        long now = System.nanoTime();
        Long last = st.throttle.get(player.getUuid());
        if (last != null && now - last < Telegraphs.seconds(3f)) {
            return;
        }
        st.throttle.put(player.getUuid(), now);
        player.sendMessage(Message.translation(MESSAGES + key));
    }
}
