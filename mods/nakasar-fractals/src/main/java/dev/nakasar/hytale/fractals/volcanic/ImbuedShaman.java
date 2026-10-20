package dev.nakasar.hytale.fractals.volcanic;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.HitShield;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Le Chamane imprégné, boss du Volcanique. Son IA (JSON) frappe et lance la flèche enflammée, le piqué, le souffle des
 * ailes et la tempête de feu ; le Java mène l'arène :
 * <ul>
 *   <li>pieds brûlants : immobile plus de {@value #STILL_SECONDS} s, ou en l'air (saut), le sol brûle
 *   ({@value #FEET_PART} des PV max par seconde) ;</li>
 *   <li>puits de lave silencieux : toutes les {@value #PIT_INTERVAL} s, des bulles de feu au sol (pas de cercle rouge)
 *   qui brûlent au bout de {@value #PIT_ARM} s ({@value #PIT_PART} des PV max par seconde) ;</li>
 *   <li>flamme qui se propage : un joueur touché par la flèche brûle et allume ceux à moins de {@value #SPREAD_RANGE}
 *   blocs ;</li>
 *   <li>à 75, 50 et 25 % de vie : bouclier de {@value #SHIELD_HITS} coups (+10 par joueur de plus), larves de braise,
 *   et il plane vers un villageois ; s'il l'atteint, il s'en nourrit (+{@value #FEED_HEAL} de sa vie) ; bouclier brisé
 *   avant : étourdi {@value #STUN} s ;</li>
 *   <li>personne dans l'arène pendant {@value #RESET_SECONDS} s : tout repart de zéro.</li>
 * </ul>
 */
final class ImbuedShaman {

    static final String FEET = "Nakasar_Fractal_Burning_Feet";
    static final String SPREAD = "Nakasar_Fractal_Spreading_Flame";
    static final float STILL_SECONDS = 1f;
    static final float FEET_PART = 0.04f;
    static final float PIT_INTERVAL = 10f;
    static final float PIT_ARM = 2f;
    static final float PIT_LIFE = 10f;
    static final double PIT_RADIUS = 2;
    static final float PIT_PART = 0.08f;
    static final double SPREAD_RANGE = 2.5;
    static final float SPREAD_PART = 0.03f;
    static final int SHIELD_HITS = 40;
    static final double GLIDE_SPEED = 1.6;
    static final double FEED_RANGE = 2;
    static final float FEED_HEAL = 0.25f;
    static final float STUN = 4f;
    static final int LARVAE = 3;
    static final float RESET_SECONDS = 20f;
    private static final float[] THRESHOLDS = {0.75f, 0.50f, 0.25f};

    private static final class Pit {
        final Vector3d at;
        float age;

        Pit(Vector3d at) {
            this.at = at;
        }
    }

    private Ref<EntityStore> boss;
    volatile boolean down;
    private boolean engaged;
    private boolean victory;
    private float idle;
    private int threshold;
    private boolean shielded;
    private int gliding = -1;
    private final Ref<EntityStore>[] villagers;
    private final boolean[] eaten;
    private final Map<UUID, Float> still = new HashMap<>();
    private final List<Pit> pits = new ArrayList<>();
    private final List<Ref<EntityStore>> larvae = new ArrayList<>();
    private float pitClock;
    private float tick;

    @SuppressWarnings("unchecked")
    ImbuedShaman() {
        villagers = new Ref[VolcanicLayout.VILLAGERS.length];
        eaten = new boolean[villagers.length];
    }

    static boolean inArena(Vector3d at) {
        double[] c = VolcanicLayout.ARENA_CENTER;
        return at.y() >= c[1] - 3 && at.y() <= c[1] + 10
                && Math.hypot(at.x() - c[0], at.z() - c[2]) <= VolcanicLayout.ARENA_RADIUS + 0.5;
    }

    /** Un pas de jeu ; vrai à la victoire (une seule fois). */
    boolean step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        if (victory) {
            return false;
        }
        if (down) {
            return win(store);
        }
        keepVillagers(store);
        if (boss == null || !boss.isValid()) {
            boss = Spawns.spawnBoss(world, store, Volcanic.IMBUED, Spawns.point(VolcanicLayout.ARENA_CENTER), 0f);
            if (boss == null) {
                return false;
            }
        }
        List<PlayerRef> inArena = new ArrayList<>();
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && inArena(at)) {
                inArena.add(player);
            }
        }
        if (inArena.isEmpty()) {
            idle(world, store, dt);
            return false;
        }
        idle = 0f;
        if (!engaged) {
            engaged = true;
            pitClock = PIT_INTERVAL - 4f;
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "shaman.enter"));
        }
        larvae.removeIf(ref -> !Spawns.alive(store, ref));
        if (!shielded && threshold < THRESHOLDS.length && Hurt.healthFraction(store, boss) < THRESHOLDS[threshold]) {
            shield(world, store);
        }
        if (gliding >= 0) {
            glide(world, store, dt);
        }
        tick += dt;
        boolean second = tick >= 0.5f;
        if (second) {
            tick = 0f;
            feet(world, store, inArena, 0.5f);
            spread(store, inArena, 0.5f);
        } else {
            feet(world, store, inArena, 0f);
        }
        pits(world, store, inArena, dt, second);
        return false;
    }

    // --- arène ---------------------------------------------------------------------------------------

    /** Pieds brûlants : immobile au sol plus d'une seconde, ou en l'air. `tickSeconds` &gt; 0 : on applique les dégâts. */
    private void feet(World world, Store<EntityStore> store, List<PlayerRef> players, float tickSeconds) {
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            MovementStatesComponent movement = store.getComponent(ref, MovementStatesComponent.getComponentType());
            if (movement == null || movement.getMovementStates() == null) {
                continue;
            }
            var states = movement.getMovementStates();
            boolean airborne = states.jumping || !states.onGround;
            float t = states.horizontalIdle && states.onGround ? still.getOrDefault(player.getUuid(), 0f) + 0.25f : 0f;
            still.put(player.getUuid(), t);
            if (tickSeconds <= 0f || (t < STILL_SECONDS && !airborne)) {
                continue;
            }
            Hurt.percent(store, ref, FEET_PART * tickSeconds, Volcanic.FIRE_CAUSE);
            Hurt.effect(store, ref, FEET, 1f);
            Volcanic.tell(stateOf(world), player, "feet.burning");
        }
    }

    private static Volcanic.State stateOf(World world) {
        return ((Volcanic) dev.nakasar.hytale.fractals.stage.Stages.of(world)).state(world);
    }

    /** Flamme qui se propage : le porteur brûle et l'allume chez ses voisins. */
    private void spread(Store<EntityStore> store, List<PlayerRef> players, float seconds) {
        List<Vector3d> burning = new ArrayList<>();
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            if (Hurt.has(store, ref, SPREAD)) {
                Vector3d at = Telegraphs.position(store, ref);
                if (at != null) {
                    burning.add(at);
                    Telegraphs.particle(store, SPREAD, at, 1f);
                }
                Hurt.percent(store, ref, SPREAD_PART * seconds, Volcanic.FIRE_CAUSE);
            }
        }
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || Hurt.has(store, ref, SPREAD)) {
                continue;
            }
            for (Vector3d source : burning) {
                if (source.distance(at) <= SPREAD_RANGE) {
                    Hurt.effect(store, ref, SPREAD, 6f);
                    break;
                }
            }
        }
    }

    /** Puits de lave silencieux : des bulles, puis la brûlure, aucun cercle rouge. */
    private void pits(World world, Store<EntityStore> store, List<PlayerRef> players, float dt, boolean second) {
        pitClock += dt;
        if (pitClock >= PIT_INTERVAL) {
            pitClock = 0f;
            double[] c = VolcanicLayout.ARENA_CENTER;
            ThreadLocalRandom random = ThreadLocalRandom.current();
            int count = 3 + FractalRuns.partySize(world) / 2;
            for (int k = 0; k < count; k++) {
                double a = random.nextDouble(Math.PI * 2);
                double r = random.nextDouble(2, VolcanicLayout.ARENA_RADIUS - 2);
                pits.add(new Pit(new Vector3d(c[0] + Math.cos(a) * r, c[1], c[2] + Math.sin(a) * r)));
            }
        }
        for (Iterator<Pit> it = pits.iterator(); it.hasNext(); ) {
            Pit pit = it.next();
            pit.age += dt;
            if (pit.age >= PIT_LIFE) {
                it.remove();
                continue;
            }
            if (!second) {
                continue;
            }
            boolean armed = pit.age >= PIT_ARM;
            Telegraphs.particle(store, "Nakasar_Fractal_Lava_Pit", pit.at, armed ? 1.2f : 0.5f);
            if (!armed) {
                continue;
            }
            for (PlayerRef player : players) {
                Vector3d at = Telegraphs.position(store, player.getReference());
                if (at != null && Telegraphs.horizontal(at, pit.at) <= PIT_RADIUS && Math.abs(at.y() - pit.at.y()) <= 2) {
                    Hurt.percent(store, player.getReference(), PIT_PART * 0.5f, Volcanic.FIRE_CAUSE);
                }
            }
        }
    }

    // --- boucliers et vol vers les villageois ---------------------------------------------------------------

    private void keepVillagers(Store<EntityStore> store) {
        double[] c = VolcanicLayout.ARENA_CENTER;
        for (int i = 0; i < villagers.length; i++) {
            if (eaten[i] || (villagers[i] != null && villagers[i].isValid())) {
                continue;
            }
            Vector3d at = Spawns.point(VolcanicLayout.VILLAGERS[i]);
            villagers[i] = Spawns.spawn(store, Volcanic.CAPTIVE, at, Telegraphs.yawToward(at, Spawns.point(c)));
            if (villagers[i] != null) {
                store.ensureAndGetComponent(villagers[i], Frozen.getComponentType());
                store.ensureAndGetComponent(villagers[i], Invulnerable.getComponentType());
            }
        }
    }

    private void shield(World world, Store<EntityStore> store) {
        shielded = true;
        int hits = SHIELD_HITS + 10 * (FractalRuns.partySize(world) - 1);
        Ref<EntityStore> me = boss;
        HitShield.raise(boss, hits, () -> broken(world, me));
        Vector3d at = Telegraphs.position(store, boss);
        if (at != null) {
            Telegraphs.particle(store, HitShield.PARTICLE, new Vector3d(at).add(0, 1, 0), 2.2f);
            for (int k = 0; k < LARVAE; k++) {
                double a = Math.PI * 2 * k / LARVAE;
                Ref<EntityStore> larva = Spawns.spawnFoe(world, store, Volcanic.LARVA,
                        new double[]{at.x() + Math.cos(a) * 3, at.y(), at.z() + Math.sin(a) * 3});
                if (larva != null) {
                    larvae.add(larva);
                }
            }
            gliding = nearestVillager(at);
        }
        if (gliding >= 0) {
            BossStun.hold(world, store, boss);
        }
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "shaman.shield").param("hits", hits));
    }

    private int nearestVillager(Vector3d from) {
        int best = -1;
        double bestDistance = Double.MAX_VALUE;
        for (int i = 0; i < villagers.length; i++) {
            if (eaten[i]) {
                continue;
            }
            double d = Spawns.point(VolcanicLayout.VILLAGERS[i]).distance(from);
            if (d < bestDistance) {
                bestDistance = d;
                best = i;
            }
        }
        return best;
    }

    /** Il plane vers le villageois visé ; arrivé, il s'en nourrit. */
    private void glide(World world, Store<EntityStore> store, float dt) {
        Vector3d at = Telegraphs.position(store, boss);
        if (at == null) {
            return;
        }
        Vector3d goal = Spawns.point(VolcanicLayout.VILLAGERS[gliding]);
        Vector3d way = new Vector3d(goal).sub(at);
        way.y = 0;
        double distance = way.length();
        if (distance <= FEED_RANGE) {
            feed(world, store, gliding);
            return;
        }
        Vector3d next = new Vector3d(at).add(way.mul(Math.min(distance, GLIDE_SPEED * dt) / distance));
        store.putComponent(boss, Teleport.getComponentType(),
                new Teleport(next, new Rotation3f(0f, Telegraphs.yawToward(at, goal), 0f)));
        Telegraphs.particle(store, "Nakasar_Fractal_Shaman_Glide", next, 1f);
    }

    private void feed(World world, Store<EntityStore> store, int index) {
        eaten[index] = true;
        Vector3d at = Spawns.point(VolcanicLayout.VILLAGERS[index]);
        Telegraphs.particle(store, "Nakasar_Fractal_Shaman_Feed", at, 1.5f);
        Spawns.remove(store, villagers[index]);
        villagers[index] = null;
        EntityStatMap stats = store.getComponent(boss, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.min(health.getMax(), health.get() + health.getMax() * FEED_HEAL));
        }
        HitShield.drop(boss);
        endPhase(store);
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "shaman.fed"));
    }

    /** Bouclier brisé à temps : le vol s'arrête et il est étourdi. */
    private void broken(World world, Ref<EntityStore> me) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (!me.equals(boss) || !shielded) {
            return;
        }
        endPhase(store);
        BossStun.stun(world, store, boss, STUN, BossStun.EFFECT);
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "shaman.broken"));
    }

    private void endPhase(Store<EntityStore> store) {
        shielded = false;
        gliding = -1;
        threshold++;
        BossStun.release(store, boss);
    }

    // --- remise à zéro et victoire ------------------------------------------------------------------------

    void idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged || victory) {
            return;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return;
        }
        engaged = false;
        idle = 0f;
        threshold = 0;
        shielded = false;
        gliding = -1;
        pits.clear();
        Spawns.removeAll(store, larvae);
        if (boss != null) {
            HitShield.drop(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        for (int i = 0; i < eaten.length; i++) {
            eaten[i] = false;
        }
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "shaman.reset"));
    }

    private boolean win(Store<EntityStore> store) {
        victory = true;
        pits.clear();
        Spawns.removeAll(store, larvae);
        if (boss != null) {
            HitShield.drop(boss);
        }
        return true;
    }
}
