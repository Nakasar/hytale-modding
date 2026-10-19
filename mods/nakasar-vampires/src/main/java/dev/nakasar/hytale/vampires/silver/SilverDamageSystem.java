package dev.nakasar.hytale.vampires.silver;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;
import dev.nakasar.hytale.vampires.purifying.PurifyingFireSystem;

import java.util.Set;

/**
 * L'argent contre les vampires : un coup d'arme en argent inflige {@value #MULTIPLIER} fois ses dégâts à un PNJ du
 * groupe {@value #VAMPIRE_GROUP} (Comte, Comtesse, rejetons).
 *
 * <ul>
 *   <li>Projectile ({@code Damage.ProjectileSource}) : compte s'il a été marqué au tir
 *       ({@link SilverProjectileSystems}), quelle que soit l'arme tenue à l'impact.</li>
 *   <li>Coup direct : compte si l'attaquant tient une arme en argent et que le coup vient d'une attaque d'arme. Les
 *       sorts de runes ({@code Ability2}, {@code Ability3}) et les dégâts sans interaction (effets, poison) ne
 *       comptent pas, même arme en argent en main.</li>
 * </ul>
 * L'argent infusé (tag {@code Material: Infused_Silver}) frappe à {@value #INFUSED_MULTIPLIER} les vampires et à
 * {@value #INFUSED_UNDEAD_MULTIPLIER} les autres morts-vivants du groupe {@value #UNDEAD_GROUP}.
 * Joueurs et PNJ (chasseurs de vampires) sont traités de la même façon. On multiplie avant les réductions d'armure et
 * de garde, comme si l'arme frappait deux fois plus fort, et après les filtres qui annulent ou rétablissent un coup.
 */
public final class SilverDamageSystem extends DamageEventSystem {

    public static final String VAMPIRE_GROUP = "Nakasar_Vampires";
    public static final float MULTIPLIER = 2f;
    /** Argent infusé (établi des chasseurs, niveau 3) : plus fort contre les vampires, et contre les autres morts-vivants. */
    public static final String UNDEAD_GROUP = PurifyingFireSystem.UNDEAD_GROUP;
    public static final float INFUSED_MULTIPLIER = 2.5f;
    public static final float INFUSED_UNDEAD_MULTIPLIER = 1.5f;

    /** Interactions qui ne sont pas des attaques de l'arme tenue. */
    private static final Set<InteractionType> NOT_WEAPON_ATTACKS = Set.of(
            InteractionType.Ability2, InteractionType.Ability3, InteractionType.EntityStatEffect);

    @SuppressWarnings("deprecation") // ArmorDamageReduction est déprécié mais toujours enregistré en 0.7.2
    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, AllegianceDamageFilter.class),
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
        if (attacker == null || target == null || attacker.equals(target)) {
            return;
        }
        Hit hit = silverHit(damage, source, attacker, buffer);
        if (hit == Hit.NONE) {
            return;
        }
        boolean infused = hit == Hit.INFUSED;
        if (Allegiances.inGroup(target, VAMPIRE_GROUP, buffer)) {
            damage.setAmount(damage.getAmount() * (infused ? INFUSED_MULTIPLIER : MULTIPLIER));
        } else if (infused && Allegiances.inGroup(target, UNDEAD_GROUP, buffer)) {
            damage.setAmount(damage.getAmount() * INFUSED_UNDEAD_MULTIPLIER);
        }
    }

    /**
     * Multiplicateur de l'argent contre un vampire pour ce coup : {@value #MULTIPLIER}, {@value #INFUSED_MULTIPLIER}
     * pour l'argent infusé, 1 sans argent. Lu pour les joueurs vampires ({@code vampirism.VampireDamageSystem}).
     */
    public static float vampireMultiplier(Damage damage, CommandBuffer<EntityStore> buffer) {
        if (damage.isCancelled() || !(damage.getSource() instanceof Damage.EntitySource source)
                || source.getRef() == null) {
            return 1f;
        }
        return switch (silverHit(damage, source, source.getRef(), buffer)) {
            case NONE -> 1f;
            case SILVER -> MULTIPLIER;
            case INFUSED -> INFUSED_MULTIPLIER;
        };
    }

    /** Ce qui a porté le coup : rien d'argent, de l'argent, ou de l'argent infusé. */
    private enum Hit { NONE, SILVER, INFUSED }

    private static Hit silverHit(Damage damage, Damage.EntitySource source, Ref<EntityStore> attacker,
                                 CommandBuffer<EntityStore> buffer) {
        if (source instanceof Damage.ProjectileSource projectile) {
            Ref<EntityStore> ref = projectile.getProjectile();
            if (!SilverWeapons.isSilverProjectile(ref)) {
                return Hit.NONE;
            }
            return SilverWeapons.isInfusedProjectile(ref) ? Hit.INFUSED : Hit.SILVER;
        }
        InteractionType type = damage.getMetaObject(Damage.INTERACTION_TYPE);
        if (type == null || NOT_WEAPON_ATTACKS.contains(type) || !attacker.isValid()) {
            return Hit.NONE;
        }
        ItemStack weapon = InventoryComponent.getItemInHand(buffer, attacker);
        if (!SilverWeapons.isSilver(weapon)) {
            return Hit.NONE;
        }
        return SilverWeapons.isInfused(weapon) ? Hit.INFUSED : Hit.SILVER;
    }
}
