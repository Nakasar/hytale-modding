package dev.nakasar.hytale.fractals.sirensreef;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.CrouchPickup;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les trésors maudits d'Arabella Crowe (labyrinthe, plages de la crique), d'après GW2 :
 * <ul>
 *   <li>ils se ramassent accroupi et restent en main ({@link CrouchPickup}) ; les saisir au sol coûte
 *   {@value #GRAB_PART} des PV ;</li>
 *   <li>tant qu'on en porte un, la malédiction monte d'un point par seconde : Malédiction I à {@code TIERS[0]} (ralenti),
 *   II à {@code TIERS[1]} (la vie s'en va, {@value #CURSE_PART} des PV par seconde), III à {@code TIERS[2]} : figé, le
 *   trésor tombe. Sans trésor, elle retombe de {@value #CURSE_FALL} points par seconde ;</li>
 *   <li>clic droit : le lancer au joueur visé (jusqu'à {@value #THROW_RANGE} blocs, dans un cône de
 *   {@value #THROW_CONE_DEG}°) qui n'en porte pas ; sinon il tombe {@value #DROP_AHEAD} blocs devant. Le lanceur reçoit
 *   l'Allègement de la malédiction ({@value #RELIEF_SECONDS} s, la malédiction ne monte plus) ;</li>
 *   <li>porté à moins de {@value #DEPOSIT_RADIUS} blocs du coffre de la sirène, il y est déposé ;</li>
 *   <li>un escroc fantôme à moins de {@value #SWINDLE_RADIUS} blocs d'un trésor au sol le rapporte à une cachette ;</li>
 *   <li>labyrinthe : des orbes spectrales rebondissent contre les haies ; qui en touche une fait lever
 *   {@value #ORB_GHOSTS} fantômes (sans butin), et l'orbe revient {@value #ORB_BACK} s plus tard.</li>
 * </ul>
 */
final class CursedTreasure {

    static final float GRAB_PART = 0.05f;
    static final float[] TIERS = {6f, 12f, 18f};
    static final float CURSE_FALL = 2f;
    static final float CURSE_PART = 0.01f;
    static final String[] CURSES = {"Nakasar_Fractal_Cursed_1", "Nakasar_Fractal_Cursed_2", "Nakasar_Fractal_Cursed_3"};
    static final String RELIEF = "Nakasar_Fractal_Curse_Relief";
    static final float RELIEF_SECONDS = 8f;
    static final float RELIEF_DROP = 6f;
    static final double THROW_RANGE = 16;
    static final double THROW_CONE_DEG = 35;
    static final double DROP_AHEAD = 3;
    static final double DEPOSIT_RADIUS = 3;
    static final double SWINDLE_RADIUS = 2.5;
    static final double ORB_TOUCH = 1.5;
    static final double ORB_SPEED = 3;
    static final int ORB_GHOSTS = 2;
    static final float ORB_BACK = 20f;
    /** Toutes les {@value #AUDIT_EVERY} s : un trésor perdu (objet au sol disparu, porteur parti) revient à sa cachette. */
    static final float AUDIT_EVERY = 3f;

    private static final class Orb {
        final Vector3d home;
        final Vector3d at;
        double vx;
        double vz;
        long back;

        Orb(double[] home) {
            this.home = Spawns.point(home);
            this.at = new Vector3d(this.home);
            double a = ThreadLocalRandom.current().nextDouble(Math.PI * 2);
            vx = Math.cos(a) * ORB_SPEED;
            vz = Math.sin(a) * ORB_SPEED;
        }
    }

    private boolean active;
    private double[][] homes = new double[0][];
    private double[] chest;
    private int total;
    private int delivered;
    private final List<Orb> orbs = new ArrayList<>();
    private final List<Ref<EntityStore>> swindlers = new ArrayList<>();
    private final Map<UUID, Float> curse = new HashMap<>();
    private final Set<UUID> carrying = new HashSet<>();
    /** Joueurs qui viennent de recevoir un trésor lancé : pas de morsure à la saisie. */
    private final Set<UUID> caught = new HashSet<>();
    private float audit;
    private float glow;
    private long lastTick;

    static void register() {
        CrouchPickup.register(new CrouchPickup.Item(SirensReef.TREASURE, SirensReef.FRACTAL,
                SirensReef.MESSAGES + "treasure.crouch", SirensReef.MESSAGES + "treasure.already",
                (store, at) -> Carried.drop(store, SirensReef.TREASURE, at)));
    }

    /** Pose les trésors à leurs cachettes `spots` ; à rapporter au coffre `chestAt` ; `withOrbs` : celles du labyrinthe. */
    void begin(World world, Store<EntityStore> store, SirensReef.State st, double[][] spots, double[] chestAt, boolean withOrbs) {
        active = true;
        homes = spots;
        chest = chestAt;
        total = spots.length;
        delivered = 0;
        audit = 0f;
        for (double[] at : spots) {
            Carried.drop(store, SirensReef.TREASURE, Spawns.point(at));
        }
        orbs.clear();
        if (withOrbs) {
            for (double[] at : SirensReefLayout.ORBS) {
                orbs.add(new Orb(at));
            }
        }
    }

    boolean complete() {
        return active && delivered >= total;
    }

    /** Fin d'une manche : plus d'orbes ni d'escrocs suivis, les trésors restants disparaissent. */
    void end(World world, Store<EntityStore> store) {
        active = false;
        orbs.clear();
        swindlers.clear();
        CrouchPickup.removeGround(world, store, SirensReef.TREASURE);
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            if (ref != null && ref.isValid()) {
                CrouchPickup.removeAll(store, ref, SirensReef.TREASURE);
            }
        }
    }

    void swindler(Ref<EntityStore> ref) {
        swindlers.add(ref);
    }

    // --- malédiction, dépôt, escrocs (4 fois par seconde) ----------------------------------------------------------

    void step(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        glow += dt;
        boolean fx = glow >= 0.5f;
        if (fx) {
            glow = 0f;
        }
        Set<UUID> here = new HashSet<>();
        for (PlayerRef p : players) {
            here.add(p.getUuid());
            curse(world, store, st, p, dt, fx);
        }
        curse.keySet().retainAll(here);
        carrying.retainAll(here);
        if (!active) {
            return;
        }
        swindlers.removeIf(ref -> !Spawns.alive(store, ref));
        List<Ref<EntityStore>> ground = CrouchPickup.onGround(world, SirensReef.TREASURE);
        for (Ref<EntityStore> item : ground) {
            Vector3d at = Telegraphs.position(store, item);
            if (at == null) {
                continue;
            }
            if (fx) {
                Telegraphs.particle(store, "Nakasar_Fractal_Treasure_Glow", at, 1f);
            }
            if (hidden(at)) {
                continue;               // déjà dans une cachette : les escrocs n'y touchent plus
            }
            for (Ref<EntityStore> s : swindlers) {
                Vector3d sp = Telegraphs.position(store, s);
                if (sp != null && sp.distance(at) <= SWINDLE_RADIUS) {
                    store.removeEntity(item, RemoveReason.REMOVE);
                    Vector3d home = Spawns.point(homes[ThreadLocalRandom.current().nextInt(homes.length)]);
                    Carried.drop(store, SirensReef.TREASURE, home);
                    Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", at, 1f);
                    Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "treasure.swindled"));
                    break;
                }
            }
        }
        deposit(world, store, players);
        audit += dt;
        if (audit >= AUDIT_EVERY) {
            audit = 0f;
            audit(world, store, players);
        }
    }

    private boolean hidden(Vector3d at) {
        for (double[] h : homes) {
            if (Spawns.point(h).distance(at) <= SWINDLE_RADIUS) {
                return true;
            }
        }
        return false;
    }

    private void curse(World world, Store<EntityStore> store, SirensReef.State st, PlayerRef p, float dt, boolean fx) {
        Ref<EntityStore> ref = p.getReference();
        UUID id = p.getUuid();
        boolean holds = CrouchPickup.count(store, ref, SirensReef.TREASURE) > 0;
        if (holds && carrying.add(id) && !caught.remove(id)) {
            Hurt.percent(store, ref, GRAB_PART, SirensReef.REEF_CAUSE);
            SirensReef.tell(st, p, "treasure.grab");
        } else if (!holds) {
            carrying.remove(id);
            caught.remove(id);
        }
        float c = curse.getOrDefault(id, 0f);
        if (holds && !Hurt.has(store, ref, RELIEF)) {
            c += dt;
        } else {
            c = Math.max(0f, c - CURSE_FALL * dt);
        }
        int tier = c >= TIERS[2] ? 3 : c >= TIERS[1] ? 2 : c >= TIERS[0] ? 1 : 0;
        if (tier == 3 && holds) {
            Vector3d at = Telegraphs.position(store, ref);
            CrouchPickup.removeAll(store, ref, SirensReef.TREASURE);
            if (at != null) {
                Carried.drop(store, SirensReef.TREASURE, at);
            }
            Hurt.effect(store, ref, CURSES[2], 2f);
            p.sendMessage(Message.translation(SirensReef.MESSAGES + "treasure.cursed"));
            carrying.remove(id);
            c = TIERS[1];
        } else if (tier >= 1) {
            Hurt.effect(store, ref, CURSES[tier - 1], 0.6f);
            if (tier == 2) {
                Hurt.percent(store, ref, CURSE_PART * dt, SirensReef.REEF_CAUSE);
            }
        }
        curse.put(id, c);
        if (fx && holds) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Curse_Motes", new Vector3d(at).add(0, 1, 0), 1f);
            }
        }
    }

    private void deposit(World world, Store<EntityStore> store, List<PlayerRef> players) {
        Vector3d c = Spawns.point(chest);
        for (PlayerRef p : players) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || Telegraphs.horizontal(at, c) > DEPOSIT_RADIUS || Math.abs(at.y() - c.y()) > 3) {
                continue;
            }
            int n = CrouchPickup.removeAll(store, ref, SirensReef.TREASURE);
            if (n == 0) {
                continue;
            }
            delivered += n;
            carrying.remove(p.getUuid());
            Telegraphs.particle(store, "Nakasar_Fractal_Treasure_Glow", c, 2f);
            Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "treasure.deposit")
                    .param("count", Math.min(delivered, total)).param("total", total));
        }
    }

    /** Trésors attendus = non déposés ; ceux qui manquent (au sol disparus, porteur parti) reviennent à une cachette. */
    private void audit(World world, Store<EntityStore> store, List<PlayerRef> players) {
        int have = CrouchPickup.onGround(world, SirensReef.TREASURE).size();
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            if (ref != null && ref.isValid()) {
                have += CrouchPickup.count(store, ref, SirensReef.TREASURE);
            }
        }
        for (int i = have; i < total - delivered; i++) {
            Carried.drop(store, SirensReef.TREASURE, Spawns.point(homes[i % homes.length]));
        }
    }

    // --- lancer ---------------------------------------------------------------------------------------------------

    void toss(World world, Store<EntityStore> store, SirensReef.State st, PlayerRef thrower) {
        Ref<EntityStore> ref = thrower.getReference();
        Vector3d from = Telegraphs.position(store, ref);
        Vector3d look = Moves.look(store, ref);
        if (from == null || look == null || !CrouchPickup.holds(store, ref, SirensReef.TREASURE)) {
            return;
        }
        Vector3d eye = new Vector3d(from).add(0, 1.6, 0);
        double cone = Math.cos(Math.toRadians(THROW_CONE_DEG));
        PlayerRef target = null;
        double best = cone;
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            if (p.getUuid().equals(thrower.getUuid())) {
                continue;
            }
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null || at.distance(from) > THROW_RANGE
                    || CrouchPickup.count(store, p.getReference(), SirensReef.TREASURE) > 0) {
                continue;
            }
            Vector3d to = new Vector3d(at).add(0, 1, 0).sub(eye).normalize();
            double dot = to.dot(look);
            if (dot >= best) {
                best = dot;
                target = p;
            }
        }
        CrouchPickup.removeAll(store, ref, SirensReef.TREASURE);
        carrying.remove(thrower.getUuid());
        Vector3d landing;
        if (target != null) {
            landing = new Vector3d(Telegraphs.position(store, target.getReference()));
            caught.add(target.getUuid());
            CrouchPickup.give(store, target.getReference(), SirensReef.TREASURE);
            target.sendMessage(Message.translation(SirensReef.MESSAGES + "treasure.caught").param("name", thrower.getUsername()));
        } else {
            landing = Moves.flatLook(store, ref).mul(DROP_AHEAD).add(from);
            Vector3d free = Moves.cast(world.getChunkStore(), eye, new Vector3d(landing).add(0, 1, 0).sub(eye), eye.distance(landing) + 1);
            if (free != null) {
                landing = new Vector3d(free.x(), from.y(), free.z());
            }
            Carried.drop(store, SirensReef.TREASURE, landing);
        }
        double length = eye.distance(landing);
        for (double t = 1.5; t < length; t += 1.5) {
            Telegraphs.particle(store, "Nakasar_Fractal_Treasure_Glow", new Vector3d(eye).lerp(new Vector3d(landing).add(0, 1, 0), t / length), 0.6f);
        }
        Hurt.effect(store, ref, RELIEF, RELIEF_SECONDS);
        curse.merge(thrower.getUuid(), 0f, (c, z) -> Math.max(0f, c - RELIEF_DROP));
        SirensReef.tell(st, thrower, "treasure.thrown");
    }

    // --- orbes du labyrinthe (chaque tick) --------------------------------------------------------------------------

    void tick(World world, Store<EntityStore> store, SirensReef.State st, long now) {
        double dt = lastTick == 0 ? 0 : Math.min(0.2, (now - lastTick) / 1e9);
        lastTick = now;
        if (!active || orbs.isEmpty()) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        int[] box = SirensReefLayout.MAZE_BOX;
        int y = (int) Math.floor(SirensReefLayout.MAZE_STAND);
        List<PlayerRef> players = null;
        for (Orb orb : orbs) {
            if (orb.back > 0) {
                if (now < orb.back) {
                    continue;
                }
                orb.back = 0;
                orb.at.set(orb.home);
            }
            double nx = orb.at.x() + orb.vx * dt;
            double nz = orb.at.z() + orb.vz * dt;
            if (blocked(chunks, nx, y, orb.at.z()) || nx < box[0] || nx > box[1] + 1) {
                orb.vx = -orb.vx;
                nx = orb.at.x();
            }
            if (blocked(chunks, nx, y, nz) || nz < box[2] || nz > box[3] + 1) {
                orb.vz = -orb.vz;
                nz = orb.at.z();
            }
            orb.at.set(nx, orb.home.y(), nz);
            double bob = 0.9 + 0.4 * Math.abs(Math.sin(now / 2.5e8));
            if ((now / 100_000_000L) % 2 == 0) {
                Telegraphs.particle(store, "Nakasar_Fractal_Reef_Orb", new Vector3d(orb.at).add(0, bob, 0), 1f);
            }
            if (players == null) {
                players = Spawns.alivePlayers(world, store);
            }
            for (PlayerRef p : players) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, orb.at) <= ORB_TOUCH && Math.abs(at.y() - orb.at.y()) < 2.5) {
                    burst(world, store, st, orb, now);
                    break;
                }
            }
        }
    }

    private static boolean blocked(ChunkStore chunks, double x, int y, double z) {
        int bx = (int) Math.floor(x);
        int bz = (int) Math.floor(z);
        return WorldBlocks.solid(chunks, bx, y, bz) || WorldBlocks.solid(chunks, bx, y + 1, bz);
    }

    private static void burst(World world, Store<EntityStore> store, SirensReef.State st, Orb orb, long now) {
        Vector3d at = new Vector3d(orb.at);
        orb.back = now + Telegraphs.seconds(ORB_BACK);
        Telegraphs.particle(store, "Nakasar_Fractal_Orb_Ring", at, 1f);
        Telegraphs.particle(store, "Nakasar_Fractal_Ghost_Rise", at, 1.2f);
        for (int i = 0; i < ORB_GHOSTS; i++) {
            st.foe(world, store, SirensReef.GHOST, new double[]{at.x() + (i == 0 ? 1 : -1), at.y(), at.z()}, false);
        }
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "orb.touch"));
    }
}
