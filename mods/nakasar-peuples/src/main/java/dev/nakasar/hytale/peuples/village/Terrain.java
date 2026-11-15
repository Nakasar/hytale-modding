package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.FluidSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiPredicate;

/**
 * Lecture et retouche du relief pour poser un village : hauteur du sol naturel d'une colonne, chargement des chunks
 * d'une zone, aplanissement d'une emprise avec un fondu vers le terrain d'origine (GDD, Faisabilité : « emplacements en
 * périphérie, terrain aplani par le Java »). Toutes les écritures se font sur le thread du monde.
 */
public final class Terrain {

    /** Rendu par {@link #surface} quand la colonne n'est pas chargée ou n'a pas de sol. */
    public static final int NONE = Integer.MIN_VALUE;
    /** Plus haut bloc sondé pour trouver le sol. */
    public static final int TOP = 300;
    public static final String GRASS = "Soil_Grass";
    public static final String DIRT = "Soil_Dirt";
    public static final String PATHWAY = "Soil_Pathway";

    private final World world;
    private final ChunkStore chunks;

    public Terrain(World world) {
        this.world = world;
        this.chunks = world.getChunkStore();
    }

    /** Charge (ou génère) les chunks qui couvrent le rectangle de blocs donné. À appeler depuis le thread du monde. */
    public static CompletableFuture<Void> load(World world, int x0, int x1, int z0, int z1) {
        ChunkStore store = world.getChunkStore();
        List<CompletableFuture<?>> futures = new ArrayList<>();
        for (int cx = ChunkUtil.chunkCoordinate(x0); cx <= ChunkUtil.chunkCoordinate(x1); cx++) {
            for (int cz = ChunkUtil.chunkCoordinate(z0); cz <= ChunkUtil.chunkCoordinate(z1); cz++) {
                futures.add(store.getChunkReferenceAsync(ChunkUtil.indexChunk(cx, cz)));
            }
        }
        return CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new));
    }

    /** Vrai pour un bloc de relief naturel (terre, pierre, sable...) : ni plante, ni bois, ni meuble. */
    public static boolean isGround(String name) {
        return name != null && (name.startsWith("Soil_") || name.startsWith("Rock_")) && !name.contains("_Brick");
    }

    /** Vrai pour la végétation qu'on peut abattre en dégageant une emprise (arbres, feuillages, herbes, fleurs). */
    public static boolean isVegetation(String name) {
        return name != null && (name.startsWith("Plant_") || name.startsWith("Wood_"));
    }

    /** Hauteur du bloc de sol le plus haut de la colonne (x, z), ou {@link #NONE}. */
    public int surface(int x, int z) {
        for (int y = TOP; y >= 0; y--) {
            int id = Blocks.id(chunks, x, y, z);
            if (id == Blocks.UNLOADED) {
                continue;
            }
            if (id == BlockType.EMPTY_ID) {
                continue;
            }
            BlockType type = BlockType.getAssetMap().getAsset(id);
            if (type != null && isGround(type.getId())) {
                return y;
            }
        }
        return NONE;
    }

    /** Nom du bloc de sol de la colonne, ou null. */
    public String surfaceBlock(int x, int z) {
        int y = surface(x, z);
        return y == NONE ? null : Blocks.name(chunks, x, y, z);
    }

    /** Vrai si un fluide (eau, lave) couvre le bloc (x, y, z). */
    public boolean hasFluid(int x, int y, int z) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return false;
        }
        FluidSection fluids = chunks.getStore().getComponent(ref, FluidSection.getComponentType());
        return fluids != null && fluids.getFluidId(x, y, z) != 0;
    }

    /**
     * Vrai si un PNJ peut apparaître debout sur la colonne (x, z) : sol naturel trouvé (pas de vide), ni eau ni lave
     * sur le sol ni à hauteur du corps, deux blocs libres au-dessus (pas dans un tronc ou un mur ; herbes et fleurs
     * permises), et au moins trois voisins à un bloc près (pas une pente impraticable ni un pic).
     *
     * @return la hauteur des pieds (sol + 1), ou {@link #NONE}
     */
    public int safeFeet(int x, int z) {
        int y = surface(x, z);
        if (y == NONE || hasFluid(x, y, z)) {
            return NONE;
        }
        for (int dy = 1; dy <= 2; dy++) {
            if (hasFluid(x, y + dy, z) || !passable(x, y + dy, z)) {
                return NONE;
            }
        }
        int level = 0;
        int[][] around = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] d : around) {
            int n = surface(x + d[0], z + d[1]);
            if (n != NONE && Math.abs(n - y) <= 1 && !hasFluid(x + d[0], n + 1, z + d[1])) {
                level++;
            }
        }
        return level >= 3 ? y + 1 : NONE;
    }

    /** Vrai si un corps peut tenir dans le bloc : vide, ou herbe et fleur basses (ni feuillage, ni tronc, ni cactus). */
    private boolean passable(int x, int y, int z) {
        if (Blocks.isEmpty(chunks, x, y, z)) {
            return true;
        }
        String name = Blocks.name(chunks, x, y, z);
        return name != null && name.startsWith("Plant_") && !name.contains("Leaves") && !name.contains("Cactus")
                && !name.contains("Trunk") && !name.contains("Sapling");
    }

    /**
     * Le point sûr ({@link #safeFeet}) le plus proche de (x, z), cherché par anneaux jusqu'à `radius` blocs : un bloc
     * sur deux au-delà de 4 blocs, pour rester léger. Recherche commune de toutes les apparitions de PNJ du mod
     * (demandes, chaîne, raids, Klops, villageois).
     *
     * @return {x, pieds, z}, ou null si rien de sûr (ou rien de chargé) dans le rayon
     */
    public int[] safeSpot(int x, int z, int radius) {
        for (int r = 0; r <= radius; r++) {
            int step = r > 4 ? 2 : 1;
            if (r > 4 && r % 2 == 1 && r != radius) {
                continue;
            }
            for (int dx = -r; dx <= r; dx += step) {
                for (int dz = -r; dz <= r; dz += step) {
                    if (Math.max(Math.abs(dx), Math.abs(dz)) != r) {
                        continue;
                    }
                    int feet = safeFeet(x + dx, z + dz);
                    if (feet != NONE) {
                        return new int[] {x + dx, feet, z + dz};
                    }
                }
            }
        }
        return null;
    }

    /** Hauteur médiane du sol sur le rectangle (pas de `step` blocs), ou {@link #NONE} si rien n'est chargé. */
    public int medianSurface(int x0, int x1, int z0, int z1, int step) {
        List<Integer> heights = new ArrayList<>();
        for (int x = x0; x <= x1; x += step) {
            for (int z = z0; z <= z1; z += step) {
                int h = surface(x, z);
                if (h != NONE) {
                    heights.add(h);
                }
            }
        }
        if (heights.isEmpty()) {
            return NONE;
        }
        int[] sorted = heights.stream().mapToInt(Integer::intValue).toArray();
        Arrays.sort(sorted);
        return sorted[sorted.length / 2];
    }

    /**
     * Aplanit le rectangle [x0, x1] x [z0, z1] à la hauteur `h` avec une marge plate de `margin` blocs, des talus doux
     * vers le relief d'origine et le retrait des arbres entiers qui touchent l'emprise ({@link Grading}). Hors de
     * l'emprise, les colonnes que `keep` réserve (emprise d'un autre bâtiment) ne sont pas touchées.
     */
    public void flatten(int x0, int x1, int z0, int z1, int h, int margin, int blend, String top, BiPredicate<Integer, Integer> keep) {
        flatten(x0, x1, z0, z1, h, margin, blend, top, GRASS, keep);
    }

    /** Comme {@link #flatten(int, int, int, int, int, int, int, String, BiPredicate)}, avec `ground` aux talus (étape 8 : sable, neige). */
    public void flatten(int x0, int x1, int z0, int z1, int h, int margin, int blend, String top, String ground,
                        BiPredicate<Integer, Integer> keep) {
        new Grading(world).pad(x0, x1, z0, z1, h, margin, top).apply(blend, ground, keep);
    }
}
