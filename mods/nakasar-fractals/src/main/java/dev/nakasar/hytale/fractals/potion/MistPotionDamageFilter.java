package dev.nakasar.hytale.fractals.potion;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.entity.effect.ActiveEntityEffect;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.potion.MistPotions.Kind;
import dev.nakasar.hytale.fractals.progress.Agony;

import java.util.Set;

/**
 * Potions des Brumes dans les dégâts (avant les armures), dans une fractale seulement :
 * <ul>
 *   <li>Offensive : les coups d'un joueur, et les dégâts des effets qu'il a posés (états), × (1 + 3 % par pile) ;</li>
 *   <li>Défensive : les dégâts reçus par un joueur × (1 - 5 % par pile), sauf l'agonie (seule la résistance la
 *   réduit, comme dans GW2).</li>
 * </ul>
 */
public final class MistPotionDamageFilter extends DamageEventSystem {

    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.BEFORE, DamageSystems.ArmorDamageReduction.class));

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
        return EntityStatMap.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || !MistPotions.active(store.getExternalData().getWorld())) {
            return;
        }
        Ref<EntityStore> attacker = damage.getSource() instanceof Damage.EntitySource source ? source.getRef()
                : damage.getSource() instanceof ActiveEntityEffect effect ? effect.getOwner() : null;
        int offensive = MistPotions.stacks(buffer, attacker, Kind.OFFENSIVE);
        if (offensive > 0) {
            damage.setAmount(damage.getAmount() * (1f + Kind.OFFENSIVE.perStack * offensive));
        }
        MistPotionState victim = chunk.getComponent(index, MistPotionState.getComponentType());
        int defensive = victim == null ? 0 : victim.stacks(Kind.DEFENSIVE);
        if (defensive > 0 && (damage.getCause() == null || !Agony.DAMAGE_CAUSE.equals(damage.getCause().getId()))) {
            damage.setAmount(damage.getAmount() * (1f - Kind.DEFENSIVE.perStack * defensive));
        }
    }
}
