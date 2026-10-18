package dev.nakasar.hytale.vampires.allegiance;

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
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.role.support.CombatSupport;
import com.hypixel.hytale.server.npc.systems.NPCDamageSystems;
import dev.nakasar.hytale.vampires.domination.Dominations;

import java.util.Set;

/**
 * Les dégâts entre camps (coups directs et projectiles : {@code Damage.ProjectileSource} est une
 * {@code EntitySource} dont la référence est le tireur). Tourne dans le groupe de filtrage des dégâts :
 * <ol>
 *   <li>une victime de la Domination (joueur ou PNJ) ne blesse pas son dominateur ;</li>
 *   <li>un PNJ dominé et ses anciens alliés se blessent de nouveau : le filtre vanilla des rôles
 *       ({@code DisableDamageGroups}) les protégeait, on lève son annulation. On passe juste après lui et avant
 *       les filtres d'invulnérabilité et de configuration du monde, qui peuvent donc toujours annuler ;</li>
 *   <li>deux mobs du fragment qui ne sont pas en guerre ne se blessent pas (flèche perdue, coup de zone).</li>
 * </ol>
 */
public final class AllegianceDamageFilter extends DamageEventSystem {

    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, NPCDamageSystems.FilterDamageSystem.class),
            new SystemDependency<>(Order.BEFORE, DamageSystems.FilterUnkillable.class),
            new SystemDependency<>(Order.BEFORE, DamageSystems.FilterNPCWorldConfig.class));

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
        return Query.any();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (!(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> attacker = source.getRef();
        Ref<EntityStore> target = chunk.getReferenceTo(index);
        if (attacker == null || target == null || !attacker.isValid() || attacker.equals(target)) {
            return;
        }
        if (Dominations.isDominatedBy(attacker, target)) {
            damage.setCancelled(true);
            return;
        }
        if (!Allegiances.isNpc(attacker, buffer) || !Allegiances.isNpc(target, buffer)) {
            return;
        }
        Ref<EntityStore> attackerMaster = Dominations.dominatorOf(attacker);
        Ref<EntityStore> targetMaster = Dominations.dominatorOf(target);
        if ((attackerMaster == null) != (targetMaster == null)) {
            // Un seul des deux a changé de camp : anciens alliés, désormais ennemis.
            if (damage.isCancelled() && Allegiances.wereAllies(attacker, target, buffer)
                    && !CombatSupport.get(target, buffer).getCanCauseDamage(target, attacker, buffer)) {
                damage.setCancelled(false);
            }
        } else if (attackerMaster == null && Allegiances.bothInFaction(attacker, target, buffer)) {
            damage.setCancelled(true);
        }
    }
}
