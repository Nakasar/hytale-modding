package dev.nakasar.hytale.fractals.uncategorized;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Polarity;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphInteraction;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.progress.Agony;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * L'Asura fou, dernier combat de l'Inclassable. Lui reste invulnérable sur son estrade ; il faut abattre ses quatre
 * golems de cristal, réveillés un à un, puis tous les quatre ensemble. Pendant tout le combat :
 * <ul>
 *   <li>charges + et - ({@link Polarity}) : deux charges opposées à moins de 3 blocs s'électrocutent ; seul, deux
 *   pylônes portent les charges et la vôtre s'inverse toutes les 20 s ;</li>
 *   <li>salve toutes les {@value #BOLT_INTERVAL} s : un cercle rouge sous chaque joueur de l'arène ;</li>
 *   <li>orbe toutes les {@value #ORB_INTERVAL} s : une boule violette suit un joueur ({@value #ORB_SPEED} blocs/s,
 *   {@value #ORB_LIFE} s au plus) et éclate à son contact (cercle de {@value #ORB_RADIUS} blocs, 1 s, agonie).</li>
 * </ul>
 * Personne dans l'arène pendant {@value #RESET_SECONDS} s : tout repart de zéro.
 */
final class MadAsura {

    static final float BOLT_INTERVAL = 7f;
    static final float ORB_INTERVAL = 10f;
    static final double ORB_SPEED = 3.5;
    static final float ORB_LIFE = 10f;
    static final double ORB_RADIUS = 2.2;
    static final float ORB_DAMAGE = 25f;
    static final float RESET_SECONDS = 20f;

    private static final class Orb {
        final Vector3d at;
        final PlayerRef target;
        float life;

        Orb(Vector3d at, PlayerRef target) {
            this.at = at;
            this.target = target;
        }
    }

    private Ref<EntityStore> asura;
    private final Ref<EntityStore>[] golems;
    private final boolean[] dormant;
    private final Polarity polarity = new Polarity(Uncategorized.MESSAGES);
    private final List<Orb> orbs = new ArrayList<>();
    private boolean engaged;
    /** Golem réveillé (0 à 3), puis 4 : tous ensemble ({@link #finalDeaths} comptés). */
    private int phase;
    private int down;
    private int finalDeaths;
    private volatile int deaths;
    private float boltClock;
    private float orbClock;
    private float idle;
    private boolean victory;

    @SuppressWarnings("unchecked")
    MadAsura() {
        golems = new Ref[UncategorizedLayout.GOLEMS.length];
        dormant = new boolean[golems.length];
    }

    static boolean inArena(Vector3d at) {
        double[] c = UncategorizedLayout.ARENA_CENTER;
        return at.y() >= c[1] - 3 && at.y() <= c[1] + 8
                && Math.hypot(at.x() - c[0], at.z() - c[2]) <= UncategorizedLayout.ARENA_RADIUS + 0.5;
    }

    static List<PlayerRef> inArena(Store<EntityStore> store, List<PlayerRef> players) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && inArena(at)) {
                out.add(player);
            }
        }
        return out;
    }

    /** Vrai pour un golem pas encore réveillé (les coups ne lui font rien). */
    boolean dormant(Ref<EntityStore> ref) {
        for (int i = 0; i < golems.length; i++) {
            if (ref.equals(golems[i])) {
                return dormant[i];
            }
        }
        return false;
    }

    void golemDown() {
        deaths++;
    }

    /** Un pas de jeu ; vrai à la victoire (une seule fois). */
    boolean step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        if (victory) {
            return false;
        }
        keepAsura(store);
        if (!engaged) {
            keepDormant(world, store);
        }
        List<PlayerRef> inArena = inArena(store, players);
        if (inArena.isEmpty()) {
            idle(world, store, dt);
            return false;
        }
        idle = 0f;
        if (!engaged) {
            engaged = true;
            phase = 0;
            down = deaths;
            List<Polarity.Pylon> pylons = new ArrayList<>();
            for (double[] p : UncategorizedLayout.PYLONS) {
                pylons.add(new Polarity.Pylon(new Vector3d(p[0], p[1], p[2]), (int) p[3]));
            }
            polarity.start(inArena, pylons);
            Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "asura.enter"));
            wake(world, store, 0);
        }
        int newDeaths = deaths - down;
        if (newDeaths > 0) {
            down = deaths;
            if (phase < golems.length) {
                phase++;
                if (phase < golems.length) {
                    wake(world, store, phase);
                } else {
                    finalDeaths = 0;
                    allTogether(world, store);
                }
            } else {
                finalDeaths += newDeaths;
                if (finalDeaths >= golems.length) {
                    return win(world, store, inArena);
                }
            }
        }
        polarity.step(world, store, inArena, dt);
        float wf = FractalRuns.windupFactor(world);
        boltClock += dt;
        if (boltClock >= BOLT_INTERVAL) {
            boltClock = 0f;
            bolts(world, store, inArena, wf);
        }
        orbClock += dt;
        if (orbClock >= ORB_INTERVAL) {
            orbClock = 0f;
            launchOrb(store, inArena);
        }
        orbs(world, store, dt);
        return false;
    }

    private void keepAsura(Store<EntityStore> store) {
        if (asura != null && asura.isValid()) {
            return;
        }
        double[] at = UncategorizedLayout.ASURA;
        double[] c = UncategorizedLayout.ARENA_CENTER;
        Vector3d where = Spawns.point(at);
        asura = Spawns.spawn(store, Uncategorized.ASURA, where, Telegraphs.yawToward(where, Spawns.point(c)));
        if (asura != null) {
            store.ensureAndGetComponent(asura, Frozen.getComponentType());
            store.ensureAndGetComponent(asura, Invulnerable.getComponentType());
        }
    }

    /** Avant le combat : les quatre golems dorment à leur place, figés et invulnérables. */
    private void keepDormant(World world, Store<EntityStore> store) {
        double[] c = UncategorizedLayout.ARENA_CENTER;
        for (int i = 0; i < golems.length; i++) {
            if (golems[i] != null && golems[i].isValid()) {
                continue;
            }
            Vector3d at = Spawns.point(UncategorizedLayout.GOLEMS[i]);
            golems[i] = Spawns.spawnFoe(world, store, Uncategorized.CRYSTAL_GOLEM, at, Telegraphs.yawToward(at, Spawns.point(c)));
            if (golems[i] != null) {
                store.ensureAndGetComponent(golems[i], Frozen.getComponentType());
                store.ensureAndGetComponent(golems[i], Invulnerable.getComponentType());
                dormant[i] = true;
            }
        }
    }

    private void wake(World world, Store<EntityStore> store, int index) {
        Ref<EntityStore> golem = golems[index];
        if (golem == null || !golem.isValid()) {
            return;
        }
        dormant[index] = false;
        store.tryRemoveComponent(golem, Frozen.getComponentType());
        store.tryRemoveComponent(golem, Invulnerable.getComponentType());
        Vector3d at = Telegraphs.position(store, golem);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Golem_Wake", at, 1.5f);
        }
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "asura.wake"));
    }

    /** Dernière phase : l'Asura recolle les quatre golems et les lâche ensemble. */
    private void allTogether(World world, Store<EntityStore> store) {
        double[] c = UncategorizedLayout.ARENA_CENTER;
        for (int i = 0; i < golems.length; i++) {
            Spawns.remove(store, golems[i]);
            Vector3d at = Spawns.point(UncategorizedLayout.GOLEMS[i]);
            golems[i] = Spawns.spawnFoe(world, store, Uncategorized.CRYSTAL_GOLEM, at, Telegraphs.yawToward(at, Spawns.point(c)));
            dormant[i] = false;
            Telegraphs.particle(store, "Nakasar_Fractal_Golem_Wake", at, 1.5f);
        }
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "asura.all"));
    }

    private void bolts(World world, Store<EntityStore> store, List<PlayerRef> targets, float wf) {
        for (PlayerRef p : targets) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                TelegraphInteraction.spec("Circle", 1.4f * wf).radius(2.2f).damage(16f, "Physical").playersOnly()
                        .impact("Nakasar_Fractal_Asura_Bolt", "SFX_Spirit_Root_Alerted")
                        .launch(world, asura, p.getReference(), at, 0);
            }
        }
    }

    private void launchOrb(Store<EntityStore> store, List<PlayerRef> targets) {
        Vector3d from = Telegraphs.position(store, asura);
        List<PlayerRef> picked = Spawns.pick(targets, 1);
        if (from == null || picked.isEmpty()) {
            return;
        }
        orbs.add(new Orb(new Vector3d(from).add(0, 1.5, 0), picked.get(0)));
    }

    /** Les orbes suivent leur cible et éclatent à son contact, ou au bout de leur vie. */
    private void orbs(World world, Store<EntityStore> store, float dt) {
        for (Iterator<Orb> it = orbs.iterator(); it.hasNext(); ) {
            Orb orb = it.next();
            orb.life += dt;
            Vector3d target = Telegraphs.position(store, orb.target.getReference());
            if (target != null) {
                Vector3d aim = new Vector3d(target).add(0, 1, 0).sub(orb.at);
                double length = aim.length();
                if (length > 1e-3) {
                    orb.at.add(aim.mul(Math.min(length, ORB_SPEED * dt) / length));
                }
            }
            Telegraphs.particle(store, "Nakasar_Fractal_Asura_Orb", orb.at, 1.2f);
            boolean touch = target != null && orb.at.distance(new Vector3d(target).add(0, 1, 0)) <= 1.3;
            if (touch || orb.life >= ORB_LIFE || target == null) {
                pop(world, store, new Vector3d(orb.at.x(), target != null ? target.y() : orb.at.y() - 1, orb.at.z()));
                it.remove();
            }
        }
    }

    private void pop(World world, Store<EntityStore> store, Vector3d at) {
        Telegraphs.circle(store, at, ORB_RADIUS, 1f);
        Delayed.later(world, 1f, s -> {
            Telegraphs.particle(s, "Nakasar_Fractal_Asura_Bolt", at, 1.5f);
            for (PlayerRef p : Spawns.alivePlayers(world, s)) {
                Ref<EntityStore> r = p.getReference();
                Vector3d there = Telegraphs.position(s, r);
                if (there != null && Telegraphs.horizontal(there, at) <= ORB_RADIUS + Telegraphs.BODY && Math.abs(there.y() - at.y()) <= 2.5) {
                    Hurt.amount(s, r, ORB_DAMAGE * (1f + FractalRuns.level(world) / 150f), "Physical");
                    if (FractalRuns.level(world) > 25) {
                        Hurt.effect(s, r, Agony.EFFECT, 4f);
                    }
                }
            }
        });
    }

    /** Personne dans l'arène : au bout de {@value #RESET_SECONDS} s, le combat repart de zéro. */
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
        phase = 0;
        orbs.clear();
        polarity.stop(store, List.of());
        for (int i = 0; i < golems.length; i++) {
            Spawns.remove(store, golems[i]);
            golems[i] = null;
        }
        Spawns.tellAll(world, Message.translation(Uncategorized.MESSAGES + "asura.reset"));
    }

    private boolean win(World world, Store<EntityStore> store, List<PlayerRef> players) {
        victory = true;
        orbs.clear();
        polarity.stop(store, players);
        Vector3d at = Telegraphs.position(store, asura);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", at, 1.5f);
        }
        Spawns.remove(store, asura);
        asura = null;
        return true;
    }
}
