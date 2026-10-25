package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.progress.Agony;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Kanaxai, Faux de la maison Aurkus, au-dessus du gouffre violet (GW2). Coups de faux et salve des aspects : rôle
 * JSON. En Java :
 * <ul>
 *   <li>Visage de l'effroi toutes les {@value #DREAD_EVERY} s ({@link Nightmare#dread}) : détourner le regard ;</li>
 *   <li>Tempête déchirante toutes les {@value #STORM_EVERY} s : un joueur marqué de plus à chaque fois ; au bout de
 *   {@value #STORM_WINDUP} s, l'orage frappe autour de chacun et laisse une flaque de saignement
 *   ({@value #POOL_SECONDS} s) : s'écarter, et poser ses flaques au bord ;</li>
 *   <li>Aspects au bord de l'arène (mort, exposition, peur, léthargie, tourment) : Tir de herse toutes les
 *   {@value #HARROW_EVERY} s (cercle sous un joueur, l'état de l'Aspect s'il touche) et un lien vers le joueur le plus
 *   proche ; tenu {@value #TETHER_SECONDS} s sur le même joueur, il l'emporte en Fantasmagorie ;</li>
 *   <li>Ombres rassemblées à chaque tranche de 10 % (de 90 à 10 %) : défiance ouverte {@value #SHADOWS_WINDOW} s ;
 *   brisée, il est étourdi ; sinon un joueur part en Fantasmagorie ;</li>
 *   <li>Fantasmagorie : un Aspect que seul ce joueur voit ({@link AspectVisibilitySystem}) l'attend sur une des cinq
 *   îles : y aller au grappin, le tuer seul, revenir par le champignon ; sinon, au bout de {@value #PHANTASM_SECONDS} s,
 *   {@value #PHANTASM_PART} de ses PV ;</li>
 *   <li>Fendeur de mondes à 66 et 33 % : Kanaxai s'élève, invulnérable, les cinq Aspects se lèvent au bord ; au bout de
 *   {@value #CLEAVER_SECONDS} s, le coup retire {@value #CLEAVER_BASE} des PV plus {@value #CLEAVER_PER_ASPECT} par
 *   Aspect encore debout, et de l'Agonie ;</li>
 *   <li>Vitesse effrayante toutes les {@value #SPEED_EVERY} s après le premier Fendeur ({@link Nightmare#speed}).</li>
 * </ul>
 * Personne sur l'arène ou ses îles pendant {@value #RESET_SECONDS} s : il se dissout et attend le prochain venu.
 */
final class Kanaxai {

    enum Outcome { NONE, WON, RESET }

    static final float DREAD_EVERY = 32f;
    static final float STORM_EVERY = 24f;
    static final float STORM_WINDUP = 3f;
    static final double STORM_RADIUS = 3;
    static final float STORM_PART = 0.2f;
    static final double POOL_RADIUS = 2.5;
    static final float POOL_SECONDS = 25f;
    static final float POOL_PART_PER_SECOND = 0.04f;
    static final float HARROW_EVERY = 16f;
    static final float HARROW_WINDUP = 3f;
    static final double HARROW_RADIUS = 4.5;
    static final double TETHER_RANGE = 14;
    static final float TETHER_SECONDS = 3f;
    static final float TETHER_COOLDOWN = 10f;
    static final float SHADOWS_WINDOW = 5f;
    static final float PHANTASM_SECONDS = 30f;
    static final float PHANTASM_PART = 0.4f;
    static final float[] CLEAVER_AT = {0.66f, 0.33f};
    static final float CLEAVER_SECONDS = 20f;
    static final float CLEAVER_BASE = 0.2f;
    static final float CLEAVER_PER_ASPECT = 0.3f;
    static final float CLEAVER_AGONY = 10f;
    static final float SPEED_EVERY = 28f;
    static final double SPEED_RADIUS = 16;
    static final float RESET_SECONDS = 20f;
    static final double ARENA_REACH = 58;
    static final int START_ASPECTS = 2;

    private record Phantasm(UUID owner, long until) {
    }

    private record Pool(Vector3d at, long until) {
    }

    private static final class Tether {
        UUID target;
        float held;
        float cooldown;
    }

    private Ref<EntityStore> boss;
    private boolean engaged;
    private volatile boolean dead;
    private final Ref<EntityStore>[] edge = newRefs(SilentSurf.ASPECTS.length);
    private final Tether[] tethers = new Tether[SilentSurf.ASPECTS.length];
    private final Map<Ref<EntityStore>, Phantasm> phantasms = new HashMap<>();
    private final List<Pool> pools = new ArrayList<>();
    private int storms;
    private float dreadClock;
    private float stormClock;
    private float harrowClock;
    private float speedClock;
    private float idle;
    private float poolFx;
    private int cleavers;
    private boolean cleaving;
    private long cleaverAt;
    private int shadows;
    private long shadowsUntil;
    private boolean speeding;
    private boolean warned;
    private float tetherFx;
    /** Change à chaque combat et remise à zéro : les attaques encore en vol d'un combat fini s'arrêtent. */
    private int epoch;

    @SuppressWarnings("unchecked")
    private static Ref<EntityStore>[] newRefs(int n) {
        return (Ref<EntityStore>[]) new Ref[n];
    }

    boolean engaged() {
        return engaged;
    }

    void down() {
        dead = true;
    }

    /** Faux si Kanaxai n'a pas pu apparaître (l'arène reste ouverte, on réessaiera). */
    boolean engage(World world, Store<EntityStore> store) {
        Vector3d c = center();
        boss = Spawns.spawnBoss(world, store, SilentSurf.KANAXAI, c, Telegraphs.yawToward(c, new Vector3d(c).add(0, 0, 1)));
        if (boss == null) {
            return false;
        }
        engaged = true;
        epoch++;
        pools.clear();
        warned = false;
        dead = false;
        storms = 0;
        cleavers = 0;
        cleaving = false;
        shadows = 0;
        shadowsUntil = 0;
        speeding = false;
        idle = 0f;
        dreadClock = DREAD_EVERY - 12f;
        stormClock = STORM_EVERY - 8f;
        harrowClock = 0f;
        speedClock = 0f;
        for (int i = 0; i < tethers.length; i++) {
            tethers[i] = new Tether();
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Shadows", c, 2.5f);
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.enter"));
        List<Integer> kinds = new ArrayList<>(List.of(0, 1, 2, 3, 4));
        Collections.shuffle(kinds);
        for (int i = 0; i < START_ASPECTS; i++) {
            raiseEdge(world, store, kinds.get(i));
        }
        return true;
    }

    /** Vrai tant que le combat lancé à l'époque `e` dure. */
    private boolean live(int e) {
        return engaged && !dead && epoch == e;
    }

    static Vector3d center() {
        return Spawns.point(SilentSurfLayout.ARENA_CENTER);
    }

    /** Joueurs sur l'arène ou ses îles. */
    static List<PlayerRef> inside(Store<EntityStore> store, List<PlayerRef> players) {
        Vector3d c = center();
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && Telegraphs.horizontal(at, c) <= ARENA_REACH && at.y() > c.y() - 20 && at.y() < c.y() + 30) {
                out.add(p);
            }
        }
        return out;
    }

    Outcome step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        if (!engaged) {
            return Outcome.NONE;
        }
        if (dead) {
            clear(store);
            return Outcome.WON;
        }
        List<PlayerRef> inside = inside(store, players);
        if (inside.isEmpty()) {
            return idle(world, store, dt) ? Outcome.RESET : Outcome.NONE;
        }
        idle = 0f;
        if (boss == null || !boss.isValid()) {
            return Outcome.NONE;
        }
        long now = System.nanoTime();
        for (int i = 0; i < edge.length; i++) {
            if (edge[i] != null && !Spawns.alive(store, edge[i])) {
                edge[i] = null;
            }
        }
        phantasms(world, store, now);
        pools(store, inside, dt);
        tethers(world, store, inside, dt);
        if (cleaving) {
            if (now >= cleaverAt) {
                cleave(world, store, inside);
            } else if (!warned && cleaverAt - now <= Telegraphs.seconds(3f)) {
                warned = true;
                Telegraphs.circle(store, center(), SilentSurfLayout.ARENA_RADIUS, (cleaverAt - now) / 1e9f);
            }
            return Outcome.NONE;
        }
        float health = Hurt.healthFraction(store, boss);
        if (cleavers < CLEAVER_AT.length && health <= CLEAVER_AT[cleavers] + 0.001f && !speeding) {
            rise(world, store);
            return Outcome.NONE;
        }
        shadows(world, store, inside, health, now);
        if (speeding || shadowsUntil > now || BossStun.isStunned(boss)) {
            return Outcome.NONE;
        }
        dreadClock += dt;
        stormClock += dt;
        harrowClock += dt;
        if (cleavers > 0) {
            speedClock += dt;
        }
        if (cleavers > 0 && speedClock >= SPEED_EVERY) {
            speedClock = 0f;
            dreadClock = Math.min(dreadClock, DREAD_EVERY - 8f);
            speeding = true;
            Nightmare.speed(world, store, boss, name(), center(), SPEED_RADIUS, () -> speeding = false);
        } else if (dreadClock >= DREAD_EVERY) {
            dreadClock = 0f;
            Nightmare.dread(world, store, boss, name());
        } else if (stormClock >= STORM_EVERY) {
            stormClock = 0f;
            storm(world, store, inside);
        }
        if (harrowClock >= HARROW_EVERY) {
            harrowClock = 0f;
            harrow(world, store, inside);
        }
        return Outcome.NONE;
    }

    // --- Aspects du bord ------------------------------------------------------------------------------------------

    private void raiseEdge(World world, Store<EntityStore> store, int kind) {
        if (edge[kind] != null && Spawns.alive(store, edge[kind])) {
            return;
        }
        Vector3d at = Spawns.point(SilentSurfLayout.EDGE_ASPECTS[kind]);
        edge[kind] = Spawns.spawnFoe(world, store, SilentSurf.ASPECTS[kind], at, Telegraphs.yawToward(at, center()));
        Telegraphs.particle(store, "Nakasar_Fractal_Aspect_Rise", at, 1.4f);
    }

    /** Lien de chaque Aspect du bord vers le joueur le plus proche ; tenu trop longtemps : Fantasmagorie. */
    private void tethers(World world, Store<EntityStore> store, List<PlayerRef> inside, float dt) {
        tetherFx += dt;
        boolean fx = tetherFx >= 0.5f;
        if (fx) {
            tetherFx = 0f;
        }
        for (int i = 0; i < edge.length; i++) {
            Tether t = tethers[i];
            if (t == null) {
                continue;
            }
            Vector3d from = edge[i] == null ? null : Telegraphs.position(store, edge[i]);
            if (from == null) {
                t.target = null;
                continue;
            }
            if (t.cooldown > 0) {
                t.cooldown -= dt;
                continue;
            }
            PlayerRef near = null;
            double best = TETHER_RANGE;
            for (PlayerRef p : inside) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && at.distance(from) < best && !phantasmOf(p.getUuid())) {
                    best = at.distance(from);
                    near = p;
                }
            }
            if (near == null) {
                t.target = null;
                t.held = 0f;
                continue;
            }
            if (!near.getUuid().equals(t.target)) {
                t.target = near.getUuid();
                t.held = 0f;
                SilentSurf.tellPlayer(near, "kanaxai.tether");
            }
            t.held += dt;
            Vector3d to = fx ? Telegraphs.position(store, near.getReference()) : null;
            if (to != null) {
                Vector3d a = new Vector3d(from).add(0, 1.6, 0);
                Vector3d b = new Vector3d(to).add(0, 1.0, 0);
                int n = (int) Math.max(3, a.distance(b) / 1.5);
                for (int k = 1; k < n; k++) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Tether", new Vector3d(a).lerp(b, k / (double) n), 1f);
                }
            }
            if (t.held >= TETHER_SECONDS) {
                t.held = 0f;
                t.target = null;
                t.cooldown = TETHER_COOLDOWN;
                phantasm(world, store, near);
            }
        }
    }

    /** Tir de herse : chaque Aspect du bord vise un joueur ; touché, il prend l'état de cet Aspect. */
    private void harrow(World world, Store<EntityStore> store, List<PlayerRef> inside) {
        float windup = HARROW_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        List<Integer> kinds = new ArrayList<>();
        for (int i = 0; i < edge.length; i++) {
            if (edge[i] == null) {
                continue;
            }
            PlayerRef p = inside.get(ThreadLocalRandom.current().nextInt(inside.size()));
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                circles.add(new Telegraphs.Circle(at, HARROW_RADIUS, now, windup));
                kinds.add(i);
            }
        }
        if (circles.isEmpty()) {
            return;
        }
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.harrow"));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            boolean done = true;
            for (Telegraphs.Circle c : circles) {
                done &= c.step(s, t);
            }
            if (!done) {
                return false;
            }
            for (int k = 0; k < circles.size(); k++) {
                Telegraphs.Circle c = circles.get(k);
                Telegraphs.particle(s, "Nakasar_Fractal_Aspect_Rise", c.origin(), 1.2f);
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && c.contains(at)) {
                        condition(s, p.getReference(), kinds.get(k), c.origin());
                    }
                }
            }
            return true;
        });
    }

    private static void condition(ComponentAccessor<EntityStore> s, Ref<EntityStore> ref, int kind, Vector3d from) {
        Hurt.percent(s, ref, 0.08f, "Physical");
        switch (SilentSurf.ASPECT_KINDS[kind]) {
            case "Death" -> Hurt.percent(s, ref, 0.15f, SilentSurf.TORMENT_CAUSE);
            case "Exposure" -> Hurt.effect(s, ref, "Nakasar_Fractal_Exposure", 8f);
            case "Fear" -> {
                Hurt.effect(s, ref, "Nakasar_Fractal_Fear", 2f);
                Vector3d at = Telegraphs.position(s, ref);
                if (at != null) {
                    Vector3d away = new Vector3d(at).sub(from);
                    away.y = 0;
                    Moves.velocity(s, ref, (away.lengthSquared() < 1e-4 ? new Vector3d(1, 0, 0) : away.normalize())
                            .mul(8).add(0, 3, 0));
                }
            }
            case "Lethargy" -> Hurt.effect(s, ref, "Nakasar_Fractal_Lethargy", 5f);
            default -> Hurt.effect(s, ref, "Nakasar_Fractal_Torment", 6f);
        }
    }

    // --- Tempête déchirante ------------------------------------------------------------------------------------------

    private void storm(World world, Store<EntityStore> store, List<PlayerRef> inside) {
        storms++;
        List<PlayerRef> marked = Spawns.pick(inside, Math.min(inside.size(), storms));
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.storm"));
        float windup = STORM_WINDUP * FractalRuns.windupFactor(world);
        long[] begin = {-1};
        long[] shown = {0};
        int e = epoch;
        TelegraphSystem.start(world, (w, s, now) -> {
            if (!live(e)) {
                return true;
            }
            if (begin[0] < 0) {
                begin[0] = now;
            }
            long left = begin[0] + Telegraphs.seconds(windup) - now;
            if (left > 0) {
                if (now - shown[0] > Telegraphs.seconds(0.5f)) {
                    shown[0] = now;
                    for (PlayerRef p : marked) {
                        Vector3d at = Telegraphs.position(s, p.getReference());
                        if (at != null) {
                            Telegraphs.circle(s, at, STORM_RADIUS, Math.max(0.3f, left / 1e9f));
                        }
                    }
                }
                return false;
            }
            List<PlayerRef> all = Spawns.alivePlayers(w, s);
            for (PlayerRef p : marked) {
                Vector3d at = Telegraphs.position(s, p.getReference());
                if (at == null) {
                    continue;
                }
                Vector3d spot = new Vector3d(at);
                Telegraphs.particle(s, "Nakasar_Fractal_Cleaver", spot, 0.6f);
                Telegraphs.sound(s, "SFX_Ability_Ground_Slam_Spike_Erupt", spot);
                for (PlayerRef q : all) {
                    Vector3d qa = Telegraphs.position(s, q.getReference());
                    if (qa != null && Telegraphs.horizontal(qa, spot) <= STORM_RADIUS && Math.abs(qa.y() - spot.y()) < 3) {
                        Hurt.percent(s, q.getReference(), STORM_PART, SilentSurf.TORMENT_CAUSE);
                    }
                }
                pools.add(new Pool(spot, now + Telegraphs.seconds(POOL_SECONDS)));
            }
            return true;
        });
    }

    private void pools(Store<EntityStore> store, List<PlayerRef> inside, float dt) {
        long now = System.nanoTime();
        pools.removeIf(p -> now >= p.until());
        poolFx += dt;
        boolean fx = poolFx >= 1f;
        if (fx) {
            poolFx = 0f;
        }
        for (Pool pool : pools) {
            if (fx) {
                Telegraphs.particle(store, "Nakasar_Fractal_Bleeding_Pool", pool.at(), (float) POOL_RADIUS);
            }
            for (PlayerRef p : inside) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, pool.at()) <= POOL_RADIUS && Math.abs(at.y() - pool.at().y()) < 2) {
                    Hurt.percent(store, p.getReference(), POOL_PART_PER_SECOND * dt, SilentSurf.TORMENT_CAUSE);
                    Hurt.effect(store, p.getReference(), "Nakasar_Fractal_Bleeding", 1.5f);
                }
            }
        }
    }

    // --- Ombres rassemblées et Fantasmagorie ----------------------------------------------------------------------

    private void shadows(World world, Store<EntityStore> store, List<PlayerRef> inside, float health, long now) {
        if (shadowsUntil > 0) {
            boolean broken = !Defiance.isOpen(boss) && now < shadowsUntil - Telegraphs.seconds(0.15f);
            if (broken) {
                shadowsUntil = 0;
            } else if (now >= shadowsUntil) {
                shadowsUntil = 0;
                Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.shadowsFail"));
                PlayerRef victim = inside.get(ThreadLocalRandom.current().nextInt(inside.size()));
                phantasm(world, store, victim);
            }
            return;
        }
        if (shadows < 9 && health <= 0.9f - 0.1f * shadows + 0.001f && !speeding) {
            shadows++;
            BossStun.interrupt(world, store, boss);
            Defiance.open(world, boss, SHADOWS_WINDOW);
            shadowsUntil = now + Telegraphs.seconds(SHADOWS_WINDOW);
            Vector3d at = Telegraphs.position(store, boss);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Shadows", at, 2f);
            }
            Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.shadows"));
        }
    }

    private boolean phantasmOf(UUID player) {
        for (Phantasm p : phantasms.values()) {
            if (p.owner().equals(player)) {
                return true;
            }
        }
        return false;
    }

    /** `player` part en Fantasmagorie : un Aspect privé l'attend sur une île libre. */
    private void phantasm(World world, Store<EntityStore> store, PlayerRef player) {
        if (phantasmOf(player.getUuid())) {
            return;
        }
        double[][] islands = SilentSurfLayout.ISLANDS;
        List<Integer> free = new ArrayList<>();
        for (int i = 0; i < islands.length; i++) {
            free.add(i);
        }
        for (Ref<EntityStore> ref : phantasms.keySet()) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at != null) {
                free.removeIf(i -> Telegraphs.horizontal(at, Spawns.point(islands[i])) < 8);
            }
        }
        if (free.isEmpty()) {
            return;
        }
        int island = free.get(ThreadLocalRandom.current().nextInt(free.size()));
        int kind = ThreadLocalRandom.current().nextInt(SilentSurf.ASPECTS.length);
        Vector3d at = Spawns.point(islands[island]);
        Ref<EntityStore> aspect = Spawns.spawnFoe(world, store, SilentSurf.ASPECTS[kind], at,
                Telegraphs.yawToward(at, center()));
        if (aspect == null) {
            return;
        }
        AspectVisibilitySystem.hide(aspect, player.getUuid());
        phantasms.put(aspect, new Phantasm(player.getUuid(), System.nanoTime() + Telegraphs.seconds(PHANTASM_SECONDS)));
        Hurt.effect(store, player.getReference(), "Nakasar_Fractal_Phantasmagoria", PHANTASM_SECONDS);
        player.sendMessage(Message.translation(SilentSurf.MESSAGES + "kanaxai.phantasm").param("island", island + 1));
    }

    private void phantasms(World world, Store<EntityStore> store, long now) {
        Iterator<Map.Entry<Ref<EntityStore>, Phantasm>> it = phantasms.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<Ref<EntityStore>, Phantasm> e = it.next();
            PlayerRef owner = SilentSurf.player(world, e.getValue().owner());
            boolean alive = Spawns.alive(store, e.getKey());
            if (alive && now < e.getValue().until() && owner != null) {
                continue;
            }
            if (alive && owner != null) {
                Hurt.percent(store, owner.getReference(), PHANTASM_PART, SilentSurf.TORMENT_CAUSE);
                Hurt.effect(store, owner.getReference(), "Nakasar_Fractal_Fear", 2f);
            }
            if (owner != null) {
                Hurt.clear(store, owner.getReference(), "Nakasar_Fractal_Phantasmagoria");
            }
            AspectVisibilitySystem.forget(e.getKey());
            Spawns.remove(store, e.getKey());
            it.remove();
        }
    }

    // --- Fendeur de mondes ---------------------------------------------------------------------------------------

    private void rise(World world, Store<EntityStore> store) {
        cleavers++;
        cleaving = true;
        warned = false;
        cleaverAt = System.nanoTime() + Telegraphs.seconds(CLEAVER_SECONDS * FractalRuns.windupFactor(world));
        BossStun.interrupt(world, store, boss);
        BossStun.hold(world, store, boss);
        Defiance.forget(boss);
        shadowsUntil = 0;
        store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
        Vector3d up = new Vector3d(center()).add(0, 7, 0);
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(up, new Rotation3f()));
        Telegraphs.particle(store, "Nakasar_Fractal_Shadows", center(), 3f);
        for (int k = 0; k < edge.length; k++) {
            raiseEdge(world, store, k);
        }
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.cleaver"));
    }

    private void cleave(World world, Store<EntityStore> store, List<PlayerRef> inside) {
        cleaving = false;
        int standing = 0;
        for (Ref<EntityStore> ref : edge) {
            if (ref != null && Spawns.alive(store, ref)) {
                standing++;
            }
        }
        float part = Math.min(0.95f, CLEAVER_BASE + CLEAVER_PER_ASPECT * standing);
        Vector3d c = center();
        Telegraphs.particle(store, "Nakasar_Fractal_Cleaver", c, 4f);
        Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", c);
        for (PlayerRef p : inside) {
            Hurt.percent(store, p.getReference(), part, SilentSurf.TORMENT_CAUSE);
            Hurt.effect(store, p.getReference(), Agony.EFFECT, CLEAVER_AGONY);
        }
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.cleaverHit"));
        store.tryRemoveComponent(boss, Invulnerable.getComponentType());
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(c, new Rotation3f()));
        BossStun.release(store, boss);
        speedClock = SPEED_EVERY - 6f;
    }

    // --- coups ---------------------------------------------------------------------------------------------------

    /**
     * Kanaxai : rien pendant le Fendeur de mondes ; sa vie ne passe pas le seuil du prochain Fendeur avant qu'il ne
     * s'élève. Aspect de Fantasmagorie : seul son joueur le blesse.
     */
    void filter(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> victim, String victimRole,
                Ref<EntityStore> attacker, UUID attackerId, Damage damage) {
        if (!engaged) {
            return;
        }
        if (victim.equals(boss)) {
            if (cleaving) {
                damage.setCancelled(true);
                return;
            }
            if (cleavers < CLEAVER_AT.length) {
                EntityStatMap stats = accessor.getComponent(victim, EntityStatMap.getComponentType());
                EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
                if (health != null) {
                    float floor = health.getMax() * CLEAVER_AT[cleavers];
                    damage.setAmount(Math.max(0f, Math.min(damage.getAmount(), health.get() - floor)));
                }
            }
            return;
        }
        UUID owner = AspectVisibilitySystem.owner(victim);
        if (owner != null && !owner.equals(attackerId)) {
            damage.setCancelled(true);
        }
    }

    /** Coup d'un Aspect de Fantasmagorie : il ne touche que son joueur (les autres ne le voient pas). */
    static boolean strayPhantasmHit(Ref<EntityStore> attacker, UUID victimId) {
        UUID owner = attacker == null ? null : AspectVisibilitySystem.owner(attacker);
        return owner != null && !owner.equals(victimId);
    }

    // --- remise à zéro -----------------------------------------------------------------------------------------------

    private boolean idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged || dead) {
            return false;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return false;
        }
        clear(store);
        Spawns.tellAll(world, Message.translation(SilentSurf.MESSAGES + "kanaxai.reset"));
        return true;
    }

    void clear(Store<EntityStore> store) {
        if (boss != null) {
            BossStun.release(store, boss);
            Defiance.forget(boss);
            if (boss.isValid()) {
                store.tryRemoveComponent(boss, Invulnerable.getComponentType());
            }
        }
        Spawns.remove(store, boss);
        boss = null;
        for (int i = 0; i < edge.length; i++) {
            Spawns.remove(store, edge[i]);
            edge[i] = null;
        }
        for (Ref<EntityStore> ref : phantasms.keySet()) {
            AspectVisibilitySystem.forget(ref);
            Spawns.remove(store, ref);
        }
        phantasms.clear();
        pools.clear();
        engaged = false;
        epoch++;
        cleaving = false;
        speeding = false;
        shadowsUntil = 0;
        idle = 0f;
    }

    static String name() {
        return SilentSurf.MESSAGES + "npc.Kanaxai.name";
    }
}
