package dev.nakasar.hytale.vampires.silver;

import com.hypixel.hytale.builtin.tagset.config.NPCGroup;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;

import java.util.Map;
import java.util.Set;

/**
 * L'argent contre les vampires : un coup porté avec une arme en argent (tag {@code Material: Silver}, voir
 * {@code tools/generate_silver_weapons.py}) inflige {@value #MULTIPLIER} fois ses dégâts à un PNJ du groupe
 * {@value #VAMPIRE_GROUP} (Comte, Comtesse, rejetons).
 *
 * <p>L'arme est celle que l'attaquant tient au moment du coup : pour une flèche ou une balle,
 * {@code Damage.ProjectileSource} désigne le tireur, qui tient encore son arc, son arbalète ou son tromblon. Joueurs
 * et PNJ (chasseurs de vampires) sont traités de la même façon. On multiplie avant les réductions d'armure et de
 * garde, comme si l'arme frappait deux fois plus fort.
 */
public final class SilverDamageSystem extends DamageEventSystem {

    public static final String VAMPIRE_GROUP = "Nakasar_Vampires";
    public static final float MULTIPLIER = 2f;

    /** L'épée en acier argenté vanilla compte aussi comme une arme en argent. */
    private static final Set<String> VANILLA_SILVER = Set.of("Weapon_Sword_Silversteel");

    @SuppressWarnings("deprecation") // ArmorDamageReduction est déprécié mais toujours enregistré en 0.7.2
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.BEFORE, DamageSystems.ArmorDamageReduction.class),
            new SystemDependency<>(Order.BEFORE, DamageSystems.WieldingDamageReduction.class));

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getFilterDamageGroup();
    }

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || !(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> attacker = source.getRef();
        Ref<EntityStore> target = chunk.getReferenceTo(index);
        if (attacker == null || target == null || !attacker.isValid() || attacker.equals(target)) {
            return;
        }
        if (isSilver(InventoryComponent.getItemInHand(buffer, attacker)) && isVampire(target, buffer)) {
            damage.setAmount(damage.getAmount() * MULTIPLIER);
        }
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
        if (item == null || item.getData() == null) {
            return false;
        }
        Map<String, String[]> tags = item.getData().getRawTags();
        String[] materials = tags == null ? null : tags.get("Material");
        if (materials != null) {
            for (String material : materials) {
                if ("Silver".equals(material)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static boolean isVampire(Ref<EntityStore> target, CommandBuffer<EntityStore> buffer) {
        int group = NPCGroup.getAssetMap().getIndexOrDefault(VAMPIRE_GROUP, Integer.MIN_VALUE);
        return group != Integer.MIN_VALUE && WorldSupport.isGroupMember(Integer.MIN_VALUE, target, group, buffer);
    }
}
