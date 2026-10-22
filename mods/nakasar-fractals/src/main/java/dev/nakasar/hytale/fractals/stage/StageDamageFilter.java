package dev.nakasar.hytale.fractals.stage;

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
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.HitShield;
import dev.nakasar.hytale.fractals.instability.Instabilities;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import dev.nakasar.hytale.fractals.party.FractalRuns;

import java.util.Set;

/**
 * Filtre commun des dégâts dans les fractales (avant les armures) :
 * <ul>
 *   <li>boucliers à compteur de coups ({@link HitShield}) : le coup est annulé, un coup de joueur en retire un ;</li>
 *   <li>le déroulé de la fractale ({@link FractalStage#filter}) : phases, invulnérabilités, charges ;</li>
 *   <li>les ennemis frappent plus fort avec le niveau : × (1 + niveau / 150) sur les joueurs ;</li>
 *   <li>les instabilités du jour ({@link Instabilities#filter}).</li>
 * </ul>
 */
public final class StageDamageFilter extends DamageEventSystem {

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
        if (damage.isCancelled()) {
            return;
        }
        World world = store.getExternalData().getWorld();
        if (FractalCatalog.fractalOf(world) == null) {
            return;
        }
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        Ref<EntityStore> attacker = damage.getSource() instanceof Damage.EntitySource source ? source.getRef() : null;
        if (attacker != null && !attacker.isValid()) {
            attacker = null;
        }
        boolean byPlayer = attacker != null && buffer.getComponent(attacker, PlayerRef.getComponentType()) != null;
        if (HitShield.absorb(world, store, victim, byPlayer, damage)) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        FractalStage stage = Stages.of(world);
        if (stage != null) {
            stage.filter(world, store, buffer, victim, npc == null ? null : npc.getRoleName(), attacker, damage);
            if (damage.isCancelled()) {
                return;
            }
        }
        boolean toPlayer = buffer.getComponent(victim, PlayerRef.getComponentType()) != null;
        boolean byFoe = attacker != null && Foes.inGroup(attacker, buffer);
        if (toPlayer && byFoe) {
            damage.setAmount(damage.getAmount() * (1f + FractalRuns.level(world) / 150f));
        }
        Instabilities.filter(world, buffer, victim, toPlayer, attacker, byPlayer, byFoe, damage);
    }
}
