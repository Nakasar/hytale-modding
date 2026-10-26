package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Colonnes de vent du Pic de Sunqua (GW2 : les courants qui portent du socle au plateau de la Voix, puis du plateau à la
 * corniche des cascades). Ouverte, une colonne tourbillonne à son pied ; qui y entre est porté le long de son trajet
 * ({@link SunquaPeakLayout#COLUMN_1}, {@link SunquaPeakLayout#COLUMN_2}) : comme les trajets du Ressac silencieux, le
 * serveur pose à chaque tick la vitesse du joueur vers un point qui avance sur le trajet ; trop loin (plus de
 * {@value #SNAP} blocs), il y est replacé. Pas de dégâts de chute pendant le trajet et {@value #LANDING} s après.
 */
final class WindColumns {

    static final double[][][] PATHS = {SunquaPeakLayout.COLUMN_1, SunquaPeakLayout.COLUMN_2};
    static final double SPEED = 9;
    static final double SNAP = 6;
    static final double GAIN = 5;
    static final double MAX_SPEED = 40;
    static final float LANDING = 3f;
    /** On entre dans la colonne à moins de cette distance (horizontale) de son pied. */
    static final double REACH = 1.5;

    private static final double[][] LENGTHS = new double[PATHS.length][];

    static {
        for (int r = 0; r < PATHS.length; r++) {
            double[][] path = PATHS[r];
            double[] acc = new double[path.length];
            for (int i = 1; i < path.length; i++) {
                acc[i] = acc[i - 1] + Spawns.point(path[i - 1]).distance(Spawns.point(path[i]));
            }
            LENGTHS[r] = acc;
        }
    }

    private static final class Ride {
        final Ref<EntityStore> ref;
        final int column;
        double s;

        Ride(Ref<EntityStore> ref, int column) {
            this.ref = ref;
            this.column = column;
        }
    }

    private final boolean[] open = new boolean[PATHS.length];
    private final Map<UUID, Ride> rides = new HashMap<>();
    private int beat;

    void open(int column) {
        open[column] = true;
    }

    /** Un tick du monde : entrées dans les colonnes, trajets en cours. */
    void tick(World world, Store<EntityStore> store, SunquaPeak.State st, float dt) {
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        boolean puff = ++beat % 12 == 0;
        for (int c = 0; c < PATHS.length; c++) {
            if (!open[c]) {
                continue;
            }
            Vector3d foot = Spawns.point(PATHS[c][0]);
            if (puff) {
                Telegraphs.particle(store, "Nakasar_Fractal_Wind_Column", foot, 1f);
            }
            for (PlayerRef p : players) {
                if (rides.containsKey(p.getUuid())) {
                    continue;
                }
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, foot) <= REACH && Math.abs(at.y() - foot.y()) < 2) {
                    rides.put(p.getUuid(), new Ride(p.getReference(), c));
                    Telegraphs.sound(store, "SFX_Ability_Wind_Strike_Slash", foot);
                }
            }
        }
        Iterator<Map.Entry<UUID, Ride>> it = rides.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<UUID, Ride> e = it.next();
            Ride r = e.getValue();
            Vector3d at = Telegraphs.position(store, r.ref);
            if (at == null) {
                it.remove();
                continue;
            }
            st.safe(e.getKey(), LANDING);
            double[] lengths = LENGTHS[r.column];
            r.s += SPEED * dt;
            if (r.s >= lengths[lengths.length - 1]) {
                Moves.velocity(store, r.ref, tangent(r.column, r.s).mul(2));
                it.remove();
                continue;
            }
            Vector3d target = point(r.column, r.s);
            if (at.distance(target) > SNAP) {
                Moves.teleport(store, r.ref, target);
                continue;
            }
            Vector3d v = tangent(r.column, r.s).mul(SPEED).add(new Vector3d(target).sub(at).mul(GAIN));
            if (v.length() > MAX_SPEED) {
                v.normalize().mul(MAX_SPEED);
            }
            Moves.velocity(store, r.ref, v);
            if (beat % 4 == 0) {
                Telegraphs.particle(store, "Nakasar_Fractal_Wind_Column", new Vector3d(at).add(0, 0.5, 0), 0.5f);
            }
        }
    }

    private static Vector3d point(int column, double s) {
        double[][] path = PATHS[column];
        double[] acc = LENGTHS[column];
        int i = 1;
        while (i < path.length - 1 && acc[i] < s) {
            i++;
        }
        double seg = acc[i] - acc[i - 1];
        double t = seg <= 0 ? 1 : Math.max(0, Math.min(1, (s - acc[i - 1]) / seg));
        double[] a = path[i - 1];
        double[] b = path[i];
        return new Vector3d(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
    }

    private static Vector3d tangent(int column, double s) {
        Vector3d d = point(column, s + 0.5).sub(point(column, Math.max(0, s - 0.5)));
        return d.lengthSquared() < 1e-6 ? new Vector3d() : d.normalize();
    }
}
