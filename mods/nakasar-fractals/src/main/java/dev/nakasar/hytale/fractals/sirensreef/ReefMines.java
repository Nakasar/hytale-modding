package dev.nakasar.hytale.fractals.sirensreef;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Mines du récif, blocs posés par le Java (non sauvegardés) : celles du ravin, qui reviennent {@value #RESPAWN} s après
 * avoir sauté, et celles que Black Peter sème dans son fort.
 * <ul>
 *   <li>un joueur à moins de {@value #ARM_RADIUS} blocs l'arme : mèche, cercle rouge de {@value #BLAST_RADIUS} blocs (le
 *   souffle exact) pendant {@value #FUSE} s, puis {@value #BLAST_PART} des PV et projection pour qui est dedans ;</li>
 *   <li>un boulet du canon des ombres la fait sauter sans blesser personne ({@link #shot}).</li>
 * </ul>
 */
final class ReefMines {

    static final double ARM_RADIUS = 1.6;
    static final double BLAST_RADIUS = 2.5;
    static final float FUSE = 1.2f;
    static final float BLAST_PART = 0.15f;
    static final float RESPAWN = 30f;
    static final String RAVINE = "Ravine";
    static final String FORT = "Fort";

    static final class Mine {
        final int x;
        final int y;
        final int z;
        final String group;
        final boolean respawn;
        boolean placed;
        long back;
        long blastAt;

        Mine(int x, int y, int z, String group, boolean respawn) {
            this.x = x;
            this.y = y;
            this.z = z;
            this.group = group;
            this.respawn = respawn;
        }

        Vector3d center() {
            return new Vector3d(x + 0.5, y, z + 0.5);
        }
    }

    private final List<Mine> mines = new ArrayList<>();

    /** Pose une mine en {x, y, z} (bloc) ; `respawn` : elle revient après avoir sauté. Une case n'en porte qu'une : la
     * mine encore là (semée à une vague précédente) est gardée telle quelle. */
    Mine add(World world, int[] cell, String group, boolean respawn) {
        for (Mine old : mines) {
            if (old.x == cell[0] && old.y == cell[1] && old.z == cell[2]) {
                if (!old.placed) {
                    place(world, old);
                }
                return old;
            }
        }
        Mine m = new Mine(cell[0], cell[1], cell[2], group, respawn);
        mines.add(m);
        place(world, m);
        return m;
    }

    private static void place(World world, Mine m) {
        WorldBlocks.set(world.getChunkStore(), m.x, m.y, m.z, SirensReef.MINE, 0);
        m.placed = true;
        m.blastAt = 0;
    }

    private static void lift(World world, Mine m) {
        ChunkStore chunks = world.getChunkStore();
        if (SirensReef.MINE.equals(WorldBlocks.name(chunks, m.x, m.y, m.z))) {
            WorldBlocks.clear(chunks, m.x, m.y, m.z);
        }
        m.placed = false;
        m.blastAt = 0;
    }

    void step(World world, Store<EntityStore> store, List<PlayerRef> players, long now) {
        for (Mine m : List.copyOf(mines)) {
            if (!m.placed) {
                if (m.respawn && m.back > 0 && now >= m.back) {
                    place(world, m);
                }
                continue;
            }
            if (m.blastAt > 0) {
                if (now >= m.blastAt) {
                    blast(world, store, m, now);
                }
                continue;
            }
            Vector3d c = m.center();
            for (PlayerRef p : players) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, c) <= ARM_RADIUS && Math.abs(at.y() - c.y()) < 2) {
                    arm(store, m, now);
                    break;
                }
            }
        }
    }

    private static void arm(Store<EntityStore> store, Mine m, long now) {
        m.blastAt = now + Telegraphs.seconds(FUSE);
        Telegraphs.circle(store, m.center(), BLAST_RADIUS, FUSE);
        Telegraphs.particle(store, "Nakasar_Fractal_Mine_Fuse", m.center(), 1f);
        Telegraphs.sound(store, "SFX_Bomb_Fuse", m.center());
    }

    /** La mine saute : souffle sur les joueurs du cercle, retour plus tard pour celles du ravin. */
    void blast(World world, Store<EntityStore> store, Mine m, long now) {
        Vector3d c = m.center();
        lift(world, m);
        Telegraphs.particle(store, "Nakasar_Fractal_Mine_Blast", c, 1.2f);
        Telegraphs.sound(store, "SFX_Weapon_Goblin_Cannon_Fire", c);
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            Ref<EntityStore> ref = p.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || !Telegraphs.inCircle(at, c, BLAST_RADIUS)) {
                continue;
            }
            Hurt.percent(store, ref, BLAST_PART, SirensReef.REEF_CAUSE);
            Vector3d away = new Vector3d(at).sub(c);
            away.y = 0;
            Moves.velocity(store, ref, (away.lengthSquared() < 1e-4 ? new Vector3d(1, 0, 0) : away.normalize()).mul(6).add(0, 8, 0));
        }
        settle(m, now);
    }

    private void settle(Mine m, long now) {
        if (m.respawn) {
            m.back = now + Telegraphs.seconds(RESPAWN);
        } else {
            mines.remove(m);
        }
    }

    /** Un boulet tombe en `at` : les mines posées à moins de `radius` blocs sautent sans dégâts. Rend combien. */
    int shot(World world, Store<EntityStore> store, Vector3d at, double radius) {
        int n = 0;
        long now = System.nanoTime();
        for (Mine m : List.copyOf(mines)) {
            if (m.placed && Telegraphs.horizontal(at, m.center()) <= radius + 0.5 && Math.abs(at.y() - m.y) < 4) {
                lift(world, m);
                Telegraphs.particle(store, "Nakasar_Fractal_Mine_Blast", m.center(), 0.8f);
                settle(m, now);
                n++;
            }
        }
        return n;
    }

    /** La mine posée du groupe `group` la plus proche de `from` (null : aucune). */
    Mine nearest(String group, Vector3d from) {
        Mine best = null;
        double d = Double.MAX_VALUE;
        for (Mine m : mines) {
            if (m.placed && m.blastAt == 0 && m.group.equals(group) && m.center().distance(from) < d) {
                d = m.center().distance(from);
                best = m;
            }
        }
        return best;
    }

    /** Retire la mine sans qu'elle saute (Black Peter l'avale). */
    void swallow(World world, Mine m) {
        lift(world, m);
        settle(m, System.nanoTime());
    }

    int count(String group) {
        int n = 0;
        for (Mine m : mines) {
            if (m.placed && m.group.equals(group)) {
                n++;
            }
        }
        return n;
    }

    /** Retire toutes les mines du groupe `group`. */
    void clear(World world, String group) {
        for (Mine m : List.copyOf(mines)) {
            if (m.group.equals(group)) {
                lift(world, m);
                mines.remove(m);
            }
        }
    }
}
