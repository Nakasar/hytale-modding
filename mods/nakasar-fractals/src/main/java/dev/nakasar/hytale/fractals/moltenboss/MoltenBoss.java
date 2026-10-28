package dev.nakasar.hytale.fractals.moltenboss;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.FractalItemsSystem;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
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
 * Boss en fusion (GW2) : la fonderie de l'Alliance en fusion. Avec Braham et Rox, on descend du camp dans l'atelier :
 * <ol>
 *   <li>quatre meutes ({@link Packs}) ; la quatrième garde un résonateur qui rend le chaman de la flamme d'élite
 *   invulnérable ; elle tombée, le pont du canal de lave se pose ;</li>
 *   <li>la fonderie : l'Effigie en fusion ({@link Effigy}), son Protecteur et un second résonateur ;</li>
 *   <li>la cour des wagonnets et la passerelle des cuves : quatre groupes, puis le pont du creuset s'ouvre ;</li>
 *   <li>la plate-forme du creuset : le Berserker et la Tempête de feu en fusion ({@link MoltenDuo}).</li>
 * </ol>
 * La lave (bassins, creuset, canal) brûle ; tombé dans le canal, on revient au dernier point de retour. Pas de soin
 * nulle part (AGENTS.md) : un boss laissé seul attend, avec ses PV du moment. Tout ce que pose le
 * Java est non sauvegardé : une instance rechargée repart du départ.
 */
public final class MoltenBoss implements FractalStage {

    public static final String FRACTAL = "MoltenBoss";
    static final String MESSAGES = "nakasar_fractals_molten_boss.";
    static final String CAUSE = "Nakasar_Fractal_Molten";
    static final String BRAHAM = "Nakasar_Fractal_Braham";
    static final String ROX = "Nakasar_Fractal_Rox";
    static final String RESONATOR = "Nakasar_Fractal_Dredge_Resonator";
    static final String ELITE_SHAMAN = "Nakasar_Fractal_Elite_Flame_Shaman";
    static final String PROTECTOR = "Nakasar_Fractal_Molten_Protector";
    static final String EFFIGY = "Nakasar_Fractal_Molten_Effigy";
    static final String BERSERKER = "Nakasar_Fractal_Molten_Berserker";
    static final String FIRESTORM = "Nakasar_Fractal_Molten_Firestorm";
    static final String BERSERKER_2 = "Nakasar_Fractal_Molten_Berserker_Empowered";
    static final String FIRESTORM_2 = "Nakasar_Fractal_Molten_Firestorm_Empowered";
    static final String BURNING = "Nakasar_Fractal_Molten_Burning";
    static final String ENRAGED = "Nakasar_Fractal_Molten_Enraged";
    static final String SHIELDED = "Nakasar_Fractal_Molten_Shielded";
    static final String LINK = "Nakasar_Fractal_Molten_Link";
    /** Brûlure de la fonderie : part des PV max par seconde. */
    static final float BURN_PART = 0.02f;
    /** Dans la lave : part des PV max par seconde (la brûlure ne s'y ajoute qu'une fois sorti). */
    static final float LAVA_PART = 0.08f;
    /** Tombé dans le canal : ramené au point de retour après ce temps. */
    static final float CHANNEL_SECONDS = 1.5f;
    /** Un monstre tombé de plus de 4 blocs sous son aire y est ramené. */
    static final double FALL_LIMIT = 4;

    enum Phase { FACILITY, EFFIGY, GAUNTLET, DUO, DONE }

    static final class State {
        boolean started;
        Phase phase = Phase.FACILITY;
        Ref<EntityStore> braham;
        Ref<EntityStore> rox;
        final Packs packs = new Packs();
        final Effigy effigy = new Effigy();
        final MoltenDuo duo = new MoltenDuo();
        /** Temps passé dans le canal de lave par joueur. */
        final Map<UUID, Float> channel = new HashMap<>();
        final Map<String, Long> throttle = new HashMap<>();
        boolean ticking;
        long lastTick;
    }

    /** Cases de lave des bassins et du creuset, en clés {@link #cell} : y du sol autour (surface un bloc dessous). */
    private static final Map<Long, Integer> LAVA = new HashMap<>();

    static {
        for (int[] c : MoltenBossLayout.LAVA_CELLS) {
            LAVA.put(cell(c[0], c[1]), c[2]);
        }
    }

    private static long cell(int x, int z) {
        return ((long) x << 32) ^ (z & 0xffffffffL);
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Brûlure, rage et protection : perdues hors de la fractale. */
    public static FractalItemsSystem.Rule itemsRule() {
        return new FractalItemsSystem.Rule(FRACTAL, Set.of(), new String[]{BURNING, ENRAGED, SHIELDED});
    }

    /** Barres de boss : chaman d'élite, Effigie (puissance), Protecteur, duo de la plate-forme. */
    public static void register() {
        for (String role : new String[]{ELITE_SHAMAN, PROTECTOR, EFFIGY, BERSERKER, FIRESTORM, BERSERKER_2, FIRESTORM_2}) {
            BossBarSystem.register(role);
        }
        BossBarSystem.label(EFFIGY, Effigy::label);
        Instabilities.exempt(BRAHAM, ROX);
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
            // Ondes de choc et flammes au sol : à chaque tick.
            TelegraphSystem.start(world, new TelegraphSystem.Task() {
                @Override
                public boolean step(World w, Store<EntityStore> s, long now) {
                    if (states.get(w) != st) {
                        return true;
                    }
                    float tickDt = st.lastTick == 0 ? 0f : Math.min(0.1f, (now - st.lastTick) / 1e9f);
                    st.lastTick = now;
                    st.effigy.tick(w, s, tickDt);
                    st.duo.tick(w, s, tickDt);
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
        lava(world, store, st, players, dt);
        switch (st.phase) {
            case FACILITY -> {
                if (st.packs.workshop(world, store, players)) {
                    st.phase = Phase.EFFIGY;
                }
            }
            case EFFIGY -> {
                if (st.effigy.step(world, store, st, players, dt)) {
                    Gates.open(world, store, MoltenBossLayout.FOUNDRY_GATE, MESSAGES + "effigy.victory");
                    Gates.checkpoint(world, MoltenBossLayout.CHECKPOINT_B, MESSAGES + "checkpoint");
                    st.phase = Phase.GAUNTLET;
                }
            }
            case GAUNTLET -> {
                if (st.packs.gauntlet(world, store, players)) {
                    Gates.open(world, store, MoltenBossLayout.BOILERS_GATE, MESSAGES + "boilers.open");
                    Gates.checkpoint(world, MoltenBossLayout.CHECKPOINT_D, MESSAGES + "checkpoint");
                    move(store, st.braham, Spawns.point(MoltenBossLayout.BRAHAM_END), Spawns.point(MoltenBossLayout.ARENA));
                    move(store, st.rox, Spawns.point(MoltenBossLayout.ROX_END), Spawns.point(MoltenBossLayout.ARENA));
                    st.phase = Phase.DUO;
                }
            }
            case DUO -> {
                if (st.duo.step(world, store, st, players, dt)) {
                    st.phase = Phase.DONE;
                    Gates.victory(world, MoltenBossLayout.REWARD, MoltenBossLayout.END_EXIT,
                            MESSAGES + "title.victory", MESSAGES + "duo.victory");
                }
            }
            default -> {
            }
        }
    }

    /** Braham et Rox (invulnérables, ils regardent la rampe) et la première meute. */
    private static void start(World world, Store<EntityStore> store, State st) {
        st.started = true;
        Vector3d spawn = Spawns.point(MoltenBossLayout.SPAWN);
        st.braham = ally(store, BRAHAM, Spawns.point(MoltenBossLayout.BRAHAM), spawn);
        st.rox = ally(store, ROX, Spawns.point(MoltenBossLayout.ROX), spawn);
        Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
        Spawns.tellAll(world, Message.translation(MESSAGES + "intro.rox"));
    }

    private static Ref<EntityStore> ally(Store<EntityStore> store, String role, Vector3d at, Vector3d face) {
        Ref<EntityStore> ref = Spawns.spawn(store, role, at, Telegraphs.yawToward(at, face));
        if (ref != null && ref.isValid()) {
            store.ensureAndGetComponent(ref, Invulnerable.getComponentType());
        }
        return ref;
    }

    /**
     * La lave : dans un bassin ou le creuset, elle brûle ; dans le canal (sous le niveau du sol) ou au fond du gouffre,
     * elle brûle puis rejette au dernier point de retour au bout de {@value #CHANNEL_SECONDS} s. La brûlure ronge la vie tant qu'elle dure.
     */
    private static void lava(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        for (PlayerRef p : players) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            // La surface de la lave est un bloc sous le sol : on y est quand les pieds sont sous le niveau du sol.
            Integer floor = LAVA.get(cell((int) Math.floor(at.x()), (int) Math.floor(at.z())));
            boolean inLava = floor != null && at.y() < floor - 0.1 && at.y() > floor - 3;
            // Canal et gouffre : on brûle, puis on revient au dernier point de retour.
            if (MoltenBossLayout.CHANNEL.contains(at.x(), at.y(), at.z()) || at.y() < MoltenBossLayout.ABYSS_Y) {
                inLava = true;
                float t = st.channel.merge(p.getUuid(), dt, Float::sum);
                if (t >= CHANNEL_SECONDS) {
                    st.channel.remove(p.getUuid());
                    Vector3d back = Gates.spawnPoint(world);
                    Moves.teleport(store, ref, back != null ? back : Spawns.point(MoltenBossLayout.SPAWN));
                    p.sendMessage(Message.translation(MESSAGES + "lava.out"));
                }
            } else {
                st.channel.remove(p.getUuid());
            }
            if (inLava) {
                Hurt.percent(store, ref, LAVA_PART * dt, CAUSE);
                Hurt.effect(store, ref, BURNING, 3f);
                tell(st, p, "lava");
            } else if (Hurt.has(store, ref, BURNING)) {
                Hurt.percent(store, ref, BURN_PART * dt, CAUSE);
            }
        }
    }

    // --- coups, morts ----------------------------------------------------------------------------------------------

    @Override
    public boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        State st = state(world);
        return switch (role) {
            case ELITE_SHAMAN -> st.packs.shamanShielded(store);
            case PROTECTOR, EFFIGY -> st.effigy.shielded(store, role);
            default -> false;
        };
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        State st = state(world);
        if (victimRole == null) {
            // Les coups de l'Effigie montent avec sa puissance.
            if (attacker != null && EFFIGY.equals(Spawns.role(store, attacker))) {
                damage.setAmount(damage.getAmount() * st.effigy.might());
            }
            return;
        }
        if (shielded(world, store, victim, victimRole)) {
            damage.setCancelled(true);
            PlayerRef by = attacker == null ? null : buffer.getComponent(attacker, PlayerRef.getComponentType());
            if (by != null) {
                tell(st, by, EFFIGY.equals(victimRole) ? "effigy.protected" : "shielded");
            }
        }
    }

    // --- outils --------------------------------------------------------------------------------------------------

    /** Déplace un PNJ (téléportation), tourné vers `face`. */
    static void move(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d to, Vector3d face) {
        if (ref != null && ref.isValid()) {
            store.putComponent(ref, Teleport.getComponentType(),
                    new Teleport(new Vector3d(to), new Rotation3f(0f, Telegraphs.yawToward(to, face), 0f)));
        }
    }

    /** Joueurs à moins de `radius` blocs (horizontalement, 5 blocs de haut) du point `c`. */
    static List<PlayerRef> near(Store<EntityStore> store, List<PlayerRef> players, Vector3d c, double radius) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && Telegraphs.horizontal(pos, c) <= radius && pos.y() - c.y() > -5 && pos.y() - c.y() < 5) {
                out.add(p);
            }
        }
        return out;
    }

    /** Joueurs dans `shape` au moment du coup : part `part` des PV max, et l'effet `effect` (null : aucun). */
    static void strike(World world, Store<EntityStore> store, Telegraphs.Shape shape, float part, String effect,
                       float seconds) {
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && shape.contains(pos)) {
                Hurt.percent(store, p.getReference(), part, CAUSE);
                if (effect != null) {
                    Hurt.effect(store, p.getReference(), effect, seconds);
                }
            }
        }
    }

    /**
     * Protection visible : l'effet {@value #SHIELDED} (icône) sur `ward` et un rayon de lumière de `source` à `ward`,
     * reposés tant que dure la protection.
     */
    static void link(Store<EntityStore> store, Ref<EntityStore> source, Ref<EntityStore> ward, boolean beam) {
        if (ward == null || !ward.isValid()) {
            return;
        }
        Hurt.effect(store, ward, SHIELDED, 1.5f);
        Vector3d a = Telegraphs.position(store, source);
        Vector3d b = Telegraphs.position(store, ward);
        if (!beam || a == null || b == null) {
            return;
        }
        double d = a.distance(b);
        int n = Math.max(2, (int) (d / 1.5));
        for (int k = 0; k <= n; k++) {
            double t = (double) k / n;
            Telegraphs.particle(store, LINK, new Vector3d(a.x() + (b.x() - a.x()) * t, a.y() + 1.6 + (b.y() - a.y()) * t,
                    a.z() + (b.z() - a.z()) * t), 0.6f);
        }
    }

    static void tell(State st, PlayerRef player, String key) {
        long now = System.nanoTime();
        String id = player.getUuid() + ":" + key;
        Long last = st.throttle.get(id);
        if (last != null && now - last < Telegraphs.seconds(2.5f)) {
            return;
        }
        if (st.throttle.size() > 256) {
            st.throttle.values().removeIf(t -> now - t > Telegraphs.seconds(2.5f));
        }
        st.throttle.put(id, now);
        player.sendMessage(Message.translation(MESSAGES + key));
    }
}
