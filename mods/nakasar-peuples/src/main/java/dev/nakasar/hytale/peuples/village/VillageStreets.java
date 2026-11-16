package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/**
 * Sentiers et décor entre les bâtiments (Kevin, 2026-11-16 : « un village qui s'organise de manière plus agréable et
 * vivante, avec des décorations, des petits sentiers »). Le plan ({@link VillageLayout#streets()}, calculé par
 * tools/village_streets.py) donne par palier les cases de sentier et le décor : petits prefabs vanilla (lampadaires,
 * bancs, jardinets des villages Kweebec Oak) ou blocs vanilla du peuple posés sur le sol.
 *
 * <p>Posé par {@link VillageLifeSystem} quand un joueur est près du village et que le palier dépasse le dernier posé
 * ({@link Village#streetsTier()}) : à la génération, après chaque chantier, et une fois sur les villages bâtis avant ce
 * changement. Les sentiers de tous les paliers atteints sont reposés à chaque fois (le terrassement d'un nouveau
 * bâtiment a pu en raboter), le décor seulement pour les nouveaux paliers (un joueur peut l'avoir ramassé).
 *
 * <p>On ne touche qu'au sol NATUREL (terre, herbe, sable, neige, gravier) : jamais un bâtiment, un champ labouré, un
 * arbre ni un bloc de joueur. Une case dont le sol est trop loin de la hauteur de la place est laissée telle quelle.
 */
public final class VillageStreets {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    /** Écart de hauteur maximal entre le sol d'une case et la place (falaises, ravins : on n'y pose rien). */
    private static final int MAX_DROP = 10;

    private static final Set<String> BUSY = Collections.synchronizedSet(new HashSet<>());

    private VillageStreets() {
    }

    /** Vrai si le village a des sentiers ou du décor à poser pour son palier. */
    public static boolean due(Village village) {
        VillageLayout layout = Chantiers.layout(village);
        return layout != null && layout.streets().length > 0 && village.streetsTier() < village.tier()
                && !BUSY.contains(village.id()) && !Chantiers.busy(village);
    }

    /** Charge les chunks du village puis pose les sentiers et le décor jusqu'à son palier. */
    public static void lay(World world, Village village) {
        if (!BUSY.add(village.id())) {
            return;
        }
        try {
            Chantiers.loadThen(world, village, () -> {
                try {
                    layNow(world, village);
                } finally {
                    BUSY.remove(village.id());
                }
            });
        } catch (RuntimeException e) {
            BUSY.remove(village.id());
            throw e;
        }
    }

    /** Pose sur-le-champ (chunks chargés) les sentiers des paliers 0..palier et le décor des paliers pas encore posés. */
    public static void layNow(World world, Village village) {
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return;
        }
        int tier = village.tier();
        int from = village.streetsTier();
        if (from >= tier) {
            return;
        }
        Terrain terrain = new Terrain(world);
        ChunkStore chunks = world.getChunkStore();
        Store<EntityStore> store = world.getEntityStore().getStore();
        int plaza = village.y() - 1;
        int paths = 0;
        int decor = 0;
        for (VillageLayout.StreetStep step : layout.streets()) {
            if (step.tier() > tier) {
                continue;
            }
            for (String cell : step.paths()) {
                String[] p = cell.split(" ");
                if (p.length >= 3 && path(terrain, chunks, village, layout, plaza, village.x() + Integer.parseInt(p[0]),
                        village.z() + Integer.parseInt(p[1]), p[2])) {
                    paths++;
                }
            }
            if (step.tier() <= from) {
                continue;
            }
            for (String entry : step.decor()) {
                String[] p = entry.split(" ", 5);
                if (p.length == 5 && decor(world, store, terrain, chunks, village, layout, plaza, village.x() + Integer.parseInt(p[0]),
                        village.z() + Integer.parseInt(p[1]), Integer.parseInt(p[2]), p[3].equals("P"), p[4])) {
                    decor++;
                }
            }
        }
        village.setStreetsTier(tier);
        LOGGER.atInfo().log("Nakasar Peuples : sentiers de %s posés jusqu'au palier %d (%d cases, %d décors)", village.name(), tier, paths, decor);
    }

    /** Pose une case de sentier si son sol est naturel. Vrai si le bloc a changé. */
    private static boolean path(Terrain terrain, ChunkStore chunks, Village village, VillageLayout layout, int plaza,
                                int x, int z, String block) {
        if (insideBuilding(village, layout, x, z)) {
            return false;
        }
        int y = surface(chunks, plaza, x, z);
        if (y == Terrain.NONE || Math.abs(y - plaza) > MAX_DROP) {
            return false;
        }
        String top = Blocks.name(chunks, x, y, z);
        if (top == null || top.equals(block)) {
            return false;
        }
        // Mince couche de neige sur le sol : on la retire et on pave dessous.
        if (top.startsWith("Soil_Snow_Half")) {
            String below = Blocks.name(chunks, x, y - 1, z);
            if (below == null || !soil(below)) {
                return false;
            }
            Blocks.set(chunks, x, y, z, null, 0);
            y--;
            top = below;
        }
        if (!soil(top) || !clearAbove(chunks, x, y, z)) {
            return false;
        }
        return Blocks.set(chunks, x, y, z, block, 0);
    }

    /** Pose un élément de décor (prefab vanilla ou bloc) sur le sol naturel libre. Vrai s'il est posé. */
    private static boolean decor(World world, Store<EntityStore> store, Terrain terrain, ChunkStore chunks, Village village,
                                 VillageLayout layout, int plaza, int x, int z, int rotation, boolean prefab, String id) {
        if (insideBuilding(village, layout, x, z)) {
            return false;
        }
        int y = surface(chunks, plaza, x, z);
        if (y == Terrain.NONE || Math.abs(y - plaza) > MAX_DROP || terrain.hasFluid(x, y + 1, z)) {
            return false;
        }
        String top = Blocks.name(chunks, x, y, z);
        if (top == null || !(soil(top) || top.startsWith("Soil_Pathway") || top.startsWith("Soil_Gravel"))) {
            return false;
        }
        if (!prefab) {
            if (!clearAbove(chunks, x, y, z)) {
                return false;
            }
            return Blocks.set(chunks, x, y + 1, z, id, Math.floorMod(rotation, 4));
        }
        int[] box = VillageBuilder.bounds(id, x, y, z, rotation);
        if (box == null) {
            return false;
        }
        // Le prefab ne doit rien écraser : au-dessus du sol de son emprise, seulement de l'air ou de l'herbe basse, et un
        // sol à un bloc près (pas de prefab à cheval sur une marche).
        for (int bx = box[0] + 1; bx <= box[1] - 1; bx++) {
            for (int bz = box[4] + 1; bz <= box[5] - 1; bz++) {
                int s = surface(chunks, plaza, bx, bz);
                if (s == Terrain.NONE || Math.abs(s - y) > 1 || insideBuilding(village, layout, bx, bz)) {
                    return false;
                }
                for (int by = s + 1; by <= s + 3; by++) {
                    String name = Blocks.name(chunks, bx, by, bz);
                    if (name != null && !Grading.isSmallPlant(name)) {
                        return false;
                    }
                }
            }
        }
        return VillageBuilder.paste(world, store, id, x, y, z, rotation);
    }

    /**
     * Hauteur du sol de la colonne, cherchée seulement autour de la hauteur de la place (bien plus court que
     * {@link Terrain#surface}, qui part de y = 300 : quelques centaines de colonnes par palier), ou {@link Terrain#NONE}.
     */
    private static int surface(ChunkStore chunks, int plaza, int x, int z) {
        for (int y = plaza + MAX_DROP + 6; y >= plaza - MAX_DROP - 1; y--) {
            String name = Blocks.name(chunks, x, y, z);
            if (name != null && Terrain.isGround(name)) {
                return y;
            }
        }
        return Terrain.NONE;
    }

    /** Sol naturel qu'on peut paver : terre, herbe, sable, neige, gravier, boue (pas un champ labouré). */
    private static boolean soil(String name) {
        return name.startsWith("Soil_") && Chantiers.natural(name) && !name.contains("Tilled");
    }

    /**
     * Retire l'herbe basse et les fleurs au-dessus de (x, y, z). Faux (rien retiré) si autre chose surmonte le sol :
     * tronc, feuillage, meuble, bloc de joueur.
     */
    private static boolean clearAbove(ChunkStore chunks, int x, int y, int z) {
        for (int dy = 1; dy <= 2; dy++) {
            String name = Blocks.name(chunks, x, y + dy, z);
            if (name != null && !Grading.isSmallPlant(name)) {
                return false;
            }
        }
        for (int dy = 2; dy >= 1; dy--) {
            if (Blocks.name(chunks, x, y + dy, z) != null) {
                Blocks.set(chunks, x, y + dy, z, null, 0);
            }
        }
        return true;
    }

    /** Vrai si (x, z) tombe dans l'emprise d'un bâtiment du plan ou d'un terrain E1/E2 (garde-fou du générateur). */
    private static boolean insideBuilding(Village village, VillageLayout layout, int x, int z) {
        int lx = x - village.x();
        int lz = z - village.z();
        for (VillageLayout.Building b : layout.buildings()) {
            int[] r = b.rect();
            if (lx >= r[0] && lx <= r[1] && lz >= r[2] && lz <= r[3]) {
                return true;
            }
        }
        for (VillageLayout.Plot p : layout.plots()) {
            int[] r = p.rect();
            if (lx >= r[0] && lx <= r[1] && lz >= r[2] && lz <= r[3]) {
                return true;
            }
        }
        return false;
    }
}
