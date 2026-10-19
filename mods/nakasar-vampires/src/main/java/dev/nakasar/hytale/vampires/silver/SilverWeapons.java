package dev.nakasar.hytale.vampires.silver;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Arrays;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les armes en argent (tag {@code Material: Silver}, voir {@code tools/generate_silver_weapons.py}) et les
 * projectiles tirés ou lancés avec l'une d'elles.
 *
 * <p>Un projectile est marqué à son départ, d'après l'arme que tient le tireur à ce moment : l'arme qu'il tient
 * à l'impact peut être une autre. Les marques des projectiles disparus sont purgées à chaque nouveau tir.
 */
public final class SilverWeapons {

    /** L'épée en acier argenté vanilla compte aussi comme une arme en argent. */
    private static final Set<String> VANILLA_SILVER = Set.of("Weapon_Sword_Silversteel");

    /** Projectiles en argent, avec vrai s'ils sont en argent infusé (tag {@code Material: Infused_Silver}). */
    private static final Map<Ref<EntityStore>, Boolean> SILVER_PROJECTILES = new ConcurrentHashMap<>();

    private SilverWeapons() {
    }

    /** Vrai si l'objet est une arme en argent. */
    public static boolean isSilver(ItemStack stack) {
        if (ItemStack.isEmpty(stack)) {
            return false;
        }
        return VANILLA_SILVER.contains(stack.getItemId()) || hasMaterial(stack, "Silver");
    }

    /** Vrai si l'objet est une arme en argent infusé (établi des chasseurs, {@code tools/generate_infused_weapons.py}). */
    public static boolean isInfused(ItemStack stack) {
        return !ItemStack.isEmpty(stack) && hasMaterial(stack, "Infused_Silver");
    }

    private static boolean hasMaterial(ItemStack stack, String material) {
        Item item = stack.getItem();
        if (item == null || item.getData() == null || item.getData().getRawTags() == null) {
            return false;
        }
        Map<String, String[]> tags = item.getData().getRawTags();
        String[] materials = tags.get("Material");
        return materials != null && Arrays.asList(materials).contains(material);
    }

    static void markProjectile(Ref<EntityStore> projectile, boolean infused) {
        SILVER_PROJECTILES.keySet().removeIf(ref -> !ref.isValid());
        SILVER_PROJECTILES.put(projectile, infused);
    }

    static boolean isInfusedProjectile(Ref<EntityStore> projectile) {
        return projectile != null && SILVER_PROJECTILES.getOrDefault(projectile, false);
    }

    static boolean isSilverProjectile(Ref<EntityStore> projectile) {
        return projectile != null && SILVER_PROJECTILES.containsKey(projectile);
    }

    public static void clearAll() {
        SILVER_PROJECTILES.clear();
    }
}
