package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.VillageBuilder;

import java.util.HashMap;
import java.util.Map;

/**
 * Pose des prefabs vanilla du monde vivant : à demeure (traces, auberges, arbres brûlés) ou pour un temps (campements,
 * étals de foire), auquel cas les blocs changés sont notés ({@link WorldLifeRegistry.Part#STRUCTURES}) et rendus à la
 * fin. On ne rend un bloc que s'il est encore celui du prefab : ce qu'un joueur a construit ou cassé entre-temps reste.
 */
public final class Sites {

    /** Préfixe d'une note dont le propriétaire est parti : {@link #retry} la rendra dès que la zone sera chargée. */
    private static final String RELEASED = "!";

    private Sites() {
    }

    /** Vrai si la colonne (x, z) est chargée (son sol est connu). */
    public static boolean loaded(World world, int x, int z) {
        return new Terrain(world).surface(x, z) != Terrain.NONE;
    }

    /** Hauteur de pose du prefab : la médiane du sol sous son emprise, ou {@link Terrain#NONE}. */
    public static int ground(World world, String prefab, int x, int z, int rotation) {
        int[] b = VillageBuilder.bounds(prefab, x, 0, z, rotation);
        Terrain terrain = new Terrain(world);
        if (b == null) {
            return terrain.surface(x, z);
        }
        return terrain.medianSurface(b[0] + 1, b[1] - 1, b[4] + 1, b[5] - 1, 2);
    }

    /** Pose à demeure ; faux si le prefab manque ou que la zone n'est pas chargée. */
    public static boolean pastePermanent(World world, Store<EntityStore> store, String prefab, int x, int y, int z, int rotation) {
        return VillageBuilder.paste(world, store, prefab, x, y, z, rotation);
    }

    /**
     * Pose pour un temps sous l'id `id` : les blocs changés sont notés pour {@link #restore}. Faux si rien n'a été
     * posé.
     */
    public static boolean pasteTemporary(World world, Store<EntityStore> store, String id, String prefab, int x, int y, int z, int rotation) {
        int[] b = VillageBuilder.bounds(prefab, x, y, z, rotation);
        if (b == null) {
            return false;
        }
        ChunkStore chunks = world.getChunkStore();
        Map<Long, String> before = new HashMap<>();
        for (int bx = b[0]; bx <= b[1]; bx++) {
            for (int by = b[2]; by <= b[3]; by++) {
                for (int bz = b[4]; bz <= b[5]; bz++) {
                    before.put(pack(bx - x, by - y, bz - z), cell(chunks, bx, by, bz));
                }
            }
        }
        if (!VillageBuilder.paste(world, store, prefab, x, y, z, rotation)) {
            return false;
        }
        StringBuilder sb = new StringBuilder();
        sb.append(x).append(',').append(y).append(',').append(z);
        String old = WorldLife.registry(world).get(WorldLifeRegistry.Part.STRUCTURES, id);
        for (Map.Entry<Long, String> e : before.entrySet()) {
            int[] d = unpack(e.getKey());
            String now = cell(chunks, x + d[0], y + d[1], z + d[2]);
            if (!now.equals(e.getValue())) {
                sb.append(';').append(d[0]).append(',').append(d[1]).append(',').append(d[2]).append(',')
                        .append(e.getValue()).append(',').append(now.substring(0, now.indexOf('/')));
            }
        }
        // Plusieurs prefabs sous le même id (campement : tente et feu) : leurs notes s'ajoutent.
        WorldLife.registry(world).put(WorldLifeRegistry.Part.STRUCTURES, id, old == null ? sb.toString() : old + "#" + sb);
        return true;
    }

    /** Pose d'un seul bloc pour un temps (drapeau de course, enseigne) sous l'id `id`. */
    public static boolean setTemporary(World world, String id, int x, int y, int z, String block, int rotation) {
        ChunkStore chunks = world.getChunkStore();
        String was = cell(chunks, x, y, z);
        if (!Blocks.set(chunks, x, y, z, block, rotation)) {
            return false;
        }
        String old = WorldLife.registry(world).get(WorldLifeRegistry.Part.STRUCTURES, id);
        String note = x + "," + y + "," + z + ";0,0,0," + was + "," + block;
        WorldLife.registry(world).put(WorldLifeRegistry.Part.STRUCTURES, id, old == null ? note : old + "#" + note);
        return true;
    }

    /**
     * Rend les blocs notés sous l'id `id` (là où le prefab est encore là) ; faux si la zone n'est pas chargée (la note
     * reste, on réessaiera).
     */
    public static boolean restore(World world, String id) {
        String note = WorldLife.registry(world).get(WorldLifeRegistry.Part.STRUCTURES, id);
        if (note == null) {
            return true;
        }
        if (note.startsWith(RELEASED)) {
            note = note.substring(RELEASED.length());
        }
        ChunkStore chunks = world.getChunkStore();
        // Tous les blocs notés doivent être chargés (une emprise peut toucher plusieurs chunks) : sinon on ne touche à
        // rien et la note reste.
        for (String group : note.split("#")) {
            String[] parts = group.split(";");
            String[] o = parts[0].split(",");
            if (o.length < 3) {
                continue;
            }
            int x = Integer.parseInt(o[0]);
            int y = Integer.parseInt(o[1]);
            int z = Integer.parseInt(o[2]);
            if (Blocks.id(chunks, x, y, z) == Blocks.UNLOADED) {
                return false;
            }
            for (int i = 1; i < parts.length; i++) {
                String[] c = parts[i].split(",");
                if (c.length >= 3 && Blocks.id(chunks, x + Integer.parseInt(c[0]), y + Integer.parseInt(c[1]),
                        z + Integer.parseInt(c[2])) == Blocks.UNLOADED) {
                    return false;
                }
            }
        }
        for (String group : note.split("#")) {
            String[] parts = group.split(";");
            String[] o = parts[0].split(",");
            if (o.length < 3) {
                continue;
            }
            int x = Integer.parseInt(o[0]);
            int y = Integer.parseInt(o[1]);
            int z = Integer.parseInt(o[2]);
            for (int i = 1; i < parts.length; i++) {
                String[] c = parts[i].split(",");
                if (c.length < 5) {
                    continue;
                }
                int bx = x + Integer.parseInt(c[0]);
                int by = y + Integer.parseInt(c[1]);
                int bz = z + Integer.parseInt(c[2]);
                String placed = c[4];
                String now = Blocks.name(chunks, bx, by, bz);
                if (!placed.equals(now == null ? "-" : now)) {
                    continue; // changé depuis par un joueur : on n'y touche pas
                }
                String[] was = c[3].split("/");
                String block = "-".equals(was[0]) ? null : was[0];
                int rot = was.length > 1 ? Integer.parseInt(was[1]) : 0;
                Blocks.set(chunks, bx, by, bz, block, rot);
            }
        }
        WorldLife.registry(world).put(WorldLifeRegistry.Part.STRUCTURES, id, null);
        return true;
    }

    /**
     * Le propriétaire de la structure `id` n'en a plus besoin (foire finie, course finie) : elle est rendue tout de
     * suite si sa zone est chargée, sinon marquée pour {@link #retry}.
     */
    public static void release(World world, String id) {
        if (restore(world, id)) {
            return;
        }
        WorldLifeRegistry r = WorldLife.registry(world);
        String note = r.get(WorldLifeRegistry.Part.STRUCTURES, id);
        if (note != null && !note.startsWith(RELEASED)) {
            r.put(WorldLifeRegistry.Part.STRUCTURES, id, RELEASED + note);
        }
    }

    /** Réessaie de rendre les structures abandonnées (pas toutes les 2 s du monde vivant). */
    public static void retry(World world) {
        Map<String, String> part = WorldLife.registry(world).part(WorldLifeRegistry.Part.STRUCTURES);
        for (Map.Entry<String, String> e : new HashMap<>(part).entrySet()) {
            if (e.getValue().startsWith(RELEASED)) {
                restore(world, e.getKey());
            }
        }
    }

    /** Ids des structures encore posées (commande). */
    public static int count(World world) {
        return WorldLife.registry(world).part(WorldLifeRegistry.Part.STRUCTURES).size();
    }

    private static String cell(ChunkStore chunks, int x, int y, int z) {
        String name = Blocks.name(chunks, x, y, z);
        return (name == null ? "-" : name) + "/" + (name == null ? 0 : Blocks.rotation(chunks, x, y, z));
    }

    private static long pack(int dx, int dy, int dz) {
        return ((long) (dx + 1024) << 32) | ((long) (dy + 1024) << 16) | (dz + 1024);
    }

    private static int[] unpack(long k) {
        return new int[] {(int) (k >>> 32) - 1024, (int) ((k >>> 16) & 0xffff) - 1024, (int) (k & 0xffff) - 1024};
    }
}
