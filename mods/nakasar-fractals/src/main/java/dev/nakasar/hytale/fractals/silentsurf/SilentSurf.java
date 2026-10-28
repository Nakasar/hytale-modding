package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.FractalItemsSystem;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
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
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Le Ressac silencieux (saison 2), d'après GW2 : une fractale de parcours sous la mer de jade pétrifiée, avec
 * l'équipement de prospection ({@link SurveyGear}) et les trajets guidés ({@link Rides}).
 * <ol>
 *   <li>points de contrôle 1 à 4 : un cercle blanc ; la moitié du groupe dedans l'active (point de retour, Thess y
 *   vient) et réveille ses ennemis (chauves-souris ; la Mère de couvée et ses araignées ; les nagas ; les marins
 *   luxons puis le second Dolus, {@link Dolus}). Les engins de la section suivante ne partent qu'une fois le camp
 *   vidé ;</li>
 *   <li>la Garde de Thess : une chute qui retirerait plus de {@value #WARD_PART} des PV, ou le gouffre (filet
 *   anti-chute), ramène au dernier point de contrôle ;</li>
 *   <li>l'arène : Kanaxai s'éveille quand on approche de son centre ({@link Kanaxai}) ; Thess tombe sous sa faux.</li>
 * </ol>
 * Les provisions abandonnées de chaque point de contrôle rechargent l'équipement. Tout ce que pose le Java est non
 * sauvegardé : une instance rechargée repart du départ.
 */
public final class SilentSurf implements FractalStage {

    public static final String FRACTAL = "SilentSurf";
    static final String MESSAGES = "nakasar_fractals_silent_surf.";
    static final String THESS = "Nakasar_Fractal_Thess";
    static final String BROOD_MOTHER = "Nakasar_Fractal_Brood_Mother";
    static final String SPIDERLING = "Nakasar_Fractal_Cave_Spiderling";
    static final String WAVECALLER = "Nakasar_Fractal_Naga_Wavecaller";
    static final String DOLUS = "Nakasar_Fractal_First_Mate_Dolus";
    static final String KANAXAI = "Nakasar_Fractal_Kanaxai";
    static final String[] ASPECT_KINDS = {"Death", "Exposure", "Fear", "Lethargy", "Torment"};
    static final String[] ASPECTS = {"Nakasar_Fractal_Aspect_Death", "Nakasar_Fractal_Aspect_Exposure",
            "Nakasar_Fractal_Aspect_Fear", "Nakasar_Fractal_Aspect_Lethargy", "Nakasar_Fractal_Aspect_Torment"};
    static final String BOUNCE_CAP = "Nakasar_Fractal_Bounce_Cap";
    static final String TORMENT_CAUSE = "Nakasar_Fractal_Torment";
    static final String WARD_EFFECT = "Nakasar_Fractal_Thess_Ward";
    static final float WARD_PART = 0.35f;
    static final float TORMENT_PART = 0.01f;
    static final float BROOD_EVERY = 14f;
    static final int BROOD_MAX = 8;
    static final double ENGAGE_RADIUS = 9;
    /**
     * Un monstre tombé de plus de {@value #FALL_LIMIT} blocs sous son point d'apparition y est ramené (Kevin,
     * 25 octobre 2026 : les monstres ne tombent pas des plates-formes ; un monstre perdu dans le gouffre bloquait le
     * point de contrôle).
     */
    static final double FALL_LIMIT = 3;

    static final class State {
        boolean started;
        int checkpoint;
        final boolean[] cleared = {true, false, false, false, false};
        int fight = -1;
        final List<Ref<EntityStore>> foes = new ArrayList<>();
        /** Point d'apparition de chaque monstre des combats ({@link #FALL_LIMIT}). */
        final Map<Ref<EntityStore>, Vector3d> homes = new HashMap<>();
        Ref<EntityStore> brood;
        float broodClock;
        Ref<EntityStore> thess;
        boolean done;
        final Rides rides = new Rides();
        final SurveyGear gear = new SurveyGear();
        final Dolus dolus = new Dolus();
        final Kanaxai kanaxai = new Kanaxai();
        final Set<UUID> geared = new HashSet<>();
        final Map<UUID, Long> safeUntil = new HashMap<>();
        final Map<UUID, Long> throttle = new HashMap<>();
        boolean ticking;
        float wardClock;

        /** Pas de dégâts de chute pour `player` pendant `seconds` s (trajet, grappin, parachute, poudre). */
        void safe(UUID player, float seconds) {
            safeUntil.merge(player, System.nanoTime() + Telegraphs.seconds(seconds), Math::max);
        }

        boolean isSafe(UUID player) {
            Long until = safeUntil.get(player);
            return until != null && System.nanoTime() < until;
        }
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Barres de boss de la Mère de couvée, du Mande-vague, de Dolus et de Kanaxai (défiance des Ombres rassemblées). */
    /** L'équipement de prospection et les effets du Ressac (la Garde de Thess dure une heure) se perdent hors de la
     * fractale. */
    public static FractalItemsSystem.Rule itemsRule() {
        return new FractalItemsSystem.Rule(FRACTAL, Set.of(SurveyGear.ITEMS), WARD_EFFECT, "Nakasar_Fractal_Phantasmagoria",
                "Nakasar_Fractal_Torment", "Nakasar_Fractal_Parachute_Open");
    }

    public static void register() {
        for (String role : new String[]{BROOD_MOTHER, WAVECALLER, DOLUS, KANAXAI}) {
            BossBarSystem.register(role);
        }
        BossBarSystem.label(KANAXAI, Defiance::label);
        Instabilities.exempt(THESS);
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
        AspectVisibilitySystem.clearAll();
    }

    // --- pas de jeu ---------------------------------------------------------------------------------------------

    @Override
    public void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        if (!st.ticking) {
            st.ticking = true;
            TelegraphSystem.start(world, new TelegraphSystem.Task() {
                @Override
                public boolean step(World w, Store<EntityStore> s, long now) {
                    if (states.get(w) != st) {
                        return true;
                    }
                    st.rides.tick(w, s, st, now);
                    return false;
                }

                @Override
                public void abort(World w, Store<EntityStore> s) {
                    st.ticking = false;     // une erreur a coupé la tâche : on la relance au prochain pas
                }
            });
        }
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        if (players.isEmpty()) {
            if (st.kanaxai.engaged() && !st.done) {
                arena(world, store, st, players, dt);     // victoire au dernier souffle, ou remise à zéro
            }
            return;
        }
        if (!st.started) {
            st.started = true;
            st.thess = Spawns.spawn(store, THESS, Spawns.point(SilentSurfLayout.THESS[0]), 0f);
            protect(store, st.thess);
            Spawns.tellAll(world, Message.translation(MESSAGES + "intro"));
        }
        gearUp(world, store, st, players);
        ward(store, st, players, dt);
        torment(store, players, dt);
        reach(world, store, st, players);
        fight(world, store, st, dt);
        if (st.checkpoint == 4 && st.cleared[4] && !st.done) {
            arena(world, store, st, players, dt);
        }
    }

    /** L'équipement à qui ne l'a pas encore reçu (arrivée, retour dans la fractale). */
    private static void gearUp(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        Set<UUID> here = new HashSet<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            here.add(p.getUuid());
        }
        st.geared.retainAll(here);      // parti ailleurs (l'équipement lui a été retiré) : il le retrouvera au retour
        for (PlayerRef p : players) {
            if (st.geared.add(p.getUuid())) {
                SurveyGear.refill(store, p.getReference(), st.cleared[2]);
                p.sendMessage(Message.translation(MESSAGES + "gear.given"));
            }
        }
    }

    /** L'effet de la Garde de Thess, pour qu'on la voie (la Garde elle-même est dans {@link #filter}). */
    private static void ward(Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        st.wardClock -= dt;
        if (st.wardClock > 0) {
            return;
        }
        st.wardClock = 30f;
        for (PlayerRef p : players) {
            Hurt.effect(store, p.getReference(), WARD_EFFECT, 3600f);
        }
    }

    /** Tourment : une part des PV chaque seconde, doublée quand on bouge. */
    private static void torment(Store<EntityStore> store, List<PlayerRef> players, float dt) {
        for (PlayerRef p : players) {
            Ref<EntityStore> ref = p.getReference();
            if (Hurt.has(store, ref, "Nakasar_Fractal_Torment")) {
                Hurt.percent(store, ref, TORMENT_PART * dt * (Moves.moving(store, ref) ? 2 : 1), TORMENT_CAUSE);
            }
        }
    }

    /** Un cercle blanc rejoint par la moitié du groupe : point de retour, Thess, ennemis du camp. */
    private static void reach(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        int next = st.checkpoint + 1;
        if (next >= SilentSurfLayout.RINGS.length || !st.cleared[st.checkpoint]) {
            return;
        }
        Vector3d c = Spawns.point(SilentSurfLayout.RINGS[next]);
        double r = SilentSurfLayout.RING_RADIUS[next] + 0.6;
        int in = 0;
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && Telegraphs.horizontal(at, c) <= r && Math.abs(at.y() - c.y()) < 3) {
                in++;
            }
        }
        if (in * 2 < players.size()) {
            return;
        }
        st.checkpoint = next;
        Gates.checkpoint(world, SilentSurfLayout.RINGS[next], MESSAGES + "checkpoint");
        Telegraphs.particle(store, "Nakasar_Fractal_Checkpoint", c, (float) r);
        Spawns.tellAll(world, Message.translation(MESSAGES + "cp" + next));
        moveThess(store, st, next);
        startFight(world, store, st, next);
    }

    private static void moveThess(Store<EntityStore> store, State st, int checkpoint) {
        if (st.thess == null || !st.thess.isValid()) {
            return;
        }
        Vector3d at = Spawns.point(SilentSurfLayout.THESS[checkpoint]);
        Vector3d face = Spawns.point(SilentSurfLayout.RINGS[checkpoint]);
        store.putComponent(st.thess, Teleport.getComponentType(),
                new Teleport(at, new Rotation3f(0f, Telegraphs.yawToward(at, face), 0f)));
        Telegraphs.particle(store, "Nakasar_Fractal_Thess_Ward", at, 1f);
    }

    // --- combats des points de contrôle ---------------------------------------------------------------------------

    private static void startFight(World world, Store<EntityStore> store, State st, int k) {
        String[] roles = SilentSurfLayout.FIGHT_ROLES[k];
        if (roles.length == 0) {
            st.cleared[k] = true;
            return;
        }
        st.fight = k;
        st.foes.clear();
        st.homes.clear();
        double[][] spots = SilentSurfLayout.FIGHT_SPAWNS[k];
        Vector3d c = Spawns.point(SilentSurfLayout.RINGS[k]);
        int extra = (FractalRuns.partySize(world) - 1) / 2;
        int spot = 0;
        for (int i = 0; i < roles.length; i++) {
            int n = SilentSurfLayout.FIGHT_COUNTS[k][i] + (SilentSurfLayout.FIGHT_COUNTS[k][i] > 1 ? extra : 0);
            for (int j = 0; j < n; j++) {
                Vector3d at = Spawns.point(spots[spot++ % spots.length]);
                Ref<EntityStore> ref = Spawns.spawnFoe(world, store, roles[i], at, Telegraphs.yawToward(at, c));
                if (ref != null) {
                    st.foes.add(ref);
                    st.homes.put(ref, at);
                    if (BROOD_MOTHER.equals(roles[i])) {
                        st.brood = ref;
                        st.broodClock = 0f;
                    }
                }
            }
        }
    }

    private static void fight(World world, Store<EntityStore> store, State st, float dt) {
        int k = st.fight;
        if (k < 0) {
            return;
        }
        st.foes.removeIf(ref -> !Spawns.alive(store, ref));
        st.homes.keySet().retainAll(st.foes);
        for (Map.Entry<Ref<EntityStore>, Vector3d> e : st.homes.entrySet()) {
            Leash.keepAbove(store, e.getKey(), e.getValue(), FALL_LIMIT);
        }
        brood(world, store, st, dt);
        if (k == 4) {
            if (st.foes.isEmpty() && !st.dolus.engaged()) {
                st.dolus.engage(world, store);
            }
            if (!st.dolus.step(world, store, dt)) {
                return;
            }
        } else if (!st.foes.isEmpty()) {
            return;
        }
        st.cleared[k] = true;
        st.fight = -1;
        st.brood = null;
        String key = k == 2 || k == 3 || k == 4 ? "cp" + k + ".clear" : "fight.cleared";
        Spawns.tellAll(world, Message.translation(MESSAGES + key));
        if (k == 2) {
            for (PlayerRef p : Spawns.alivePlayers(world, store)) {
                SurveyGear.refill(store, p.getReference(), true);   // Thess donne la poudre noire
            }
        }
    }

    /** La Mère de couvée pond des araignées tant qu'elle vit. */
    private static void brood(World world, Store<EntityStore> store, State st, float dt) {
        if (st.brood == null || !Spawns.alive(store, st.brood)) {
            return;
        }
        st.broodClock += dt;
        if (st.broodClock < BROOD_EVERY || st.foes.size() >= BROOD_MAX) {
            return;
        }
        st.broodClock = 0f;
        Vector3d at = Telegraphs.position(store, st.brood);
        if (at == null) {
            return;
        }
        for (int i = 0; i < 2; i++) {
            Vector3d s = new Vector3d(at).add(i == 0 ? 1.5 : -1.5, 0, i == 0 ? -1 : 1);
            Ref<EntityStore> ref = Spawns.noLoot(store,
                    Spawns.spawnFoe(world, store, SPIDERLING, s, Telegraphs.yawToward(s, at) + (float) Math.PI));
            if (ref != null) {
                st.foes.add(ref);
                Vector3d home = st.homes.get(st.brood);
                st.homes.put(ref, home != null ? home : s);
            }
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Bounce", at, 1.2f);
    }

    // --- l'arène de Kanaxai ----------------------------------------------------------------------------------------

    private static void arena(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        if (!st.kanaxai.engaged()) {
            Vector3d c = Kanaxai.center();
            for (PlayerRef p : players) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, c) <= ENGAGE_RADIUS && Math.abs(at.y() - c.y()) < 3) {
                    engageKanaxai(world, store, st);
                    break;
                }
            }
            return;
        }
        Kanaxai.Outcome outcome = st.kanaxai.step(world, store, players, dt);
        if (outcome == Kanaxai.Outcome.WON) {
            st.done = true;
            Gates.victory(world, SilentSurfLayout.REWARD, SilentSurfLayout.END_EXIT, MESSAGES + "title.victory",
                    MESSAGES + "kanaxai.victory");
        } else if (outcome == Kanaxai.Outcome.RESET) {
            reopenArena(world, st);
        }
    }

    private static void engageKanaxai(World world, Store<EntityStore> store, State st) {
        if (!st.kanaxai.engage(world, store)) {
            return;
        }
        double[] c = SilentSurfLayout.ARENA_CENTER;
        double[] edge = {c[0], c[1], c[2] + SilentSurfLayout.ARENA_RADIUS - 4};
        Gates.checkpoint(world, edge, MESSAGES + "checkpoint");
        if (st.thess != null && st.thess.isValid()) {
            Vector3d at = Telegraphs.position(store, st.thess);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Shadows", at, 1.5f);
            }
            Spawns.remove(store, st.thess);
            st.thess = null;
            Spawns.tellAll(world, Message.translation(MESSAGES + "kanaxai.thess"));
        }
    }

    private static void reopenArena(World world, State st) {
        Gates.checkpoint(world, SilentSurfLayout.RINGS[st.checkpoint], MESSAGES + "checkpoint");
    }

    // --- blocs utilisés, équipement, coups, morts --------------------------------------------------------------------

    @Override
    public void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                    int x, int y, int z) {
        State st = state(world);
        switch (action) {
            case "SilentSurf_Supplies" -> {
                SurveyGear.refill(store, ref, st.cleared[2]);
                tell(st, player, "gear.refilled");
            }
            case "SilentSurf_Ride" -> st.rides.use(world, store, st, player, x, y, z);
            default -> {
            }
        }
    }

    void gear(World world, Store<EntityStore> store, PlayerRef player, String gear) {
        State st = state(world);
        st.gear.use(world, store, st, player, gear);
    }

    @Override
    public boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        return KANAXAI.equals(role) && state(world).kanaxai.shielded(ref);
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        State st = state(world);
        if (victimRole == null) {
            PlayerRef hit = buffer.getComponent(victim, PlayerRef.getComponentType());
            if (hit != null && Kanaxai.strayPhantasmHit(attacker, hit.getUuid())) {
                damage.setCancelled(true);
                return;
            }
            fall(world, buffer, st, victim, damage);
            return;
        }
        if (THESS.equals(victimRole)) {
            damage.setCancelled(true);
            return;
        }
        PlayerRef by = attacker == null ? null : buffer.getComponent(attacker, PlayerRef.getComponentType());
        st.kanaxai.filter(buffer, victim, victimRole, attacker, by == null ? null : by.getUuid(), damage);
    }

    /**
     * Garde de Thess : pas de dégâts de chute pendant un trajet ou un équipement ; une chute qui retirerait plus de
     * {@value #WARD_PART} des PV ramène au dernier point de contrôle, sans dégâts.
     */
    private static void fall(World world, CommandBuffer<EntityStore> buffer, State st, Ref<EntityStore> victim,
                             Damage damage) {
        int fall = DamageCause.getAssetMap().getIndexOrDefault("Fall", Integer.MIN_VALUE);
        if (damage.getDamageCauseIndex() != fall) {
            return;
        }
        PlayerRef player = buffer.getComponent(victim, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        if (st.isSafe(player.getUuid())) {
            damage.setCancelled(true);
            return;
        }
        EntityStatMap stats = buffer.getComponent(victim, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || damage.getAmount() < health.getMax() * WARD_PART) {
            return;
        }
        damage.setCancelled(true);
        world.execute(() -> {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                return;
            }
            Store<EntityStore> store = world.getEntityStore().getStore();
            st.rides.cancel(player.getUuid());
            st.gear.cancel(player.getUuid());
            Vector3d back = Gates.spawnPoint(world);    // le dernier point de contrôle (Gates.checkpoint)
            if (back == null) {
                back = Spawns.point(SilentSurfLayout.RINGS[st.checkpoint]);
            }
            Moves.teleport(store, ref, back);
            Telegraphs.particle(store, "Nakasar_Fractal_Thess_Ward", back, 1f);
            player.sendMessage(Message.translation(MESSAGES + "ward"));
        });
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        switch (role) {
            case DOLUS -> st.dolus.down();
            case KANAXAI -> st.kanaxai.down();
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

    static PlayerRef player(World world, UUID id) {
        for (PlayerRef p : world.getPlayerRefs()) {
            if (p.getUuid().equals(id)) {
                return p;
            }
        }
        return null;
    }

    static void tellPlayer(PlayerRef player, String key) {
        player.sendMessage(Message.translation(MESSAGES + key));
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
