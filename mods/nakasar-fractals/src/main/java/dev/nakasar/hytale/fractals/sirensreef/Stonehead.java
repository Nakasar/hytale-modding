package dev.nakasar.hytale.fractals.sirensreef;

import com.hypixel.hytale.component.CommandBuffer;
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
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Tête-de-pierre, champion des raptors, dans sa clairière (GW2). Morsure, charge et piétinement : rôle JSON. En Java :
 * <ul>
 *   <li>à {@code PACKS} (75 et 50 %), il appelle une meute de {@value #PACK_SIZE} raptors de poche (sans butin) ;</li>
 *   <li>sa vie ne passe pas {@value #FLEE_AT} avant sa fuite ; là, il rugit (peur et recul à {@value #ROAR_RADIUS}
 *   blocs, cercle rouge de cette taille), devient invulnérable, brise les rochers du ravin et y court jusqu'à la
 *   première mine, qui saute sous lui : il meurt (son butin tombe), le ravin est miné ;</li>
 *   <li>personne dans la clairière pendant {@value #RESET_SECONDS} s avant sa fuite : il disparaît, et revient au
 *   prochain venu.</li>
 * </ul>
 * Pas de soin : sa vie reste où les joueurs l'ont mise (AGENTS.md).
 */
final class Stonehead {

    enum Outcome { NONE, DONE, RESET }

    static final float[] PACKS = {0.75f, 0.5f};
    static final int PACK_SIZE = 4;
    static final float FLEE_AT = 0.25f;
    static final double ROAR_RADIUS = 8;
    static final float ROAR_WINDUP = 1.5f;
    static final float ROAR_FEAR = 2f;
    static final double RUN_SPEED = 9;
    static final float RESET_SECONDS = 20f;
    /** Rayon où il est tenu (la clairière et ses abords). */
    static final double LEASH = SirensReefLayout.CLEARING_RADIUS + 4;

    private Ref<EntityStore> boss;
    private final List<Ref<EntityStore>> pack = new ArrayList<>();
    private int packs;
    private boolean fleeing;
    private boolean dying;
    private boolean done;
    private float idle;
    private int epoch;

    boolean engage(World world, Store<EntityStore> store, SirensReef.State st) {
        boss = st.boss(world, store, SirensReef.STONEHEAD, SirensReefLayout.STONEHEAD, SirensReefLayout.CLEARING);
        if (boss == null) {
            return false;
        }
        epoch++;
        packs = 0;
        fleeing = false;
        dying = false;
        done = false;
        idle = 0f;
        Telegraphs.particle(store, "Nakasar_Fractal_Stonehead_Roar", Spawns.point(SirensReefLayout.STONEHEAD), 1f);
        Telegraphs.sound(store, "SFX_Bear_Voidtaken_Roar", Spawns.point(SirensReefLayout.STONEHEAD));
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "stonehead.enter"));
        return true;
    }

    Outcome step(World world, Store<EntityStore> store, SirensReef.State st, List<PlayerRef> players, float dt) {
        if (done) {
            return Outcome.DONE;
        }
        if (fleeing) {
            return Outcome.NONE;        // la course est menée par sa tâche (flee)
        }
        if (boss == null || !boss.isValid()) {
            done = true;            // tué autrement (ne devrait pas arriver : sa vie est bornée)
            mineRavine(world, st, false);
            Gates.open(world, store, SirensReefLayout.WALL1, null);
            return Outcome.DONE;
        }
        pack.removeIf(ref -> !Spawns.alive(store, ref));
        if (!SirensReef.anyNear(store, players, SirensReefLayout.CLEARING, LEASH + 10)) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                clear(store);
                Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "stonehead.reset"));
                return Outcome.RESET;
            }
            return Outcome.NONE;
        }
        idle = 0f;
        Leash.keepOnDisc(store, boss, Spawns.point(SirensReefLayout.CLEARING), LEASH, 3, SirensReef.FALL_LIMIT);
        float health = Hurt.healthFraction(store, boss);
        if (packs < PACKS.length && health <= PACKS[packs] + 0.001f) {
            packs++;
            callPack(world, store, st);
        }
        if (health <= FLEE_AT + 0.001f) {
            flee(world, store, st);
        }
        return Outcome.NONE;
    }

    private void callPack(World world, Store<EntityStore> store, SirensReef.State st) {
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "stonehead.pack"));
        double[][] spots = SirensReefLayout.CLEARING_SPOTS;
        int first = ThreadLocalRandom.current().nextInt(spots.length);
        for (int i = 0; i < PACK_SIZE; i++) {
            double[] at = spots[(first + i) % spots.length];
            Ref<EntityStore> ref = st.foe(world, store, SirensReef.RAPTOR, at, false);
            if (ref != null) {
                pack.add(ref);
                Telegraphs.particle(store, "Nakasar_Fractal_Stonehead_Roar", Spawns.point(at), 0.4f);
            }
        }
    }

    /** Rugissement annoncé, rochers brisés, course jusqu'à la première mine du ravin. */
    private void flee(World world, Store<EntityStore> store, SirensReef.State st) {
        fleeing = true;
        BossStun.interrupt(world, store, boss);
        BossStun.hold(world, store, boss);
        store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
        Vector3d c = Telegraphs.position(store, boss);
        if (c == null) {
            c = Spawns.point(SirensReefLayout.STONEHEAD);
        }
        Vector3d roar = new Vector3d(c);
        Telegraphs.circle(store, roar, ROAR_RADIUS, ROAR_WINDUP);
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "stonehead.flee"));
        mineRavine(world, st, true);
        Ref<EntityStore> runner = boss;
        int e = epoch;
        double[][] path = runPath(roar);
        long[] begin = {-1};
        double[] travelled = {0};
        long[] last = {0};
        boolean[] roared = {false};
        TelegraphSystem.start(world, new TelegraphSystem.Task() {
            @Override
            public boolean step(World w, Store<EntityStore> s, long now) {
                if (e != epoch) {
                    return true;
                }
                if (!runner.isValid()) {
                    ranOff(w, s, e, runner);     // retiré pendant sa course : il ne reviendra pas
                    return true;
                }
                if (begin[0] < 0) {
                    begin[0] = now;
                    last[0] = now;
                }
                if (now - begin[0] < Telegraphs.seconds(ROAR_WINDUP)) {
                    last[0] = now;
                    return false;
                }
                if (!roared[0]) {
                    roared[0] = true;
                    roar(w, s, roar);
                    Gates.open(w, s, SirensReefLayout.WALL1, null);
                }
                travelled[0] += RUN_SPEED * (now - last[0]) / 1e9;
                last[0] = now;
                Vector3d at = along(path, travelled[0]);
                if (at == null) {
                    trip(w, s, st, runner);
                    return true;
                }
                Vector3d ahead = along(path, travelled[0] + 1);
                float yaw = ahead == null ? 0f : Telegraphs.yawToward(at, ahead);
                s.putComponent(runner, Teleport.getComponentType(), new Teleport(at, new Rotation3f(0f, yaw, 0f)));
                return false;
            }

            @Override
            public void abort(World w, Store<EntityStore> s) {
                ranOff(w, s, e, runner);
            }
        });
    }

    /** La course n'a pas pu finir (il a disparu, ou la tâche a échoué) : la route du ravin s'ouvre quand même. */
    private void ranOff(World world, Store<EntityStore> store, int e, Ref<EntityStore> runner) {
        if (e != epoch || done) {
            return;
        }
        if (runner.isValid()) {
            BossStun.release(store, runner);
            Spawns.remove(store, runner);
        }
        Gates.open(world, store, SirensReefLayout.WALL1, null);
        done = true;
        fleeing = false;
    }

    /** Peur et recul pour qui est dans le cercle du rugissement. */
    private static void roar(World world, Store<EntityStore> store, Vector3d at) {
        Telegraphs.particle(store, "Nakasar_Fractal_Stonehead_Roar", at, 1.2f);
        Telegraphs.sound(store, "SFX_Bear_Voidtaken_Roar", at);
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d pos = Telegraphs.position(store, ref);
            if (pos == null || !Telegraphs.inCircle(pos, at, ROAR_RADIUS)) {
                continue;
            }
            Hurt.effect(store, ref, "Nakasar_Fractal_Fear", ROAR_FEAR);
            Vector3d away = new Vector3d(pos).sub(at);
            away.y = 0;
            Moves.velocity(store, ref, (away.lengthSquared() < 1e-4 ? new Vector3d(1, 0, 0) : away.normalize()).mul(9).add(0, 4, 0));
        }
    }

    /** Du point de fuite à l'entrée du ravin, puis le long du ravin jusqu'à la première mine. */
    private static double[][] runPath(Vector3d from) {
        double[][] ravine = SirensReefLayout.RAVINE;
        int[] mine = SirensReefLayout.RAVINE_MINES[0];
        int stop = 0;
        double best = Double.MAX_VALUE;
        for (int i = 0; i < ravine.length; i++) {
            double d = Math.hypot(ravine[i][0] - mine[0] - 0.5, ravine[i][2] - mine[2] - 0.5);
            if (d < best) {
                best = d;
                stop = i;
            }
        }
        double[][] out = new double[stop + 3][];
        out[0] = new double[]{from.x(), from.y(), from.z()};
        System.arraycopy(ravine, 0, out, 1, stop + 1);
        out[stop + 2] = new double[]{mine[0] + 0.5, mine[1], mine[2] + 0.5};
        return out;
    }

    /** Le point à `distance` blocs le long de `path` (null : au bout). */
    private static Vector3d along(double[][] path, double distance) {
        double left = distance;
        for (int i = 0; i + 1 < path.length; i++) {
            Vector3d a = Spawns.point(path[i]);
            Vector3d b = Spawns.point(path[i + 1]);
            double d = a.distance(b);
            if (left <= d) {
                return d < 1e-6 ? b : new Vector3d(a).lerp(b, left / d);
            }
            left -= d;
        }
        return null;
    }

    /** La première mine saute sous lui : il meurt, et la mine reviendra comme les autres. */
    private void trip(World world, Store<EntityStore> store, SirensReef.State st, Ref<EntityStore> runner) {
        ReefMines.Mine first = st.mines.nearest(ReefMines.RAVINE, Spawns.point(new double[]{
                SirensReefLayout.RAVINE_MINES[0][0] + 0.5, SirensReefLayout.RAVINE_MINES[0][1], SirensReefLayout.RAVINE_MINES[0][2] + 0.5}));
        if (first != null) {
            st.mines.blast(world, store, first, System.nanoTime());
        }
        Spawns.tellAll(world, Message.translation(SirensReef.MESSAGES + "stonehead.mine"));
        dying = true;
        BossStun.release(store, runner);
        store.tryRemoveComponent(runner, Invulnerable.getComponentType());
        Hurt.percent(store, runner, 2f, SirensReef.REEF_CAUSE);
        done = true;
        fleeing = false;
    }

    /** Pose les mines du ravin ; `withFirst` : la première aussi (Tête-de-pierre va sauter dessus). */
    private static void mineRavine(World world, SirensReef.State st, boolean withFirst) {
        int[][] cells = SirensReefLayout.RAVINE_MINES;
        for (int i = withFirst ? 0 : 1; i < cells.length; i++) {
            st.mines.add(world, cells[i], ReefMines.RAVINE, true);
        }
    }

    /** Sa vie ne passe pas le seuil de fuite ; rien pendant la fuite ; la mine l'achève. */
    void filter(CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim, Damage damage) {
        if (!victim.equals(boss) || dying) {
            return;
        }
        if (fleeing) {
            damage.setCancelled(true);
            return;
        }
        EntityStatMap stats = buffer.getComponent(victim, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            float floor = health.getMax() * FLEE_AT;
            damage.setAmount(Math.max(0f, Math.min(damage.getAmount(), health.get() - floor)));
        }
    }

    private void clear(Store<EntityStore> store) {
        epoch++;
        if (boss != null) {
            BossStun.release(store, boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        Spawns.removeAll(store, pack);
        pack.clear();
        fleeing = false;
        idle = 0f;
    }
}
