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

    private static final Set<Ref<EntityStore>> SILVER_PROJECTILES = ConcurrentHashMap.newKeySet();

    private SilverWeapons() {
    }

    /** Vrai si l'objet est une arme en argent. */
    public static boolean isSilver(ItemStack stack) {
        if (ItemStack.isEmpty(stack)) {
            return false;
        }
        if (VANILLA_SILVER.contains(stack.getItemId())) {
            return true;
        }
        Item item = stack.getItem();
        if (item == null || item.getData() == null || item.getData().getRawTags() == null) {
            return false;
        }
        Map<String, String[]> tags = item.getData().getRawTags();
        String[] materials = tags.get("Material");
        return materials != null && Arrays.asList(materials).contains("Silver");
    }

    static void markProjectile(Ref<EntityStore> projectile) {
        SILVER_PROJECTILES.removeIf(ref -> !ref.isValid());
        SILVER_PROJECTILES.add(projectile);
    }

    static boolean isSilverProjectile(Ref<EntityStore> projectile) {
        return projectile != null && SILVER_PROJECTILES.contains(projectile);
    }

    public static void clearAll() {
        SILVER_PROJECTILES.clear();
    }
}
