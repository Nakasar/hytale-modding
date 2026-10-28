package dev.nakasar.hytale.fractals.volcanic;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.CrouchPickup;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.SafeLandings;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.boss.PinnedHealth;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.HitShield;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
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
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Le Volcanique (étape 6 du GDD), fidèle au déroulé de GW2 :
 * <ol>
 *   <li>{@link Step#CAMP} : le camp des grawls, {@value #CAMP_GROUPS} groupes de {@value #GROUP_SIZE} grawls qui
 *   chargent (un de plus tous les deux joueurs de plus) ; la vie du totem du rituel, fixée par le Java, ne descend qu'à
 *   chaque grawl abattu, et sa barre se voit de toute la fractale ; des rochers tombent près des joueurs ;</li>
 *   <li>{@link Step#CORRIDOR} : le couloir aux rochers ({@link Boulders}) ;</li>
 *   <li>{@link Step#CHAMPION} : le Champion chaman, ses vétérans et les captifs ({@link Champion}) ;</li>
 *   <li>{@link Step#MINE} : la mine, rails au-dessus de la lave ({@link SafeLandings}), chauves-souris ;</li>
 *   <li>{@link Step#ARENA} : le Chamane imprégné ({@link ImbuedShaman}) ; {@link Step#DONE} ensuite.</li>
 * </ol>
 * Tout ce que pose le Java est non sauvegardé : une instance rechargée repart du camp.
 */
public final class Volcanic implements FractalStage {

    public static final String FRACTAL = "Volcanic";
    static final String MESSAGES = "nakasar_fractals_volcanic.";
    static final String WARRIOR = "Nakasar_Fractal_Grawl_Warrior";
    static final String GRAWL_SHAMAN = "Nakasar_Fractal_Grawl_Shaman";
    static final String TOTEM = "Nakasar_Fractal_Grawl_Totem";
    static final String VETERAN = "Nakasar_Fractal_Grawl_Veteran";
    static final String CHAMPION = "Nakasar_Fractal_Champion_Shaman";
    static final String CAPTIVE = "Nakasar_Fractal_Captive";
    static final String BAT = "Nakasar_Fractal_Cave_Bat";
    static final String IMBUED = "Nakasar_Fractal_Imbued_Shaman";
    static final String LARVA = "Nakasar_Fractal_Ember_Larva";
    static final String STONE = "Nakasar_Fractal_Imbued_Stone";
    static final String FIRE_CAUSE = "Nakasar_Fractal_Fire";
    static final String LAVA_BURN = "Nakasar_Fractal_Lava_Burn";
    /**
     * Blocs de lave qui brûlent : la roche en fusion du Volcanique (mine, fonds des gouffres ; dans la mine, les retours de
     * saut rattrapent avant) et les cratères en fusion de l'île du Chamane. Le lac, lui, est un fluide ({@link #inLake}).
     */
    static final Set<String> LAVA_BLOCKS = Set.of("Rock_Volcanic_Cracked_Lava", "Nakasar_Fractal_Crater_Lava");
    static final float LAVA_PART = 0.30f;
    static final int LAVA_REACH = 2;

    static final int CAMP_GROUPS = 3;
    static final int GROUP_SIZE = 7;
    /** Un nouveau groupe quand il reste au plus tant de grawls du précédent, après {@value #CAMP_PAUSE} s. */
    static final int GROUP_LEFT = 2;
    static final float CAMP_PAUSE = 4f;
    static final float CAMP_ROCKS = 8f;
    static final double ROCK_RADIUS = 2;
    static final float ROCK_SECONDS = 1.6f;
    static final float ROCK_PART = 0.20f;

    enum Step { CAMP, CORRIDOR, CHAMPION, MINE, ARENA, DONE }

    static final class State {
        Step step = Step.CAMP;
        boolean started;
        final List<Ref<EntityStore>> camp = new ArrayList<>();
        volatile int kills;
        int required;
        Ref<EntityStore> totem;
        float refill;
        float rocks;
        int groups;
        int shownKills = -1;
        final Boulders boulders = new Boulders();
        final Champion champion = new Champion();
        final SafeLandings landings = new SafeLandings(VolcanicLayout.JUMP_ZONES, MESSAGES + "landing.back");
        final List<Ref<EntityStore>> bats = new ArrayList<>();
        boolean batsSpawned;
        final ImbuedShaman shaman = new ImbuedShaman();
        final Map<UUID, Long> throttle = new HashMap<>();
        long stoneMessage;
        float lavaClock;
    }

    private final Map<World, State> states = Collections.synchronizedMap(new WeakHashMap<>());

    /** Barres de boss du Volcanique, charges du Champion et rôles fixes que les instabilités laissent tranquilles. */
    public static void register() {
        BossBarSystem.everywhere(TOTEM);
        BossBarSystem.register(CHAMPION);
        BossBarSystem.label(CHAMPION, Champion::label);
        BossBarSystem.register(IMBUED);
        BossBarSystem.label(IMBUED, HitShield::label);
        Instabilities.exempt(TOTEM, CAPTIVE);
        CrouchPickup.register(new CrouchPickup.Item(STONE, FRACTAL, MESSAGES + "stone.crouch", MESSAGES + "stone.already",
                Volcanic::dropStone));
    }

    /** Fait tomber une pierre imprégnée en `at` ; elle se ramasse accroupi ({@link CrouchPickup}). */
    static void dropStone(Store<EntityStore> store, Vector3d at) {
        Carried.drop(store, STONE, at);
        Telegraphs.particle(store, "Nakasar_Fractal_Imbued_Glow", at, 1f);
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
        Champion.clearLabels();
    }

    // --- pas de jeu ---------------------------------------------------------------------------------

    @Override
    public void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        State st = state(world);
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        if (players.isEmpty()) {
            st.champion.idle(world, store, dt);
            st.shaman.idle(world, store, dt);
            return;
        }
        if (!st.started) {
            st.started = true;
            st.required = GROUP_SIZE * (CAMP_GROUPS + (FractalRuns.partySize(world) - 1) / 2);
            Spawns.tellAll(world, Message.translation(MESSAGES + "intro").param("count", st.required));
        }
        st.boulders.step(world, store, players, Boulders.anyInCorridor(store, players), dt);
        st.landings.step(world, store, players);
        lavaFloor(world, store, st, players, dt);
        switch (st.step) {
            case CAMP -> camp(world, store, st, players, dt);
            case CORRIDOR -> {
                if (Champion.inArena(store, players).size() > 0) {
                    st.step = Step.CHAMPION;
                    Gates.checkpoint(world, VolcanicLayout.LANDING_CHECKPOINT, MESSAGES + "checkpoint");
                }
            }
            case CHAMPION -> {
                if (st.champion.step(world, store, st, players, dt)) {
                    st.step = Step.MINE;
                    Gates.open(world, store, VolcanicLayout.GATE_CHAMPION, MESSAGES + "champion.victory");
                }
            }
            case MINE -> mine(world, store, st, players);
            case ARENA -> {
                if (st.shaman.step(world, store, st, players, dt)) {
                    st.step = Step.DONE;
                    Spawns.removeAll(store, st.bats);
                    Gates.victory(world, VolcanicLayout.REWARD, VolcanicLayout.END_EXIT, MESSAGES + "title.victory",
                            MESSAGES + "shaman.victory");
                }
            }
            default -> {
            }
        }
    }

    // --- camp des grawls -------------------------------------------------------------------------------

    private void camp(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        if (st.totem == null || !st.totem.isValid()) {
            st.totem = Spawns.spawn(store, TOTEM, Spawns.point(VolcanicLayout.TOTEM), 0f);
            if (st.totem != null) {
                store.ensureAndGetComponent(st.totem, Frozen.getComponentType());
            }
        }
        showProgress(store, st);
        if (st.kills >= st.required) {
            Vector3d at = Telegraphs.position(store, st.totem);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", at, 1.5f);
            }
            PinnedHealth.unpin(st.totem);
            Spawns.remove(store, st.totem);
            st.totem = null;
            Spawns.removeAll(store, st.camp);
            st.step = Step.CORRIDOR;
            Gates.open(world, store, VolcanicLayout.GATE_CAMP, MESSAGES + "camp.done");
            Gates.checkpoint(world, VolcanicLayout.CORRIDOR_CHECKPOINT, MESSAGES + "checkpoint");
            Spawns.tellAll(world, Message.translation(MESSAGES + "corridor.enter"));
            return;
        }
        st.camp.removeIf(ref -> !Spawns.alive(store, ref));
        st.refill = st.camp.size() <= GROUP_LEFT ? st.refill + dt : 0f;
        if ((st.refill >= CAMP_PAUSE || st.groups == 0) && st.kills + st.camp.size() < st.required) {
            st.refill = 0f;
            group(world, store, st);
        }
        List<PlayerRef> inCamp = Spawns.in(store, players, VolcanicLayout.CAMP);
        st.rocks += dt;
        if (st.rocks >= CAMP_ROCKS && !inCamp.isEmpty()) {
            st.rocks = 0f;
            fallingRocks(world, store, st, inCamp, 1 + FractalRuns.partySize(world) / 2, false);
        }
    }

    /**
     * Un groupe de {@value #GROUP_SIZE} grawls (deux chamans) serrés autour d'un point du bord du camp, à tour de rôle ;
     * ils voient tout le camp et chargent aussitôt.
     */
    private void group(World world, Store<EntityStore> store, State st) {
        double[][] points = VolcanicLayout.CAMP_SPAWNS;
        double[] center = points[st.groups++ % points.length];
        int count = Math.min(GROUP_SIZE, st.required - st.kills - st.camp.size());
        for (int k = 0; k < count; k++) {
            double a = Math.PI * 2 * k / count;
            double[] at = {center[0] + Math.cos(a) * 2.2, center[1], center[2] + Math.sin(a) * 2.2};
            Ref<EntityStore> grawl = Spawns.spawnFoe(world, store, k % 3 == 2 ? GRAWL_SHAMAN : WARRIOR, at);
            if (grawl != null) {
                st.camp.add(grawl);
            }
        }
        Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", Spawns.point(center));
        Spawns.tellAll(world, Message.translation(MESSAGES + "camp.group"));
    }

    /** La vie du totem montre les grawls qu'il reste à abattre : fixée ({@link PinnedHealth}), elle ne bouge qu'aux morts. */
    private void showProgress(Store<EntityStore> store, State st) {
        EntityStatMap stats = st.totem == null ? null : store.getComponent(st.totem, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || st.required <= 0) {
            return;
        }
        float wanted = Math.max(1f, health.getMax() * (st.required - st.kills) / st.required);
        PinnedHealth.pin(st.totem, wanted);
        if (st.shownKills != st.kills) {
            boolean first = st.shownKills < 0;
            st.shownKills = st.kills;
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), wanted);
            Vector3d at = Telegraphs.position(store, st.totem);
            if (at != null && !first) {
                Telegraphs.particle(store, "Nakasar_Fractal_Totem_Pulse", at, 1.2f);
            }
        }
    }

    /**
     * Rochers qui tombent du volcan : un cercle rouge près de chaque joueur choisi ({@value #ROCK_SECONDS} s), puis
     * {@value #ROCK_PART} des PV max et un étourdissement de 2 s ; avec `stones`, un rocher sur trois laisse une pierre
     * imprégnée.
     */
    static void fallingRocks(World world, Store<EntityStore> store, State st, List<PlayerRef> targets, int count, boolean stones) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        float seconds = ROCK_SECONDS * FractalRuns.windupFactor(world);
        for (PlayerRef target : Spawns.pick(targets, count)) {
            Vector3d at = Telegraphs.position(store, target.getReference());
            if (at == null) {
                continue;
            }
            double a = random.nextDouble(Math.PI * 2);
            double r = random.nextDouble(0, 3);
            Vector3d center = new Vector3d(at.x() + Math.cos(a) * r, at.y(), at.z() + Math.sin(a) * r);
            Telegraphs.circle(store, center, ROCK_RADIUS, seconds);
            Telegraphs.particle(store, "Nakasar_Fractal_Falling_Rock", center, 1f);
            boolean drop = stones && random.nextInt(3) == 0;
            Delayed.later(world, seconds, s -> {
                Telegraphs.particle(s, "Nakasar_Fractal_Rock_Impact", center, 1.2f);
                Telegraphs.sound(s, "SFX_Goblin_Feastmaster_Slam", center);
                for (PlayerRef p : Spawns.alivePlayers(world, s)) {
                    Ref<EntityStore> ref = p.getReference();
                    Vector3d there = Telegraphs.position(s, ref);
                    if (there != null && Telegraphs.horizontal(there, center) <= ROCK_RADIUS + Telegraphs.BODY && Math.abs(there.y() - center.y()) <= 2.5) {
                        Hurt.percent(s, ref, ROCK_PART, FIRE_CAUSE);
                        Hurt.effect(s, ref, "Hazard_Electric_Stun", 2f);
                    }
                }
                if (drop && st.step == Step.CHAMPION && st.champion.shielded()) {   // seulement Champion protégé
                    dropStone(s, center);
                    long now = System.nanoTime();
                    if (now - st.stoneMessage > Telegraphs.seconds(10f)) {
                        st.stoneMessage = now;
                        Spawns.tellAll(world, Message.translation(MESSAGES + "stone.drop"));
                    }
                }
            });
        }
    }

    /**
     * Dans la lave du lac du volcan, debout sur de la roche en fusion (coulées, cratère en fusion) ou juste au-dessus en
     * sautant : {@value #LAVA_PART} des PV max par seconde, l'armure n'y fait rien.
     */
    static void lavaFloor(World world, Store<EntityStore> store, State st, List<PlayerRef> players, float dt) {
        st.lavaClock += dt;
        if (st.lavaClock < 0.5f) {
            return;
        }
        float seconds = st.lavaClock;
        st.lavaClock = 0f;
        ChunkStore chunks = world.getChunkStore();
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            String floor = floorBelow(chunks, at);
            if (inLake(at) || floor != null && LAVA_BLOCKS.contains(floor)) {
                Hurt.percent(store, ref, LAVA_PART * seconds, FIRE_CAUSE);
                Hurt.effect(store, ref, LAVA_BURN, 1f);
                tell(st, player, "lava.burn");
            }
        }
    }

    /** Dans la lave du lac (fluide : pas un bloc sous les pieds), sous la surface et au-dessus du fond. */
    static boolean inLake(Vector3d at) {
        if (at.y() > VolcanicLayout.LAKE_SURFACE + 0.5) {
            return false;
        }
        for (double[] disc : VolcanicLayout.LAKE) {
            if (Math.hypot(at.x() - disc[0], at.z() - disc[1]) <= disc[2]) {
                return true;
            }
        }
        return false;
    }

    /** Premier bloc non vide sous les pieds, jusqu'à {@value #LAVA_REACH} blocs plus bas (un saut ne protège pas). */
    private static String floorBelow(ChunkStore chunks, Vector3d at) {
        int x = (int) Math.floor(at.x());
        int z = (int) Math.floor(at.z());
        int top = (int) Math.floor(at.y() - 0.2);
        for (int y = top; y >= top - LAVA_REACH; y--) {
            String name = WorldBlocks.name(chunks, x, y, z);
            if (name != null) {
                return name;
            }
        }
        return null;
    }

    /** Les joueurs dans une arène ronde : à {@code radius} + 0,5 du centre, de 3 blocs sous lui à {@code above} au-dessus. */
    static List<PlayerRef> inCylinder(Store<EntityStore> store, List<PlayerRef> players, double[] center, double radius, double above) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && inCylinder(at, center, radius, above)) {
                out.add(player);
            }
        }
        return out;
    }

    static boolean inCylinder(Vector3d at, double[] center, double radius, double above) {
        return at.y() >= center[1] - 3 && at.y() <= center[1] + above
                && Math.hypot(at.x() - center[0], at.z() - center[2]) <= radius + 0.5;
    }

    // --- mine ---------------------------------------------------------------------------------------

    private void mine(World world, Store<EntityStore> store, State st, List<PlayerRef> players) {
        if (!st.batsSpawned && Spawns.anyIn(store, players, VolcanicLayout.MINE)) {
            st.batsSpawned = true;
            Spawns.tellAll(world, Message.translation(MESSAGES + "mine.enter"));
            for (double[] at : VolcanicLayout.BATS) {
                Ref<EntityStore> bat = Spawns.spawnFoe(world, store, BAT, at);
                if (bat != null) {
                    st.bats.add(bat);
                }
            }
        }
        if (Spawns.anyIn(store, players, VolcanicLayout.END_PAD)) {
            st.step = Step.ARENA;
            Gates.checkpoint(world, VolcanicLayout.END_CHECKPOINT, MESSAGES + "checkpoint");
        }
    }

    // --- coups, objets lancés, morts ---------------------------------------------------------------------

    @Override
    public boolean shielded(World world, Store<EntityStore> store, Ref<EntityStore> ref, String role) {
        return CHAMPION.equals(role) && state(world).champion.shielded(ref);
    }

    @Override
    public void filter(World world, Store<EntityStore> store, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim,
                       String victimRole, Ref<EntityStore> attacker, Damage damage) {
        if (TOTEM.equals(victimRole) || CAPTIVE.equals(victimRole)) {
            damage.setCancelled(true);
            return;
        }
        if (CHAMPION.equals(victimRole)) {
            state(world).champion.filter(victim, damage);
        }
    }

    @Override
    public void thrown(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String action,
                       Ref<EntityStore> target) {
        if ("ImbuedStone".equals(action)) {
            state(world).champion.stone(world, store, target);
        }
    }

    @Override
    public void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        State st = state(world);
        if (st.step == Step.CAMP && (WARRIOR.equals(role) || GRAWL_SHAMAN.equals(role))) {
            st.kills++;
        } else if (CHAMPION.equals(role)) {
            st.champion.down = true;
        } else if (IMBUED.equals(role)) {
            st.shaman.down = true;
        }
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
