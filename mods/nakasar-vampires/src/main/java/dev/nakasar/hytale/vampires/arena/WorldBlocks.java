package dev.nakasar.hytale.vampires.arena;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.protocol.BlockMaterial;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.universe.world.chunk.BlockOperations;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import it.unimi.dsi.fastutil.ints.IntArrayList;
import it.unimi.dsi.fastutil.ints.IntList;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Lecture et écriture des blocs du décor des combats d'élites (poteaux de grange, porte de cellule, cloche d'alarme,
 * lanternes-citrouilles, braseros). Tout se fait sur le thread du monde, dans les sections chargées : une section non
 * chargée compte comme vide.
 */
public final class WorldBlocks {

    private WorldBlocks() {
    }

    /** Id du bloc en (x, y, z), {@link BlockType#EMPTY_ID} hors des sections chargées. */
    public static int id(ChunkStore chunks, int x, int y, int z) {
        BlockSection section = section(chunks, x, y, z);
        return section == null ? BlockType.EMPTY_ID : section.get(x, y, z);
    }

    public static BlockType type(ChunkStore chunks, int x, int y, int z) {
        int id = id(chunks, x, y, z);
        return id == BlockType.EMPTY_ID ? null : BlockType.getAssetMap().getAsset(id);
    }

    /** Nom du bloc en (x, y, z), null si vide. */
    public static String name(ChunkStore chunks, int x, int y, int z) {
        BlockType type = type(chunks, x, y, z);
        return type == null ? null : type.getId();
    }

    public static boolean solid(ChunkStore chunks, int x, int y, int z) {
        BlockType type = type(chunks, x, y, z);
        return type != null && type.getMaterial() == BlockMaterial.Solid;
    }

    public static int rotation(ChunkStore chunks, int x, int y, int z) {
        BlockSection section = section(chunks, x, y, z);
        return section == null ? 0 : section.getRotationIndex(x, y, z);
    }

    /** Pose le bloc `blockId` (null ou vide : air) en gardant la rotation donnée. Faux si la section n'est pas chargée. */
    public static boolean set(ChunkStore chunks, int x, int y, int z, String blockId, int rotation) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return false;
        }
        BlockType type = blockId == null || blockId.isBlank() ? BlockType.EMPTY : BlockType.getAssetMap().getAsset(blockId);
        if (type == null) {
            return false;
        }
        int id = type == BlockType.EMPTY ? BlockType.EMPTY_ID : BlockType.getAssetMap().getIndex(blockId);
        return BlockOperations.setBlock(chunks, ref, x, y, z, id, type, rotation, 0, 0);
    }

    public static boolean clear(ChunkStore chunks, int x, int y, int z) {
        return set(chunks, x, y, z, null, 0);
    }

    /** Ligne de vue entre deux points : faux si un bloc plein se trouve sur le segment (pas d'un tiers de bloc). */
    public static boolean clearLine(ChunkStore chunks, Vector3d a, Vector3d b) {
        double length = a.distance(b);
        int steps = Math.max(1, (int) Math.ceil(length * 3));
        int lastX = Integer.MIN_VALUE;
        int lastY = Integer.MIN_VALUE;
        int lastZ = Integer.MIN_VALUE;
        for (int i = 1; i < steps; i++) {
            double t = (double) i / steps;
            int x = (int) Math.floor(a.x() + (b.x() - a.x()) * t);
            int y = (int) Math.floor(a.y() + (b.y() - a.y()) * t);
            int z = (int) Math.floor(a.z() + (b.z() - a.z()) * t);
            if (x == lastX && y == lastY && z == lastZ) {
                continue;
            }
            lastX = x;
            lastY = y;
            lastZ = z;
            if (solid(chunks, x, y, z)) {
                return false;
            }
        }
        return true;
    }

    /** Blocs dont l'id est dans `names`, dans le cube de rayon `radius` autour de `from` (sections chargées). */
    public static List<Vector3i> find(ChunkStore chunks, Vector3d from, int radius, Collection<String> names) {
        IntList ids = new IntArrayList();
        for (String name : names) {
            int id = BlockType.getAssetMap().getIndexOrDefault(name, -1);
            if (id >= 0) {
                ids.add(id);
            }
        }
        List<Vector3i> out = new ArrayList<>();
        if (ids.isEmpty()) {
            return out;
        }
        Store<ChunkStore> store = chunks.getStore();
        int cx = (int) Math.floor(from.x());
        int cy = (int) Math.floor(from.y());
        int cz = (int) Math.floor(from.z());
        int minY = Math.max(0, cy - radius);
        int maxY = cy + radius;
        for (int sx = (cx - radius) >> ChunkUtil.BITS; sx <= (cx + radius) >> ChunkUtil.BITS; sx++) {
            for (int sy = minY >> ChunkUtil.BITS; sy <= maxY >> ChunkUtil.BITS; sy++) {
                for (int sz = (cz - radius) >> ChunkUtil.BITS; sz <= (cz + radius) >> ChunkUtil.BITS; sz++) {
                    int baseX = sx << ChunkUtil.BITS;
                    int baseY = sy << ChunkUtil.BITS;
                    int baseZ = sz << ChunkUtil.BITS;
                    Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(baseX, baseY, baseZ);
                    if (ref == null || !ref.isValid()) {
                        continue;
                    }
                    BlockSection section = store.getComponent(ref, BlockSection.getComponentType());
                    if (section == null || !section.containsAny(ids)) {
                        continue;
                    }
                    section.find(ids, index -> {
                        int x = baseX + ChunkUtil.xFromIndex(index);
                        int y = baseY + ChunkUtil.yFromIndex(index);
                        int z = baseZ + ChunkUtil.zFromIndex(index);
                        if (Math.abs(x - cx) <= radius && Math.abs(y - cy) <= radius && Math.abs(z - cz) <= radius) {
                            out.add(new Vector3i(x, y, z));
                        }
                    });
                }
            }
        }
        return out;
    }

    /** Le plus proche de `from` parmi `blocks` (distance au centre du bloc), ou null. */
    public static Vector3i nearest(List<Vector3i> blocks, Vector3d from) {
        Vector3i best = null;
        double bestDistance = Double.MAX_VALUE;
        for (Vector3i block : blocks) {
            double distance = from.distanceSquared(block.x + 0.5, block.y + 0.5, block.z + 0.5);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = block;
            }
        }
        return best;
    }

    public static Vector3d center(Vector3i block) {
        return new Vector3d(block.x + 0.5, block.y + 0.5, block.z + 0.5);
    }

    public static long key(int x, int y, int z) {
        return ((long) (x & 0x3FFFFFF) << 38) | ((long) (z & 0x3FFFFFF) << 12) | (y & 0xFFF);
    }

    private static BlockSection section(ChunkStore chunks, int x, int y, int z) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return null;
        }
        return chunks.getStore().getComponent(ref, BlockSection.getComponentType());
    }
}
