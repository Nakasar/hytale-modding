package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.worldgen.biome.Biome;
import com.hypixel.hytale.server.worldgen.chunk.ChunkGenerator;
import com.hypixel.hytale.server.worldgen.chunk.ZoneBiomeResult;
import com.hypixel.hytale.server.worldgen.container.WaterContainer;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.zone.Zones;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * Trajet par la terre ferme entre deux points quand aucune route balisée ne les relie (Kevin, 16 novembre 2026 : « que
 * les PNJ ne passent pas par l'eau, que leur trajet reste logique »). Le relief et l'eau sont lus dans le générateur
 * vanilla, sans charger de chunk : hauteur du sol {@code ChunkGenerator.getHeight} et niveau d'eau du biome
 * {@code WaterContainer} (comme {@code UniquePrefabGenerator.getHeight} vanilla, qui pose les prefabs uniques au-dessus
 * de l'eau). Une colonne est mouillée quand l'eau du biome monte au-dessus du sol.
 * <ul>
 *   <li>ligne droite sèche : gardée telle quelle ;</li>
 *   <li>sinon A* sur une grille de {@value #CELL} blocs (8 voisins, chaque pas vérifié tous les {@value #PROBE} blocs,
 *   les pentes coûtent plus cher), dans une boîte autour des deux points, puis lissage : on saute les points tant que la
 *   ligne reste sèche ;</li>
 *   <li>pas de générateur (instances, mondes plats) ou pas de passage dans la limite de calcul : null, l'appelant garde
 *   la ligne droite.</li>
 * </ul>
 * Le terrain généré ne change pas : les trajets et les colonnes sondées sont gardés en mémoire pour la session.
 */
public final class LandPath {

    /** Côté d'une case de la grille (blocs). */
    static final int CELL = 16;
    /** Pas de sondage le long d'un segment (blocs) : plus fin que la largeur d'une rivière. */
    static final int PROBE = 4;
    /** Cases ouvertes au plus par recherche (le calcul tourne sur le thread du monde). */
    static final int MAX_EXPANSIONS = 6000;
    /** Marge de la boîte de recherche autour des deux points : au moins ceci, ou 60 % de leur distance. */
    static final int MIN_MARGIN = 192;
    /** Coût d'un bloc de dénivelé entre deux cases, en plus de la distance ; au-delà de STEEP, chaque bloc coûte STEEP_COST. */
    static final double CLIMB_COST = 3.0;
    static final int STEEP = 8;
    static final double STEEP_COST = 20.0;

    private static final int WET = Integer.MIN_VALUE;
    private static final int UNKNOWN = Integer.MIN_VALUE + 1;
    private static final int MAX_COLUMNS = 250_000;
    private static final int MAX_PATHS = 512;

    /** Colonnes sondées, par graine de monde (clé x, z) : hauteur du sol, ou WET. */
    private static final Map<Integer, Map<Long, Integer>> COLUMNS = new HashMap<>();
    /** Trajets trouvés (clé des deux points arrondis au bloc) ; une liste vide = ligne droite. */
    private static final Map<String, List<double[]>> PATHS = new LinkedHashMap<>(64, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, List<double[]>> eldest) {
            return size() > MAX_PATHS;
        }
    };

    private LandPath() {
    }

    /** Oublie tout (changement de monde, arrêt du plugin). */
    public static synchronized void clear() {
        COLUMNS.clear();
        PATHS.clear();
    }

    /**
     * Points (x, z) d'un trajet à pied sec de (fx, fz) à (tx, tz), départ et arrivée compris, ou null pour la ligne
     * droite (déjà sèche, monde sans générateur, ou aucun passage trouvé).
     */
    public static synchronized List<double[]> find(World world, double fx, double fz, double tx, double tz) {
        ChunkGenerator g = Zones.generator(world);
        if (g == null) {
            return null;
        }
        int seed = Zones.seed(world);
        String key = seed + ":" + Math.round(fx) + "," + Math.round(fz) + ">" + Math.round(tx) + "," + Math.round(tz);
        List<double[]> cached = PATHS.get(key);
        if (cached != null) {
            return cached.isEmpty() ? null : cached;
        }
        List<double[]> path = null;
        if (!dry(g, seed, fx, fz, tx, tz)) {
            long t0 = System.nanoTime();
            path = search(g, seed, fx, fz, tx, tz);
            long ms = (System.nanoTime() - t0) / 1_000_000;
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples : trajet à pied sec %d,%d -> %d,%d : %s (%d ms)",
                    (int) fx, (int) fz, (int) tx, (int) tz, path == null ? "aucun, ligne droite" : path.size() + " points", ms);
        }
        PATHS.put(key, path == null ? List.of() : path);
        return path;
    }

    // ---- Recherche ----

    private record Node(int cx, int cz, double f) {
    }

    private static List<double[]> search(ChunkGenerator g, int seed, double fx, double fz, double tx, double tz) {
        double dist = Math.hypot(tx - fx, tz - fz);
        int margin = (int) Math.max(MIN_MARGIN, dist * 0.6);
        int minX = cell(Math.min(fx, tx) - margin);
        int maxX = cell(Math.max(fx, tx) + margin);
        int minZ = cell(Math.min(fz, tz) - margin);
        int maxZ = cell(Math.max(fz, tz) + margin);
        int sx = cell(fx);
        int sz = cell(fz);
        int gx = cell(tx);
        int gz = cell(tz);
        Map<Long, Double> cost = new HashMap<>();
        Map<Long, Long> prev = new HashMap<>();
        PriorityQueue<Node> open = new PriorityQueue<>((a, b) -> Double.compare(a.f(), b.f()));
        long start = key(sx, sz);
        long goal = key(gx, gz);
        cost.put(start, 0.0);
        open.add(new Node(sx, sz, h(sx, sz, gx, gz)));
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
        int expansions = 0;
        boolean found = false;
        while (!open.isEmpty() && expansions < MAX_EXPANSIONS) {
            Node n = open.poll();
            long k = key(n.cx(), n.cz());
            double c = cost.get(k);
            if (n.f() > c + h(n.cx(), n.cz(), gx, gz) + 1e-6) {
                continue;
            }
            if (k == goal) {
                found = true;
                break;
            }
            expansions++;
            double ax = k == start ? fx : centre(n.cx());
            double az = k == start ? fz : centre(n.cz());
            int here = height(g, seed, ax, az);
            for (int[] d : dirs) {
                int nx = n.cx() + d[0];
                int nz = n.cz() + d[1];
                if (nx < minX || nx > maxX || nz < minZ || nz > maxZ) {
                    continue;
                }
                long nk = key(nx, nz);
                boolean isGoal = nk == goal;
                double bx = isGoal ? tx : centre(nx);
                double bz = isGoal ? tz : centre(nz);
                int there = height(g, seed, bx, bz);
                // L'arrivée (un cœur de village au bord de l'eau, un ponton) compte comme sèche.
                if ((there == WET && !isGoal) || !dry(g, seed, ax, az, bx, bz)) {
                    continue;
                }
                // En diagonale, les deux cases d'angle doivent être sèches (pas de coin de lac coupé).
                if (d[0] != 0 && d[1] != 0 && (height(g, seed, centre(n.cx() + d[0]), centre(n.cz())) == WET
                        || height(g, seed, centre(n.cx()), centre(n.cz() + d[1])) == WET)) {
                    continue;
                }
                boolean known = here != WET && here != UNKNOWN && there != WET && there != UNKNOWN;
                int climb = known ? Math.abs(there - here) : 0;
                double step = Math.hypot(bx - ax, bz - az) + CLIMB_COST * climb + (climb > STEEP ? STEEP_COST * (climb - STEEP) : 0);
                double nc = c + step;
                Double old = cost.get(nk);
                if (old == null || nc < old) {
                    cost.put(nk, nc);
                    prev.put(nk, k);
                    open.add(new Node(nx, nz, nc + h(nx, nz, gx, gz)));
                }
            }
        }
        if (!found) {
            return null;
        }
        List<double[]> cells = new ArrayList<>();
        for (Long k = goal; k != null; k = prev.get(k)) {
            if (k == goal) {
                cells.add(0, new double[] {tx, tz});
            } else if (k == start) {
                cells.add(0, new double[] {fx, fz});
            } else {
                cells.add(0, new double[] {centre((int) (k >> 32)), centre((int) (long) k)});
            }
            if (k == start) {
                break;
            }
        }
        if (start == goal) {
            cells.add(0, new double[] {fx, fz});
        }
        return smooth(g, seed, cells);
    }

    /** Saute les points intermédiaires tant que la ligne reste sèche (au plus 16 points d'un coup). */
    private static List<double[]> smooth(ChunkGenerator g, int seed, List<double[]> pts) {
        List<double[]> out = new ArrayList<>();
        int i = 0;
        out.add(pts.get(0));
        while (i < pts.size() - 1) {
            int j = Math.min(pts.size() - 1, i + 16);
            while (j > i + 1 && !dry(g, seed, pts.get(i)[0], pts.get(i)[1], pts.get(j)[0], pts.get(j)[1])) {
                j--;
            }
            out.add(pts.get(j));
            i = j;
        }
        return out;
    }

    // ---- Terrain ----

    /** Vrai si le segment ne passe sur aucune colonne mouillée (sondée tous les PROBE blocs, bouts exclus). */
    private static boolean dry(ChunkGenerator g, int seed, double ax, double az, double bx, double bz) {
        double len = Math.hypot(bx - ax, bz - az);
        int steps = (int) Math.ceil(len / PROBE);
        for (int s = 1; s < steps; s++) {
            double f = (double) s / steps;
            if (height(g, seed, ax + (bx - ax) * f, az + (bz - az) * f) == WET) {
                return false;
            }
        }
        return true;
    }

    /** Hauteur du sol généré en (x, z), ou WET si l'eau du biome la recouvre, ou UNKNOWN. */
    static int height(ChunkGenerator g, int seed, double x, double z) {
        int bx = (int) Math.floor(x);
        int bz = (int) Math.floor(z);
        long k = key(bx, bz);
        Map<Long, Integer> columns = COLUMNS.computeIfAbsent(seed, s -> new LinkedHashMap<>(4096, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<Long, Integer> eldest) {
                return size() > MAX_COLUMNS;
            }
        });
        Integer v = columns.get(k);
        if (v != null) {
            return v;
        }
        int h;
        try {
            h = g.getHeight(seed, bx, bz);
            ZoneBiomeResult r = g.getZoneBiomeResultAt(seed, bx, bz);
            Biome biome = r == null ? null : r.getBiome();
            WaterContainer water = biome == null ? null : biome.getWaterContainer();
            if (water != null && water.hasEntries()) {
                for (WaterContainer.Entry e : water.getEntries()) {
                    int max = e.getMax(seed, bx, bz);
                    if (max >= e.getMin(seed, bx, bz) && max > h && e.shouldPopulate(seed, bx, bz)) {
                        h = WET;
                        break;
                    }
                }
            }
        } catch (RuntimeException e) {
            h = UNKNOWN;
        }
        columns.put(k, h);
        return h;
    }

    private static double h(int cx, int cz, int gx, int gz) {
        return Math.hypot(cx - gx, cz - gz) * CELL;
    }

    private static int cell(double v) {
        return Math.floorDiv((int) Math.floor(v), CELL);
    }

    private static double centre(int c) {
        return c * CELL + CELL / 2.0;
    }

    private static long key(int a, int b) {
        return ((long) a << 32) | (b & 0xffffffffL);
    }
}
