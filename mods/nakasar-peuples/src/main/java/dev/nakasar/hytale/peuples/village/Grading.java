package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiPredicate;

/**
 * Terrassement d'un site de village en une passe : plusieurs plateformes (place, emprises) posées ensemble, des talus
 * à un bloc de pente au plus vers le relief d'origine, puis le nettoyage de la végétation. Remplace l'ancien
 * aplanissement emprise par emprise, qui coupait les arbres à la verticale du bord (troncs tranchés, feuillages en
 * l'air) et laissait des marches de deux ou trois blocs entre une emprise et son voisinage.
 *
 * <p>Ordre : hauteurs visées (plateformes fixes, talus bornés par une pente d'un bloc par bloc depuis les colonnes
 * qu'on ne touche pas), arbres entiers retirés (tronc, branches, racines et le feuillage qu'ils portent) dès qu'ils
 * touchent le site, écriture du relief, puis retrait de tout ce qui flotte : grappes de bois et de feuilles qui ne
 * reposent plus sur rien, plantes sans sol. Toutes les écritures se font sur le thread du monde.
 */
public final class Grading {

    /** Débord horizontal sondé autour du site pour trouver les arbres entiers (couronnes des grands chênes). */
    private static final int TREE_REACH = 14;
    /** Distance (en blocs de feuillage) jusqu'à laquelle une feuille appartient au bois le plus proche. */
    private static final int LEAF_REACH = 7;
    /** Hauteur sondée au-dessus du plus haut sol du site pour les arbres. */
    private static final int TREE_HEIGHT = 48;
    /** Profondeur sondée sous le plus bas sol du site (racines). */
    private static final int ROOT_DEPTH = 8;
    /** Garde-fou : nombre maximal de blocs d'arbre examinés. */
    private static final int MAX_TREE_BLOCKS = 600_000;

    private static final byte ANCHOR = 0;
    private static final byte PAD = 1;
    private static final byte FREE = 2;

    private static final byte WOOD = 1;
    private static final byte LEAF = 2;

    private record Pad(int x0, int x1, int z0, int z1, int h, int margin, String top) {
        double distance(int x, int z) {
            int dx = Math.max(0, Math.max(x0 - x, x - x1));
            int dz = Math.max(0, Math.max(z0 - z, z - z1));
            return Math.hypot(dx, dz);
        }

        boolean contains(int x, int z) {
            return x >= x0 && x <= x1 && z >= z0 && z <= z1;
        }
    }

    private final ChunkStore chunks;
    private final Terrain terrain;
    private final List<Pad> pads = new ArrayList<>();
    private final Map<Long, BlockSection> sections = new HashMap<>();

    public Grading(World world) {
        this.chunks = world.getChunkStore();
        this.terrain = new Terrain(world);
    }

    /**
     * Ajoute une plateforme : le rectangle [x0, x1] x [z0, z1] plus `margin` blocs autour, à la hauteur `h`, couche
     * du dessus `top`. Une colonne dans plusieurs rectangles prend le dernier ajouté.
     */
    public Grading pad(int x0, int x1, int z0, int z1, int h, int margin, String top) {
        pads.add(new Pad(x0, x1, z0, z1, h, margin, top));
        return this;
    }

    /**
     * Terrasse le site. Le talus s'étend jusqu'à `2 x blend` blocs au-delà des marges mais ne retouche que les colonnes
     * qui l'exigent (pente d'un bloc par bloc). `ground` couvre les talus. Les colonnes que `keep` réserve hors des
     * rectangles (emprise d'un bâtiment existant) ne sont jamais touchées, ni leurs arbres.
     */
    public void apply(int blend, String ground, BiPredicate<Integer, Integer> keep) {
        if (pads.isEmpty()) {
            return;
        }
        int maxMargin = 0;
        int bx0 = Integer.MAX_VALUE, bx1 = Integer.MIN_VALUE, bz0 = Integer.MAX_VALUE, bz1 = Integer.MIN_VALUE;
        for (Pad p : pads) {
            maxMargin = Math.max(maxMargin, p.margin());
            bx0 = Math.min(bx0, p.x0());
            bx1 = Math.max(bx1, p.x1());
            bz0 = Math.min(bz0, p.z0());
            bz1 = Math.max(bz1, p.z1());
        }
        int slope = 2 * blend;
        int ring = maxMargin + slope + 1;
        int x0 = bx0 - ring, z0 = bz0 - ring;
        int w = bx1 - bx0 + 1 + 2 * ring;
        int d = bz1 - bz0 + 1 + 2 * ring;

        // 1. Nature et hauteur de chaque colonne.
        byte[] kind = new byte[w * d];
        int[] padOf = new int[w * d];
        int[] surface = new int[w * d];
        boolean[] protect = new boolean[w * d];
        for (int i = 0; i < w; i++) {
            for (int k = 0; k < d; k++) {
                int x = x0 + i, z = z0 + k, c = i * d + k;
                surface[c] = terrain.surface(x, z);
                padOf[c] = -1;
                int inside = -1;
                for (int p = 0; p < pads.size(); p++) {
                    if (pads.get(p).contains(x, z)) {
                        inside = p;
                    }
                }
                if (inside >= 0) {
                    kind[c] = PAD;
                    padOf[c] = inside;
                    continue;
                }
                if (keep != null && keep.test(x, z)) {
                    protect[c] = true;
                    kind[c] = ANCHOR;
                    continue;
                }
                double best = Double.MAX_VALUE;
                int nearest = -1;
                boolean inSlope = false;
                for (int p = 0; p < pads.size(); p++) {
                    Pad pad = pads.get(p);
                    double dist = pad.distance(x, z);
                    if (dist <= pad.margin() && dist < best) {
                        best = dist;
                        nearest = p;
                    }
                    inSlope |= dist <= pad.margin() + slope;
                }
                if (nearest >= 0) {
                    kind[c] = PAD;
                    padOf[c] = nearest;
                } else if (inSlope && surface[c] != Terrain.NONE && untouched(x, surface[c], z)) {
                    kind[c] = FREE;
                } else {
                    kind[c] = ANCHOR;
                }
            }
        }

        // 2. Bornes de pente : chaque colonne libre reste à un bloc par bloc (distance de Manhattan) des colonnes fixes.
        int inf = Integer.MAX_VALUE / 4;
        int[] upper = new int[w * d];
        int[] lower = new int[w * d];
        for (int c = 0; c < w * d; c++) {
            int fixed = kind[c] == PAD ? pads.get(padOf[c]).h() : kind[c] == ANCHOR ? surface[c] : Terrain.NONE;
            upper[c] = fixed == Terrain.NONE ? inf : fixed;
            lower[c] = fixed == Terrain.NONE ? -inf : fixed;
        }
        for (int pass = 0; pass < 6; pass++) {
            boolean changed = false;
            for (int i = 0; i < w; i++) {
                for (int k = 0; k < d; k++) {
                    changed |= relax(upper, lower, kind, w, d, i, k, i - 1, k);
                    changed |= relax(upper, lower, kind, w, d, i, k, i, k - 1);
                }
            }
            for (int i = w - 1; i >= 0; i--) {
                for (int k = d - 1; k >= 0; k--) {
                    changed |= relax(upper, lower, kind, w, d, i, k, i + 1, k);
                    changed |= relax(upper, lower, kind, w, d, i, k, i, k + 1);
                }
            }
            if (!changed) {
                break;
            }
        }
        int[] target = new int[w * d];
        boolean[] core = new boolean[w * d];
        int minY = Integer.MAX_VALUE, maxY = Integer.MIN_VALUE;
        for (int c = 0; c < w * d; c++) {
            int s = surface[c];
            if (kind[c] == PAD) {
                target[c] = pads.get(padOf[c]).h();
            } else if (kind[c] == FREE) {
                target[c] = lower[c] <= upper[c] ? Math.max(lower[c], Math.min(upper[c], s))
                        : (int) Math.round((lower[c] + (double) upper[c]) / 2);
            } else {
                target[c] = s;
            }
            if (s != Terrain.NONE) {
                minY = Math.min(minY, Math.min(s, target[c]));
                maxY = Math.max(maxY, Math.max(s, target[c]));
            }
            core[c] = kind[c] == PAD || (kind[c] == FREE && target[c] != s);
        }
        if (minY == Integer.MAX_VALUE) {
            return;
        }

        // 3. Arbres entiers, sur le relief d'origine.
        Set<Long> touched = new HashSet<>();
        clearTrees(x0, z0, w, d, core, protect, surface, minY - ROOT_DEPTH, Math.min(Terrain.TOP, maxY + TREE_HEIGHT), touched);

        // 4. Relief.
        for (int i = 0; i < w; i++) {
            for (int k = 0; k < d; k++) {
                int c = i * d + k;
                int s = surface[c];
                if (s == Terrain.NONE || !core[c]) {
                    continue;
                }
                int x = x0 + i, z = z0 + k, t = target[c];
                clearPlantsAbove(x, s, z);
                for (int y = t + 1; y <= s; y++) {
                    Blocks.set(chunks, x, y, z, null, 0);
                }
                for (int y = s + 1; y < t; y++) {
                    Blocks.set(chunks, x, y, z, Terrain.DIRT, 0);
                }
                Blocks.set(chunks, x, t, z, kind[c] == PAD ? pads.get(padOf[c]).top() : ground, 0);
                touched.add(column(x, z));
            }
        }

        // 5. Plantes laissées sans sol (sur un tronc retiré, au bord d'une colonne rabotée).
        for (long col : touched) {
            int x = (int) (col >> 32), z = (int) col;
            int s = terrain.surface(x, z);
            if (s == Terrain.NONE) {
                continue;
            }
            for (int y = s + 1; y <= s + 6; y++) {
                String name = Blocks.name(chunks, x, y, z);
                if (isSmallPlant(name) && Blocks.isEmpty(chunks, x, y - 1, z)) {
                    Blocks.set(chunks, x, y, z, null, 0);
                }
            }
        }
    }

    /** Une colonne libre n'est retouchée que si son sol est naturel et que rien de construit ne la surmonte. */
    private boolean untouched(int x, int s, int z) {
        String top = Blocks.name(chunks, x, s, z);
        if (top == null || !Chantiers.natural(top)) {
            return false;
        }
        String above = Blocks.name(chunks, x, s + 1, z);
        return above == null || Chantiers.natural(above);
    }

    private static boolean relax(int[] upper, int[] lower, byte[] kind, int w, int d, int i, int k, int ni, int nk) {
        if (ni < 0 || nk < 0 || ni >= w || nk >= d) {
            return false;
        }
        int c = i * d + k, n = ni * d + nk;
        if (kind[c] != FREE) {
            return false;
        }
        boolean changed = false;
        if (upper[n] + 1 < upper[c]) {
            upper[c] = upper[n] + 1;
            changed = true;
        }
        if (lower[n] - 1 > lower[c]) {
            lower[c] = lower[n] - 1;
            changed = true;
        }
        return changed;
    }

    /** Retire les plantes posées sur le sol (herbes, buissons, cactus) avant de raboter ou recouvrir la colonne. */
    private void clearPlantsAbove(int x, int s, int z) {
        for (int y = s + 1; y <= s + 8; y++) {
            String name = Blocks.name(chunks, x, y, z);
            if (!isSmallPlant(name)) {
                return;
            }
            Blocks.set(chunks, x, y, z, null, 0);
        }
    }

    /**
     * Arbres du site. Les blocs de bois naturels forment des arbres (composantes reliées, diagonales comprises) ; chaque
     * feuille appartient au bois le plus proche à travers le feuillage. Un arbre est retiré en entier si un de ses
     * blocs ou une de ses feuilles surplombe une colonne du site. Ensuite, toute grappe de bois et de feuilles qui ne
     * repose plus sur aucun bloc solide est retirée aussi (morceaux d'arbres coupés par une génération précédente).
     */
    private void clearTrees(int rx0, int rz0, int rw, int rd, boolean[] core, boolean[] protect, int[] surface,
                            int yLo, int yHi, Set<Long> touched) {
        int x0 = rx0 - TREE_REACH, z0 = rz0 - TREE_REACH;
        int x1 = rx0 + rw - 1 + TREE_REACH, z1 = rz0 + rd - 1 + TREE_REACH;
        Map<Long, Byte> tree = new HashMap<>();
        for (int x = x0; x <= x1; x++) {
            for (int z = z0; z <= z1; z++) {
                if (inRegion(x, z, rx0, rz0, rw, rd) && protect[(x - rx0) * rd + (z - rz0)]) {
                    continue;
                }
                for (int y = yLo; y <= yHi; y++) {
                    byte t = treeKind(name(x, y, z));
                    if (t != 0) {
                        tree.put(key(x, y, z), t);
                        if (tree.size() > MAX_TREE_BLOCKS) {
                            return;
                        }
                    }
                }
            }
        }
        if (tree.isEmpty()) {
            return;
        }

        // Arbres : composantes de bois.
        Map<Long, Integer> owner = new HashMap<>();
        List<Boolean> doomed = new ArrayList<>();
        for (Map.Entry<Long, Byte> e : tree.entrySet()) {
            if (e.getValue() != WOOD || owner.containsKey(e.getKey())) {
                continue;
            }
            int id = doomed.size();
            doomed.add(false);
            ArrayDeque<Long> queue = new ArrayDeque<>();
            queue.add(e.getKey());
            owner.put(e.getKey(), id);
            while (!queue.isEmpty()) {
                long p = queue.poll();
                forNeighbours26(p, n -> {
                    if (tree.get(n) != null && tree.get(n) == WOOD && !owner.containsKey(n)) {
                        owner.put(n, id);
                        queue.add(n);
                    }
                });
            }
        }
        // Feuilles : au bois le plus proche à travers le feuillage.
        Map<Long, Integer> dist = new HashMap<>();
        ArrayDeque<Long> queue = new ArrayDeque<>();
        for (Map.Entry<Long, Integer> e : owner.entrySet()) {
            dist.put(e.getKey(), 0);
            queue.add(e.getKey());
        }
        while (!queue.isEmpty()) {
            long p = queue.poll();
            int dp = dist.get(p);
            if (dp >= LEAF_REACH) {
                continue;
            }
            int id = owner.get(p);
            forNeighbours26(p, n -> {
                if (tree.get(n) != null && tree.get(n) == LEAF && !owner.containsKey(n)) {
                    owner.put(n, id);
                    dist.put(n, dp + 1);
                    queue.add(n);
                }
            });
        }

        // Arbres qui touchent le site.
        Set<Long> removed = new HashSet<>();
        for (long p : tree.keySet()) {
            int x = kx(p), z = kz(p);
            if (inRegion(x, z, rx0, rz0, rw, rd) && core[(x - rx0) * rd + (z - rz0)]) {
                removed.add(p);
                Integer id = owner.get(p);
                if (id != null) {
                    doomed.set(id, true);
                }
            }
        }
        for (Map.Entry<Long, Integer> e : owner.entrySet()) {
            if (doomed.get(e.getValue())) {
                removed.add(e.getKey());
            }
        }

        // Grappes restantes qui ne reposent sur rien.
        Set<Long> seen = new HashSet<>(removed);
        for (long start : tree.keySet()) {
            if (seen.contains(start)) {
                continue;
            }
            List<Long> cluster = new ArrayList<>();
            boolean[] anchored = {false};
            ArrayDeque<Long> q = new ArrayDeque<>();
            q.add(start);
            seen.add(start);
            while (!q.isEmpty()) {
                long p = q.poll();
                cluster.add(p);
                int x = kx(p), y = ky(p), z = kz(p);
                if (x <= x0 || x >= x1 || z <= z0 || z >= z1 || y <= yLo || y >= yHi) {
                    anchored[0] = true; // déborde de la zone sondée : on ne sait pas, on garde
                }
                if (!anchored[0]) {
                    int[][] faces = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
                    for (int[] f : faces) {
                        long n = key(x + f[0], y + f[1], z + f[2]);
                        int nx = x + f[0], nz = z + f[2];
                        boolean kept = inRegion(nx, nz, rx0, rz0, rw, rd) && protect[(nx - rx0) * rd + (nz - rz0)]
                                && id(nx, y + f[1], nz) != BlockType.EMPTY_ID;
                        if (!tree.containsKey(n) && (kept || supports(nx, y + f[1], nz))) {
                            anchored[0] = true;
                            break;
                        }
                    }
                }
                forNeighbours26(p, n -> {
                    if (tree.containsKey(n) && !seen.contains(n)) {
                        seen.add(n);
                        q.add(n);
                    }
                });
            }
            if (!anchored[0]) {
                removed.addAll(cluster);
            }
        }

        for (long p : removed) {
            int x = kx(p), y = ky(p), z = kz(p);
            int s = inRegion(x, z, rx0, rz0, rw, rd) ? surface[(x - rx0) * rd + (z - rz0)] : terrain.surface(x, z);
            // Une racine sous le sol laisse de la terre, pas un trou.
            Blocks.set(chunks, x, y, z, s != Terrain.NONE && y < s ? Terrain.DIRT : null, 0);
            touched.add(column(x, z));
        }
    }

    /** Bloc qui porte un arbre : sol, pierre, construction (ni air, ni plante, ni fluide). Hors chargement : on suppose que oui. */
    private boolean supports(int x, int y, int z) {
        int id = id(x, y, z);
        if (id == Blocks.UNLOADED) {
            return true;
        }
        if (id == BlockType.EMPTY_ID) {
            return false;
        }
        BlockType type = BlockType.getAssetMap().getAsset(id);
        String name = type == null ? null : type.getId();
        return name != null && !name.startsWith("Plant_") && !name.contains("Fluid_");
    }

    /** {@link #WOOD} pour le bois d'un arbre, {@link #LEAF} pour son feuillage, 0 sinon. */
    static byte treeKind(String name) {
        if (name == null) {
            return 0;
        }
        String base = name.startsWith("*") ? name.substring(1) : name;
        if (base.startsWith("Plant_Leaves_")) {
            return base.endsWith("_Floor") ? 0 : LEAF;
        }
        if (base.startsWith("Wood_")) {
            return (base.endsWith("_Trunk") || base.endsWith("_Trunk_Full") || base.contains("_Branch_") || base.endsWith("_Roots"))
                    ? WOOD : 0;
        }
        if (base.startsWith("Plant_") && (base.contains("_Trunk") || base.contains("_Branch"))) {
            return WOOD;
        }
        return 0;
    }

    /** Herbe, fleur, buisson, cactus... : une plante qui n'est ni du bois ni du feuillage d'arbre. */
    static boolean isSmallPlant(String name) {
        return name != null && (name.startsWith("Plant_") || name.startsWith("*Plant_")) && treeKind(name) == 0;
    }

    private static boolean inRegion(int x, int z, int rx0, int rz0, int rw, int rd) {
        return x >= rx0 && z >= rz0 && x < rx0 + rw && z < rz0 + rd;
    }

    // Lecture rapide : une recherche de section par tranche de 32 blocs plutôt que par bloc.

    private int id(int x, int y, int z) {
        if (y < 0 || y > 319) {
            return Blocks.UNLOADED;
        }
        long sk = key(x >> 5, y >> 5, z >> 5);
        BlockSection section = sections.get(sk);
        if (section == null && !sections.containsKey(sk)) {
            Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
            section = ref == null || !ref.isValid() ? null : chunks.getStore().getComponent(ref, BlockSection.getComponentType());
            sections.put(sk, section);
        }
        return section == null ? Blocks.UNLOADED : section.get(x, y, z);
    }

    private String name(int x, int y, int z) {
        int id = id(x, y, z);
        if (id == Blocks.UNLOADED || id == BlockType.EMPTY_ID) {
            return null;
        }
        BlockType type = BlockType.getAssetMap().getAsset(id);
        return type == null ? null : type.getId();
    }

    // Clés de position : x et z sur 26 bits signés, y sur 12 bits.

    private static long key(int x, int y, int z) {
        return ((long) (x & 0x3FFFFFF) << 38) | ((long) (z & 0x3FFFFFF) << 12) | (y & 0xFFF);
    }

    private static int kx(long k) {
        return (int) (k >> 38) << 6 >> 6;
    }

    private static int kz(long k) {
        return (int) ((k >> 12) & 0x3FFFFFF) << 6 >> 6;
    }

    private static int ky(long k) {
        return (int) (k & 0xFFF);
    }

    private static long column(int x, int z) {
        return ((long) x << 32) | (z & 0xFFFFFFFFL);
    }

    private static void forNeighbours26(long p, java.util.function.LongConsumer action) {
        int x = kx(p), y = ky(p), z = kz(p);
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                for (int dz = -1; dz <= 1; dz++) {
                    if ((dx | dy | dz) != 0) {
                        action.accept(key(x + dx, y + dy, z + dz));
                    }
                }
            }
        }
    }
}
