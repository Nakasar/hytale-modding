package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.block.components.ItemContainerBlock;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Deposits;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.workshop.Workshops;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Coffre de dépôt d'un avant-poste (Kevin, 2026-11-16) : un petit coffre vanilla du peuple, posé à côté du panneau de
 * l'avant-poste à la fin des travaux (ou au premier passage d'un joueur pour les avant-postes déjà debout).
 * <ul>
 *   <li>Chaque matin ({@link GameClock#MORNING} h), la production du jour (lot × niveau) entre dans ce coffre. Coffre
 *       pas chargé (personne près de l'avant-poste) ou plein : elle attend dans le stock de l'avant-poste
 *       ({@link AnnexState#stock()}) et y entre dès qu'il est chargé et a de la place. Le stock garde au plus
 *       {@value #STOCK_DAYS} jours de production ; au-delà, la production du jour est perdue (annonce).</li>
 *   <li>Le joueur s'y sert librement : ce qu'il prend n'ira pas au village.</li>
 *   <li>À {@value #DEPART_HOUR} h, le convoi part avec tout le contenu du coffre (objets simples : ni usés ni porteurs de
 *       données, ceux-là restent au coffre) et le stock. Coffre pas chargé : il ne prend que le stock.</li>
 *   <li>Dépôt du village plein (chargé et plus rien n'y entre) : le convoi ne part pas, tout reste à l'avant-poste ; on
 *       réessaie à chaque pas, une annonce par jour.</li>
 * </ul>
 */
public final class AnnexChests {

    /** Heure de départ du convoi : le matin, la production attend au coffre de l'avant-poste. */
    public static final int DEPART_HOUR = 12;
    /** Jours de production que le stock de l'avant-poste garde au plus. */
    public static final int STOCK_DAYS = 3;
    private static final String KEYS = Annexes.KEYS;
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    /** Places du coffre (repère local de l'avant-poste : fondation à l'origine, joueur au sud, bâtiment au nord). */
    private static final int[][] SPOTS = {{2, 0}, {-2, 0}, {2, 1}, {-2, 1}, {3, 0}, {-3, 0}, {1, 1}, {-1, 1}, {3, 1}, {-3, 1}};
    /** Dernier jour où une annonce a été faite, par avant-poste et par sujet. */
    private static final Map<String, Long> NOTICE = new ConcurrentHashMap<>();

    private AnnexChests() {
    }

    /** Vrai si l'avant-poste produit (une tour de guet ne livre rien : pas de coffre). */
    static boolean produces(Workshop w) {
        return w.annex().delivery() != null;
    }

    /**
     * Pose le coffre à côté du panneau, tourné vers le côté d'où le joueur a posé la fondation. Sans effet tant que la
     * zone n'est pas chargée ou qu'aucune place ne convient.
     */
    static void place(World world, Village village, Workshop w, AnnexState a) {
        if (a.hasChest() || !produces(w)) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        if (Blocks.id(chunks, a.x(), a.y(), a.z()) == Blocks.UNLOADED) {
            return;
        }
        WorkshopState ws = village.workshop(w.getId());
        int near = ws != null && ws.hasBoard() ? ws.board()[1] : a.ground() + 1;
        Terrain terrain = new Terrain(world);
        int[] rect = Annexes.worldRect(w, a);
        String block = village.people().depositBlock();
        for (int[] spot : SPOTS) {
            int[] at = Annexes.toWorld(a, spot[0], spot[1]);
            int x = at[0];
            int z = at[1];
            if (ws != null && ws.hasBoard() && ws.board()[0] == x && ws.board()[2] == z) {
                continue;
            }
            int y = Workshops.standY(chunks, terrain, x, z);
            if (y == Workshops.UNLOADED_SPOT) {
                return;
            }
            if (y == Terrain.NONE || Math.abs(y - near) > 2 || !Blocks.solid(chunks, x, y - 1, z)
                    || x >= rect[0] && x <= rect[1] && z >= rect[2] && z <= rect[3]) {
                continue;
            }
            if (Blocks.set(chunks, x, y, z, block, a.rotation())) {
                a.setChest(x, y, z);
                LOGGER.atInfo().log("Nakasar Peuples : coffre de l'avant-poste %s posé en %d %d %d (%s)", w.getId(), x, y, z, village.name());
                return;
            }
        }
    }

    /**
     * Conteneur du coffre de l'avant-poste, ou null s'il n'est pas posé ou pas chargé. Un coffre disparu (cassé) alors
     * que sa section est chargée est oublié : il sera reposé.
     */
    public static ItemContainer container(World world, Village village, AnnexState a) {
        int[] c = a.chest();
        if (c == null) {
            return null;
        }
        ChunkStore chunks = world.getChunkStore();
        if (Blocks.id(chunks, c[0], c[1], c[2]) == Blocks.UNLOADED) {
            return null;
        }
        if (!Blocks.is(Blocks.name(chunks, c[0], c[1], c[2]), village.people().depositBlock())) {
            a.clearChest();
            return null;
        }
        ItemContainerBlock container = BlockModule.getComponent(ItemContainerBlock.getComponentType(), world, c[0], c[1], c[2]);
        return container == null ? null : container.getItemContainer();
    }

    /** Pas d'un avant-poste debout : coffre à poser, production du matin, stock à ranger au coffre. */
    static void step(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a, boolean watched) {
        if (!produces(w)) {
            return;
        }
        if (!a.hasChest() && watched) {
            place(world, village, w, a);
        }
        produce(world, store, village, w, a);
        ItemContainer chest = container(world, village, a);
        if (chest != null && a.stockTotal() > 0) {
            Map<String, Integer> left = new LinkedHashMap<>();
            for (Map.Entry<String, Integer> e : a.stock().entrySet()) {
                ItemStack rest = chest.addItemStack(new ItemStack(e.getKey(), e.getValue())).getRemainder();
                if (!ItemStack.isEmpty(rest)) {
                    left.put(e.getKey(), rest.getQuantity());
                }
            }
            a.setStock(left);
        }
    }

    static int lotSize(VillageLayout.Material lot, int level, double yield) {
        return Math.max(1, (int) Math.round(lot.quantity() * level * yield));
    }

    /** Production du matin, une fois par jour de jeu : au stock, rangée au coffre au pas même s'il est chargé. */
    private static void produce(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a) {
        long day = GameClock.day(store);
        if (a.produceDay() == Long.MIN_VALUE && a.deliveryDay() >= day) {
            // Avant-poste d'avant les coffres : la livraison du jour est déjà partie.
            a.setProduceDay(day);
        }
        if (a.produceDay() >= day || GameClock.hour(store) < GameClock.MORNING) {
            return;
        }
        a.setProduceDay(day);
        int level = Math.max(1, village.workshop(w.getId()).level());
        // Gisement (Kevin, 2026-11-16) : maigre -25 %, riche +50 %, au moins 1 par lot.
        double yield = a.yieldFactor();
        int amount = 0;
        for (VillageLayout.Material lot : w.annex().lots()) {
            amount += lotSize(lot, level, yield);
        }
        int room = amount * STOCK_DAYS - a.stockTotal();
        if (room <= 0) {
            notice(world, village, w, a, "stockFull", day, Message.translation(KEYS + "chest.full")
                    .param("building", Message.translation(w.nameKey())), NotificationStyle.Warning);
            return;
        }
        for (VillageLayout.Material lot : w.annex().lots()) {
            int n = Math.min(room, lotSize(lot, level, yield));
            a.addStock(lot.itemId(), n);
            room -= n;
        }
    }

    /**
     * Le convoi du jour part (à {@value #DEPART_HOUR} h), avec le contenu du coffre et le stock ; rien si tout est vide.
     * Dépôt du village chargé et plein : il ne part pas (annonce une fois par jour) et réessaiera au pas suivant.
     */
    static void depart(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a) {
        long day = GameClock.day(store);
        if (!produces(w) || a.convoy() || a.deliveryDay() >= day || GameClock.hour(store) < DEPART_HOUR) {
            return;
        }
        Map<String, Integer> cargo = a.stock();
        ItemContainer chest = container(world, village, a);
        List<Short> slots = new ArrayList<>();
        if (chest != null) {
            for (short slot = 0; slot < chest.getCapacity(); slot++) {
                ItemStack stack = chest.getItemStack(slot);
                if (!ItemStack.isEmpty(stack) && simple(stack)) {
                    cargo.merge(stack.getItemId(), stack.getQuantity(), Integer::sum);
                    slots.add(slot);
                }
            }
        }
        if (cargo.isEmpty()) {
            a.setDeliveryDay(day);
            return;
        }
        ItemContainer deposit = Villages.depositChest(world, village);
        if (deposit != null && !Deposits.accepts(deposit, cargo)) {
            notice(world, village, w, a, "depositFull", day, Message.translation(KEYS + "deposit.full")
                    .param("building", Message.translation(w.nameKey())).param("village", village.name()), NotificationStyle.Warning);
            return;
        }
        if (chest != null) {
            for (short slot : slots) {
                chest.removeItemStackFromSlot(slot);
            }
        }
        a.setStock(Map.of());
        Convoys.start(store, village, w, a, cargo);
    }

    /** Objet que le convoi peut porter sans rien perdre : pas de données propres, pas usé. */
    private static boolean simple(ItemStack stack) {
        return stack.getMetadata() == null && (stack.getMaxDurability() <= 0 || stack.getDurability() >= stack.getMaxDurability());
    }

    /** Annonce au village, une fois par jour de jeu et par sujet pour cet avant-poste. */
    static void notice(World world, Village village, Workshop w, AnnexState a, String topic, long day, Message message,
                       NotificationStyle style) {
        String key = village.id() + "/" + w.getId() + "|" + topic;
        Long last = NOTICE.get(key);
        if (last != null && last >= day) {
            return;
        }
        NOTICE.put(key, day);
        Chantiers.announce(world, village, message, null, style);
        Annexes.announceNear(world, world.getEntityStore().getStore(), a, message, style, village);
    }

    public static void clearAll() {
        NOTICE.clear();
    }
}
