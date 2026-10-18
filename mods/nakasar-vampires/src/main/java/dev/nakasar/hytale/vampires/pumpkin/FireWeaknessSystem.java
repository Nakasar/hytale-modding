package dev.nakasar.hytale.vampires.pumpkin;

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

import java.util.Set;

/**
 * La citrouille géante et ses vrilles (groupe {@value #GROUP}) prennent {@value #MULTIPLIER} fois les dégâts de feu
 * (cause {@code Fire} ou une cause qui en hérite : brûlure, lave, bâton de feu…). Aucun champ de rôle ne règle une
 * faiblesse par type de dégâts ; on multiplie donc le montant pendant le filtrage des dégâts, après les filtres de
 * camp (un coup annulé reste annulé).
 */
public final class FireWeaknessSystem extends DamageEventSystem {

    public static final String GROUP = "Nakasar_Pumpkin_Patch";
    private static final float MULTIPLIER = 2f;

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
        int group = NPCGroup.getAssetMap().getIndexOrDefault(GROUP, Integer.MIN_VALUE);
        Ref<EntityStore> target = chunk.getReferenceTo(index);
        if (group != Integer.MIN_VALUE && WorldSupport.isGroupMember(Integer.MIN_VALUE, target, group, buffer)) {
            damage.setAmount(damage.getAmount() * MULTIPLIER);
        }
    }
}
