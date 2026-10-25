package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

/**
 * Une grille de dalles carrées posées au-dessus du vide (gouffre, arène de la Voix) : colonne 0 à l'ouest, rangée 0 au
 * nord. Une dalle est là (dalles de basalte, cœur runique), rouge (elle va tomber : la zone rouge est la dalle même) ou
 * absente.
 */
final class Tiles {

    static final String EDGE = "Rock_Basalt_Brick_Smooth";
    static final String CORE = "Rock_Runic_Teal_Brick";
    static final String RED = "Rock_Crystal_Red_Block";

    final int x0;
    final int z0;
    final int cols;
    final int rows;
    final int size;
    /** Y monde des blocs des dalles (on est debout un bloc au-dessus). */
    final int floorY;
    private final boolean[] present;
    private final boolean[] red;

    Tiles(int x0, int z0, int cols, int rows, int size, int floorY) {
        this.x0 = x0;
        this.z0 = z0;
        this.cols = cols;
        this.rows = rows;
        this.size = size;
        this.floorY = floorY;
        this.present = new boolean[cols * rows];
        this.red = new boolean[cols * rows];
    }

    boolean inside(int c, int r) {
        return c >= 0 && r >= 0 && c < cols && r < rows;
    }

    int index(int c, int r) {
        return r * cols + c;
    }

    boolean present(int c, int r) {
        return inside(c, r) && present[index(c, r)];
    }

    boolean red(int c, int r) {
        return inside(c, r) && red[index(c, r)];
    }

    /** Dalle sous le point `p` ({c, r}), null hors de la grille. */
    int[] cellOf(Vector3d p) {
        int c = (int) Math.floor((p.x() - x0) / size);
        int r = (int) Math.floor((p.z() - z0) / size);
        return inside(c, r) ? new int[]{c, r} : null;
    }

    /** Centre de la dalle, à hauteur des pieds. */
    Vector3d center(int c, int r) {
        return new Vector3d(x0 + c * size + size / 2.0, floorY + 1, z0 + r * size + size / 2.0);
    }

    /** Vrai si le corps en `p` mord sur la dalle (même marge que les zones rouges). */
    boolean touches(Vector3d p, int c, int r) {
        double b = Telegraphs.BODY;
        double ax = x0 + c * size;
        double az = z0 + r * size;
        double dy = p.y() - (floorY + 1);
        return p.x() >= ax - b && p.x() <= ax + size + b && p.z() >= az - b && p.z() <= az + size + b
                && dy >= -1.5 && dy <= 3.5;
    }

    void place(World world, int c, int r) {
        ChunkStore chunks = world.getChunkStore();
        for (int dx = 0; dx < size; dx++) {
            for (int dz = 0; dz < size; dz++) {
                boolean core = dx == size / 2 && dz == size / 2;
                WorldBlocks.set(chunks, x0 + c * size + dx, floorY, z0 + r * size + dz, core ? CORE : EDGE, 0);
            }
        }
        present[index(c, r)] = true;
        red[index(c, r)] = false;
    }

    /** La dalle rougit : elle tombera (la zone rouge est la dalle elle-même). */
    void redden(World world, int c, int r) {
        if (!present(c, r)) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        for (int dx = 0; dx < size; dx++) {
            for (int dz = 0; dz < size; dz++) {
                WorldBlocks.set(chunks, x0 + c * size + dx, floorY, z0 + r * size + dz, RED, 0);
            }
        }
        red[index(c, r)] = true;
    }

    void drop(World world, Store<EntityStore> store, int c, int r) {
        if (!inside(c, r)) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        for (int dx = 0; dx < size; dx++) {
            for (int dz = 0; dz < size; dz++) {
                WorldBlocks.clear(chunks, x0 + c * size + dx, floorY, z0 + r * size + dz);
            }
        }
        if (present[index(c, r)]) {
            Telegraphs.particle(store, "Nakasar_Fractal_Tile_Crumble", center(c, r), size / 3f);
        }
        present[index(c, r)] = false;
        red[index(c, r)] = false;
    }

    /** Note une dalle posée par le prefab (sans toucher aux blocs). */
    void mark(int c, int r) {
        present[index(c, r)] = true;
    }
}
