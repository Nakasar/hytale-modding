package dev.nakasar.hytale.fractals.moltenboss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Le Berserker et la Tempête de feu en fusion, sur la plate-forme du creuset (GW2). Coups au corps à corps et
 * enchaînement du Berserker, boules de feu de la Tempête : rôles JSON. En Java :
 * <ul>
 *   <li>le Berserker se téléporte près d'un joueur toutes les {@value #TELEPORT_EVERY} s et frappe le sol toutes les
 *   {@value #STOMP_EVERY} s : onde blanche au sol (à sauter) puis onde bleue en l'air (rester au sol), en
 *   alternance ({@link Shockwaves}) ;</li>
 *   <li>la Tempête lance des flammes sur deux joueurs toutes les {@value #BOLT_EVERY} s : cercle rouge, puis un brasier
 *   qui brûle au sol {@link MoltenBossLayout#FIRE_POOL_SECONDS} s ;</li>
 *   <li>chaque quart de vie perdu par l'un fait enrager l'autre ({@value #ENRAGE_SECONDS} s, attaques plus
 *   fréquentes) ;</li>
 *   <li>le premier tombé, le survivant absorbe sa flamme (forme renforcée) : le Berserker fait pleuvoir des débris, la
 *   Tempête lève une couronne de vent brûlant au bord de la plate-forme, qui repousse vers le vide.</li>
 * </ul>
 * Personne sur la plate-forme pendant {@value MoltenBoss#RESET_SECONDS} s : les chefs disparaissent (sans soin) ; au
 * retour, le combat reprend à sa phase (le survivant renforcé seul, s'il en était là).
 */
final class MoltenDuo {

    static final float TELEPORT_EVERY = 14f;
    static final float STOMP_EVERY = 9f;
    static final float STOMP_WINDUP = 1.2f;
    static final float STOMP_PART = 0.15f;
    static final float BOLT_EVERY = 7f;
    static final float BOLT_WINDUP = 1.5f;
    static final float BOLT_PART = 0.12f;
    static final float POOL_PART = 0.03f;
    static final float DEBRIS_EVERY = 10f;
    static final float DEBRIS_WINDUP = 1.6f;
    static final float DEBRIS_PART = 0.15f;
    static final float WIND_EVERY = 20f;
    static final float WIND_WINDUP = 2f;
    static final float WIND_SECONDS = 4f;
    static final float WIND_PART = 0.04f;
    static final double WIND_PUSH = 7;
    static final float ENRAGE_SECONDS = 12f;
    /** Enragé, ses recharges courent ce facteur plus vite. */
    static final float ENRAGE_RATE = 1.4f;
    /** Vitesse de vol de la Tempête sur son orbite (blocs par seconde). */
    static final double ORBIT_SPEED = 2.5;

    private record Pool(Vector3d center, long until) {
    }

    private final Shockwaves waves = new Shockwaves();
    private final List<Pool> pools = new ArrayList<>();
    private Ref<EntityStore> berserker;
    private Ref<EntityStore> firestorm;
    private boolean engaged;
    /** Rôle renforcé du survivant (null : les deux vivent encore) ; gardé après une remise à zéro. */
    private String empowered;
    private final int[] quarters = new int[2];
    private float idle;
    private float teleport;
    private float stomp;
    private boolean airNext;
    private float bolt;
    private float debris;
    private float wind;
    private List<Telegraphs.Strip> gale = List.of();
    private long galeFrom;
    private long galeUntil;
    private float pulse;
    private float poolBeat;
    /** Numéro du combat en cours : un coup différé d'un combat fini ne tombe pas dans le suivant. */
    private int fight;
    /** Angle de la Tempête sur son orbite (radians, atan2(dz, dx)). */
    private double orbit;

    /** Vrai quand les deux chefs sont vaincus. */
    boolean step(World world, Store<EntityStore> store, MoltenBoss.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(MoltenBossLayout.ARENA);
        double radius = MoltenBossLayout.ARENA_RADIUS;
        if (!engaged) {
            if (!MoltenBoss.near(store, players, c, radius - 4).isEmpty()) {
                engage(world, store, c);
            }
            return false;
        }
        boolean bAlive = berserker != null && Spawns.alive(store, berserker);
        boolean fAlive = firestorm != null && Spawns.alive(store, firestorm);
        if (!bAlive && !fAlive) {
            clear(store, false);
            return true;
        }
        List<PlayerRef> here = MoltenBoss.near(store, players, c, radius + 4);
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= MoltenBoss.RESET_SECONDS) {
                clear(store, true);
                Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "duo.reset"));
            }
            return false;
        }
        idle = 0f;
        if (empowered == null && (!bAlive || !fAlive)) {
            upgrade(world, store, bAlive ? berserker : firestorm, bAlive);
            return false;
        }
        if (bAlive) {
            Leash.keepOnDisc(store, berserker, c, radius - 2, 2, MoltenBoss.FALL_LIMIT);
            enrage(world, store, berserker, 0, firestorm, fAlive);
            berserker(world, store, here, c, radius, dt * rate(store, berserker));
        }
        if (fAlive) {
            enrage(world, store, firestorm, 1, berserker, bAlive);
            firestorm(world, store, here, c, radius, dt * rate(store, firestorm));
        }
        burnPools(store, here, dt);
        return false;
    }

    private static float rate(Store<EntityStore> store, Ref<EntityStore> boss) {
        return Hurt.has(store, boss, MoltenBoss.ENRAGED) ? ENRAGE_RATE : 1f;
    }

    /** Un quart de vie de plus perdu par `boss` : l'autre enrage. */
    private void enrage(World world, Store<EntityStore> store, Ref<EntityStore> boss, int slot, Ref<EntityStore> other,
                        boolean otherAlive) {
        int lost = Math.min(3, (int) Math.floor((1f - Hurt.healthFraction(store, boss)) * 4f + 1e-4));
        if (lost <= quarters[slot]) {
            return;
        }
        quarters[slot] = lost;
        if (!otherAlive) {
            return;
        }
        Hurt.effect(store, other, MoltenBoss.ENRAGED, ENRAGE_SECONDS);
        Vector3d at = Telegraphs.position(store, other);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Molten_Upgrade", at, 1f);
        }
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "duo.enraged").param("name", name(Spawns.role(store, other))));
    }

    // --- le Berserker --------------------------------------------------------------------------------------------

    private void berserker(World world, Store<EntityStore> store, List<PlayerRef> here, Vector3d c, double radius, float dt) {
        teleport += dt;
        if (teleport >= TELEPORT_EVERY) {
            teleport = 0f;
            blink(store, here, c, radius);
        }
        stomp += dt;
        if (stomp >= STOMP_EVERY) {
            stomp = 0f;
            stomp(world, store, radius);
        }
        if (MoltenBoss.BERSERKER_2.equals(empowered)) {
            debris += dt;
            if (debris >= DEBRIS_EVERY) {
                debris = 0f;
                debris(world, store, here);
            }
        }
    }

    /** Il disparaît et reparaît à trois blocs d'un joueur, du côté du centre de la plate-forme. */
    private void blink(Store<EntityStore> store, List<PlayerRef> here, Vector3d c, double radius) {
        PlayerRef target = here.get((int) (Math.random() * here.size()));
        Vector3d p = Telegraphs.position(store, target.getReference());
        Vector3d from = Telegraphs.position(store, berserker);
        if (p == null || from == null) {
            return;
        }
        double d = Telegraphs.horizontal(p, c);
        double k = d < 1e-3 ? 0 : 3 / d;
        Vector3d to = new Vector3d(p.x() + (c.x() - p.x()) * k, c.y(), p.z() + (c.z() - p.z()) * k);
        if (Telegraphs.horizontal(to, c) > radius - 3) {
            double s = (radius - 3) / Telegraphs.horizontal(to, c);
            to = new Vector3d(c.x() + (to.x() - c.x()) * s, c.y(), c.z() + (to.z() - c.z()) * s);
        }
        to = outOfPit(to);
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Teleport", from, 1.5f);
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Teleport", to, 1.5f);
        MoltenBoss.move(store, berserker, to, p);
    }

    /** Onde blanche (à sauter) ou bleue (rester au sol), en alternance, après une annonce sous le Berserker. */
    private void stomp(World world, Store<EntityStore> store, double radius) {
        Vector3d at = Telegraphs.position(store, berserker);
        if (at == null) {
            return;
        }
        boolean air = airNext;
        airNext = !airNext;
        Telegraphs.particle(store, air ? "Nakasar_Fractal_Molten_Windup_Air" : "Nakasar_Fractal_Molten_Windup_Ground", at, 2f);
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + (air ? "duo.air" : "duo.ground")));
        Ref<EntityStore> boss = berserker;
        Delayed.later(world, STOMP_WINDUP, s -> {
            if (boss != berserker || !Spawns.alive(s, boss)) {
                return;
            }
            Vector3d from = Telegraphs.position(s, boss);
            if (from != null) {
                Telegraphs.particle(s, "Stick_Slam_Ground_Large", from, 1.5f);
                waves.add(from, radius * 2 + 4, air ? Shockwaves.Kind.AIR : Shockwaves.Kind.GROUND, STOMP_PART);
            }
        });
    }

    /** Débris (forme renforcée) : un cercle rouge sous chaque joueur, puis la chute. */
    private void debris(World world, Store<EntityStore> store, List<PlayerRef> here) {
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "duo.debris"));
        for (PlayerRef p : here) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                fall(world, store, new Vector3d(at), MoltenBossLayout.DEBRIS_RADIUS, DEBRIS_WINDUP, DEBRIS_PART,
                        "Nakasar_Fractal_Molten_Debris", false);
            }
        }
    }

    /** `at` s'il est hors du creuset et de son muret, sinon poussé juste au-delà, à l'opposé du centre du creuset. */
    static Vector3d outOfPit(Vector3d at) {
        Vector3d pit = Spawns.point(MoltenBossLayout.PIT);
        double keep = MoltenBossLayout.PIT_RADIUS + 1.5;
        double d = Telegraphs.horizontal(at, pit);
        if (d >= keep) {
            return at;
        }
        double ax = d < 1e-3 ? 1 : (at.x() - pit.x()) / d;
        double az = d < 1e-3 ? 0 : (at.z() - pit.z()) / d;
        return new Vector3d(pit.x() + ax * keep, at.y(), pit.z() + az * keep);
    }

    // --- la Tempête de feu ---------------------------------------------------------------------------------------

    private void firestorm(World world, Store<EntityStore> store, List<PlayerRef> here, Vector3d c, double radius, float dt) {
        bolt += dt;
        if (bolt >= BOLT_EVERY) {
            bolt = 0f;
            for (PlayerRef p : Spawns.pick(here, 2)) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null) {
                    fall(world, store, new Vector3d(at), MoltenBossLayout.FIRE_POOL_RADIUS, BOLT_WINDUP, BOLT_PART,
                            "Nakasar_Fractal_Molten_Fire_Bolt", true);
                }
            }
        }
        if (MoltenBoss.FIRESTORM_2.equals(empowered)) {
            wind += dt;
            if (wind >= WIND_EVERY && gale.isEmpty()) {
                wind = 0f;
                gale(world, store, c, radius);
            }
        }
        galeStep(world, store, c, here, dt);
    }

    /**
     * La couronne de vent : {@link MoltenBossLayout#WIND_SEGMENTS} bandes rouges tout autour du bord ; au bout de
     * {@value #WIND_WINDUP} s, qui est dans une bande est brûlé et poussé vers le vide pendant {@value #WIND_SECONDS} s.
     */
    private void gale(World world, Store<EntityStore> store, Vector3d c, double radius) {
        long now = System.nanoTime();
        List<Telegraphs.Strip> strips = new ArrayList<>();
        double inner = radius - MoltenBossLayout.WIND_BAND;
        for (int k = 0; k < MoltenBossLayout.WIND_SEGMENTS; k++) {
            double a = k * Math.PI * 2 / MoltenBossLayout.WIND_SEGMENTS;
            Vector3d start = new Vector3d(c.x() + Math.cos(a) * inner, c.y(), c.z() + Math.sin(a) * inner);
            Telegraphs.Strip strip = new Telegraphs.Strip(start, a, MoltenBossLayout.WIND_BAND, MoltenBossLayout.WIND_LENGTH,
                    now, WIND_WINDUP);
            strip.step(store, now);
            strips.add(strip);
        }
        gale = strips;
        galeFrom = now + Telegraphs.seconds(WIND_WINDUP);
        galeUntil = galeFrom + Telegraphs.seconds(WIND_SECONDS);
        pulse = 0f;
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "duo.wind"));
    }

    private void galeStep(World world, Store<EntityStore> store, Vector3d c, List<PlayerRef> here, float dt) {
        if (gale.isEmpty()) {
            return;
        }
        long now = System.nanoTime();
        if (now >= galeUntil) {
            gale = List.of();
            return;
        }
        if (now < galeFrom) {
            return;
        }
        pulse -= dt;
        if (pulse > 0f) {
            return;
        }
        pulse = 0.5f;
        for (Telegraphs.Strip strip : gale) {
            Telegraphs.particle(store, "Nakasar_Fractal_Molten_Wind", strip.at(MoltenBossLayout.WIND_BAND / 2, 0), 1f);
        }
        for (PlayerRef p : here) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || gale.stream().noneMatch(s -> s.contains(at))) {
                continue;
            }
            Hurt.percent(store, ref, WIND_PART, MoltenBoss.CAUSE);
            Hurt.effect(store, ref, MoltenBoss.BURNING, 3f);
            double d = Telegraphs.horizontal(at, c);
            double k = d < 1e-3 ? 0 : WIND_PUSH / d;
            Moves.velocity(store, ref, new Vector3d((at.x() - c.x()) * k, 2, (at.z() - c.z()) * k));
        }
    }

    // --- coups qui tombent, brasiers ------------------------------------------------------------------------------

    /** Cercle rouge de `radius` en `at` ; au bout de `windup`, qui est dedans prend `part` (et un brasier s'il le faut). */
    private void fall(World world, Store<EntityStore> store, Vector3d at, double radius, float windup, float part,
                      String impact, boolean pool) {
        Telegraphs.circle(store, at, radius, windup);
        int round = fight;
        Delayed.later(world, windup, s -> {
            if (!engaged || round != fight) {
                return;
            }
            Telegraphs.particle(s, impact, at, (float) radius);
            for (PlayerRef p : MoltenBoss.near(s, Spawns.alivePlayers(world, s), Spawns.point(MoltenBossLayout.ARENA),
                    MoltenBossLayout.ARENA_RADIUS + 4)) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && Telegraphs.inCircle(pos, at, radius)) {
                    Hurt.percent(s, p.getReference(), part, MoltenBoss.CAUSE);
                    if (pool) {
                        Hurt.effect(s, p.getReference(), MoltenBoss.BURNING, 3f);
                    }
                }
            }
            if (pool) {
                pools.add(new Pool(at, System.nanoTime() + Telegraphs.seconds(MoltenBossLayout.FIRE_POOL_SECONDS)));
            }
        });
    }

    /** Les brasiers brûlent qui s'y tient (toutes les demi-secondes). */
    private void burnPools(Store<EntityStore> store, List<PlayerRef> here, float dt) {
        poolBeat += dt;
        if (poolBeat < 0.5f) {
            return;
        }
        poolBeat = 0f;
        long now = System.nanoTime();
        pools.removeIf(pool -> now >= pool.until());
        for (Pool pool : pools) {
            for (PlayerRef p : here) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.inCircle(at, pool.center(), MoltenBossLayout.FIRE_POOL_RADIUS)) {
                    Hurt.percent(store, p.getReference(), POOL_PART, MoltenBoss.CAUSE);
                    Hurt.effect(store, p.getReference(), MoltenBoss.BURNING, 3f);
                }
            }
        }
    }

    /** Un tick du monde : ondes de choc, flammes des brasiers (reposées toutes les demi-secondes). */
    private float flameBeat;

    void tick(World world, Store<EntityStore> store, float dt) {
        waves.tick(world, store, dt);
        fly(store, dt);
        flameBeat += dt;
        if (flameBeat >= 0.5f && !pools.isEmpty()) {
            flameBeat = 0f;
            for (Pool pool : pools) {
                Telegraphs.particle(store, "Nakasar_Fractal_Molten_Fire_Pool", pool.center(),
                        (float) MoltenBossLayout.FIRE_POOL_RADIUS);
            }
        }
    }

    /**
     * La Tempête tourne autour du centre à {@link MoltenBossLayout#FIRESTORM_ORBIT} blocs et
     * {@link MoltenBossLayout#FIRESTORM_HOVER} au-dessus du sol (on l'atteint au contact) ; enragée, plus vite.
     */
    private void fly(Store<EntityStore> store, float dt) {
        if (!engaged || firestorm == null || !Spawns.alive(store, firestorm)) {
            return;
        }
        Vector3d c = Spawns.point(MoltenBossLayout.ARENA);
        orbit += ORBIT_SPEED * rate(store, firestorm) * dt / MoltenBossLayout.FIRESTORM_ORBIT;
        Vector3d to = new Vector3d(c.x() + Math.cos(orbit) * MoltenBossLayout.FIRESTORM_ORBIT,
                c.y() + MoltenBossLayout.FIRESTORM_HOVER, c.z() + Math.sin(orbit) * MoltenBossLayout.FIRESTORM_ORBIT);
        MoltenBoss.move(store, firestorm, to, c);
    }

    // --- entrée, renfort, fin ------------------------------------------------------------------------------------

    private void engage(World world, Store<EntityStore> store, Vector3d c) {
        Vector3d entry = Spawns.point(MoltenBossLayout.CHECKPOINT_D);
        if (empowered != null) {
            Vector3d at = MoltenBoss.BERSERKER_2.equals(empowered) ? outOfPit(new Vector3d(c.x() + 6, c.y(), c.z() + 5))
                    : new Vector3d(c.x() + Math.cos(orbit) * MoltenBossLayout.FIRESTORM_ORBIT,
                    c.y() + MoltenBossLayout.FIRESTORM_HOVER, c.z() + Math.sin(orbit) * MoltenBossLayout.FIRESTORM_ORBIT);
            Ref<EntityStore> ref = Spawns.spawnBoss(world, store, empowered, at, Telegraphs.yawToward(at, entry));
            if (ref == null) {
                return;
            }
            if (MoltenBoss.BERSERKER_2.equals(empowered)) {
                berserker = ref;
            } else {
                firestorm = ref;
            }
        } else {
            Vector3d b = outOfPit(new Vector3d(c.x() + 6, c.y(), c.z() + 5));
            orbit = Math.PI / 4;
            Vector3d f = new Vector3d(c.x() + Math.cos(orbit) * MoltenBossLayout.FIRESTORM_ORBIT,
                    c.y() + MoltenBossLayout.FIRESTORM_HOVER, c.z() + Math.sin(orbit) * MoltenBossLayout.FIRESTORM_ORBIT);
            berserker = Spawns.spawnBoss(world, store, MoltenBoss.BERSERKER, b, Telegraphs.yawToward(b, entry));
            firestorm = Spawns.spawnBoss(world, store, MoltenBoss.FIRESTORM, f, Telegraphs.yawToward(f, entry));
            if (berserker == null && firestorm == null) {
                return;
            }
        }
        engaged = true;
        fight++;
        idle = 0f;
        quarters[0] = 0;
        quarters[1] = 0;
        teleport = 0f;
        stomp = STOMP_EVERY - 5f;
        airNext = false;
        bolt = BOLT_EVERY - 3f;
        debris = 0f;
        wind = WIND_EVERY - 8f;
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Upgrade", c, 2.5f);
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "duo.enter"));
    }

    /** Le premier chef tombé : le survivant disparaît dans une colonne de flammes et revient renforcé, à sa place. */
    private void upgrade(World world, Store<EntityStore> store, Ref<EntityStore> survivor, boolean isBerserker) {
        Vector3d at = Telegraphs.position(store, survivor);
        Vector3d c = Spawns.point(MoltenBossLayout.ARENA);
        Vector3d where = at != null ? new Vector3d(at) : c;
        String role = isBerserker ? MoltenBoss.BERSERKER_2 : MoltenBoss.FIRESTORM_2;
        Ref<EntityStore> ref = Spawns.spawnBoss(world, store, role, where, Telegraphs.yawToward(where, c));
        if (ref == null) {
            return;   // le survivant reste tel quel ; on réessaie au pas suivant
        }
        empowered = role;
        Spawns.remove(store, survivor);
        if (isBerserker) {
            berserker = ref;
            firestorm = null;
        } else {
            firestorm = ref;
            berserker = null;
        }
        quarters[0] = 0;
        quarters[1] = 0;
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Upgrade", where, 2.5f);
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "duo.upgrade").param("name", name(empowered)));
    }

    private static Message name(String role) {
        String suffix = role == null ? "" : role.substring("Nakasar_Fractal_".length());
        return Message.translation(MoltenBoss.MESSAGES + "npc." + suffix + ".name");
    }

    /** Fin du combat ; `all` : les chefs encore là disparaissent aussi (remise à zéro, le renfort est gardé). */
    private void clear(Store<EntityStore> store, boolean all) {
        waves.clear();
        pools.clear();
        gale = List.of();
        fight++;
        if (all) {
            Spawns.remove(store, berserker);
            Spawns.remove(store, firestorm);
        }
        berserker = null;
        firestorm = null;
        engaged = false;
    }
}
