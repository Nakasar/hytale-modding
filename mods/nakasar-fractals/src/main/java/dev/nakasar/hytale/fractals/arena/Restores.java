package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import org.joml.Vector3i;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Blocs du décor à remettre en place (porte de cellule ouverte ou abattue, cloche abattue, lanterne renversée, poteau
 * de grange cassé), gardés sur disque ({@code restores.tsv} du dossier du plugin) : un redémarrage du serveur ou un
 * chunk déchargé ne fait jamais perdre un bloc du décor pour de bon. Chaque monde reprend ses blocs dès que leur heure
 * est passée et que leur section est chargée ({@link #tick}, appelé par {@code TelegraphSystem}).
 */
public final class Restores {

    private record Entry(String world, int x, int y, int z, String block, int rotation, long due) {
    }

    private static final String FILE = "restores.tsv";
    private static final long CHECK_MS = 1000;

    private static final List<Entry> PENDING = new ArrayList<>();
    private static final Map<World, Long> LAST_CHECK = Collections.synchronizedMap(new WeakHashMap<>());
    private static Path file;

    private Restores() {
    }

    /** Relit les remises en place en attente (démarrage du plugin). */
    public static synchronized void load(Path dataDirectory) {
        file = dataDirectory.resolve(FILE);
        PENDING.clear();
        if (!Files.isRegularFile(file)) {
            return;
        }
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                String[] f = line.split("\t");
                if (f.length == 7) {
                    PENDING.add(new Entry(f[0], Integer.parseInt(f[1]), Integer.parseInt(f[2]), Integer.parseInt(f[3]),
                            f[4], Integer.parseInt(f[5]), Long.parseLong(f[6])));
                }
            }
        } catch (IOException | RuntimeException e) {
            FractalsPlugin.get().getLogger().atWarning().withCause(e).log("Décor : %s illisible", file);
        }
    }

    /** Remet `block` (rotation `rotation`) aux cases `blocks` dans `seconds` secondes, si elles sont restées vides. */
    public static synchronized void add(World world, List<Vector3i> blocks, String block, int rotation, float seconds) {
        long due = System.currentTimeMillis() + (long) (seconds * 1000);
        for (Vector3i at : blocks) {
            PENDING.add(new Entry(world.getName(), at.x, at.y, at.z, block, rotation, due));
        }
        save();
    }

    /** Vrai si la case attend déjà son bloc (porte ouverte : un second coup de levier ne la rouvre pas). */
    public static synchronized boolean pending(World world, Vector3i at) {
        for (Entry e : PENDING) {
            if (e.x == at.x && e.y == at.y && e.z == at.z && e.world.equals(world.getName())) {
                return true;
            }
        }
        return false;
    }

    /** Une fois par seconde par monde, sur le thread du monde : remet les blocs dont l'heure est passée. */
    public static void tick(World world) {
        long now = System.currentTimeMillis();
        Long last = LAST_CHECK.get(world);
        if (last != null && now - last < CHECK_MS) {
            return;
        }
        LAST_CHECK.put(world, now);
        synchronized (Restores.class) {
            if (PENDING.isEmpty()) {
                return;
            }
        }
        world.execute(() -> restoreDue(world, System.currentTimeMillis()));
    }

    private static synchronized void restoreDue(World world, long now) {
        ChunkStore chunks = world.getChunkStore();
        boolean changed = false;
        for (Entry e : List.copyOf(PENDING)) {
            if (e.due > now || !e.world.equals(world.getName())) {
                continue;
            }
            int id = WorldBlocks.id(chunks, e.x, e.y, e.z);
            if (id < 0) {
                continue;   // section pas chargée : on réessaiera
            }
            if (id == BlockType.EMPTY_ID && !WorldBlocks.set(chunks, e.x, e.y, e.z, e.block, e.rotation)) {
                continue;
            }
            PENDING.remove(e);
            changed = true;
        }
        if (changed) {
            save();
        }
    }

    private static void save() {
        if (file == null) {
            return;
        }
        StringBuilder out = new StringBuilder();
        for (Entry e : PENDING) {
            out.append(e.world).append('\t').append(e.x).append('\t').append(e.y).append('\t').append(e.z).append('\t')
                    .append(e.block).append('\t').append(e.rotation).append('\t').append(e.due).append('\n');
        }
        try {
            Files.createDirectories(file.getParent());
            Files.writeString(file, out, StandardCharsets.UTF_8);
        } catch (IOException e) {
            FractalsPlugin.get().getLogger().atWarning().withCause(e).log("Décor : impossible d'écrire %s", file);
        }
    }
}
