package dev.nakasar.hytale.peuples.village;

import dev.nakasar.hytale.peuples.PeuplesPlugin;

import com.hypixel.hytale.component.ResourceType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.block.components.ItemContainerBlock;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Les opérations sur les villages d'un monde : fondation (cœur, dépôt, tableau), recherche, essor, lecture du dépôt.
 * Toujours sur le thread du monde ({@code world.execute}).
 */
public final class Villages {

    /** Bloc cœur de village : invisible et traversable, comme les cellules de prison du mod Vampires. */
    public static final String HEART_BLOCK = "Nakasar_Peuples_Village_Heart";
    /** Deux villages sont séparés d'au moins cette distance (blocs, entre cœurs). */
    public static final int MIN_SPACING = 64;
    /** Rayon dans lequel un joueur « est » dans un village (commandes, dialogues). */
    public static final int RADIUS = 48;

    public static final String MESSAGES = "nakasar_peuples.village.";

    private static ResourceType<EntityStore, VillageRegistry> resourceType;

    private Villages() {
    }

    public static void setResourceType(ResourceType<EntityStore, VillageRegistry> type) {
        resourceType = type;
    }

    public static VillageRegistry registry(World world) {
        return world.getEntityStore().getStore().getResource(resourceType);
    }

    /** Résultat d'une fondation : le village, ou la clé du message d'échec. */
    public record Founding(Village village, Message error) {
    }

    /**
     * Fonde un village du peuple `people` dont le cœur est en (x, y, z) : dépôt deux blocs à l'est, tableau deux blocs
     * à l'ouest. Les trois cases doivent être vides (aucun bloc de joueur n'est écrasé).
     */
    public static Founding found(World world, String name, People people, int x, int y, int z) {
        return found(world, name, people, x, y, z, new int[]{x + 2, y, z, 0}, new int[]{x - 2, y, z, 0});
    }

    /**
     * Fonde un village dont le cœur est en (x, y, z), le dépôt et le tableau aux places {@code [x, y, z, rotation]}
     * données (cœur du plan, {@link VillageHeart}). Les trois cases doivent être vides ou ne porter que de la
     * végétation, retirée.
     */
    public static Founding found(World world, String name, People people, int x, int y, int z, int[] deposit, int[] board) {
        VillageRegistry registry = registry(world);
        for (Village other : registry.all()) {
            double d = Math.sqrt(other.distanceSquared(x + 0.5, y + 0.5, z + 0.5));
            if (d < MIN_SPACING) {
                return new Founding(null, Message.translation(MESSAGES + "tooClose")
                        .param("name", other.name()).param("distance", (int) d).param("min", MIN_SPACING));
            }
        }
        ChunkStore chunks = world.getChunkStore();
        int[][] cells = {{x, y, z}, deposit, board};
        for (int[] c : cells) {
            if (Terrain.isVegetation(Blocks.name(chunks, c[0], c[1], c[2]))) {
                Blocks.set(chunks, c[0], c[1], c[2], null, 0);
            }
            if (!Blocks.isEmpty(chunks, c[0], c[1], c[2])) {
                return new Founding(null, Message.translation(MESSAGES + "notEmpty")
                        .param("x", c[0]).param("y", c[1]).param("z", c[2]));
            }
        }
        if (!Blocks.set(chunks, x, y, z, HEART_BLOCK, 0)) {
            return new Founding(null, Message.translation(MESSAGES + "placeFailed").param("block", HEART_BLOCK));
        }
        Village village = new Village(UUID.randomUUID().toString(), name, people, x, y, z);
        if (Blocks.set(chunks, deposit[0], deposit[1], deposit[2], people.depositBlock(), deposit.length > 3 ? deposit[3] : 0)) {
            village.setDeposit(deposit[0], deposit[1], deposit[2]);
        }
        if (Blocks.set(chunks, board[0], board[1], board[2], people.boardBlock(), board.length > 3 ? board[3] : 0)) {
            village.setBoard(board[0], board[1], board[2]);
        }
        registry.add(village);
        return new Founding(village, null);
    }

    /**
     * Efface le village : retire son cœur, son tableau et sa bannière s'ils sont encore là. Le dépôt reste en place avec
     * son contenu (les objets des joueurs ne disparaissent jamais), les bâtiments collés aussi.
     */
    public static void dissolve(World world, Village village) {
        ChunkStore chunks = world.getChunkStore();
        Blocks.clearIf(chunks, village.x(), village.y(), village.z(), HEART_BLOCK);
        int[] b = village.board();
        Blocks.clearIf(chunks, b[0], b[1], b[2], village.people().boardBlock());
        for (WorkshopState w : village.workshops()) {
            if (w != null && w.hasBoard()) {
                int[] p = w.board();
                Blocks.clearIf(chunks, p[0], p[1], p[2], village.people().boardBlock());
            }
        }
        if (village.hasBanner()) {
            int[] f = village.banner();
            Blocks.clearIf(chunks, f[0], f[1], f[2], village.people().bannerBlock());
        }
        registry(world).remove(village);
    }

    /**
     * Pose la bannière du peuple (bloc marqueur de carte, découvert à moins de {@link VillageEntrySystem#REVEAL_RADIUS}
     * blocs) en (x, y, z) si la case est libre. Vrai si elle est posée.
     */
    public static boolean placeBanner(World world, Village village, int x, int y, int z) {
        return placeBanner(world, village, x, y, z, 0);
    }

    /** Comme {@link #placeBanner(World, Village, int, int, int)}, tournée de `rotation` (lacet du cœur du plan). */
    public static boolean placeBanner(World world, Village village, int x, int y, int z, int rotation) {
        ChunkStore chunks = world.getChunkStore();
        String current = Blocks.name(chunks, x, y, z);
        if (current != null && !Terrain.isVegetation(current)) {
            return false;
        }
        if (!Blocks.set(chunks, x, y, z, village.people().bannerBlock(), rotation)) {
            return false;
        }
        village.setBanner(x, y, z);
        return true;
    }

    /** Marque le premier village automatique comme posé (VillageSeeder). */
    static void setSeeded(World world, boolean seeded) {
        registry(world).setSeeded(seeded);
    }

    /** Ajoute de l'essor (borné par le seuil du palier) ; rend le gain réel. */
    public static int addEssor(Village village, int amount) {
        return village.addEssor(amount);
    }

    /** Remplace les demandes du tableau (tirage du matin). */
    public static void setRequests(Village village, dev.nakasar.hytale.peuples.request.VillageRequest[] requests, long day) {
        village.setRequests(requests, day);
    }

    /** Remplace une demande du tableau (celle qui vient d'être remplie). */
    public static void setRequest(Village village, int slot, dev.nakasar.hytale.peuples.request.VillageRequest request) {
        village.setRequest(slot, request);
    }

    public static void setTier(Village village, int tier) {
        village.setTier(tier);
    }

    /** Vrai si le cœur du village est toujours en place (section chargée). */
    public static boolean heartPresent(World world, Village village) {
        return HEART_BLOCK.equals(Blocks.name(world.getChunkStore(), village.x(), village.y(), village.z()));
    }

    /**
     * Contenu du dépôt (id d'objet → quantité, dans l'ordre des emplacements), ou null si le coffre manque ou que sa
     * section n'est pas chargée (voir {@link #depositChest}).
     */
    public static Map<String, Integer> depositContents(World world, Village village) {
        ItemContainer items = depositChest(world, village);
        if (items == null) {
            return null;
        }
        Map<String, Integer> out = new LinkedHashMap<>();
        for (short slot = 0; slot < items.getCapacity(); slot++) {
            ItemStack stack = items.getItemStack(slot);
            if (!ItemStack.isEmpty(stack)) {
                out.merge(stack.getItemId(), stack.getQuantity(), Integer::sum);
            }
        }
        return out;
    }

    /** Villages dont le dépôt introuvable a déjà été signalé dans le journal (une ligne par village et par raison). */
    private static final java.util.Set<String> DEPOSIT_WARNED = java.util.concurrent.ConcurrentHashMap.newKeySet();

    /**
     * Conteneur du coffre de dépôt, ou null s'il manque ou que sa section n'est pas chargée. Le coffre peut porter
     * l'id d'un de ses états (ouvert, refermé : voir {@link Blocks#is}). Un dépôt introuvable alors que sa section
     * est chargée est signalé une fois dans le journal avec le bloc trouvé.
     */
    public static ItemContainer depositChest(World world, Village village) {
        int[] d = village.deposit();
        if (Blocks.id(world.getChunkStore(), d[0], d[1], d[2]) == Blocks.UNLOADED) {
            return null;
        }
        String found = Blocks.name(world.getChunkStore(), d[0], d[1], d[2]);
        if (!Blocks.is(found, village.people().depositBlock())) {
            warnDeposit(village, "block", "bloc " + found + " au lieu de " + village.people().depositBlock());
            return null;
        }
        ItemContainerBlock container = BlockModule.getComponent(ItemContainerBlock.getComponentType(), world, d[0], d[1], d[2]);
        if (container == null || container.getItemContainer() == null) {
            warnDeposit(village, "container", "bloc " + found + " sans conteneur");
            return null;
        }
        return container.getItemContainer();
    }

    private static void warnDeposit(Village village, String reason, String detail) {
        if (DEPOSIT_WARNED.add(village.id() + "|" + reason)) {
            int[] d = village.deposit();
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : dépôt de %s introuvable en %d %d %d (%s)",
                    village.name(), d[0], d[1], d[2], detail);
        }
    }
}
