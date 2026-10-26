package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Ai, gardienne du pic, dans l'arène du sommet (GW2 : dernier boss du Pic de Sunqua). Coup de bâton et rafale : rôle
 * JSON. En Java, trois éléments selon sa vie :
 * <ul>
 *   <li>air (100-66 %) : ondes d'orbes (elle file au bord de l'arène et lance {@value #LINE_WAVES} vagues de deux bandes
 *   de {@link SunquaPeakLayout#ORB_LINE_LENGTH} x {@link SunquaPeakLayout#ORB_LINE_WIDTH} blocs ; sa défiance brisée,
 *   elle vacille et les vagues cessent), bombes d'orage (un cercle de {@value #BOMB_RADIUS} blocs sur chaque joueur :
 *   {@value #BOMB_OWN} des PV pour le sien, {@value #BOMB_OTHER} pour chaque autre où l'on se tient) et balayage (cône
 *   de {@value #SWEEP_DEGREES}° sur {@value #SWEEP_RADIUS} blocs) ;</li>
 *   <li>à 66 % : front d'orage, protégée au centre tant que les quatre nuages ({@link StormClouds}) ne sont pas
 *   dispersés ; puis feu (66-33 %) : météores et frappe extrême ({@link Meteors}), balayage ;</li>
 *   <li>à 33 % : pluie de météores ({@value #RAIN_SECONDS} s, protégée), puis eau : Marché des marées ({@link Tether},
 *   l'orbe est Ai elle-même) et marée partagée (un cercle de {@value #TIDE_RADIUS} blocs sur un joueur :
 *   {@value #TIDE_PART} des PV partagés entre tous ceux qui s'y tiennent).</li>
 * </ul>
 * Au rang Maître, Ai vaincue s'assombrit (Ai assombrie, neuve) : des craintes suivent chaque joueur et éclatent au bout
 * de {@value #FEAR_SECONDS} s (cercle de {@value #FEAR_RADIUS} blocs) si on ne les tue pas. Personne sur l'arène pendant
 * {@value SunquaPeak#RESET_SECONDS} s : tout disparaît, Ai reviendra neuve.
 */
final class Ai {

    enum Element { AIR, STORM, FIRE, RAIN, WATER, DARK }

    static final float STORM_AT = 0.66f;
    static final float RAIN_AT = 0.33f;
    static final float LINES_FIRST = 10f;
    static final float LINES_EVERY = 24f;
    static final int LINE_WAVES = 3;
    static final float LINE_GAP = 3f;
    static final float LINE_WINDUP = 1.5f;
    static final float LINE_PART = 0.2f;
    static final float LINES_DEFIANCE = 10f;
    static final float BOMBS_FIRST = 6f;
    static final float BOMBS_EVERY = 18f;
    static final double BOMB_RADIUS = 3;
    static final float BOMB_DELAY = 1.5f;
    static final float BOMB_WINDUP = 2f;
    static final float BOMB_OWN = 0.2f;
    static final float BOMB_OTHER = 0.4f;
    static final float SWEEP_FIRST = 4f;
    static final float SWEEP_EVERY = 14f;
    static final int SWEEP_DEGREES = 120;
    static final double SWEEP_RADIUS = 12;
    static final float SWEEP_WINDUP = 1.5f;
    static final float SWEEP_PART = 0.25f;
    static final float METEOR_FIRST = 5f;
    static final float METEOR_EVERY = 22f;
    static final float RAIN_SECONDS = 15f;
    static final float RAIN_EVERY = 1.5f;
    static final float RAIN_WINDUP = 2f;
    static final float TIDE_FIRST = 6f;
    static final float TIDE_EVERY = 16f;
    static final double TIDE_RADIUS = 3;
    static final float TIDE_WINDUP = 4f;
    static final float TIDE_PART = 0.9f;
    /** Zone favorable verte (tools/generate_warnings.py, GREEN_ZONE), comme les dents du récif de la Sirène. */
    static final String GREEN_ZONE = "Nakasar_Fractal_Green_Zone";
    static final float FEAR_EVERY = 20f;
    static final float FEAR_SECONDS = 15f;
    static final double FEAR_RADIUS = 4;
    static final float FEAR_WINDUP = 1.5f;
    static final float FEAR_PART = 0.4f;

    private final StormClouds clouds = new StormClouds(SunquaPeakLayout.SUMMIT_CLOUDS);
    private final Meteors meteors = new Meteors();
    private final Tether tether = new Tether();
    private Ref<EntityStore> boss;
    private boolean engaged;
    private boolean arrived;
    private Element element = Element.AIR;
    private float idle;
    private float lines;
    private long linesUntil;
    private float bombs;
    private float sweep;
    private float meteor;
    private float extreme = -1f;
    private float rain;
    private float rainLeft;
    private float tide;
    private float fear;
    private float swirl;
    /** Une crainte et l'instant (System.nanoTime) où elle éclate. */
    private record Fear(Ref<EntityStore> ref, long end) {
    }

    private final List<Fear> fears = new ArrayList<>();
    private int epoch;

    Tether tether() {
        return tether;
    }

    boolean shielded() {
        return element == Element.STORM || element == Element.RAIN;
    }

    private boolean live(int e) {
        return engaged && epoch == e;
    }

    /** Vrai quand Ai (et, au rang Maître, Ai assombrie) est vaincue. */
    boolean step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(SunquaPeakLayout.SUMMIT);
        double radius = SunquaPeakLayout.SUMMIT_RADIUS;
        if (!arrived && !SunquaPeak.near(store, players, Spawns.point(SunquaPeakLayout.RISE_END), 6).isEmpty()) {
            arrived = true;
            Gates.checkpoint(world, SunquaPeakLayout.RISE_END, SunquaPeak.MESSAGES + "checkpoint");
        }
        // Jusqu'à 3 blocs au-dessus des nuages d'orage : un saut chargé qui les traverse compte.
        List<PlayerRef> here = SunquaPeak.near(store, players, c, radius + 3, StormClouds.HEIGHT_HINT + 3);
        if (!engaged) {
            if (!SunquaPeak.near(store, players, c, radius - 3).isEmpty()) {
                engage(world, store, c, Element.AIR);
            }
            return false;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= SunquaPeak.RESET_SECONDS) {
                clear(world, store, st);
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.reset"));
            }
            return false;
        }
        idle = 0f;
        if (boss == null || !boss.isValid() || !Spawns.alive(store, boss)) {
            if (element != Element.DARK && SunquaPeak.rank(world) >= 3) {
                darken(world, store, st, c);
                return false;
            }
            clear(world, store, st);
            return true;
        }
        Leash.keepOnDisc(store, boss, c, radius - 1, 2, SunquaPeak.FALL_LIMIT);
        float health = Hurt.healthFraction(store, boss);
        switch (element) {
            case AIR -> {
                if (health <= STORM_AT + 0.001f) {
                    storm(world, store, st, c);
                    return false;
                }
                air(world, store, here, c, dt);
            }
            case STORM -> {
                BossStun.hold(world, store, boss);
                swirl += dt;
                if (swirl >= 0.5f) {
                    swirl = 0f;
                    Telegraphs.particle(store, "Nakasar_Fractal_Tornado", c, 2.5f);
                }
                if (clouds.step(world, store, here, dt)) {
                    st.leap.remove(world, SunquaPeakLayout.SUMMIT_ORBS);
                    BossStun.release(store, boss);
                    element = Element.FIRE;
                    meteor = METEOR_EVERY - METEOR_FIRST;
                    sweep = 0f;
                    Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.fire"));
                }
            }
            case FIRE -> {
                if (health <= RAIN_AT + 0.001f) {
                    BossStun.interrupt(world, store, boss);
                    SunquaPeak.move(store, boss, c, Spawns.point(SunquaPeakLayout.RISE_END));
                    element = Element.RAIN;
                    rainLeft = RAIN_SECONDS;
                    rain = 0f;
                    extreme = -1f;
                    Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.meteors"));
                    Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.rain"));
                    return false;
                }
                fire(world, store, here, c, dt);
            }
            case RAIN -> {
                BossStun.hold(world, store, boss);
                rainLeft -= dt;
                rain += dt;
                if (rain >= RAIN_EVERY) {
                    rain = 0f;
                    List<Vector3d> points = new ArrayList<>();
                    PlayerRef p = here.get((int) (Math.random() * here.size()));
                    Vector3d at = Telegraphs.position(store, p.getReference());
                    if (at != null) {
                        points.add(at);
                    }
                    double a = Math.random() * Math.PI * 2;
                    double r = Math.random() * (radius - 2);
                    points.add(new Vector3d(c.x() + Math.cos(a) * r, c.y(), c.z() + Math.sin(a) * r));
                    meteors.rain(world, store, points, RAIN_WINDUP, false);
                }
                if (rainLeft <= 0f) {
                    meteors.crumble(world, store);
                    BossStun.release(store, boss);
                    element = Element.WATER;
                    tide = TIDE_EVERY - TIDE_FIRST;
                    sweep = 0f;
                    tether.begin();
                    Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.water")
                            .param("total", Tether.MAX_STACKS));
                    Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.vulnerable"));
                }
            }
            case WATER -> water(world, store, here, c, dt);
            case DARK -> dark(world, store, st, here, dt);
            default -> {
            }
        }
        return false;
    }

    // --- air -----------------------------------------------------------------------------------------------------

    private void air(World world, Store<EntityStore> store, List<PlayerRef> here, Vector3d c, float dt) {
        long now = System.nanoTime();
        if (linesUntil != 0) {
            if (!Defiance.isOpen(boss) && now < linesUntil - Telegraphs.seconds(0.15f)) {
                linesUntil = 0;
                epoch++;   // les vagues restantes ne partent pas
                BossStun.release(store, boss);
                BossStun.stun(world, store, boss, Defiance.STUN_SECONDS, BossStun.EFFECT);
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.lines.broken"));
            } else if (now >= linesUntil) {
                linesUntil = 0;
                Defiance.forget(boss);
                BossStun.release(store, boss);
            } else {
                BossStun.hold(world, store, boss);
            }
            return;
        }
        lines += dt;
        if (lines >= LINES_EVERY) {
            lines = 0f;
            lines(world, store, c);
            return;
        }
        bombs += dt;
        if (bombs >= BOMBS_EVERY) {
            bombs = 0f;
            bombs(world, store, here);
        }
        sweepStep(world, store, here, dt);
    }

    /** Ai file au bord et lance des vagues de bandes en travers de l'arène ; sa défiance est ouverte. */
    private void lines(World world, Store<EntityStore> store, Vector3d c) {
        BossStun.interrupt(world, store, boss);
        double a = Math.random() * Math.PI * 2;
        double edge = SunquaPeakLayout.SUMMIT_RADIUS - 2;
        Vector3d at = new Vector3d(c.x() + Math.cos(a) * edge, c.y(), c.z() + Math.sin(a) * edge);
        SunquaPeak.move(store, boss, at, c);
        BossStun.hold(world, store, boss);
        float total = LINE_GAP * (LINE_WAVES - 1) + LINE_WINDUP + 1f;
        Defiance.open(world, boss, Math.max(LINES_DEFIANCE, total));
        linesUntil = System.nanoTime() + Telegraphs.seconds(Math.max(LINES_DEFIANCE, total));
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.lines"));
        double facing = a + Math.PI;   // du bord vers le centre
        double half = SunquaPeakLayout.ORB_LINE_LENGTH / 2;
        Vector3d back = new Vector3d(c.x() - Math.cos(facing) * half, c.y(), c.z() - Math.sin(facing) * half);
        int e = epoch;
        long begin = System.nanoTime();
        float windup = LINE_WINDUP * FractalRuns.windupFactor(world);
        List<Telegraphs.Strip> strips = new ArrayList<>();
        int[] sent = {0};
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (sent[0] < LINE_WAVES && t >= begin + Telegraphs.seconds(0.5f + LINE_GAP * sent[0])) {
                sent[0]++;
                double first = (Math.random() * 2 - 1) * (SunquaPeakLayout.SUMMIT_RADIUS - 4);
                double second = first + (first > 0 ? -1 : 1) * (6 + Math.random() * 8);
                for (double off : new double[]{first, second}) {
                    Vector3d start = new Vector3d(back.x() - Math.sin(facing) * off, c.y(), back.z() + Math.cos(facing) * off);
                    strips.add(new Telegraphs.Strip(start, facing, SunquaPeakLayout.ORB_LINE_LENGTH,
                            SunquaPeakLayout.ORB_LINE_WIDTH, t, windup));
                }
            }
            for (int i = strips.size() - 1; i >= 0; i--) {
                Telegraphs.Strip strip = strips.get(i);
                if (!strip.step(s, t)) {
                    continue;
                }
                strips.remove(i);
                for (double along = 2; along < SunquaPeakLayout.ORB_LINE_LENGTH; along += 4) {
                    Telegraphs.particle(s, "Nakasar_Fractal_Lightning_Orb_Glow", strip.at(along, 0), 1f);
                }
                SunquaPeak.strike(w, s, strip, LINE_PART, SunquaPeak.KNOCKED_DOWN, 1f);
            }
            return sent[0] >= LINE_WAVES && strips.isEmpty();
        });
    }

    /** Bombes d'orage : un cercle sur chaque joueur ; chacun prend peu du sien, beaucoup de ceux des autres. */
    private void bombs(World world, Store<EntityStore> store, List<PlayerRef> here) {
        List<PlayerRef> targets = new ArrayList<>(here);
        for (PlayerRef p : targets) {
            Hurt.effect(store, p.getReference(), "Nakasar_Fractal_Storm_Marked", BOMB_DELAY + BOMB_WINDUP);
        }
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.bombs"));
        int e = epoch;
        long begin = System.nanoTime();
        float windup = BOMB_WINDUP * FractalRuns.windupFactor(world);
        List<Telegraphs.Circle> circles = new ArrayList<>();
        List<PlayerRef> owners = new ArrayList<>();
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (circles.isEmpty()) {
                if (t < begin + Telegraphs.seconds(BOMB_DELAY)) {
                    return false;
                }
                for (PlayerRef p : targets) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null) {
                        circles.add(new Telegraphs.Circle(at, BOMB_RADIUS, t, windup));
                        owners.add(p);
                    }
                }
                if (circles.isEmpty()) {
                    return true;
                }
            }
            boolean ready = true;
            for (Telegraphs.Circle circle : circles) {
                ready &= circle.step(s, t);
            }
            if (!ready) {
                return false;
            }
            for (Telegraphs.Circle circle : circles) {
                Telegraphs.particle(s, "Nakasar_Fractal_Storm_Disperse", circle.origin(), 1.2f);
            }
            for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                Vector3d at = Telegraphs.position(s, p.getReference());
                if (at == null) {
                    continue;
                }
                float part = 0f;
                for (int i = 0; i < circles.size(); i++) {
                    if (circles.get(i).contains(at)) {
                        part += owners.get(i).getUuid().equals(p.getUuid()) ? BOMB_OWN : BOMB_OTHER;
                    }
                }
                if (part > 0f) {
                    Hurt.percent(s, p.getReference(), Math.min(1f, part), SunquaPeak.CAUSE);
                    Hurt.effect(s, p.getReference(), "Nakasar_Fractal_Dazed", 1.5f);
                }
            }
            return true;
        });
    }

    private void sweepStep(World world, Store<EntityStore> store, List<PlayerRef> here, float dt) {
        sweep += dt;
        if (sweep < SWEEP_EVERY) {
            return;
        }
        sweep = 0f;
        Vector3d b = Telegraphs.position(store, boss);
        PlayerRef target = b == null ? null : Spawns.nearestPlayer(store, here, b);
        Vector3d at = target == null ? null : Telegraphs.position(store, target.getReference());
        if (at == null) {
            return;
        }
        BossStun.interrupt(world, store, boss);
        SunquaPeak.move(store, boss, b, at);
        Telegraphs.Cone cone = new Telegraphs.Cone(b, Telegraphs.angle(b, at), Math.toRadians(SWEEP_DEGREES),
                SWEEP_RADIUS, System.nanoTime(), SWEEP_WINDUP * FractalRuns.windupFactor(world));
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.sweep"));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (!cone.step(s, t)) {
                return false;
            }
            Telegraphs.sound(s, "SFX_Ability_Wind_Strike_Slash", cone.origin());
            SunquaPeak.strike(w, s, cone, SWEEP_PART, SunquaPeak.KNOCKED_DOWN, 1f);
            return true;
        });
    }

    // --- orage, feu, eau ------------------------------------------------------------------------------------------

    private void storm(World world, Store<EntityStore> store, SunquaPeak.State st, Vector3d c) {
        linesUntil = 0;
        epoch++;
        Defiance.forget(boss);
        BossStun.release(store, boss);
        BossStun.interrupt(world, store, boss);
        SunquaPeak.move(store, boss, c, Spawns.point(SunquaPeakLayout.RISE_END));
        element = Element.STORM;
        clouds.begin();
        for (int[] at : SunquaPeakLayout.SUMMIT_ORBS) {
            st.leap.site(world, at, true);
        }
        Telegraphs.sound(store, "SFX_Ability_Wind_Strike_Slash", c);
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.storm"));
    }

    private void fire(World world, Store<EntityStore> store, List<PlayerRef> here, Vector3d c, float dt) {
        meteor += dt;
        if (meteor >= METEOR_EVERY) {
            meteor = 0f;
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.meteors"));
            meteors.call(world, store, here);
            extreme = FuryOfTheMountain.EXTREME_AFTER;
        }
        if (extreme >= 0f) {
            extreme -= dt;
            if (extreme < 0f) {
                meteors.extreme(world, store, boss, c, SunquaPeakLayout.SUMMIT_RADIUS + 1, "fury.extreme");
            }
            return;
        }
        sweepStep(world, store, here, dt);
    }

    private void water(World world, Store<EntityStore> store, List<PlayerRef> here, Vector3d c, float dt) {
        Vector3d b = Telegraphs.position(store, boss);
        if (b != null) {
            tether.step(world, store, new Vector3d(b).add(0, 2.5, 0), here, dt);
        }
        tide += dt;
        if (tide >= TIDE_EVERY) {
            tide = 0f;
            sharedTide(world, store, here);
        }
        sweepStep(world, store, here, dt);
    }

    /**
     * Marée partagée : ses dégâts se partagent entre ceux qui se tiennent dans le cercle. Zone favorable (on doit y
     * entrer) : cercle vert ({@link #GREEN_ZONE}) qui suit le joueur visé pendant la charge, reposé toutes les 0,5 s ;
     * le coup part du centre du cercle à la fin, même rayon {@value #TIDE_RADIUS}.
     */
    private void sharedTide(World world, Store<EntityStore> store, List<PlayerRef> here) {
        PlayerRef target = here.get((int) (Math.random() * here.size()));
        Vector3d start = Telegraphs.position(store, target.getReference());
        if (start == null) {
            return;
        }
        float windup = TIDE_WINDUP * FractalRuns.windupFactor(world);
        Hurt.effect(store, target.getReference(), "Nakasar_Fractal_Shared_Tide", windup);
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.shared").param("name", target.getUsername()));
        long end = System.nanoTime() + Telegraphs.seconds(windup);
        Vector3d[] center = {new Vector3d(start)};
        long[] shown = {0L};
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            Vector3d now = Telegraphs.position(s, target.getReference());
            if (now != null) {
                center[0] = new Vector3d(now);
            }
            if (t < end) {
                if (t - shown[0] >= Telegraphs.seconds(0.5f)) {
                    shown[0] = t;
                    Telegraphs.particle(s, GREEN_ZONE, new Vector3d(center[0]).add(0, 0.1, 0),
                            (float) (Telegraphs.WARNING_SCALE * TIDE_RADIUS));
                    Telegraphs.particle(s, "Nakasar_Fractal_Shared_Mark", center[0], 1.2f);
                }
                return false;
            }
            List<PlayerRef> inside = new ArrayList<>();
            for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && Telegraphs.inCircle(pos, center[0], TIDE_RADIUS)) {
                    inside.add(p);
                }
            }
            if (inside.isEmpty() && target.getReference() != null && target.getReference().isValid()) {
                inside.add(target);
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Tide_Burst", center[0], 1.5f);
            Telegraphs.sound(s, "SFX_Water_MoveIn", center[0]);
            for (PlayerRef p : inside) {
                Hurt.percent(s, p.getReference(), TIDE_PART / inside.size(), SunquaPeak.CAUSE);
            }
            return true;
        });
    }

    // --- Ai assombrie (rang Maître) ---------------------------------------------------------------------------

    private void darken(World world, Store<EntityStore> store, SunquaPeak.State st, Vector3d c) {
        tether.stop(world, store);
        meteors.clear(world, store);
        epoch++;
        // DARK d'abord : si Ai assombrie n'apparaît pas, le pas suivant compte la victoire au lieu de recommencer.
        element = Element.DARK;
        engage(world, store, c, Element.DARK);
        if (boss != null && boss.isValid()) {
            Telegraphs.particle(store, "Nakasar_Fractal_Fear_Mist", c, 2.5f);
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.dark"));
        }
    }

    private void dark(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> here, float dt) {
        long now = System.nanoTime();
        for (int i = fears.size() - 1; i >= 0; i--) {
            Fear f = fears.get(i);
            if (!Spawns.alive(store, f.ref())) {
                fears.remove(i);
                continue;
            }
            if (now >= f.end()) {
                Vector3d at = Telegraphs.position(store, f.ref());
                fears.remove(i);
                Spawns.remove(store, f.ref());
                if (at != null) {
                    burst(world, at);
                }
            }
        }
        fear += dt;
        if (fear >= FEAR_EVERY) {
            fear = 0f;
            for (PlayerRef p : here) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at == null) {
                    continue;
                }
                double a = Math.random() * Math.PI * 2;
                Vector3d where = new Vector3d(at.x() + Math.cos(a) * 6, at.y(), at.z() + Math.sin(a) * 6);
                Ref<EntityStore> ref = st.foe(world, store, SunquaPeak.FEAR, SunquaPeak.ground(world, where), at, false);
                if (ref != null) {
                    fears.add(new Fear(ref, now + Telegraphs.seconds(FEAR_SECONDS)));
                    Telegraphs.particle(store, "Nakasar_Fractal_Fear_Mist", where, 1f);
                }
            }
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.fears"));
        }
    }

    private void burst(World world, Vector3d at) {
        Telegraphs.Circle circle = new Telegraphs.Circle(at, FEAR_RADIUS, System.nanoTime(),
                FEAR_WINDUP * FractalRuns.windupFactor(world));
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.fear.burst"));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (!live(e)) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Fear_Mist", circle.origin(), 2f);
            SunquaPeak.strike(w, s, circle, FEAR_PART, "Nakasar_Fractal_Dazed", 2f);
            return true;
        });
    }

    // --- cycle ---------------------------------------------------------------------------------------------------

    /** Un tick du monde : météores qui suivent (aucun pour Ai, mais leur pas est commun). */
    void tick(World world, Store<EntityStore> store, float dt) {
        meteors.tick(world, store, dt);
    }

    private void engage(World world, Store<EntityStore> store, Vector3d c, Element first) {
        boss = Spawns.spawnBoss(world, store, first == Element.DARK ? SunquaPeak.AI_DARK : SunquaPeak.AI, c,
                Telegraphs.yawToward(c, Spawns.point(SunquaPeakLayout.RISE_END)));
        if (boss == null) {
            return;
        }
        engaged = true;
        element = first;
        idle = 0f;
        lines = LINES_EVERY - LINES_FIRST;
        linesUntil = 0;
        bombs = BOMBS_EVERY - BOMBS_FIRST;
        sweep = SWEEP_EVERY - SWEEP_FIRST;
        extreme = -1f;
        fear = FEAR_EVERY - 5f;
        epoch++;
        if (first == Element.AIR) {
            Telegraphs.particle(store, "Nakasar_Fractal_Storm_Disperse", c, 2.5f);
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "ai.enter"));
        }
    }

    private void clear(World world, Store<EntityStore> store, SunquaPeak.State st) {
        epoch++;
        clouds.stop();
        tether.stop(world, store);
        meteors.clear(world, store);
        st.leap.remove(world, SunquaPeakLayout.SUMMIT_ORBS);
        for (Fear f : fears) {
            Spawns.remove(store, f.ref());
        }
        fears.clear();
        if (boss != null) {
            BossStun.release(store, boss);
            Defiance.forget(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
        element = Element.AIR;
        linesUntil = 0;
    }
}
