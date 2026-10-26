package dev.nakasar.hytale.fractals.support;

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
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.potion.MistPotionDamageFilter;
import dev.nakasar.hytale.fractals.progress.Agony;
import org.joml.Vector3d;

import java.util.Set;

/**
 * Les runes et objets de soutien dans les dégâts, après les potions des Brumes (filtre, avant les armures) :
 * <ul>
 *   <li>Bannière de la guilde : les joueurs dans son rayon infligent {@value #MIGHT} de plus (Puissance) ou subissent
 *   {@value #GUARD} de moins (Garde), agonie exclue ;</li>
 *   <li>Égide des Brumes : le prochain coup <i>direct</i> d'un PNJ (corps à corps, projectile, coup de zone d'un boss)
 *   est annulé et l'égide tombe. L'agonie, les dégâts d'effets (poison, brûlure), les pièges et les dégâts du Java des
 *   fractales (rayons, explosions de mécanique, chutes) ne viennent pas d'un PNJ et passent ;</li>
 *   <li>Sursis : un coup qui tuerait un joueur couvert le laisse à 1 PV, une fois par lancer, puis
 *   {@value Skills#REPRIEVE_SPARE} s sans aucun dégât.</li>
 * </ul>
 */
public final class SupportDamageFilter extends DamageEventSystem {

    public static final float MIGHT = 0.10f;
    public static final float GUARD = 0.10f;

    private static final Set<Dependency<EntityStore>> DEPENDENCIES = Set.of(
            new SystemDependency<>(Order.AFTER, MistPotionDamageFilter.class));

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
    @SuppressWarnings("deprecation")
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || damage.getAmount() <= 0f) {
            return;
        }
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        boolean agony = damage.getCause() != null && Agony.DAMAGE_CAUSE.equals(damage.getCause().getId());
        Ref<EntityStore> attacker = damage.getSource() instanceof Damage.EntitySource source ? source.getRef()
                : damage.getSource() instanceof ActiveEntityEffect effect ? effect.getOwner() : null;
        boolean victimIsPlayer = buffer.getComponent(victim, PlayerRef.getComponentType()) != null;
        long now = System.nanoTime();

        // Bannière : bonus du porteur de coups, réduction pour le joueur touché.
        World world = store.getExternalData().getWorld();
        SupportStates.Banner banner = SupportStates.BANNERS.get(world);
        if (banner != null && now >= banner.until()) {
            SupportStates.BANNERS.remove(world, banner);
            banner = null;
        }
        if (banner != null) {
            if (banner.might() && attacker != null && attacker.isValid()
                    && buffer.getComponent(attacker, PlayerRef.getComponentType()) != null && inBanner(buffer, attacker, banner)) {
                damage.setAmount(damage.getAmount() * (1f + MIGHT));
            }
            if (!banner.might() && victimIsPlayer && !agony && inBanner(buffer, victim, banner)) {
                damage.setAmount(damage.getAmount() * (1f - GUARD));
            }
        }
        if (!victimIsPlayer) {
            return;
        }

        // Sursis : invulnérable quelques instants après avoir été sauvé.
        if (SupportStates.active(SupportStates.SPARED, victim, now)) {
            damage.setCancelled(true);
            return;
        }

        // Égide : seulement un coup direct d'un PNJ.
        boolean direct = damage.getSource() instanceof Damage.EntitySource && attacker != null && attacker.isValid()
                && buffer.getComponent(attacker, NPCEntity.getComponentType()) != null && !agony;
        if (direct && SupportStates.active(SupportStates.AEGIS, victim, now)) {
            SupportStates.AEGIS.remove(victim);
            damage.setCancelled(true);
            world.execute(() -> {
                if (victim.isValid()) {
                    Store<EntityStore> s = world.getEntityStore().getStore();
                    dev.nakasar.hytale.fractals.combat.Hurt.clear(s, victim, Skills.EFFECT_AEGIS);
                    Vector3d at = Telegraphs.position(s, victim);
                    if (at != null) {
                        Telegraphs.particle(s, Skills.FX_WARD, new Vector3d(at).add(0, 1, 0), 1.2f);
                    }
                }
            });
            return;
        }

        // Sursis : un coup mortel.
        SupportStates.Reprieve reprieve = SupportStates.REPRIEVE.get(victim);
        if (reprieve != null && now >= reprieve.until) {
            SupportStates.REPRIEVE.remove(victim);
            reprieve = null;
        }
        if (reprieve != null && !reprieve.used) {
            EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
            EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
            if (health != null && health.get() - damage.getAmount() <= 0f) {
                reprieve.used = true;
                damage.setAmount(Math.max(0f, health.get() - 1f));
                SupportStates.SPARED.put(victim, now + Telegraphs.seconds(Skills.REPRIEVE_SPARE));
                world.execute(() -> {
                    if (victim.isValid()) {
                        Store<EntityStore> s = world.getEntityStore().getStore();
                        dev.nakasar.hytale.fractals.combat.Hurt.clear(s, victim, Skills.EFFECT_REPRIEVE);
                        dev.nakasar.hytale.fractals.combat.Hurt.effect(s, victim, Skills.EFFECT_SPARED, Skills.REPRIEVE_SPARE);
                        Support.tell(s, victim, "reprieve.saved");
                    }
                });
            }
        }
    }

    private static boolean inBanner(CommandBuffer<EntityStore> buffer, Ref<EntityStore> ref, SupportStates.Banner banner) {
        var transform = buffer.getComponent(ref, com.hypixel.hytale.server.core.modules.entity.component.TransformComponent.getComponentType());
        return transform != null && Telegraphs.inCircle(transform.getPosition(), banner.at(), banner.radius());
    }
}
