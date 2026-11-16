package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.blockhitbox.BlockBoundingBoxes;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.FillerBlockUtil;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le dépôt du village grandit (Kevin, 2026-11-16) : à partir du palier {@value #LARGE_TIER}, le petit coffre vanilla du
 * peuple (18 emplacements) devient le grand coffre du même style (36 emplacements, deux cases), avec tout son contenu.
 *
 * <p>La seconde case est celle que le plan du cœur réserve ({@link VillageLayout.Heart#depositWide()}, choisie hors des
 * allées de la place pour ne pas gêner les villageois) ; sinon l'une des deux cases voisines sur l'axe du coffre, de
 * préférence hors d'un chemin. La case doit être vide (ou de la végétation) et posée sur un sol plein. Les cases occupées
 * par le grand coffre viennent de sa boîte de collision tournée (celle du moteur, {@link FillerBlockUtil}), jamais d'une
 * table écrite ici. Un village qui redescend d'un palier garde son grand coffre (les objets ne disparaissent jamais).
 *
 * <p>Le dépôt ouvert par un joueur (état {@code _OpenWindow}) n'est pas remplacé : on réessaie au pas suivant.
 */
public final class Deposits {

    /** Palier à partir duquel le dépôt est un grand coffre. */
    public static final int LARGE_TIER = 2;
    public static final String KEYS = "nakasar_peuples.annex.";
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    /** Villages dont l'agrandissement a échoué faute de place (signalé une fois dans le journal). */
    private static final Set<String> NO_ROOM = ConcurrentHashMap.newKeySet();

    private Deposits() {
    }

    /**
     * Seconde case prévue par le plan du cœur pour le grand coffre, en coordonnées du monde, ou null (village d'avant les
     * cœurs, plan sans cette case, ou dépôt qui n'est plus à sa place de plan).
     */
    public static int[] wideCell(Village village) {
        if (village == null || village.depositLarge() || village.heartTier() < 0 || village.layout() == null) {
            return null;
        }
        VillageLayout layout = VillageLayout.get(village.layout());
        VillageLayout.Heart heart = layout == null ? null : layout.heart();
        if (heart == null || heart.depositWide() == null || heart.deposit() == null) {
            return null;
        }
        int[] planned = VillageHeart.at(heart.deposit(), village.x(), village.y() - 1, village.z());
        int[] d = village.deposit();
        if (planned == null || planned[0] != d[0] || planned[1] != d[1] || planned[2] != d[2]) {
            return null;
        }
        int[] w = VillageHeart.at(heart.depositWide(), village.x(), village.y() - 1, village.z());
        return w == null ? null : new int[] {w[0], w[1], w[2]};
    }

    /**
     * Pas du village (joueurs près de lui) : au palier {@value #LARGE_TIER} ou plus, le petit coffre de dépôt devient le
     * grand coffre. Sans effet tant que le coffre n'est pas chargé, qu'il est ouvert ou que la place manque.
     */
    public static void upgrade(World world, Village village) {
        if (village.depositLarge() || village.tier() < LARGE_TIER) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        int[] d = village.deposit();
        if (Blocks.id(chunks, d[0], d[1], d[2]) == Blocks.UNLOADED) {
            return;
        }
        People people = village.people();
        String current = Blocks.name(chunks, d[0], d[1], d[2]);
        if (Blocks.is(current, people.depositLargeBlock())) {
            // Grand coffre déjà là (posé à la main, ou état perdu) : on retrouve sa seconde case.
            int[] f = filler(people.depositLargeBlock(), Blocks.rotation(chunks, d[0], d[1], d[2]));
            if (f != null) {
                village.setDepositLarge(d, new int[] {d[0] + f[0], d[1] + f[1], d[2] + f[2]});
            }
            return;
        }
        if (!Blocks.is(current, people.depositBlock()) || current.endsWith("_OpenWindow")) {
            return;
        }
        int rotation = Blocks.rotation(chunks, d[0], d[1], d[2]);
        int[] f = filler(people.depositLargeBlock(), rotation);
        if (f == null) {
            if (NO_ROOM.add(village.id() + "|hitbox")) {
                LOGGER.atWarning().log("Nakasar Peuples : %s n'a pas une seule case de remplissage, dépôt de %s laissé petit",
                        people.depositLargeBlock(), village.name());
            }
            return;
        }
        int[][] place = choose(world, village, d, f);
        if (place == null) {
            if (NO_ROOM.add(village.id() + "|room")) {
                LOGGER.atWarning().log("Nakasar Peuples : pas de case libre à côté du dépôt de %s (%d %d %d) pour le grand coffre",
                        village.name(), d[0], d[1], d[2]);
            }
            return;
        }
        ItemContainer old = Villages.depositChest(world, village);
        if (old == null) {
            return;
        }
        List<ItemStack> items = new ArrayList<>();
        for (short slot = 0; slot < old.getCapacity(); slot++) {
            ItemStack stack = old.getItemStack(slot);
            if (!ItemStack.isEmpty(stack)) {
                items.add(stack);
            }
        }
        old.clear();
        int[] origin = place[0];
        int[] second = place[1];
        int[] free = same(origin, d) ? second : origin;
        if (Terrain.isVegetation(Blocks.name(chunks, free[0], free[1], free[2]))) {
            Blocks.set(chunks, free[0], free[1], free[2], null, 0);
        }
        Blocks.set(chunks, d[0], d[1], d[2], null, 0);
        boolean placed = Blocks.set(chunks, origin[0], origin[1], origin[2], people.depositLargeBlock(), rotation);
        if (placed) {
            village.setDepositLarge(origin, second);
        } else {
            // Jamais d'objets perdus : le petit coffre revient à sa place.
            Blocks.set(chunks, d[0], d[1], d[2], people.depositBlock(), rotation);
        }
        ItemContainer chest = Villages.depositChest(world, village);
        List<ItemStack> left = new ArrayList<>();
        for (ItemStack stack : items) {
            ItemStack rest = chest == null ? stack : chest.addItemStack(stack).getRemainder();
            if (!ItemStack.isEmpty(rest)) {
                left.add(rest);
            }
        }
        if (!left.isEmpty()) {
            drop(world, d, left);
        }
        if (placed) {
            LOGGER.atInfo().log("Nakasar Peuples : le dépôt de %s devient un grand coffre en %d %d %d (seconde case %d %d %d, %d piles)",
                    village.name(), origin[0], origin[1], origin[2], second[0], second[1], second[2], items.size());
            Chantiers.announce(world, village, Message.translation(KEYS + "deposit.large").param("village", village.name()),
                    null, NotificationStyle.Success);
        }
    }

    /**
     * {origine, seconde case} du grand coffre : la case du plan d'abord, puis les deux voisines sur l'axe du coffre
     * (hors d'un chemin d'abord). L'origine porte le bloc et son conteneur ; la seconde est la case de remplissage.
     */
    private static int[][] choose(World world, Village village, int[] d, int[] f) {
        int[] plus = {d[0] + f[0], d[1] + f[1], d[2] + f[2]};
        int[] minus = {d[0] - f[0], d[1] - f[1], d[2] - f[2]};
        int[][] keepOrigin = {d, plus};
        int[][] moveOrigin = {minus, d};
        List<int[][]> order = new ArrayList<>();
        int[] wide = wideCell(village);
        if (wide != null && same(wide, plus)) {
            order.add(keepOrigin);
        } else if (wide != null && same(wide, minus)) {
            order.add(moveOrigin);
        }
        ChunkStore chunks = world.getChunkStore();
        boolean plusPath = onPath(chunks, plus);
        boolean minusPath = onPath(chunks, minus);
        if (plusPath && !minusPath) {
            order.add(moveOrigin);
            order.add(keepOrigin);
        } else {
            order.add(keepOrigin);
            order.add(moveOrigin);
        }
        for (int[][] option : order) {
            int[] cell = same(option[0], d) ? option[1] : option[0];
            if (free(world, village, cell)) {
                return option;
            }
        }
        return null;
    }

    private static boolean free(World world, Village village, int[] c) {
        ChunkStore chunks = world.getChunkStore();
        if (Blocks.id(chunks, c[0], c[1], c[2]) == Blocks.UNLOADED || Blocks.id(chunks, c[0], c[1] - 1, c[2]) == Blocks.UNLOADED) {
            return false;
        }
        String name = Blocks.name(chunks, c[0], c[1], c[2]);
        if (name != null && !Terrain.isVegetation(name)) {
            return false;
        }
        if (!Blocks.solid(chunks, c[0], c[1] - 1, c[2])) {
            return false;
        }
        int[] b = village.board();
        if (c[0] == village.x() && c[2] == village.z() || same(c, b) || village.hasBanner() && same(c, village.banner())) {
            return false;
        }
        return true;
    }

    private static boolean onPath(ChunkStore chunks, int[] c) {
        String under = Blocks.name(chunks, c[0], c[1] - 1, c[2]);
        return under != null && under.startsWith(Terrain.PATHWAY);
    }

    /** Seule case de remplissage {dx, dy, dz} du bloc `blockId` tourné de `rotation`, ou null s'il n'en a pas une seule. */
    static int[] filler(String blockId, int rotation) {
        BlockType type = BlockType.getAssetMap().getAsset(blockId);
        if (type == null) {
            return null;
        }
        BlockBoundingBoxes boxes = BlockBoundingBoxes.getAssetMap().getAsset(type.getHitboxTypeIndex());
        if (boxes == null) {
            return null;
        }
        List<int[]> cells = new ArrayList<>();
        FillerBlockUtil.forEachFillerBlock(boxes.get(rotation), (x, y, z) -> {
            if (x != 0 || y != 0 || z != 0) {
                cells.add(new int[] {x, y, z});
            }
        });
        return cells.size() == 1 && cells.get(0)[1] == 0 ? cells.get(0) : null;
    }

    private static void drop(World world, int[] at, List<ItemStack> items) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (Holder<EntityStore> h : ItemComponent.generateItemDrops(store, items, new Vector3d(at[0] + 0.5, at[1] + 0.5, at[2] + 0.5),
                new Rotation3f())) {
            store.addEntity(h, AddReason.SPAWN);
        }
    }

    private static boolean same(int[] a, int[] b) {
        return a != null && b != null && a[0] == b[0] && a[1] == b[1] && a[2] == b[2];
    }

    /** Places libres pour `items` dans `chest` ? Vrai si au moins un objet de la liste y entre encore. */
    public static boolean accepts(ItemContainer chest, Map<String, Integer> items) {
        for (String id : items.keySet()) {
            if (chest.canAddItemStack(new ItemStack(id, 1))) {
                return true;
            }
        }
        return false;
    }

    public static void clearAll() {
        NO_ROOM.clear();
    }
}
