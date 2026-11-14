package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.universe.world.chunk.BlockOperations;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;

/**
 * Lecture et écriture de blocs sur le thread du monde, dans les sections chargées (mêmes appels que
 * {@code arena.WorldBlocks} des mods Vampires et Fractales, copiés sans bibliothèque commune).
 */
public final class Blocks {

    /** Rendu par {@link #id} hors des sections chargées. */
    public static final int UNLOADED = -1;

    private Blocks() {
    }

    /** Index du bloc en (x, y, z), {@link #UNLOADED} si la section n'est pas chargée. */
    public static int id(ChunkStore chunks, int x, int y, int z) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return UNLOADED;
        }
        BlockSection section = chunks.getStore().getComponent(ref, BlockSection.getComponentType());
        return section == null ? UNLOADED : section.get(x, y, z);
    }

    /** Nom du bloc en (x, y, z), null si vide ou pas chargé. */
    public static String name(ChunkStore chunks, int x, int y, int z) {
        int id = id(chunks, x, y, z);
        if (id == UNLOADED || id == BlockType.EMPTY_ID) {
            return null;
        }
        BlockType type = BlockType.getAssetMap().getAsset(id);
        return type == null ? null : type.getId();
    }

    /** Rotation du bloc en (x, y, z) (index de RotationTuple), 0 si la section n'est pas chargée. */
    public static int rotation(ChunkStore chunks, int x, int y, int z) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return 0;
        }
        BlockSection section = chunks.getStore().getComponent(ref, BlockSection.getComponentType());
        return section == null ? 0 : section.getRotationIndex(x, y, z);
    }

    /**
     * Vrai si le bloc nommé `name` est `baseId` ou l'un de ses états : un coffre vanilla ouvert puis refermé devient
     * {@code *<baseId>_State_Definitions_CloseWindow} (ou {@code _OpenWindow} tant qu'il est ouvert).
     */
    public static boolean is(String name, String baseId) {
        return name != null && baseId != null
                && (name.equals(baseId) || name.startsWith("*" + baseId + "_State_Definitions_"));
    }

    public static boolean isEmpty(ChunkStore chunks, int x, int y, int z) {
        return id(chunks, x, y, z) == BlockType.EMPTY_ID;
    }

    /** Pose `blockId` (null : air) avec la rotation donnée. Faux si la section n'est pas chargée ou l'id inconnu. */
    public static boolean set(ChunkStore chunks, int x, int y, int z, String blockId, int rotation) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return false;
        }
        BlockType type = blockId == null ? BlockType.EMPTY : BlockType.getAssetMap().getAsset(blockId);
        if (type == null) {
            return false;
        }
        int id = blockId == null ? BlockType.EMPTY_ID : BlockType.getAssetMap().getIndex(blockId);
        return BlockOperations.setBlock(chunks, ref, x, y, z, id, type, rotation, 0, 0);
    }

    /** Retire le bloc en (x, y, z) s'il s'agit bien de `blockId` (on ne casse jamais un bloc posé par un joueur). */
    public static boolean clearIf(ChunkStore chunks, int x, int y, int z, String blockId) {
        return blockId.equals(name(chunks, x, y, z)) && set(chunks, x, y, z, null, 0);
    }
}
