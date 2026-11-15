package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageRegistry;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Routes des convois : les joueurs posent des balises de route ({@value #BEACON}), communes à tous les villages. Deux
 * balises à moins de {@value #LINK} blocs (à l'horizontale) sont reliées ; les cœurs des villages, la sortie de
 * l'avant-poste et le dépôt d'arrivée sont des balises aussi. Un convoi prend le plus court chemin de balise en balise
 * ({@link #path}) ; sans route complète, la ligne droite.
 */
public final class Routes {

    /** Objet (et bloc) balise de route. */
    public static final String BEACON = "Nakasar_Peuples_Route_Beacon";
    /** Deux balises plus proches que ceci sont reliées. */
    public static final int LINK = 32;
    /** Balises au plus dans un monde. */
    public static final int MAX_BEACONS = 1024;

    private Routes() {
    }

    /** Une route : ses points (x, z) et la distance parcourue à chacun. */
    public static final class Path {
        final int version;
        final double[] xs;
        final double[] zs;
        final double[] arcs;
        final int beacons;

        Path(int version, List<double[]> points, int beacons) {
            this.version = version;
            this.beacons = beacons;
            int n = points.size();
            xs = new double[n];
            zs = new double[n];
            arcs = new double[n];
            for (int i = 0; i < n; i++) {
                xs[i] = points.get(i)[0];
                zs[i] = points.get(i)[1];
                arcs[i] = i == 0 ? 0 : arcs[i - 1] + Math.hypot(xs[i] - xs[i - 1], zs[i] - zs[i - 1]);
            }
        }

        public double length() {
            return arcs[arcs.length - 1];
        }

        /** Balises de joueur sur la route (0 : ligne droite). */
        /** Version des balises au moment du calcul (comparer à {@code VillageRegistry.beaconVersion()}). */
        public int version() {
            return version;
        }

        public int beacons() {
            return beacons;
        }

        private int segment(double at) {
            for (int i = 1; i < arcs.length; i++) {
                if (at <= arcs[i]) {
                    return i;
                }
            }
            return arcs.length - 1;
        }

        /** Point (x, z) à `at` blocs du départ. */
        public double[] point(double at) {
            if (arcs.length == 1) {
                return new double[] {xs[0], zs[0]};
            }
            at = Math.max(0, Math.min(length(), at));
            int i = segment(at);
            double span = arcs[i] - arcs[i - 1];
            double f = span <= 0 ? 1 : (at - arcs[i - 1]) / span;
            return new double[] {xs[i - 1] + (xs[i] - xs[i - 1]) * f, zs[i - 1] + (zs[i] - zs[i - 1]) * f};
        }

        /** Direction (unitaire) de la route à `at`. */
        public double[] dir(double at) {
            if (arcs.length == 1) {
                return new double[] {1, 0};
            }
            int i = segment(Math.max(0, Math.min(length(), at)));
            double span = Math.max(1e-6, arcs[i] - arcs[i - 1]);
            return new double[] {(xs[i] - xs[i - 1]) / span, (zs[i] - zs[i - 1]) / span};
        }

        /** Distance parcourue du premier coude après `at + margin` (la prochaine balise à atteindre), ou la fin. */
        public double nextTurn(double at, double margin) {
            for (int i = 1; i < arcs.length; i++) {
                if (arcs[i] > at + margin) {
                    return arcs[i];
                }
            }
            return length();
        }

        /** Distance parcourue du point de la route le plus proche de (x, z), cherché entre `lo` et `hi`. */
        public double closest(double x, double z, double lo, double hi) {
            lo = Math.max(0, lo);
            hi = Math.min(length(), hi);
            double best = lo;
            double bestD = Double.MAX_VALUE;
            for (int i = 1; i < arcs.length; i++) {
                if (arcs[i] < lo || arcs[i - 1] > hi) {
                    continue;
                }
                double span = arcs[i] - arcs[i - 1];
                double t = span <= 0 ? 0 : ((x - xs[i - 1]) * (xs[i] - xs[i - 1]) + (z - zs[i - 1]) * (zs[i] - zs[i - 1])) / (span * span);
                double arc = Math.max(lo, Math.min(hi, arcs[i - 1] + Math.max(0, Math.min(1, t)) * span));
                double[] p = point(arc);
                double d = (p[0] - x) * (p[0] - x) + (p[1] - z) * (p[1] - z);
                if (d < bestD) {
                    bestD = d;
                    best = arc;
                }
            }
            return best;
        }
    }

    /**
     * Plus court chemin de (fx, fz) à (tx, tz) par les balises du monde et les cœurs des villages (liens de
     * {@value #LINK} blocs au plus). Sans chemin, la ligne droite.
     */
    public static Path path(World world, double fx, double fz, double tx, double tz) {
        VillageRegistry registry = Villages.registry(world);
        List<double[]> nodes = new ArrayList<>();
        nodes.add(new double[] {fx, fz});
        nodes.add(new double[] {tx, tz});
        for (int[] b : registry.beacons()) {
            nodes.add(new double[] {b[0] + 0.5, b[2] + 0.5, 1});
        }
        for (Village v : registry.all()) {
            nodes.add(new double[] {v.x() + 0.5, v.z() + 0.5});
        }
        int n = nodes.size();
        double[] dist = new double[n];
        int[] prev = new int[n];
        boolean[] done = new boolean[n];
        Arrays.fill(dist, Double.MAX_VALUE);
        Arrays.fill(prev, -1);
        dist[0] = 0;
        double link2 = (double) LINK * LINK;
        for (int k = 0; k < n; k++) {
            int u = -1;
            for (int i = 0; i < n; i++) {
                if (!done[i] && dist[i] < Double.MAX_VALUE && (u < 0 || dist[i] < dist[u])) {
                    u = i;
                }
            }
            if (u < 0 || u == 1) {
                break;
            }
            done[u] = true;
            double[] a = nodes.get(u);
            for (int i = 0; i < n; i++) {
                if (done[i]) {
                    continue;
                }
                double[] b = nodes.get(i);
                double d2 = (a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]);
                if (d2 <= link2 && dist[u] + Math.sqrt(d2) < dist[i]) {
                    dist[i] = dist[u] + Math.sqrt(d2);
                    prev[i] = u;
                }
            }
        }
        List<double[]> points = new ArrayList<>();
        int beacons = 0;
        if (prev[1] < 0) {
            points.add(new double[] {fx, fz});
            points.add(new double[] {tx, tz});
        } else {
            for (int i = 1; i >= 0; i = prev[i]) {
                double[] p = nodes.get(i);
                points.add(0, new double[] {p[0], p[1]});
                if (p.length == 3) {
                    beacons++;
                }
                if (i == 0) {
                    break;
                }
            }
        }
        return new Path(registry.beaconVersion(), points, beacons);
    }

    /**
     * Ce qui manque à la route de (fx, fz) à (tx, tz) : la plus courte distance entre ce qui est relié au départ et ce
     * qui est relié à l'arrivée (balises, cœurs), moins {@value #LINK} ; 0 quand la route est complète. Sert à la quête
     * de village « Baliser une route » ({@link dev.nakasar.hytale.peuples.request.RouteQuests}).
     */
    public static double gap(World world, double fx, double fz, double tx, double tz) {
        VillageRegistry registry = Villages.registry(world);
        List<double[]> nodes = new ArrayList<>();
        nodes.add(new double[] {fx, fz});
        nodes.add(new double[] {tx, tz});
        for (int[] b : registry.beacons()) {
            nodes.add(new double[] {b[0] + 0.5, b[2] + 0.5});
        }
        for (Village v : registry.all()) {
            nodes.add(new double[] {v.x() + 0.5, v.z() + 0.5});
        }
        boolean[] fromStart = reach(nodes, 0);
        if (fromStart[1]) {
            return 0;
        }
        boolean[] fromEnd = reach(nodes, 1);
        double best = Double.MAX_VALUE;
        for (int i = 0; i < nodes.size(); i++) {
            if (!fromStart[i]) {
                continue;
            }
            double[] a = nodes.get(i);
            for (int j = 0; j < nodes.size(); j++) {
                if (fromEnd[j]) {
                    double[] b = nodes.get(j);
                    best = Math.min(best, (a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]));
                }
            }
        }
        return Math.max(1, Math.sqrt(best) - LINK);
    }

    /** Points reliés (de proche en proche, liens de {@value #LINK} blocs au plus) au point `start`. */
    private static boolean[] reach(List<double[]> nodes, int start) {
        int n = nodes.size();
        boolean[] seen = new boolean[n];
        int[] queue = new int[n];
        int head = 0;
        int tail = 0;
        seen[start] = true;
        queue[tail++] = start;
        double link2 = (double) LINK * LINK;
        while (head < tail) {
            double[] a = nodes.get(queue[head++]);
            for (int i = 0; i < n; i++) {
                if (!seen[i]) {
                    double[] b = nodes.get(i);
                    if ((a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) <= link2) {
                        seen[i] = true;
                        queue[tail++] = i;
                    }
                }
            }
        }
        return seen;
    }

    /** Balises reliées à (x, z) (à moins de {@value #LINK} blocs), elle non comprise. */
    public static int links(World world, int x, int z) {
        int n = 0;
        for (int[] b : Villages.registry(world).beacons()) {
            double dx = b[0] - x;
            double dz = b[2] - z;
            if ((dx != 0 || dz != 0) && dx * dx + dz * dz <= (double) LINK * LINK) {
                n++;
            }
        }
        return n;
    }
}
