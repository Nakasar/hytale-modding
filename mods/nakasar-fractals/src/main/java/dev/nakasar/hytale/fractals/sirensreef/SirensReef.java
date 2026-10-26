package dev.nakasar.hytale.fractals.sirensreef;

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
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
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
 * Le Récif de la Sirène (saison 2), d'après GW2 : l'île du trésor maudit d'Arabella Crowe.
 * <ol>
 *   <li>la plage du naufrage : le capitaine Strohm et le mousse Weyandt, les camps de sauriens du rivage et des raptors
 *   de poche ;</li>
 *   <li>la clairière : Tête-de-pierre ({@link Stonehead}) ; à 25 % il brise les rochers et fuit dans le ravin, où il
 *   saute sur une mine ;</li>
 *   <li>le ravin miné ({@link ReefMines}) : le canon des ombres de la corniche ({@link ShadowCannon}) fait sauter les mines
 *   et abat la palissade du bout ;</li>
 *   <li>le fort englouti : une vague de fantômes, puis Black Peter la Mèche ({@link BlackPeter}) ;</li>
 *   <li>le sentier de jungle : deux meutes de raptors ; vidées, la grande tête de pierre ouvre la bouche ;</li>
 *   <li>le labyrinthe : trois trésors maudits à rapporter au coffre de la sirène ({@link CursedTreasure}) ;</li>
 *   <li>la crique et le Fierté du Kraken ({@link ReefShip}) : deux trésors, Mad Jack Squall, le second Calix, la défense
 *   du navire, puis la capitaine Arabella Crowe.</li>
 * </ol>
 * Tout ce que pose le Java (mines, PNJ, objets) est non sauvegardé : une instance rechargée repart du départ.
 */
public final class SirensReef implements FractalStage {

    public static final String FRACTAL = "SirensReef";
    static final String MESSAGES = "nakasar_fractals_sirens_reef.";
    static final String STROHM = "Nakasar_Fractal_Captain_Strohm";
    static final String WEYANDT = "Nakasar_Fractal_Cabin_Boy_Weyandt";
    static final String RAPTOR = "Nakasar_Fractal_Pocket_Raptor";
    static final String STONEHEAD = "Nakasar_Fractal_Stonehead";
    static final String GHOST = "Nakasar_Fractal_Ghost_Pirate";
    static final String MARKSMAN = "Nakasar_Fractal_Phantom_Marksman";
    static final String SWINDLER = "Nakasar_Fractal_Ghostly_Swindler";
    static final String PETER = "Nakasar_Fractal_Blasting_Black_Peter";
    static final String JACK = "Nakasar_Fractal_Mad_Jack_Squall";
    static final String CALIX = "Nakasar_Fractal_First_Mate_Calix";
    static final String ARABELLA = "Nakasar_Fractal_Arabella_Crowe";
    static final String REEF_CAUSE = "Nakasar_Fractal_Reef";
    static final String MINE = "Nakasar_Fractal_Reef_Mine";
    static final String TREASURE = "Nakasar_Fractal_Cursed_Treasure";
    /** Raptors de poche errant entre les camps. */
    static final int ROAMING_RAPTORS = 3;
    /** Raptors par clairière du sentier de jungle. */
    static final int GLADE_RAPTORS = 4;
    /** Raptors des clairières encore en vie quand on arrive à la place : rappelés s'ils sont à plus de CALL_NEAR blocs. */
    static final float CALL_EVERY = 10f;
    static final double CALL_NEAR = 12;
    /** Un joueur à moins de cette distance du centre d'un lieu (fort, crique, place de la tête) y est arrivé. */
    static final double ARRIVE = 10;
    /** Un monstre tombé de plus de 3 blocs sous son point d'apparition y est ramené (comme au Ressac silencieux). */
    static final double FALL_LIMIT = 3;

    enum Phase { BEACH, STONEHEAD, RAVINE, FORT, PETER, JUNGLE, MAZE, COVE, SHIP, DONE }

    static final class State {
        boolean started;
        Phase phase = Phase.BEACH;
        Ref<EntityStore> strohm;
        Ref<EntityStore> weyandt;
        /** Tout ce que le déroulé a fait apparaître (cible des boulets du canon). */
        final List<Ref<EntityStore>> foes = new ArrayList<>();
        /** Ennemis qui bloquent la suite (fantômes du fort, meutes du sentier). */
        final List<Ref<EntityStore>> blockers = new ArrayList<>();
        final Map<Ref<EntityStore>, Vector3d> homes = new HashMap<>();
        final ReefMines mines = new ReefMines();
        final ShadowCannon cannons = new ShadowCannon();
        final Stonehead stonehead = new Stonehead();
        final BlackPeter peter = new BlackPeter();
        final CursedTreasure treasure = new CursedTreasure();
        final ReefShip ship = new ReefShip();
        boolean fortWave;
        long callRaptors;
        boolean wall2Open;
        boolean ticking;
        final Map<UUID, Long> throttle = new HashMap<>();

        Ref<EntityStore> foe(World world, Store<EntityStore> store, String role, double[] at, boolean loot) {
            Vector3d where = Spawns.point(at);
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, role, where,
                    (float) (Math.random() * 2 * Math.PI - Math.PI));
            if (ref != null) {
                if (!loot) {
                    Spawns.noLoot(store, ref);
                }
                foes.add(ref);
                homes.put(ref, where);
            }
            return ref;
        }

        Ref<EntityStore> boss(World world, Store<EntityStore> store, String role, double[] at, double[] face) {
            Vector3d where = Spawns.point(at);
            Ref<EntityStore> ref = Spawns.spawnBoss(world, store, role, where, Telegraphs.yawToward(where, Spawns.point(face)));
            if (ref != null) {
                foes.add(ref);
            }
            return ref;
        }
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Le trésor maudit, les boulets du canon et les effets du Récif se perdent hors de la fractale. */
    public static FractalItemsSystem.Rule itemsRule() {
        return new FractalItemsSystem.Rule(FRACTAL, Set.of(TREASURE, ShadowCannon.ITEMS[0], ShadowCannon.ITEMS[1],
                ShadowCannon.ITEMS[2]), "Nakasar_Fractal_Cursed_1", "Nakasar_Fractal_Cursed_2",
                "Nakasar_Fractal_Cursed_3", CursedTreasure.RELIEF, "Nakasar_Fractal_Fetid_Fog", "Nakasar_Fractal_Piranhas",
                "Nakasar_Fractal_Grim_Lagoon", "Nakasar_Fractal_Cinders", "Nakasar_Fractal_Chilled", "Nakasar_Fractal_Dazed");
    }

    /** Barres de boss ; défiance de Black Peter ; le trésor maudit se ramasse accroupi. */
    public static void register() {
        for (String role : new String[]{STONEHEAD, PETER, JACK, CALIX, ARABELLA}) {
            BossBarSystem.register(role);
        }
        BossBarSystem.label(PETER, Defiance::label);
        Instabilities.exempt(STROHM);
        Instabilities.exempt(WEYANDT);
        CursedTreasure.register();
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
            // Orbes du labyrinthe et course de Tête-de-pierre : à chaque tick, pas seulement 4 fois par seconde.
            TelegraphSystem.start(world, new TelegraphSystem.Task() {
                @Override
                public boolean step(World w, Store<EntityStore> s, long now) {
                    if (states.get(w) != st) {
                        return true;
                    }
                    st.treasure.tick(w, s, st, now);
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
        st.blockers.removeIf(ref -> !Spawns.alive(store, ref));
        st.homes.keySet().retainAll(st.foes);
        for (Map.Entry<Ref<EntityStore>, Vector3d> e : st.homes.entrySet()) {
            Leash.keepAbove(store, e.getKey(), e.getValue(), FALL_LIMIT);
        }
        long now = System.nanoTime();
        st.mines.step(world, store, players, now);
        st.cannons.step(world, store, st);
        st.treasure.step(world, store, st, players, dt);
        switch (st.phase) {
            case BEACH -> beach(world, store, st, players);
            case STONEHEAD -> stonehead(world, store, st, players, dt);
            case RAVINE -> {
                if (st.wall2Open) {
                    st.phase = Phase.FORT;
                }
            }
            case FORT -> fort(world, store, st, players);
            case PETER -> peter(world, store, st, players, dt);
            case JUNGLE -> jungle(world, store, st, players);
            case MAZE -> {
                if (st.treasure.complete()) {
                    st.treasure.end(world, store);
                    Gates.open(world, store, SirensReefLayout.MAZE_EXIT, MESSAGES + "maze.open");
                    st.phase = Phase.COVE;
                }
            }
            case COVE -> {
                if (anyNear(store, players, SirensReefLayout.COVE, ARRIVE)) {
                    Gates.checkpoint(world, SirensReefLayout.COVE, MESSAGES + "checkpoint");
                    Spawns.tellAll(world, Message.translation(MESSAGES + "cove.enter"));
                    st.ship.start(world, store, st);
                    st.phase = Phase.SHIP;
                }
            }
            case SHIP -> {
                if (st.ship.step(world, store, st, players, dt)) {
                    st.phase = Phase.DONE;
                    st.cannons.clear(world, store);
                    Gates.victory(world, SirensReefLayout.REWARD, SirensReefLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "ship.victory");
                }
            }
            default -> {
            }
        }
    }

    /** Strohm et Weyandt sur la plage, camps de sauriens et raptors errants (avec butin : ils ne reviennent pas). */
    private static void start(World world, Store<EntityStore> store, State st) {
        st.started = true;
        st.strohm = Spawns.spawn(store, STROHM, Spawns.point(SirensReefLayout.STROHM),
                Telegraphs.yawToward(Spawns.point(SirensReefLayout.STROHM), Spawns.point(SirensReefLayout.SPAWN)));
        st.weyandt = Spawns.spawn(store, WEYANDT, Spawns.point(SirensReefLayout.WEYANDT),
                Telegraphs.yawToward(Spawns.point(SirensReefLayout.WEYANDT), Spawns.point(SirensReefLayout.SPAWN)));
        protect(store, st.strohm);
        protect(store, st.weyandt);
        for (int i = 0; i < SirensReefLayout.CAMP_ROLES.length; i++) {
            String[] roles = SirensReefLayout.CAMP_ROLES[i];
            for (int j = 0; j < roles.length; j++) {
                st.foe(world, store, roles[j], SirensReefLayout.CAMP_SPOTS[i][j % SirensReefLayout.CAMP_SPOTS[i].length], true);
            }
        }
        for (int i = 0; i < ROAMING_RAPTORS; i++) {
            st.foe(world, store, RAPTOR, SirensReefLayout.RAPTOR_ROAM, true);
        }
        Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
        Spawns.tellAll(world, Message.translation(MESSAGES + "weyandt"));
    }

    private static void beach(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        if (anyNear(store, players, SirensReefLayout.CLEARING, SirensReefLayout.CLEARING_RADIUS)) {
            if (st.stonehead.engage(world, store, st)) {
                Gates.checkpoint(world, SirensReefLayout.CLEARING, MESSAGES + "checkpoint");
                st.phase = Phase.STONEHEAD;
            }
        }
    }

    private static void stonehead(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        switch (st.stonehead.step(world, store, st, players, dt)) {
            case DONE -> st.phase = Phase.RAVINE;
            case RESET -> st.phase = Phase.BEACH;
            default -> {
            }
        }
    }

    /** Arrivée au fort : point de retour et vague de fantômes ; vidée, Black Peter. */
    private static void fort(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        if (!st.fortWave) {
            if (!anyNear(store, players, SirensReefLayout.FORT, SirensReefLayout.FORT_RADIUS)) {
                return;
            }
            st.fortWave = true;
            Gates.checkpoint(world, SirensReefLayout.FORT, MESSAGES + "checkpoint");
            double[][] spots = SirensReefLayout.FORT_GHOSTS;
            int extra = (FractalRuns.partySize(world) - 1) / 2;
            for (int i = 0; i < spots.length + extra; i++) {
                String role = i % 4 == 3 ? MARKSMAN : GHOST;
                Ref<EntityStore> ref = st.foe(world, store, role, spots[i % spots.length], true);
                if (ref != null) {
                    st.blockers.add(ref);
                    Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", Spawns.point(spots[i % spots.length]), 1f);
                }
            }
            Spawns.tellAll(world, Message.translation(MESSAGES + "fort.ghosts"));
            return;
        }
        if (st.blockers.isEmpty() && st.peter.engage(world, store, st)) {
            st.phase = Phase.PETER;
        }
    }

    private static void peter(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        if (!st.peter.engaged()) {
            if (anyNear(store, players, SirensReefLayout.FORT, SirensReefLayout.FORT_RADIUS)) {
                st.peter.engage(world, store, st);
            }
            return;
        }
        if (st.peter.step(world, store, st, players, dt) == BlackPeter.Outcome.WON) {
            Gates.open(world, store, SirensReefLayout.FORT_GATE, MESSAGES + "peter.victory");
            for (double[][] glade : SirensReefLayout.GLADE_SPOTS) {
                for (int i = 0; i < GLADE_RAPTORS; i++) {
                    Ref<EntityStore> ref = st.foe(world, store, RAPTOR, glade[i % glade.length], true);
                    if (ref != null) {
                        st.blockers.add(ref);
                    }
                }
            }
            st.phase = Phase.JUNGLE;
        }
    }

    /** Meutes du sentier vidées et un joueur sur la place : la bouche s'ouvre sur le labyrinthe. */
    private static void jungle(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        if (!anyNear(store, players, SirensReefLayout.PLAZA, ARRIVE)) {
            return;
        }
        if (!st.blockers.isEmpty()) {
            callRaptors(world, store, st);
            return;
        }
        Gates.open(world, store, SirensReefLayout.MOUTH, MESSAGES + "head.open");
        Gates.checkpoint(world, SirensReefLayout.PLAZA, MESSAGES + "checkpoint");
        st.treasure.begin(world, store, st, SirensReefLayout.TREASURES, SirensReefLayout.MAZE_CHEST, true);
        int extra = (FractalRuns.partySize(world) - 1) / 2;
        double[][] spots = SirensReefLayout.MAZE_GHOSTS;
        for (int i = 0; i < spots.length + extra; i++) {
            String role = i % 2 == 1 ? SWINDLER : GHOST;
            Ref<EntityStore> ref = st.foe(world, store, role, spots[i % spots.length], true);
            if (ref != null && SWINDLER.equals(role)) {
                st.treasure.swindler(ref);
            }
        }
        Spawns.tellAll(world, Message.translation(MESSAGES + "treasure.intro"));
        st.phase = Phase.MAZE;
    }

    /**
     * Un joueur est sur la place et des raptors des clairières vivent encore (laissés derrière, coincés dans le décor) :
     * ceux qui sont loin de la place y accourent, toutes les {@value #CALL_EVERY} s, pour qu'on puisse les abattre.
     */
    private static void callRaptors(World world, Store<EntityStore> store, State st) {
        long now = System.nanoTime();
        if (now < st.callRaptors) {
            return;
        }
        st.callRaptors = now + Telegraphs.seconds(CALL_EVERY);
        Vector3d plaza = Spawns.point(SirensReefLayout.PLAZA);
        boolean called = false;
        for (Ref<EntityStore> ref : st.blockers) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at != null && Telegraphs.horizontal(at, plaza) <= CALL_NEAR && Math.abs(at.y() - plaza.y()) < 4) {
                continue;
            }
            double a = Math.random() * 2 * Math.PI;
            Vector3d to = new Vector3d(plaza).add(Math.cos(a) * 5, 0, Math.sin(a) * 5);
            store.putComponent(ref, Teleport.getComponentType(), new Teleport(to, new Rotation3f(0f, Telegraphs.yawToward(to, plaza), 0f)));
            st.homes.put(ref, to);
            Telegraphs.particle(store, "Nakasar_Fractal_Stonehead_Roar", to, 0.4f);
            called = true;
        }
        if (called) {
            Spawns.tellAll(world, Message.translation(MESSAGES + "head.last"));
        }
    }

    // --- blocs utilisés, objets, coups, morts --------------------------------------------------------------------

    @Override
    public void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                    int x, int y, int z) {
        if ("SirensReef_Cannon".equals(action)) {
            State st = state(world);
            st.cannons.use(world, store, st, player, x, y, z);
        }
    }

    /** Clic droit avec un objet du Récif ({@link ReefActionInteraction}). */
    void action(World world, Store<EntityStore> store, PlayerRef player, String action) {
        State st = state(world);
        if ("Throw".equals(action)) {
            st.treasure.toss(world, store, st, player);
        } else {
            st.cannons.fire(world, store, st, player, action);
        }
    }

    /**
     * Un boulet tombe en `at` : les ennemis dans `radius` prennent `damage` (Mitraille : étourdis, Glace : gelés ; les
     * boss n'en sont pas gelés, leur défiance prend `defiance` points), les mines sautent sans blesser personne, la
     * palissade du ravin s'abat.
     */
    static void impact(World world, Store<EntityStore> store, State st, Vector3d at, double radius, float damage,
                       String freezeEffect, float freezeSeconds, int defiance) {
        for (Ref<EntityStore> ref : List.copyOf(st.foes)) {
            Vector3d p = Telegraphs.position(store, ref);
            if (p == null || !Telegraphs.inCircle(p, at, radius)) {
                continue;
            }
            Hurt.amount(store, ref, damage, REEF_CAUSE);
            if (isBoss(store, ref)) {
                Defiance.hit(world, store, ref, defiance);
            } else if (freezeEffect != null) {
                BossStun.stun(world, store, ref, freezeSeconds, freezeEffect);
            }
        }
        if (st.mines.shot(world, store, at, radius) > 0) {
            Spawns.tellAll(world, Message.translation(MESSAGES + "mine.cleared"));
        }
        // La palissade ne tombe qu'une fois Tête-de-pierre vaincu (on peut sauter de la corniche dans le ravin).
        if (!st.wall2Open && st.phase.ordinal() >= Phase.RAVINE.ordinal()
                && near(at, SirensReefLayout.WALL2, radius + ShadowCannon.WALL_REACH)) {
            st.wall2Open = true;
            Gates.open(world, store, SirensReefLayout.WALL2, MESSAGES + "wall2.open");
        }
    }

    private static boolean isBoss(Store<EntityStore> store, Ref<EntityStore> ref) {
        String role = Spawns.role(store, ref);
        return STONEHEAD.equals(role) || PETER.equals(role) || JACK.equals(role) || CALIX.equals(role)
                || ARABELLA.equals(role);
    }

    /** Vrai si un bloc de `cells` est à moins de `reach` blocs (horizontalement) de `at`. */
    private static boolean near(Vector3d at, int[][] cells, double reach) {
        for (int[] c : cells) {
            double dx = c[0] + 0.5 - at.x();
            double dz = c[2] + 0.5 - at.z();
            if (dx * dx + dz * dz <= reach * reach && Math.abs(c[1] - at.y()) < 6) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        if (victimRole == null) {
            return;
        }
        if (STROHM.equals(victimRole) || WEYANDT.equals(victimRole)) {
            damage.setCancelled(true);
            return;
        }
        State st = state(world);
        if (STONEHEAD.equals(victimRole)) {
            st.stonehead.filter(buffer, victim, damage);
        }
        if (!damage.isCancelled()) {
            st.ship.filter(buffer, victim, damage);
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        switch (role) {
            case PETER -> st.peter.down();
            case GHOST, MARKSMAN, SWINDLER -> st.ship.defenderDown(world);
            default -> {
            }
        }
    }

    // --- outils --------------------------------------------------------------------------------------------------

    private static void protect(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref != null && ref.isValid()) {
            store.ensureAndGetComponent(ref, Invulnerable.getComponentType());
        }
    }

    /** Vrai si un joueur est à moins de `radius` blocs (horizontalement, 4 blocs de haut) du point `at`. */
    static boolean anyNear(Store<EntityStore> store, List<PlayerRef> players, double[] at, double radius) {
        Vector3d c = Spawns.point(at);
        for (PlayerRef p : players) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && Telegraphs.horizontal(pos, c) <= radius && Math.abs(pos.y() - c.y()) < 4) {
                return true;
            }
        }
        return false;
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
