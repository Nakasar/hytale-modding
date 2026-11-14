package dev.nakasar.hytale.peuples.village;

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
        VillageRegistry registry = registry(world);
        for (Village other : registry.all()) {
            double d = Math.sqrt(other.distanceSquared(x + 0.5, y + 0.5, z + 0.5));
            if (d < MIN_SPACING) {
                return new Founding(null, Message.translation(MESSAGES + "tooClose")
                        .param("name", other.name()).param("distance", (int) d).param("min", MIN_SPACING));
            }
        }
        ChunkStore chunks = world.getChunkStore();
        int[][] cells = {{x, y, z}, {x + 2, y, z}, {x - 2, y, z}};
        for (int[] c : cells) {
            if (!Blocks.isEmpty(chunks, c[0], c[1], c[2])) {
                return new Founding(null, Message.translation(MESSAGES + "notEmpty")
                        .param("x", c[0]).param("y", c[1]).param("z", c[2]));
            }
        }
        if (!Blocks.set(chunks, x, y, z, HEART_BLOCK, 0)) {
            return new Founding(null, Message.translation(MESSAGES + "placeFailed").param("block", HEART_BLOCK));
        }
        Village village = new Village(UUID.randomUUID().toString(), name, people, x, y, z);
        if (Blocks.set(chunks, x + 2, y, z, people.depositBlock(), 0)) {
            village.setDeposit(x + 2, y, z);
        }
        if (Blocks.set(chunks, x - 2, y, z, people.boardBlock(), 0)) {
            village.setBoard(x - 2, y, z);
        }
        registry.add(village);
        return new Founding(village, null);
    }

    /**
     * Efface le village : retire son cœur et son tableau s'ils sont encore là. Le dépôt reste en place avec son
     * contenu (les objets des joueurs ne disparaissent jamais).
     */
    public static void dissolve(World world, Village village) {
        ChunkStore chunks = world.getChunkStore();
        Blocks.clearIf(chunks, village.x(), village.y(), village.z(), HEART_BLOCK);
        int[] b = village.board();
        Blocks.clearIf(chunks, b[0], b[1], b[2], village.people().boardBlock());
        registry(world).remove(village);
    }

    /** Ajoute de l'essor (borné par le seuil du palier) ; rend le gain réel. */
    public static int addEssor(Village village, int amount) {
        return village.addEssor(amount);
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
     * section n'est pas chargée. Lecture seule : le crédit des demandes (retrait des objets) vient à l'étape 3.
     */
    public static Map<String, Integer> depositContents(World world, Village village) {
        int[] d = village.deposit();
        if (!village.people().depositBlock().equals(Blocks.name(world.getChunkStore(), d[0], d[1], d[2]))) {
            return null;
        }
        ItemContainerBlock container = BlockModule.getComponent(ItemContainerBlock.getComponentType(), world, d[0], d[1], d[2]);
        if (container == null) {
            return null;
        }
        ItemContainer items = container.getItemContainer();
        Map<String, Integer> out = new LinkedHashMap<>();
        if (items == null) {
            return out;
        }
        for (short slot = 0; slot < items.getCapacity(); slot++) {
            ItemStack stack = items.getItemStack(slot);
            if (!ItemStack.isEmpty(stack)) {
                out.merge(stack.getItemId(), stack.getQuantity(), Integer::sum);
            }
        }
        return out;
    }
}
