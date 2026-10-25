package dev.nakasar.hytale.fractals.volcanic;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.PinnedHealth;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.HitShield;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Le Chamane imprégné, boss du Volcanique, sur son île au milieu du lac de lave. Son IA (JSON) frappe et lance la
 * flèche enflammée, le piqué, le souffle des ailes et la tempête de feu ; le Java mène l'arène :
 * <ul>
 *   <li>cratères : toutes les {@value #CRATER_INTERVAL} s, quelques petits cratères de l'île chauffent (leurs blocs
 *   passent du brun volcanique à l'orange puis au jaune en {@value #HEAT_SECONDS} s), puis crachent de la lave active
 *   {@value #LAVA_SECONDS} s : on y brûle très fort ({@link Volcanic#lavaFloor}) ; ils refroidissent ensuite ;</li>
 *   <li>flamme qui se propage : un joueur touché par la flèche brûle et allume ceux à moins de {@value #SPREAD_RANGE}
 *   blocs ;</li>
 *   <li>à 75, 50 et 25 % de vie : bouclier de {@value #SHIELD_HITS} coups (quel que soit le nombre de joueurs), larves de braise,
 *   et il plane lentement vers un villageois : il met {@value #GLIDE_SECONDS} s (+{@value #GLIDE_PER_PLAYER} s par
 *   joueur de plus) à l'atteindre, puis s'en nourrit (+{@value #FEED_HEAL} de sa vie) ; bouclier brisé avant : étourdi
 *   {@value #STUN} s ;</li>
 *   <li>sa vie ne remonte jamais d'elle-même ({@link PinnedHealth#noRegen}), seulement quand il se nourrit ;</li>
 *   <li>personne dans l'arène pendant {@value #RESET_SECONDS} s : tout repart de zéro.</li>
 * </ul>
 */
final class ImbuedShaman {

    static final String SPREAD = "Nakasar_Fractal_Spreading_Flame";
    static final float CRATER_INTERVAL = 7f;
    static final float HEAT_SECONDS = 3.5f;
    static final float LAVA_SECONDS = 6f;
    static final float COOL_SECONDS = 2f;
    /** État « lave active » des cratères (index dans VolcanicLayout.CRATER_STAGES). */
    private static final int LAVA = 4;
    static final double SPREAD_RANGE = 2.5;
    static final float SPREAD_PART = 0.03f;
    static final int SHIELD_HITS = 50;
    static final float GLIDE_SECONDS = 24f;
    static final float GLIDE_PER_PLAYER = 4f;
    static final double FEED_RANGE = 2;
    static final float FEED_HEAL = 0.25f;
    static final float STUN = 4f;
    static final int LARVAE = 3;
    static final float RESET_SECONDS = 20f;
    private static final float[] THRESHOLDS = {0.75f, 0.50f, 0.25f};

    private Ref<EntityStore> boss;
    volatile boolean down;
    private boolean engaged;
    private boolean victory;
    private float idle;
    private int threshold;
    private boolean shielded;
    private int gliding = -1;
    private float glideClock;
    private float glideSeconds;
    private Vector3d glideFrom;
    private final Ref<EntityStore>[] villagers;
    private final boolean[] eaten;
    private final List<Ref<EntityStore>> larvae = new ArrayList<>();
    /** Âge de chaque cratère depuis qu'il chauffe ; négatif : au repos. */
    private final float[] craterAge = new float[VolcanicLayout.CRATERS.length];
    private final int[] craterStage = new int[VolcanicLayout.CRATERS.length];
    private float craterClock;
    private float tick;

    @SuppressWarnings("unchecked")
    ImbuedShaman() {
        villagers = new Ref[VolcanicLayout.VILLAGERS.length];
        eaten = new boolean[villagers.length];
        Arrays.fill(craterAge, -1f);
    }

    static boolean inArena(Vector3d at) {
        return Volcanic.inCylinder(at, VolcanicLayout.ARENA_CENTER, VolcanicLayout.ARENA_RADIUS, 10);
    }

    /** Un pas de jeu ; vrai à la victoire (une seule fois). */
    boolean step(World world, Store<EntityStore> store, Volcanic.State st, List<PlayerRef> players, float dt) {
        if (victory) {
            return false;
        }
        if (down) {
            return win(world, store);
        }
        keepVillagers(store);
        if (boss == null || !boss.isValid()) {
            boss = Spawns.spawnBoss(world, store, Volcanic.IMBUED, Spawns.point(VolcanicLayout.ARENA_CENTER), 0f);
            if (boss == null) {
                return false;
            }
            PinnedHealth.noRegen(boss);
        }
        List<PlayerRef> inArena = Volcanic.inCylinder(store, players, VolcanicLayout.ARENA_CENTER, VolcanicLayout.ARENA_RADIUS, 10);
        if (inArena.isEmpty()) {
            idle(world, store, dt);
            return false;
        }
        idle = 0f;
        if (!engaged) {
            engaged = true;
            coolAll(world);
            craterClock = CRATER_INTERVAL - 4f;
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
        if (tick >= 0.5f) {
            spread(store, inArena, tick);
            tick = 0f;
        }
        craters(world, store, dt);
        return false;
    }

    // --- arène ---------------------------------------------------------------------------------------

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

    /** Cratères : de nouveaux chauffent toutes les {@value #CRATER_INTERVAL} s ; chacun suit sa couleur puis sa lave. */
    private void craters(World world, Store<EntityStore> store, float dt) {
        float heat = HEAT_SECONDS * FractalRuns.windupFactor(world);
        craterClock += dt;
        if (craterClock >= CRATER_INTERVAL) {
            craterClock = 0f;
            List<Integer> idle = new ArrayList<>();
            for (int i = 0; i < craterAge.length; i++) {
                if (craterAge[i] < 0f) {
                    idle.add(i);
                }
            }
            Collections.shuffle(idle);
            int count = Math.min(idle.size(), 2 + FractalRuns.partySize(world) / 2);
            for (int k = 0; k < count; k++) {
                craterAge[idle.get(k)] = 0f;
            }
        }
        for (int i = 0; i < craterAge.length; i++) {
            if (craterAge[i] < 0f) {
                continue;
            }
            craterAge[i] += dt;
            float age = craterAge[i];
            int stage;
            if (age < heat) {
                stage = 1 + Math.min(2, (int) (age / heat * 3));
            } else if (age < heat + LAVA_SECONDS) {
                stage = LAVA;
            } else if (age < heat + LAVA_SECONDS + COOL_SECONDS) {
                stage = 2;
            } else {
                stage = 0;
                craterAge[i] = -1f;
            }
            if (stage != craterStage[i]) {
                paint(world, i, stage);
                Vector3d at = Spawns.point(VolcanicLayout.CRATERS[i]);
                if (stage == LAVA) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Lava_Pit", at, 1.6f);
                    Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", at);
                } else if (stage > 0 && stage < LAVA) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Lava_Pit", at, 0.3f + 0.2f * stage);
                }
            }
        }
    }

    /** Pose l'état `stage` (0 : froid … {@value #LAVA} : lave active) sur les cases du cratère `index`. */
    private void paint(World world, int index, int stage) {
        craterStage[index] = stage;
        ChunkStore chunks = world.getChunkStore();
        String block = VolcanicLayout.CRATER_STAGES[stage];
        for (int[] cell : VolcanicLayout.CRATER_CELLS[index]) {
            WorldBlocks.set(chunks, cell[0], cell[1], cell[2], block, 0);
        }
    }

    /** Tous les cratères froids (début du combat, remise à zéro, victoire). */
    private void coolAll(World world) {
        for (int i = 0; i < craterAge.length; i++) {
            craterAge[i] = -1f;
            paint(world, i, 0);
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
        int hits = SHIELD_HITS;   // fixe, quel que soit le nombre de joueurs (Kevin, 2026-10-24)
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
            glideClock = 0f;
            glideSeconds = GLIDE_SECONDS + GLIDE_PER_PLAYER * (FractalRuns.partySize(world) - 1);
            glideFrom = new Vector3d(at);
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

    /**
     * Il plane lentement vers le villageois visé, en ligne droite depuis où il a levé son bouclier : il s'arrête à
     * {@value #FEED_RANGE} blocs au bout du temps prévu et s'en nourrit. Le temps ne dépend pas de la distance : les
     * joueurs ont toujours de quoi briser le bouclier.
     */
    private void glide(World world, Store<EntityStore> store, float dt) {
        Vector3d at = Telegraphs.position(store, boss);
        if (at == null || glideFrom == null) {
            return;
        }
        glideClock += dt;
        if (glideClock >= glideSeconds) {
            feed(world, store, gliding);
            return;
        }
        Vector3d goal = Spawns.point(VolcanicLayout.VILLAGERS[gliding]);
        Vector3d way = new Vector3d(goal).sub(glideFrom);
        way.y = 0;
        double length = way.length();
        double reach = Math.max(0, length - FEED_RANGE) * glideClock / glideSeconds;
        Vector3d next = length < 1e-3 ? new Vector3d(glideFrom) : new Vector3d(glideFrom).add(way.mul(reach / length));
        next.y = at.y();
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
            PinnedHealth.heal(store, boss, Math.min(health.getMax(), health.get() + health.getMax() * FEED_HEAL));
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
        glideFrom = null;
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
        glideFrom = null;
        coolAll(world);
        Spawns.removeAll(store, larvae);
        if (boss != null) {
            HitShield.drop(boss);
            PinnedHealth.unpin(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        for (int i = 0; i < eaten.length; i++) {
            eaten[i] = false;
        }
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "shaman.reset"));
    }

    private boolean win(World world, Store<EntityStore> store) {
        victory = true;
        coolAll(world);
        Spawns.removeAll(store, larvae);
        if (boss != null) {
            HitShield.drop(boss);
        }
        return true;
    }
}
