package dev.nakasar.hytale.fractals.deepstone;

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
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.FractalItemsSystem;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
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
 * Roche des Abysses (saison 2), d'après GW2 : le caveau des nains de Deldrimor, au pied d'une montagne enneigée.
 * <ol>
 *   <li>la descente des corniches (chauves-souris) jusqu'à la salle du cristal, avec Torin et Kay ;</li>
 *   <li>à l'ouest, la grille de runes ({@link RuneGrid}) puis la Sentinelle ({@link Sentinel}) ; à l'est, les nids et le
 *   pont du vent puis la Reine de la couvée ({@link EastPath}). Chaque boss laisse une orbe de lumière : on la prend
 *   (retour au cristal) et on la dépose au cristal ;</li>
 *   <li>les deux orbes déposées, chacun reçoit la Lumière de Deldrimor ({@link DeepLight}) et le Minotaure des ombres
 *   surgit ({@link Minotaur}) ; vaincu, la porte nord s'ouvre ;</li>
 *   <li>la salle du gouffre ({@link AbyssPit}), l'ascenseur ({@link Lift}), puis l'arène de la Voix ({@link Voice}).</li>
 * </ol>
 * Tout ce que pose le Java (dalles, PNJ, objets) est non sauvegardé : une instance rechargée repart du départ.
 */
public final class Deepstone implements FractalStage {

    public static final String FRACTAL = "Deepstone";
    static final String MESSAGES = "nakasar_fractals_deepstone.";
    static final String CAUSE = "Nakasar_Fractal_Deepstone";
    static final String LIGHT = "Nakasar_Fractal_Light_Of_Deldrimor";
    static final String TORIN = "Nakasar_Fractal_Torin";
    static final String KAY = "Nakasar_Fractal_Kay";
    static final String BAT = "Nakasar_Fractal_Cave_Bat";
    static final String SPIDERLING = "Nakasar_Fractal_Cave_Spiderling";
    static final String BROOD_MOTHER = "Nakasar_Fractal_Brood_Mother";
    static final String SENTINEL = "Nakasar_Fractal_Deepstone_Sentinel";
    static final String WIND_SPRITE = "Nakasar_Fractal_Wind_Sprite";
    static final String NEST = "Nakasar_Fractal_Spider_Nest";
    static final String QUEEN = "Nakasar_Fractal_Brood_Queen";
    static final String IMP = "Nakasar_Fractal_Shadow_Imp";
    static final String MAULER = "Nakasar_Fractal_Shadow_Mauler";
    static final String BLOODSUCKER = "Nakasar_Fractal_Shadow_Bloodsucker";
    static final String MINOTAUR = "Nakasar_Fractal_Shadow_Minotaur";
    static final String SHADE = "Nakasar_Fractal_Deepstone_Shade";
    static final String FLAME = "Nakasar_Fractal_Spectral_Flame";
    static final String VOICE = "Nakasar_Fractal_The_Voice";
    static final String LIGHT_ORB = "Nakasar_Fractal_Deepstone_Light_Orb";
    static final String VENOM = "Nakasar_Fractal_Brood_Venom";
    /** Venin de la couvée : part des PV max par seconde. */
    static final float VENOM_PART = 0.015f;
    /** Un monstre tombé de plus de 4 blocs sous son point d'apparition y est ramené. */
    static final double FALL_LIMIT = 4;
    /** Un joueur à moins de cette distance de la salle du cristal y est arrivé. */
    static final double HALL_REACH = 15;

    enum Phase { DESCENT, VAULT, MINOTAUR, PIT, LIFT, VOICE, DONE }

    static final class State {
        boolean started;
        Phase phase = Phase.DESCENT;
        Ref<EntityStore> torin;
        Ref<EntityStore> kay;
        final List<Ref<EntityStore>> foes = new ArrayList<>();
        final Map<Ref<EntityStore>, Vector3d> homes = new HashMap<>();
        final RuneGrid grid = new RuneGrid();
        final Sentinel sentinel = new Sentinel();
        final EastPath east = new EastPath();
        final DeepLight light = new DeepLight();
        final Minotaur minotaur = new Minotaur();
        final AbyssPit pit = new AbyssPit();
        final Lift lift = new Lift();
        final Voice voice = new Voice();
        /** Orbes de lumière : posée (après le boss), portée (par qui), déposée au cristal. */
        final boolean[] orbReady = new boolean[2];
        final UUID[] carrier = new UUID[2];
        final boolean[] deposited = new boolean[2];
        /** Dernier envoi de chaque message (joueur:clé). */
        final Map<String, Long> throttle = new HashMap<>();
        boolean ticking;
        float lightCheck;

        Ref<EntityStore> foe(World world, Store<EntityStore> store, String role, Vector3d where, boolean loot) {
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, role, where, (float) (Math.random() * 2 * Math.PI - Math.PI));
            if (ref != null) {
                if (!loot) {
                    Spawns.noLoot(store, ref);
                }
                foes.add(ref);
                homes.put(ref, new Vector3d(where));
                Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", where, 0.6f);
            }
            return ref;
        }

        Ref<EntityStore> boss(World world, Store<EntityStore> store, String role, Vector3d where, Vector3d face) {
            Ref<EntityStore> ref = Spawns.spawnBoss(world, store, role, where, Telegraphs.yawToward(where, face));
            if (ref != null) {
                foes.add(ref);
                homes.put(ref, new Vector3d(where));
            }
            return ref;
        }
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** La Lumière de Deldrimor et les effets de la Roche des Abysses se perdent hors de la fractale. */
    public static FractalItemsSystem.Rule itemsRule() {
        return new FractalItemsSystem.Rule(FRACTAL, Set.of(LIGHT), "Nakasar_Fractal_Captured",
                "Nakasar_Fractal_Shadow_Touch", VENOM, "Nakasar_Fractal_Siphoned", "Nakasar_Fractal_Shadow_Bomb",
                Voice.UPDRAFT + 1, Voice.UPDRAFT + 2, Voice.UPDRAFT + 3, Voice.UPDRAFT + 4, "Nakasar_Fractal_Chilled",
                "Nakasar_Fractal_Dazed", "Nakasar_Fractal_Crippled");
    }

    /** Barres de boss (défiance des esprits du vent et de la Voix). */
    public static void register() {
        for (String role : new String[]{SENTINEL, QUEEN, MINOTAUR, VOICE, BLOODSUCKER, WIND_SPRITE}) {
            BossBarSystem.register(role);
        }
        BossBarSystem.label(WIND_SPRITE, Defiance::label);
        BossBarSystem.label(VOICE, Defiance::label);
        Instabilities.exempt(TORIN, KAY);
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
            // Esprits du vent, plate-forme, flammes : à chaque tick, pas seulement 4 fois par seconde.
            TelegraphSystem.start(world, new TelegraphSystem.Task() {
                @Override
                public boolean step(World w, Store<EntityStore> s, long now) {
                    if (states.get(w) != st) {
                        return true;
                    }
                    st.sentinel.tick(w, s, st, now);
                    st.voice.tick(w, s, st, now);
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
        st.foes.removeIf(ref -> !ref.isValid());
        st.homes.keySet().retainAll(st.foes);
        for (Map.Entry<Ref<EntityStore>, Vector3d> e : st.homes.entrySet()) {
            String role = Spawns.role(store, e.getKey());
            Vector3d at = Telegraphs.position(store, e.getKey());
            if (FLAME.equals(role) || BLOODSUCKER.equals(role) || at == null || at.y() >= e.getValue().y() - FALL_LIMIT) {
                continue;
            }
            // tombé : retour au-dessus d'un sol qui existe encore (sa dalle a pu tomber)
            e.setValue(ground(world, e.getValue()));
            Leash.keepAbove(store, e.getKey(), e.getValue(), FALL_LIMIT);
        }
        venom(store, players, dt);
        st.light.step(world, store, st, players, dt);
        if (st.phase.ordinal() >= Phase.MINOTAUR.ordinal()) {
            st.lightCheck += dt;
            if (st.lightCheck >= 2f) {
                st.lightCheck = 0f;
                for (PlayerRef p : players) {
                    if (Carried.count(store, p.getReference(), LIGHT) == 0) {
                        Carried.give(store, p.getReference(), LIGHT);
                    }
                }
            }
        }
        switch (st.phase) {
            case DESCENT -> {
                if (anyNear(store, players, DeepstoneLayout.HALL_CENTER, HALL_REACH)) {
                    Gates.checkpoint(world, DeepstoneLayout.RETURN, MESSAGES + "checkpoint");
                    move(store, st.torin, Spawns.point(DeepstoneLayout.TORIN_HALL), Spawns.point(DeepstoneLayout.HALL_CENTER));
                    move(store, st.kay, Spawns.point(DeepstoneLayout.KAY_HALL), Spawns.point(DeepstoneLayout.HALL_CENTER));
                    Spawns.tellAll(world, Message.translation(MESSAGES + "hall.enter"));
                    st.phase = Phase.VAULT;
                }
            }
            case VAULT -> {
                st.grid.step(world, store, st, players, dt);
                st.sentinel.step(world, store, st, players, dt);
                st.east.step(world, store, st, players, dt);
                if (st.deposited[0] && st.deposited[1]) {
                    for (PlayerRef p : players) {
                        Carried.give(store, p.getReference(), LIGHT);
                    }
                    Spawns.tellAll(world, Message.translation(MESSAGES + "crystal.full"));
                    st.phase = Phase.MINOTAUR;
                }
            }
            case MINOTAUR -> {
                if (st.minotaur.step(world, store, st, players, dt)) {
                    Gates.open(world, store, DeepstoneLayout.NORTH_GATE, MESSAGES + "minotaur.victory");
                    st.pit.begin(world, store, st);
                    st.phase = Phase.PIT;
                }
            }
            case PIT -> {
                if (st.pit.step(world, store, st, players, dt)) {
                    st.lift.begin(world, store);
                    st.phase = Phase.LIFT;
                }
            }
            case LIFT -> {
                if (st.lift.step(world, store, st, players, dt)) {
                    st.phase = Phase.VOICE;
                }
            }
            case VOICE -> {
                if (st.voice.step(world, store, st, players, dt)) {
                    st.phase = Phase.DONE;
                    Gates.victory(world, DeepstoneLayout.REWARD, DeepstoneLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "voice.victory");
                }
            }
            default -> {
            }
        }
    }

    /** Torin et Kay au sommet, chauves-souris le long de la descente (avec butin : elles ne reviennent pas). */
    private static void start(World world, Store<EntityStore> store, State st) {
        st.started = true;
        Vector3d spawn = Spawns.point(DeepstoneLayout.SPAWN);
        st.torin = Spawns.spawn(store, TORIN, Spawns.point(DeepstoneLayout.TORIN),
                Telegraphs.yawToward(Spawns.point(DeepstoneLayout.TORIN), spawn));
        st.kay = Spawns.spawn(store, KAY, Spawns.point(DeepstoneLayout.KAY),
                Telegraphs.yawToward(Spawns.point(DeepstoneLayout.KAY), spawn));
        protect(store, st.torin);
        protect(store, st.kay);
        for (double[] at : DeepstoneLayout.BATS) {
            st.foe(world, store, BAT, Spawns.point(at), true);
        }
        Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
        Spawns.tellAll(world, Message.translation(MESSAGES + "kay"));
    }

    /** Venin de la couvée (estocades de la Reine) : la vie s'en va tant qu'il dure. */
    private static void venom(Store<EntityStore> store, List<PlayerRef> players, float dt) {
        for (PlayerRef p : players) {
            if (Hurt.has(store, p.getReference(), VENOM)) {
                Hurt.percent(store, p.getReference(), VENOM_PART * dt, CAUSE);
            }
        }
    }

    // --- blocs utilisés, objets, coups, morts --------------------------------------------------------------------

    @Override
    public void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                    int x, int y, int z) {
        State st = state(world);
        switch (action) {
            case "Deepstone_Orb" -> takeOrb(world, store, st, player, x, y, z);
            case "Deepstone_Crystal" -> crystal(world, store, st, player);
            case "Deepstone_Lift_Rune" -> st.lift.rune(world, store, st, player);
            default -> {
            }
        }
    }

    /** Clic droit avec la Lumière de Deldrimor ({@link DeepstoneActionInteraction}). */
    void action(World world, Store<EntityStore> store, PlayerRef player, String action) {
        if ("Light".equals(action)) {
            State st = state(world);
            st.light.use(world, store, st, player);
        }
    }

    /** Un boss vaincu laisse son orbe (0 : ouest, 1 : est). */
    static void dropOrb(World world, State st, int wing) {
        int[] at = wing == 0 ? DeepstoneLayout.WEST_ORB : DeepstoneLayout.EAST_ORB;
        WorldBlocks.set(world.getChunkStore(), at[0], at[1], at[2], LIGHT_ORB, 0);
        st.orbReady[wing] = true;
    }

    /** L'orbe d'un boss : on la prend, retour au cristal. */
    private static void takeOrb(World world, Store<EntityStore> store, State st, PlayerRef player, int x, int y, int z) {
        for (int wing = 0; wing < 2; wing++) {
            int[] at = wing == 0 ? DeepstoneLayout.WEST_ORB : DeepstoneLayout.EAST_ORB;
            if (at[0] != x || at[1] != y || at[2] != z || !st.orbReady[wing]) {
                continue;
            }
            st.orbReady[wing] = false;
            st.carrier[wing] = player.getUuid();
            WorldBlocks.clear(world.getChunkStore(), x, y, z);
            Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Flash", new Vector3d(x + 0.5, y, z + 0.5), 1f);
            Moves.teleport(store, player.getReference(), Spawns.point(DeepstoneLayout.RETURN));
            Spawns.tellAll(world, Message.translation(MESSAGES + "orb.taken").param("name", player.getUsername()));
            player.sendMessage(Message.translation(MESSAGES + "orb.carry"));
            return;
        }
    }

    /** Le cristal : le porteur d'une orbe l'y dépose (n'importe qui, si le porteur n'est plus là). */
    private static void crystal(World world, Store<EntityStore> store, State st, PlayerRef player) {
        List<UUID> here = new ArrayList<>();
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            here.add(p.getUuid());
        }
        boolean any = false;
        for (int wing = 0; wing < 2; wing++) {
            UUID c = st.carrier[wing];
            if (c != null && !st.deposited[wing] && (c.equals(player.getUuid()) || !here.contains(c))) {
                st.deposited[wing] = true;
                st.carrier[wing] = null;
                any = true;
            }
        }
        int[] at = DeepstoneLayout.CRYSTAL;
        Vector3d c = new Vector3d(at[0] + 0.5, at[1], at[2] + 0.5);
        if (!any) {
            tell(st, player, (st.deposited[0] || st.deposited[1]) && !(st.deposited[0] && st.deposited[1])
                    ? "crystal.one" : "crystal.empty");
            return;
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Flash", c, 1.5f);
        Telegraphs.sound(store, "SFX_Crystal_Break", c);
        if (!(st.deposited[0] && st.deposited[1])) {
            Spawns.tellAll(world, Message.translation(MESSAGES + "crystal.one"));
        }
    }

    @Override
    public boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        State st = state(world);
        return switch (role) {
            case MINOTAUR -> !st.minotaur.vulnerable();
            case QUEEN -> st.east.queenShielded();
            case VOICE -> st.voice.shielded();
            default -> false;
        };
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        if (victimRole == null) {
            return;
        }
        State st = state(world);
        switch (victimRole) {
            case TORIN, KAY -> damage.setCancelled(true);
            case MINOTAUR -> {
                if (!st.minotaur.vulnerable()) {
                    damage.setCancelled(true);
                }
            }
            case QUEEN -> {
                if (st.east.queenShielded()) {
                    damage.setCancelled(true);
                }
            }
            case VOICE -> {
                if (st.voice.shielded()) {
                    damage.setCancelled(true);
                }
            }
            default -> {
            }
        }
    }

    // --- outils --------------------------------------------------------------------------------------------------

    /** Rang de la partie : 0 (niveaux 1-25) à 3 (76-100). */
    static int rank(World world) {
        return Math.min(3, (Math.max(1, FractalRuns.level(world)) - 1) / Observatory.RANK_SIZE);
    }

    private static void protect(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref != null && ref.isValid()) {
            store.ensureAndGetComponent(ref, Invulnerable.getComponentType());
        }
    }

    /** Déplace un PNJ (téléportation), tourné vers `face`. */
    static void move(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d to, Vector3d face) {
        if (ref != null && ref.isValid()) {
            store.putComponent(ref, Teleport.getComponentType(),
                    new Teleport(new Vector3d(to), new Rotation3f(0f, Telegraphs.yawToward(to, face), 0f)));
        }
    }

    /** Vrai si un joueur est à moins de `radius` blocs (horizontalement, 5 blocs de haut) du point `at`. */
    static boolean anyNear(Store<EntityStore> store, List<PlayerRef> players, double[] at, double radius) {
        return !near(store, players, Spawns.point(at), radius).isEmpty();
    }

    static List<PlayerRef> near(Store<EntityStore> store, List<PlayerRef> players, Vector3d c, double radius) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && Telegraphs.horizontal(pos, c) <= radius && Math.abs(pos.y() - c.y()) < 5) {
                out.add(p);
            }
        }
        return out;
    }

    /** Vrai si le joueur est sur la rune (plaque de pression) posée en `at` (pieds). */
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
                    if (WorldBlocks.solid(chunks, bx + dx, by, bz + dz) && !WorldBlocks.solid(chunks, bx + dx, by + 1, bz + dz)) {
                        return new Vector3d(bx + dx + 0.5, home.y(), bz + dz + 0.5);
                    }
                }
            }
        }
        return home;
    }

    static boolean onRune(Store<EntityStore> store, PlayerRef p, double[] at) {
        Vector3d pos = Telegraphs.position(store, p.getReference());
        return pos != null && Math.abs(pos.x() - at[0]) <= 0.5 + Telegraphs.BODY
                && Math.abs(pos.z() - at[2]) <= 0.5 + Telegraphs.BODY && pos.y() >= at[1] - 0.5 && pos.y() <= at[1] + 2;
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
