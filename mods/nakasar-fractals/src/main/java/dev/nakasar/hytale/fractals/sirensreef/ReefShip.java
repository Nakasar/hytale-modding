package dev.nakasar.hytale.fractals.sirensreef;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * La crique et le Fierté du Kraken (GW2) : deux trésors à rapporter au coffre du pont, Mad Jack Squall, le second Calix,
 * la défense du navire, puis la capitaine Arabella Crowe. Pendant les combats :
 * <ul>
 *   <li>Brouillard fétide : hors du pont (plages, passerelles), {@value #FOG_PART} des PV par seconde ; dans l'eau, les
 *   piranhas des profondeurs : {@value #WATER_PART} par seconde ;</li>
 *   <li>Courants fantômes : bandes rouges de {@value #DRAFT_LENGTH} x {@value #DRAFT_WIDTH} blocs en travers du pont
 *   ({@value #DRAFT_WINDUP} s) ; qui y reste passe par-dessus bord ({@value #DRAFT_PART} des PV). Mad Jack dès 50 % (une
 *   bande toutes les {@value #DRAFT_EVERY} s), Calix à 50 % (une) et 25 % (deux), Arabella à 75 % (deux) et 50 %
 *   (trois) ;</li>
 *   <li>Lagon sinistre (Calix, Arabella) toutes les {@value #LAGOON_EVERY} s : cercle rouge de {@value #LAGOON_RADIUS}
 *   blocs sous un joueur ({@value #LAGOON_WINDUP} s), puis une flaque d'eau noire {@value #LAGOON_SECONDS} s, du même
 *   rayon : les joueurs dedans prennent plus de dégâts et sont ralentis, les ennemis dedans en prennent deux fois
 *   moins ;</li>
 *   <li>Dents des profondeurs (Arabella) toutes les {@value #TEETH_EVERY} s : cercle vert de {@value #TEETH_RADIUS} blocs
 *   sur un joueur ({@value #TEETH_WINDUP} s), {@value #TEETH_PART} des PV partagés entre ceux qui sont dedans (seul,
 *   le joueur visé prend tout) ;</li>
 *   <li>fantômes de l'équipage : Mad Jack à 75, 50 et 25 %, Arabella à chaque tranche de 10 % (sans butin) ;
 *   Arabella bondit à la proue à 75 %, à la poupe à 50 %, revient au milieu à 25 % ;</li>
 *   <li>défense : {@value #DEFEND_TOTAL} membres d'équipage à abattre, qui montent par les deux passerelles ;</li>
 *   <li>personne dans la crique pendant {@value #RESET_SECONDS} s : le boss disparaît et reviendra, neuf, quand un
 *   joueur remontera sur le pont (pas de soin, AGENTS.md).</li>
 * </ul>
 */
final class ReefShip {

    enum Step { SOUTH, JACK, NORTH, CALIX, DEFEND, ARABELLA, DONE }

    static final float FOG_PART = 0.02f;
    static final float WATER_PART = 0.05f;
    static final double DRAFT_LENGTH = 14;
    static final double DRAFT_WIDTH = 8;
    static final float DRAFT_WINDUP = 3f;
    static final float DRAFT_EVERY = 12f;
    static final float DRAFT_PART = 0.1f;
    static final double DRAFT_PUSH = 14;
    static final float LAGOON_EVERY = 18f;
    static final double LAGOON_RADIUS = 4;
    static final float LAGOON_WINDUP = 3f;
    static final float LAGOON_SECONDS = 10f;
    static final float LAGOON_PART = 0.03f;
    static final float TEETH_EVERY = 25f;
    static final double TEETH_RADIUS = 3;
    static final float TEETH_WINDUP = 5f;
    static final float TEETH_PART = 0.6f;
    static final int DEFEND_TOTAL = 20;
    static final int DEFEND_ALIVE = 6;
    static final float DEFEND_WAVE = 7f;
    static final float RESET_SECONDS = 25f;
    static final String GREEN_ZONE = "Nakasar_Fractal_Green_Zone";

    private record Lagoon(Vector3d at, long until) {
    }

    private Step step = Step.SOUTH;
    private Ref<EntityStore> boss;
    private boolean pending;
    private final List<Ref<EntityStore>> adds = new ArrayList<>();
    private final List<Lagoon> lagoons = new ArrayList<>();
    private int marks;
    private int jumped;
    private int drafts;
    private float draftClock;
    private float lagoonClock;
    private float teethClock;
    private float idle;
    private float fx;
    private volatile int killed;
    private float waveClock;
    private int epoch;

    /** Arrivée dans la crique : le premier trésor, sur la plage sud, et ses gardiens. */
    void start(World world, Store<EntityStore> store, SirensReef.State st) {
        beach(world, store, st, SirensReefLayout.SOUTH_TREASURE, SirensReefLayout.SOUTH_GHOSTS, "ship.south");
    }

    private static void beach(World world, Store<EntityStore> store, SirensReef.State st, double[] treasure,
                              double[][] guards, String key) {
        st.treasure.begin(world, store, st, new double[][]{treasure}, SirensReefLayout.DECK, false);
        for (int i = 0; i < guards.length; i++) {
            String role = i == 0 ? SirensReef.MARKSMAN : i == guards.length - 1 ? SirensReef.SWINDLER : SirensReef.GHOST;
            Ref<EntityStore> ref = st.foe(world, store, role, guards[i], true);
            if (ref != null && SirensReef.SWINDLER.equals(role)) {
                st.treasure.swindler(ref);
            }
        }
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + key));
    }

    /** Vrai une fois Arabella vaincue. */
    boolean step(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        adds.removeIf(ref -> !Spawns.alive(store, ref));
        long now = System.nanoTime();
        lagoons.removeIf(l -> now >= l.until());
        switch (step) {
            case SOUTH, NORTH -> {
                if (st.treasure.complete()) {
                    st.treasure.end(world, store);
                    step = step == Step.SOUTH ? Step.JACK : Step.CALIX;
                    pending = true;
                }
            }
            case DEFEND -> defend(world, store, st, players, dt);
            case JACK, CALIX, ARABELLA -> fight(world, store, st, players, dt);
            default -> {
            }
        }
        if (step == Step.JACK || step == Step.CALIX || step == Step.ARABELLA || step == Step.DEFEND) {
            if (!pending) {
                hazards(world, store, st, players, dt);
            }
        }
        return step == Step.DONE;
    }

    // --- boss --------------------------------------------------------------------------------------------------

    private String role() {
        return switch (step) {
            case JACK -> SirensReef.JACK;
            case CALIX -> SirensReef.CALIX;
            default -> SirensReef.ARABELLA;
        };
    }

    private void fight(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        if (pending) {
            if (!onDeck(store, players).isEmpty()) {
                summon(world, store, st);
            }
            return;
        }
        if (boss != null && !boss.isValid()) {
            boss = null;
        }
        if (boss == null || Telegraphs.position(store, boss) == null) {
            down(world, store, st);
            return;
        }
        if (inCove(store, players).isEmpty()) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                reset(world, store, st);
            }
            return;
        }
        idle = 0f;
        keepAboard(store, boss);
        float health = Hurt.healthFraction(store, boss);
        List<PlayerRef> aboard = onDeck(store, players);
        switch (step) {
            case JACK -> {
                if (marks < 3 && health <= 0.75f - 0.25f * marks + 0.001f) {
                    marks++;
                    crew(world, store, st, 3);
                }
                drafts = health <= 0.5f ? 1 : 0;
            }
            case CALIX -> {
                drafts = health <= 0.25f ? 2 : health <= 0.5f ? 1 : 0;
                lagoon(world, store, aboard, dt);
            }
            default -> {
                if (marks < 9 && health <= 0.9f - 0.1f * marks + 0.001f) {
                    marks++;
                    crew(world, store, st, 2);
                }
                arabella(world, store, health);
                lagoon(world, store, aboard, dt);
                teeth(world, store, aboard, dt);
            }
        }
        if (drafts > 0) {
            draftClock += dt;
            if (draftClock >= DRAFT_EVERY && !BossStun.isStunned(boss)) {
                draftClock = 0f;
                drafts(world, store, drafts);
            }
        }
    }

    private void summon(World world, Store<EntityStore> store, SirensReef.State st) {
        boss = st.boss(world, store, role(), SirensReefLayout.DECK, SirensReefLayout.SOUTH_BOARD);
        if (boss == null) {
            return;
        }
        pending = false;
        epoch++;
        marks = 0;
        jumped = 0;
        drafts = 0;
        draftClock = DRAFT_EVERY - 4f;
        lagoonClock = LAGOON_EVERY - 8f;
        teethClock = TEETH_EVERY - 12f;
        idle = 0f;
        Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", Spawns.point(SirensReefLayout.DECK), 2f);
        String key = switch (step) {
            case JACK -> "ship.jack";
            case CALIX -> "ship.calix";
            default -> "ship.arabella";
        };
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + key));
    }

    /** Le boss est tombé : la suite. */
    private void down(World world, Store<EntityStore> store, SirensReef.State st) {
        clearFight(store);
        switch (step) {
            case JACK -> {
                step = Step.NORTH;
                beach(world, store, st, SirensReefLayout.NORTH_TREASURE, SirensReefLayout.NORTH_GHOSTS, "ship.north");
            }
            case CALIX -> {
                step = Step.DEFEND;
                killed = 0;
                waveClock = DEFEND_WAVE;
                Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.defend"));
            }
            default -> step = Step.DONE;
        }
    }

    private void reset(World world, Store<EntityStore> store, SirensReef.State st) {
        Spawns.remove(store, boss);
        st.cannons.clear(world, store);
        clearFight(store);
        pending = true;
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.reset"));
    }

    private void clearFight(Store<EntityStore> store) {
        if (boss != null) {
            BossStun.release(store, boss);
        }
        boss = null;
        Spawns.removeAll(store, adds);
        adds.clear();
        lagoons.clear();
        epoch++;
        idle = 0f;
    }

    /** Le boss ne quitte pas le pont : jeté à l'eau ou sur une plage, il y revient. */
    private static void keepAboard(Store<EntityStore> store, Ref<EntityStore> ref) {
        Vector3d at = Telegraphs.position(store, ref);
        if (at == null || store.getComponent(ref, Teleport.getComponentType()) != null || deck(at)) {
            return;
        }
        Vector3d back = Spawns.point(SirensReefLayout.DECK);
        store.putComponent(ref, Teleport.getComponentType(), new Teleport(back, new Rotation3f(0f, Telegraphs.yawToward(back, at), 0f)));
    }

    /** `count` membres d'équipage montent à bord par les passerelles (sans butin). */
    private void crew(World world, Store<EntityStore> store, SirensReef.State st, int count) {
        for (int i = 0; i < count; i++) {
            double[] at = i % 2 == 0 ? SirensReefLayout.SOUTH_BOARD : SirensReefLayout.NORTH_BOARD;
            String role = i % 3 == 2 ? SirensReef.MARKSMAN : SirensReef.GHOST;
            Ref<EntityStore> ref = st.foe(world, store, role, at, false);
            if (ref != null) {
                adds.add(ref);
                Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", Spawns.point(at), 1f);
            }
        }
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.ghosts"));
    }

    /** Arabella bondit d'un bout à l'autre du pont à 75, 50 et 25 %. */
    private void arabella(World world, Store<EntityStore> store, float health) {
        int leaps = health <= 0.25f ? 3 : health <= 0.5f ? 2 : health <= 0.75f ? 1 : 0;
        drafts = health <= 0.5f ? 3 : health <= 0.75f ? 2 : 0;
        if (leaps <= jumped) {
            return;
        }
        jumped = leaps;
        double[] to = leaps == 1 ? SirensReefLayout.DECK_EAST : leaps == 2 ? SirensReefLayout.DECK_WEST : SirensReefLayout.DECK;
        Vector3d from = Telegraphs.position(store, boss);
        Vector3d dest = Spawns.point(to);
        BossStun.interrupt(world, store, boss);
        if (from != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", from, 1.5f);
        }
        store.putComponent(boss, Teleport.getComponentType(), new Teleport(dest, new Rotation3f(0f,
                Telegraphs.yawToward(dest, Spawns.point(SirensReefLayout.DECK)), 0f)));
        Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", dest, 1.5f);
        draftClock = DRAFT_EVERY - 3f;
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.leap"));
    }

    // --- courants fantômes -------------------------------------------------------------------------------------------

    /** `count` bandes en travers du pont, sur des tranches distinctes. */
    private void drafts(World world, Store<EntityStore> store, int count) {
        int[] d = SirensReefLayout.DECK_BOX;
        double x0 = d[0] + DRAFT_WIDTH / 2;
        double x1 = d[1] + 1 - DRAFT_WIDTH / 2;
        int slots = Math.max(1, (int) Math.floor((x1 - x0) / (DRAFT_WIDTH + 1)) + 1);
        List<Integer> order = new ArrayList<>();
        for (int i = 0; i < slots; i++) {
            order.add(i);
        }
        Collections.shuffle(order);
        float windup = DRAFT_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Strip> strips = new ArrayList<>();
        List<Vector3d> pushes = new ArrayList<>();
        for (int k = 0; k < Math.min(count, slots); k++) {
            double x = slots == 1 ? (x0 + x1) / 2 : x0 + order.get(k) * (x1 - x0) / (slots - 1);
            boolean south = ThreadLocalRandom.current().nextBoolean();
            double z = south ? d[2] - (DRAFT_LENGTH - (d[3] + 1 - d[2])) / 2 : d[3] + 1 + (DRAFT_LENGTH - (d[3] + 1 - d[2])) / 2;
            double facing = south ? Math.PI / 2 : -Math.PI / 2;
            pushes.add(new Vector3d(0, 0, south ? 1 : -1));
            strips.add(new Telegraphs.Strip(new Vector3d(x, SirensReefLayout.DECK_STAND, z), facing, DRAFT_LENGTH,
                    DRAFT_WIDTH, now, windup));
        }
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.drafts"));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (e != epoch) {
                return true;
            }
            boolean done = true;
            for (Telegraphs.Strip strip : strips) {
                done &= strip.step(s, t);
            }
            if (!done) {
                return false;
            }
            for (int k = 0; k < strips.size(); k++) {
                Telegraphs.Strip strip = strips.get(k);
                for (double a = 1; a < DRAFT_LENGTH; a += 3) {
                    Telegraphs.particle(s, "Nakasar_Fractal_Draft_Gust", strip.at(a, 0), 1f);
                }
                Vector3d dir = pushes.get(k);
                for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                    Vector3d at = Telegraphs.position(s, p.getReference());
                    if (at != null && strip.contains(at)) {
                        Hurt.percent(s, p.getReference(), DRAFT_PART, SirensReef.REEF_CAUSE);
                        Moves.velocity(s, p.getReference(), new Vector3d(dir).mul(DRAFT_PUSH).add(0, 7, 0));
                    }
                }
            }
            return true;
        });
    }

    // --- lagon sinistre et dents des profondeurs ------------------------------------------------------------------

    private void lagoon(World world, Store<EntityStore> store, List<PlayerRef> aboard, float dt) {
        lagoonClock += dt;
        if (lagoonClock < LAGOON_EVERY || aboard.isEmpty()) {
            return;
        }
        lagoonClock = 0f;
        PlayerRef target = aboard.get(ThreadLocalRandom.current().nextInt(aboard.size()));
        Vector3d at = Telegraphs.position(store, target.getReference());
        if (at == null) {
            return;
        }
        Vector3d c = new Vector3d(at);
        float windup = LAGOON_WINDUP * FractalRuns.windupFactor(world);
        Telegraphs.Circle circle = new Telegraphs.Circle(c, LAGOON_RADIUS, System.nanoTime(), windup);
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.lagoon"));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (e != epoch) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            lagoons.add(new Lagoon(c, t + Telegraphs.seconds(LAGOON_SECONDS)));
            return true;
        });
    }

    private void teeth(World world, Store<EntityStore> store, List<PlayerRef> aboard, float dt) {
        teethClock += dt;
        if (teethClock < TEETH_EVERY || aboard.isEmpty()) {
            return;
        }
        teethClock = 0f;
        PlayerRef target = aboard.get(ThreadLocalRandom.current().nextInt(aboard.size()));
        Vector3d at = Telegraphs.position(store, target.getReference());
        if (at == null) {
            return;
        }
        Vector3d c = new Vector3d(at);
        float windup = TEETH_WINDUP * FractalRuns.windupFactor(world);
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.teeth"));
        int e = epoch;
        long[] begin = {-1};
        long[] shown = {0};
        TelegraphSystem.start(world, (w, s, t) -> {
            if (e != epoch) {
                return true;
            }
            if (begin[0] < 0) {
                begin[0] = t;
            }
            if (t - begin[0] < Telegraphs.seconds(windup)) {
                if (t - shown[0] >= Telegraphs.seconds(0.5f)) {
                    shown[0] = t;
                    Telegraphs.particle(s, GREEN_ZONE, new Vector3d(c).add(0, 0.1, 0), (float) (Telegraphs.WARNING_SCALE * TEETH_RADIUS));
                }
                return false;
            }
            Telegraphs.particle(s, "Nakasar_Fractal_Deep_Teeth", c, 1f);
            Telegraphs.sound(s, "SFX_Rex_Bite", c);
            List<PlayerRef> inside = new ArrayList<>();
            for (PlayerRef p : Spawns.alivePlayers(w, s)) {
                Vector3d pos = Telegraphs.position(s, p.getReference());
                if (pos != null && Telegraphs.inCircle(pos, c, TEETH_RADIUS)) {
                    inside.add(p);
                }
            }
            if (inside.isEmpty() && target.getReference() != null && target.getReference().isValid()) {
                inside.add(target);
            }
            for (PlayerRef p : inside) {
                Hurt.percent(s, p.getReference(), TEETH_PART / inside.size(), SirensReef.REEF_CAUSE);
            }
            return true;
        });
    }

    // --- défense du navire -------------------------------------------------------------------------------------------

    private void defend(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        if (killed >= DEFEND_TOTAL) {
            Spawns.removeAll(store, adds);
            adds.clear();
            step = Step.ARABELLA;
            pending = true;
            return;
        }
        if (inCove(store, players).isEmpty()) {
            return;
        }
        waveClock += dt;
        // Pas plus en vie que ce qu'il reste à abattre : un membre d'équipage disparu sans mourir est remplacé.
        if (waveClock < DEFEND_WAVE || adds.size() >= Math.min(DEFEND_ALIVE, DEFEND_TOTAL - killed)) {
            return;
        }
        waveClock = 0f;
        crew(world, store, st, 2 + (FractalRuns.partySize(world) > 2 ? 1 : 0));
    }

    /** Un membre d'équipage tombe : compte pour la défense. */
    void defenderDown(World world) {
        if (step != Step.DEFEND) {
            return;
        }
        killed++;
        if (killed % 5 == 0 && killed <= DEFEND_TOTAL) {
            Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "ship.progress")
                    .param("count", killed).param("total", DEFEND_TOTAL));
        }
    }

    // --- brouillard et piranhas ---------------------------------------------------------------------------------------

    private void hazards(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        fx += dt;
        boolean show = fx >= 1f;
        if (show) {
            fx = 0f;
        }
        for (PlayerRef p : inCove(store, players)) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            for (Lagoon l : lagoons) {
                if (Telegraphs.inCircle(at, l.at(), LAGOON_RADIUS)) {
                    Hurt.effect(store, ref, "Nakasar_Fractal_Grim_Lagoon", 1f);
                    Hurt.percent(store, ref, LAGOON_PART * dt, SirensReef.REEF_CAUSE);
                }
            }
            if (deck(at)) {
                continue;
            }
            if (at.y() < SirensReefLayout.SEA_TOP - 0.2) {
                Hurt.effect(store, ref, "Nakasar_Fractal_Piranhas", 1f);
                Hurt.percent(store, ref, WATER_PART * dt, SirensReef.REEF_CAUSE);
                SirensReef.tell(st, p, "ship.water");
            } else {
                Hurt.effect(store, ref, "Nakasar_Fractal_Fetid_Fog", 1f);
                Hurt.percent(store, ref, FOG_PART * dt, SirensReef.REEF_CAUSE);
                SirensReef.tell(st, p, "ship.fog");
                if (show) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Fetid_Fog", at, 1f);
                }
            }
        }
        if (show) {
            for (Lagoon l : lagoons) {
                Telegraphs.particle(store, "Nakasar_Fractal_Grim_Lagoon", l.at(), (float) LAGOON_RADIUS);
            }
        }
    }

    /** Ennemis dans une flaque du lagon : moitié moins de dégâts. */
    void filter(CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim, Damage damage) {
        if (lagoons.isEmpty()) {
            return;
        }
        Vector3d at = Telegraphs.position(buffer, victim);
        if (at == null) {
            return;
        }
        for (Lagoon l : lagoons) {
            if (Telegraphs.inCircle(at, l.at(), LAGOON_RADIUS)) {
                damage.setAmount(damage.getAmount() * 0.5f);
                return;
            }
        }
    }

    // --- lieux ------------------------------------------------------------------------------------------------------

    private static boolean deck(Vector3d at) {
        int[] d = SirensReefLayout.DECK_BOX;
        return at.x() >= d[0] && at.x() <= d[1] + 1 && at.z() >= d[2] && at.z() <= d[3] + 1
                && at.y() >= SirensReefLayout.DECK_STAND - 1.5;
    }

    private static List<PlayerRef> onDeck(Store<EntityStore> store, List<PlayerRef> players) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && deck(at)) {
                out.add(p);
            }
        }
        return out;
    }

    private static List<PlayerRef> inCove(Store<EntityStore> store, List<PlayerRef> players) {
        int[] b = SirensReefLayout.COVE_BOX;
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.x() >= b[0] && at.x() <= b[1] + 1 && at.z() >= b[2] && at.z() <= b[3] + 1) {
                out.add(p);
            }
        }
        return out;
    }
}
