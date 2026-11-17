package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import dev.nakasar.hytale.peuples.village.People;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Les marchandises des routes commerciales (proposition « routes commerciales et luxes », Kevin, 16 novembre 2026) :
 * toute ressource s'échange ; chacune a une classe (commune, fine, luxe) qui fixe la taille d'un chargement par case
 * et son poids dans l'équilibre d'une route. Les neuf luxes sont des objets vanilla ; cinq ont un terroir (un peuple
 * qui les produit dès le palier 2). Les Kweebecs n'échangent aucun métal.
 */
public final class TradeGoods {

    /** Classe d'une marchandise : chargements par niveau de route (I, II, III) et poids. */
    public enum Grade {
        COMMON(new int[] {16, 24, 32}, 1),
        FINE(new int[] {6, 9, 12}, 2),
        LUXURY(new int[] {2, 3, 4}, 3);

        private final int[] loads;
        private final int weight;

        Grade(int[] loads, int weight) {
            this.loads = loads;
            this.weight = weight;
        }

        /** Chargement d'une case pour une route du niveau `level` (1 à 3). */
        public int load(int level) {
            return loads[Math.max(0, Math.min(loads.length - 1, level - 1))];
        }

        public int weight() {
            return weight;
        }

        public String key() {
            return name().toLowerCase(Locale.ROOT);
        }
    }

    /** Un luxe : son objet vanilla, son terroir (ou null), et son nom court (clé de langue). */
    public record Luxury(String item, People terroir, String key) {
    }

    /** Les neuf luxes, dans l'ordre de l'onglet Commerce. */
    public static final List<Luxury> LUXURIES = List.of(
            new Luxury("Plant_Fruit_Azure", People.KWEEBEC, "azure"),
            new Luxury("Ingredient_Leather_Heavy", People.TRORK, "leather"),
            new Luxury("Ingredient_Spices", People.FERAN, "spices"),
            new Luxury("Food_Cheese", People.RENONCE, "cheese"),
            new Luxury("Ingredient_Crystal_Purple", People.SLOTHIAN, "crystals"),
            new Luxury("Ingredient_Bar_Gold", null, "gold"),
            new Luxury("Ingredient_Bolt_Silk", null, "silk"),
            new Luxury("Food_Fish_Raw_Rare", null, "fish"),
            new Luxury("Food_Pie_Apple", null, "pastries"));

    /** Marques d'une marchandise fine (planches, briques, cuirs, lingots, farine, essences, outils, armes, mets cuisinés...). */
    private static final String[] FINE_MARKS = {"Planks", "Beam", "Brick", "Leather", "Ingredient_Bar_", "Flour", "Dough", "Essence",
            "Ingredient_Bolt_", "Potion_", "Weapon_", "Tool_", "Armor_", "Hide_Medium", "Hide_Heavy", "Marble", "Quartzite", "Calcite",
            "Food_Bread", "Food_Pie", "Food_Kebab", "Food_Salad", "_Cooked", "_Grilled", "_Uncommon", "Seeds_Wheat_Eternal",
            "Seeds_Tomato_Eternal", "Crop_Health2", "Crop_Mana2", "Crop_Stamina2", "Crop_Health3", "Crop_Mana3", "Crop_Stamina3",
            "Ingredient_Strap_", "Ingredient_Charcoal", "Furniture_"};
    /** Marques du métal (Kweebecs : jamais). */
    private static final String[] METALS = {"Copper", "Iron", "Bronze", "Silver", "Gold", "Cobalt", "Thorium", "Adamantite", "Mithril",
            "Onyxium", "Prisma", "Steel"};

    private TradeGoods() {
    }

    /** Le luxe de cet objet, ou null. */
    public static Luxury luxury(String item) {
        for (Luxury l : LUXURIES) {
            if (l.item().equals(item)) {
                return l;
            }
        }
        return null;
    }

    public static boolean isLuxury(String item) {
        return luxury(item) != null;
    }

    /** Le luxe du terroir de ce peuple (ou null). */
    public static Luxury terroir(People people) {
        for (Luxury l : LUXURIES) {
            if (l.terroir() == people) {
                return l;
            }
        }
        return null;
    }

    public static Grade grade(String item) {
        if (item == null) {
            return Grade.COMMON;
        }
        if (isLuxury(item)) {
            return Grade.LUXURY;
        }
        for (String m : FINE_MARKS) {
            if (item.contains(m)) {
                return Grade.FINE;
            }
        }
        return Grade.COMMON;
    }

    /** Vrai si l'objet est (ou contient) du métal : minerai, lingot, outil ou arme de métal. */
    public static boolean isMetal(String item) {
        if (item == null) {
            return false;
        }
        if (item.startsWith("Ore_") || item.startsWith("Ingredient_Bar_") || item.startsWith("Ingredient_Stud_")) {
            return true;
        }
        if (item.startsWith("Tool_") || item.startsWith("Weapon_") || item.startsWith("Armor_") || item.startsWith("Rock_Gold")) {
            for (String m : METALS) {
                if (item.contains(m)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** Ce peuple peut-il recevoir ou envoyer cet objet ? (Kweebecs : aucun métal.) */
    public static boolean allowed(People people, String item) {
        return item != null && !item.startsWith("Nakasar_") && !(people == People.KWEEBEC && isMetal(item));
    }

    /** Les objets des luxes, pour la validation hors ligne (ValidateAssets). */
    public static List<String> luxuryItems() {
        List<String> out = new ArrayList<>();
        for (Luxury l : LUXURIES) {
            out.add(l.item());
        }
        return Collections.unmodifiableList(out);
    }

    /** Clé de langue du nom d'un objet vanilla. */
    public static String itemKey(String item) {
        return "server.items." + item + ".name";
    }

    /** Quantité de l'objet dans le conteneur. */
    public static int stock(ItemContainer chest, String item) {
        int n = 0;
        for (short slot = 0; slot < chest.getCapacity(); slot++) {
            ItemStack stack = chest.getItemStack(slot);
            if (!ItemStack.isEmpty(stack) && item.equals(stack.getItemId())) {
                n += stack.getQuantity();
            }
        }
        return n;
    }
}
