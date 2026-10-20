package dev.nakasar.hytale.fractals.cliffside;

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
import dev.nakasar.hytale.fractals.hammer.Hammer;

import java.util.Set;

/**
 * Filtre des dégâts de la Falaise (avant les armures) :
 * <ul>
 *   <li>sceaux : tout coup est annulé ; un coup de joueur est remis à {@link Cliffside#onSealHit} (le marteau chargé
 *   les fissure) ;</li>
 *   <li>l'Archidevin : seuils de vie, transitions et mur anti-projectiles ({@link Archdiviner#filter}) ;</li>
 *   <li>un joueur à {@value #WEAK_STACKS} charges de Corruption ou plus ne fait que {@value #WEAK_FACTOR} de ses
 *   dégâts ;</li>
 *   <li>l'Archidevin en forme démoniaque frappe × 1,3 (le niveau, lui, est compté par
 *   {@link dev.nakasar.hytale.fractals.stage.StageDamageFilter}).</li>
 * </ul>
 */
public final class CliffsideDamageFilter extends DamageEventSystem {

    static final float WEAK_STACKS = 20f;
    static final float WEAK_FACTOR = 0.7f;
    static final float DEMON_FACTOR = 1.3f;

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
        if (!Cliffside.isCliffside(world)) {
            return;
        }
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        Ref<EntityStore> attacker = damage.getSource() instanceof Damage.EntitySource source ? source.getRef() : null;
        if (attacker != null && !attacker.isValid()) {
            attacker = null;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        String role = npc == null ? null : npc.getRoleName();
        if (Cliffside.SEAL_ROLE.equals(role)) {
            damage.setCancelled(true);
            if (attacker != null && buffer.getComponent(attacker, PlayerRef.getComponentType()) != null) {
                Ref<EntityStore> player = attacker;
                world.execute(() -> Cliffside.onSealHit(world, victim, player));
            }
            return;
        }
        if (Archdiviner.ROLE.equals(role)) {
            Cliffside.state(world).boss.filter(world, store, victim, damage);
            if (damage.isCancelled()) {
                return;
            }
        }
        if (attacker == null) {
            return;
        }
        PlayerRef player = buffer.getComponent(attacker, PlayerRef.getComponentType());
        if (player != null && Hammer.stacks(player.getUuid()) >= WEAK_STACKS) {
            damage.setAmount(damage.getAmount() * WEAK_FACTOR);
        }
        if (buffer.getComponent(victim, PlayerRef.getComponentType()) != null) {
            NPCEntity source = buffer.getComponent(attacker, NPCEntity.getComponentType());
            if (source != null && Archdiviner.ROLE.equals(source.getRoleName()) && Cliffside.state(world).boss.demon) {
                damage.setAmount(damage.getAmount() * DEMON_FACTOR);
            }
        }
    }
}
