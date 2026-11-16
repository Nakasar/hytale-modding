package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.HashSet;
import java.util.Set;

/**
 * Le cœur du village, propre à chaque peuple (tools/generate_village_hearts.py) : une place mise en scène avec des
 * prefabs VANILLA (chêne kweebec qui grandit, arbre aux trophées trork, bassin feran, foyer des Renoncés, sanctuaire
 * slothian) et des blocs posés un à un, qui s'enrichit à chaque palier.
 *
 * <p>Chaque palier du plan ({@link VillageLayout.HeartStep}) s'applique dans l'ordre : pièces vanilla, blocs posés
 * ({@code "x y z rotation Bloc"}, {@code Empty} pour vider), blocs retirés s'ils sont toujours là, fluides. Les
 * coordonnées sont relatives au cœur, y = 0 à la surface de la place (le cœur est en y = 1).
 *
 * <p>Jamais touchés : les coffres et autres inventaires, le cœur, le tableau, le dépôt et la bannière du village. Lors
 * d'un passage de palier (village habité), un bloc n'est remplacé que s'il est naturel, vide, du sol de la place ou un
 * bloc du cœur lui-même : une construction de joueur sur la place reste en place.
 */
public final class VillageHeart {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    private static final String EMPTY = "Empty";

    private VillageHeart() {
    }

    /**
     * Applique les paliers du cœur de `layout` d'au-dessus de `from` jusqu'à `to` compris, le cœur centré en (cx, cz)
     * et la surface de la place en `ground`. `fresh` : village qu'on vient de bâtir (rien d'un joueur sur la place).
     * Rend le nombre de blocs et pièces posés.
     */
    static int apply(World world, VillageLayout layout, Village village, int cx, int ground, int cz, int from, int to, boolean fresh) {
        VillageLayout.Heart heart = layout.heart();
        if (heart == null) {
            return 0;
        }
        ChunkStore chunks = world.getChunkStore();
        Store<EntityStore> store = world.getEntityStore().getStore();
        Set<String> own = fresh ? Set.of() : ownBlocks(heart);
        Set<Long> reserved = reserved(village);
        int count = 0;
        for (VillageLayout.HeartStep step : heart.steps()) {
            if (step.tier() <= from || step.tier() > to) {
                continue;
            }
            for (VillageLayout.HeartPiece p : step.pieces()) {
                if (!fresh && guarded(world, chunks, layout, p, cx, ground, cz)) {
                    LOGGER.atInfo().log("Nakasar Peuples : pièce %s du cœur de %s non posée (coffre ou bloc du village dessous)",
                            p.prefab(), village == null ? "?" : village.name());
                    continue;
                }
                if (VillageBuilder.paste(world, store, p.prefab(), cx + p.x(), ground + p.y(), cz + p.z(), p.rotation())) {
                    count++;
                }
            }
            for (String line : step.set()) {
                String[] f = line.trim().split("\\s+");
                if (f.length != 5) {
                    continue;
                }
                int x = cx + Integer.parseInt(f[0]);
                int y = ground + Integer.parseInt(f[1]);
                int z = cz + Integer.parseInt(f[2]);
                int rotation = Integer.parseInt(f[3]);
                String block = EMPTY.equals(f[4]) ? null : f[4];
                if (reserved.contains(key(x, y, z)) || !replaceable(world, chunks, layout, x, y, z, fresh, own)) {
                    continue;
                }
                String current = Blocks.name(chunks, x, y, z);
                if (block == null ? current == null : block.equals(current) && Blocks.rotation(chunks, x, y, z) == rotation) {
                    continue;
                }
                if (Blocks.set(chunks, x, y, z, block, rotation)) {
                    count++;
                }
            }
            for (String line : step.clear()) {
                String[] f = line.trim().split("\\s+");
                if (f.length != 4) {
                    continue;
                }
                int x = cx + Integer.parseInt(f[0]);
                int y = ground + Integer.parseInt(f[1]);
                int z = cz + Integer.parseInt(f[2]);
                if (!reserved.contains(key(x, y, z))) {
                    Blocks.clearIf(chunks, x, y, z, f[3]);
                }
            }
            if (step.fluids() != null && !step.fluids().isEmpty()) {
                VillageBuilder.paste(world, store, step.fluids(), cx, ground, cz, 0);
            }
        }
        return count;
    }

    /**
     * Passage de palier d'un village bâti par plan : pose les paliers du cœur qu'il n'a pas encore jusqu'à `tier`. Les
     * villages d'avant les cœurs ({@link Village#heartTier()} négatif, place carrée de l'ancien plan) ne sont pas
     * retouchés : leur place n'a ni la taille ni le relief du cœur.
     */
    public static void upgrade(World world, Village village, VillageLayout layout, int tier) {
        if (layout == null || layout.heart() == null || village.heartTier() < 0 || village.heartTier() >= tier) {
            return;
        }
        int n = apply(world, layout, village, village.x(), village.y() - 1, village.z(), village.heartTier(), tier, false);
        village.setHeartTier(tier);
        LOGGER.atInfo().log("Nakasar Peuples : cœur de %s au palier %d (%d blocs et pièces)", village.name(), tier, n);
    }

    /** Vrai si un inventaire ou un bloc du village se trouve sous la pièce `p` (on ne la colle pas). */
    private static boolean guarded(World world, ChunkStore chunks, VillageLayout layout, VillageLayout.HeartPiece p, int cx, int ground, int cz) {
        int[] box = VillageBuilder.bounds(p.prefab(), cx + p.x(), ground + p.y(), cz + p.z(), p.rotation());
        if (box == null) {
            return false;
        }
        for (int x = box[0]; x <= box[1]; x++) {
            for (int z = box[4]; z <= box[5]; z++) {
                for (int y = box[2]; y <= box[3]; y++) {
                    String name = Blocks.name(chunks, x, y, z);
                    if (name != null && (isVillageBlock(layout.people(), name) || (name.contains("Chest") || name.contains("Furniture_"))
                            && Burning.isContainer(world, x, y, z))) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /** Vrai si le cœur peut écrire en (x, y, z). */
    private static boolean replaceable(World world, ChunkStore chunks, VillageLayout layout, int x, int y, int z, boolean fresh, Set<String> own) {
        String current = Blocks.name(chunks, x, y, z);
        if (current == null) {
            return true;
        }
        if (Burning.isContainer(world, x, y, z) || isVillageBlock(layout.people(), current)) {
            return false;
        }
        if (fresh) {
            return true;
        }
        String base = base(current);
        People people = layout.people();
        return Terrain.isVegetation(base) || Chantiers.natural(current) || own.contains(base)
                || base.equals(people.plaza()) || base.equals(people.ground()) || base.startsWith(Terrain.PATHWAY);
    }

    /** Blocs propres au village (cœur, tableau, dépôt, bannière) : jamais écrasés. */
    private static boolean isVillageBlock(People people, String name) {
        return Blocks.is(name, Villages.HEART_BLOCK) || Blocks.is(name, people.boardBlock())
                || people.isDepositBlock(name) || Blocks.is(name, people.bannerBlock());
    }

    /** Cases du cœur, du tableau, du dépôt et de la bannière du village (null : aucune). */
    private static Set<Long> reserved(Village village) {
        Set<Long> cells = new HashSet<>();
        if (village == null) {
            return cells;
        }
        cells.add(key(village.x(), village.y(), village.z()));
        cells.add(key(village.x(), village.y() + 1, village.z()));
        int[] d = village.deposit();
        cells.add(key(d[0], d[1], d[2]));
        int[] d2 = village.deposit2();
        if (d2 != null) {
            cells.add(key(d2[0], d2[1], d2[2]));
        }
        // Seconde case du futur grand coffre (palier 2) : le cœur n'y pose jamais rien.
        int[] wide = Deposits.wideCell(village);
        if (wide != null) {
            cells.add(key(wide[0], wide[1], wide[2]));
        }
        int[] b = village.board();
        cells.add(key(b[0], b[1], b[2]));
        if (village.hasBanner()) {
            int[] f = village.banner();
            cells.add(key(f[0], f[1], f[2]));
        }
        return cells;
    }

    /** Tous les blocs que le cœur pose ou retire : il peut les remplacer à un palier suivant. */
    private static Set<String> ownBlocks(VillageLayout.Heart heart) {
        Set<String> names = new HashSet<>();
        for (VillageLayout.HeartStep step : heart.steps()) {
            for (String line : step.set()) {
                String[] f = line.trim().split("\\s+");
                if (f.length == 5 && !EMPTY.equals(f[4])) {
                    names.add(f[4]);
                }
            }
            for (String line : step.clear()) {
                String[] f = line.trim().split("\\s+");
                if (f.length == 4) {
                    names.add(f[3]);
                }
            }
        }
        return names;
    }

    /** Id de base d'un bloc à états ({@code *Bloc_State_Definitions_X} donne {@code Bloc}). */
    private static String base(String name) {
        if (!name.startsWith("*")) {
            return name;
        }
        int i = name.indexOf("_State_Definitions_");
        return i < 0 ? name.substring(1) : name.substring(1, i);
    }

    private static long key(int x, int y, int z) {
        return ((long) (x & 0x3FFFFFF) << 38) | ((long) (y & 0xFFF) << 26) | (z & 0x3FFFFFF);
    }

    /** Position absolue {@code [x, y, z, lacet]} d'une place du cœur ({@code [dx, dy, dz, lacet]}), ou null. */
    static int[] at(int[] spot, int cx, int ground, int cz) {
        if (spot == null || spot.length < 3) {
            return null;
        }
        return new int[]{cx + spot[0], ground + spot[1], cz + spot[2], spot.length > 3 ? spot[3] : 0};
    }
}
