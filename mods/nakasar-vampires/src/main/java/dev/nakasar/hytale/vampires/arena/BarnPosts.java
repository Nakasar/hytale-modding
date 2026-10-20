package dev.nakasar.hytale.vampires.arena;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.telegraph.Telegraphs;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Poteaux de bois que l'Abomination percute en chargeant (Kevin, 20 octobre 2026) : au premier choc le poteau se
 * fend (éclats, craquement), au second il cède et toute la colonne de bois disparaît. Un poteau est une colonne
 * verticale de poutres ou de troncs ({@code *_Beam}, {@code *_Trunk}) ; les murs arrêtent la charge sans céder.
 */
public final class BarnPosts {

    /** Hauteur maximale d'un poteau qu'on fait tomber (au-delà, c'est une charpente : on ne la retire pas). */
    private static final int MAX_HEIGHT = 8;
    private static final String CRACK_PARTICLE = "Impact_Sword_Basic_Stronk";
    private static final String CRACK_SOUND = "SFX_Goblin_Mace_Club_Slam_Impact";
    private static final String BREAK_PARTICLE = "Stick_Slam_Ground_Large";
    private static final String BREAK_SOUND = "SFX_Mace_T2_Signature_Impact";

    /** Poteaux déjà fendus par monde (clé du bloc le plus bas de la colonne). */
    private static final Map<World, Map<Long, Boolean>> CRACKED = Collections.synchronizedMap(new WeakHashMap<>());

    private BarnPosts() {
    }

    public static boolean isPost(String name) {
        return name != null && (name.endsWith("_Beam") || name.endsWith("_Trunk"));
    }

    /** Choc de charge sur le bloc (x, y, z) : fend le poteau, ou le fait céder s'il était déjà fendu. Faux si ce n'est pas un poteau. */
    public static boolean hit(World world, Store<EntityStore> store, int x, int y, int z) {
        ChunkStore chunks = world.getChunkStore();
        String name = WorldBlocks.name(chunks, x, y, z);
        if (!isPost(name)) {
            return false;
        }
        int bottom = y;
        while (bottom > y - MAX_HEIGHT && name.equals(WorldBlocks.name(chunks, x, bottom - 1, z))) {
            bottom--;
        }
        int top = y;
        while (top < bottom + MAX_HEIGHT && name.equals(WorldBlocks.name(chunks, x, top + 1, z))) {
            top++;
        }
        long key = WorldBlocks.key(x, bottom, z);
        Map<Long, Boolean> cracked = CRACKED.computeIfAbsent(world, w -> new HashMap<>());
        Vector3d at = new Vector3d(x + 0.5, y + 0.5, z + 0.5);
        if (cracked.remove(key) == null) {
            cracked.put(key, Boolean.TRUE);
            Telegraphs.particle(store, CRACK_PARTICLE, at, 1.5f);
            Telegraphs.sound(store, CRACK_SOUND, at);
            return true;
        }
        if (top - bottom + 1 > MAX_HEIGHT) {
            return true;
        }
        for (int yy = bottom; yy <= top; yy++) {
            WorldBlocks.clear(chunks, x, yy, z);
        }
        Telegraphs.particle(store, BREAK_PARTICLE, new Vector3d(x + 0.5, bottom + 0.1, z + 0.5), 1.2f);
        Telegraphs.sound(store, BREAK_SOUND, at);
        return true;
    }

    public static void clearAll() {
        CRACKED.clear();
    }
}
