package dev.nakasar.hytale.vampires.elite;

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
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;

import java.util.Map;
import java.util.Set;

/**
 * Faiblesse ou immunité au feu, par groupe de PNJ, sur les dégâts de cause {@code Fire} ou d'une cause qui en hérite
 * (brûlure, lave, bâton de feu…). Aucun champ de rôle ne règle une résistance par type de dégâts ; on règle donc le
 * montant pendant le filtrage des dégâts, après les filtres de camp (un coup annulé reste annulé) :
 * <ul>
 *   <li>{@value #WEAK} (citrouille géante et ses vrilles) : dégâts de feu doublés ;</li>
 *   <li>{@value #IMMUNE} (armure enchantée et ses rouages) : aucun dégât de feu.</li>
 * </ul>
 */
public final class FireAffinitySystem extends DamageEventSystem {

    public static final String WEAK = "Nakasar_Pumpkin_Patch";
    public static final String IMMUNE = "Nakasar_Fire_Immune";
    /** Multiplicateur des dégâts de feu par groupe ; 0 annule le coup. */
    private static final Map<String, Float> MULTIPLIERS = Map.of(WEAK, 2f, IMMUNE, 0f);

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, AllegianceDamageFilter.class));

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
        if (damage.isCancelled()) {
            return;
        }
        DamageCause fire = DamageCause.getAssetMap().getAsset("Fire");
        DamageCause cause = damage.getCause();
        if (fire == null || cause == null || !cause.isOrInherits(fire)) {
            return;
        }
        Ref<EntityStore> target = chunk.getReferenceTo(index);
        for (Map.Entry<String, Float> entry : MULTIPLIERS.entrySet()) {
            int group = NPCGroup.getAssetMap().getIndexOrDefault(entry.getKey(), Integer.MIN_VALUE);
            if (group == Integer.MIN_VALUE || !WorldSupport.isGroupMember(Integer.MIN_VALUE, target, group, buffer)) {
                continue;
            }
            if (entry.getValue() == 0f) {
                damage.setCancelled(true);
            } else {
                damage.setAmount(damage.getAmount() * entry.getValue());
            }
            return;
        }
    }
}
