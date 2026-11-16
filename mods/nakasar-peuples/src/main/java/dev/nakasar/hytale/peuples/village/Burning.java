package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.block.components.ItemContainerBlock;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;

import java.util.List;
import java.util.Random;
import java.util.stream.Stream;

/**
 * La version brûlée d'un bâtiment (GDD, Raids : « un raid perdu enflamme un bâtiment ») : ses blocs sont remplacés par
 * les blocs calcinés VANILLA (règle n° 2 : {@code Wood_Burnt_*}, {@code Wood_Blackwood_*}, {@code Plant_Leaves_Burnt},
 * {@code Soil_Grass_Burnt}, {@code Soil_Ash}, comme la ferme brûlée du Comté du mod Vampires), une partie du bois et des
 * feuilles s'effondre, les plantes et le mobilier disparaissent. Les coffres et autres conteneurs restent toujours
 * (les objets des joueurs ne disparaissent jamais).
 */
public final class Burning {

    /** Blocs vanilla posés par l'incendie et les chantiers ({@link SiteStyle}) (vérifiés par validateAssets dans les blocs du jeu). */
    public static final List<String> REQUIRED_BLOCKS = Stream.concat(Stream.of(
            "Wood_Burnt_Trunk", "Wood_Burnt_Trunk_Full", "Wood_Burnt_Branch_Corner", "Wood_Burnt_Branch_Long",
            "Wood_Burnt_Branch_Short", "Wood_Burnt_Roots", "Wood_Blackwood_Planks", "Wood_Blackwood_Planks_Half",
            "Wood_Blackwood_Beam", "Wood_Blackwood_Fence", "Wood_Blackwood_Stairs", "Wood_Blackwood_Roof",
            "Plant_Leaves_Burnt", "Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Soil_Ash"),
            SiteStyle.allBlocks().stream()).distinct().toList();

    /** Part du bois calciné qui s'effondre au-dessus de {@value #COLLAPSE_ABOVE} blocs. */
    private static final double COLLAPSE = 0.25;
    private static final int COLLAPSE_ABOVE = 3;
    /** Part des feuillages qui restent, noircis (le reste a brûlé). */
    private static final double LEAVES_KEPT = 0.45;

    private Burning() {
    }

    /**
     * Brûle l'emprise [x0, x1] x [z0, z1] du sol `ground` (ancre du prefab) jusqu'à `ground + height`. Rend le nombre de
     * blocs touchés.
     */
    public static int burn(World world, int x0, int x1, int z0, int z1, int ground, int height, long seed) {
        ChunkStore chunks = world.getChunkStore();
        Random random = new Random(seed);
        int changed = 0;
        for (int x = x0; x <= x1; x++) {
            for (int z = z0; z <= z1; z++) {
                for (int y = ground; y <= ground + height; y++) {
                    String name = Blocks.name(chunks, x, y, z);
                    if (name == null || (name.contains("Furniture_") && isContainer(world, x, y, z))) {
                        continue;
                    }
                    String to = charred(name, y - ground, random);
                    if (to != null && to.equals(name)) {
                        continue;
                    }
                    if (to != null && BlockType.getAssetMap().getAsset(to) == null) {
                        continue;
                    }
                    if (Blocks.set(chunks, x, y, z, to, to == null ? 0 : Blocks.rotation(chunks, x, y, z))) {
                        changed++;
                    }
                }
            }
        }
        return changed;
    }

    /**
     * Bloc calciné qui remplace `name` à `above` blocs au-dessus du sol : lui-même (inchangé), un autre id, ou null
     * (le bloc disparaît).
     */
    static String charred(String name, int above, Random random) {
        String base = name.startsWith("*") ? name.substring(1) : name;
        if (base.startsWith("Wood_Burnt_") || base.startsWith("Wood_Blackwood_")) {
            return name;
        }
        if (base.startsWith("Wood_")) {
            if (above > COLLAPSE_ABOVE && random.nextDouble() < COLLAPSE) {
                return null;
            }
            return charredWood(base);
        }
        if (base.startsWith("Plant_Leaves_")) {
            return random.nextDouble() < LEAVES_KEPT ? "Plant_Leaves_Burnt" : null;
        }
        if (base.startsWith("Plant_") || base.startsWith("Deco_")) {
            return null;
        }
        if (base.startsWith("Furniture_")) {
            // Le mobilier brûle ; quelques planches noircies en restent.
            return random.nextDouble() < 0.2 ? "Wood_Blackwood_Planks_Half" : null;
        }
        if (base.startsWith("Soil_Grass")) {
            return "Soil_Grass_Burnt";
        }
        if (base.equals("Soil_Leaves") || base.startsWith("Plant_Moss")) {
            return "Soil_Ash";
        }
        if (base.equals("Soil_Dirt")) {
            return "Soil_Dirt_Burnt";
        }
        return name;
    }

    /** Bois calciné de la même forme : tronc et branches en bois brûlé, planches et poutres en bois noir. */
    private static String charredWood(String base) {
        String rest = base.substring("Wood_".length());
        int cut = rest.indexOf('_');
        String part = cut < 0 ? "" : rest.substring(cut + 1);
        return switch (part) {
            case "Trunk", "Trunk_Full", "Branch_Corner", "Branch_Long", "Branch_Short", "Roots" -> "Wood_Burnt_" + part;
            case "Trunk_Half", "Planks_Half" -> "Wood_Blackwood_Planks_Half";
            case "Trunk_Stairs", "Stairs" -> "Wood_Blackwood_Stairs";
            case "Beam" -> "Wood_Blackwood_Beam";
            case "Fence" -> "Wood_Blackwood_Fence";
            default -> part.startsWith("Roof") ? "Wood_Blackwood_Roof" : "Wood_Blackwood_Planks";
        };
    }

    /** Vrai si le bloc porte un inventaire (coffre, armoire) : on n'y touche jamais. */
    public static boolean isContainer(World world, int x, int y, int z) {
        return BlockModule.getComponent(ItemContainerBlock.getComponentType(), world, x, y, z) != null;
    }
}
