package dev.nakasar.hytale.vampires.vampirism;

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
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;
import dev.nakasar.hytale.vampires.silver.SilverDamageSystem;

import java.util.Set;

/**
 * Les dégâts reçus et portés par un joueur vampire.
 *
 * <ul>
 *   <li><b>Argent</b> : une arme en argent (ou son projectile) lui inflige {@value SilverDamageSystem#MULTIPLIER} fois
 *       ses dégâts, comme aux vampires du Comté.</li>
 *   <li><b>Soleil</b> : tant qu'il le subit, il prend jusqu'à {@value #SUN_VULNERABILITY} fois plus de dégâts de
 *       toute source, selon l'intensité ({@link Vampire#getSun()}).</li>
 *   <li><b>Malus de vitesse d'attaque</b> (soleil ou affamé) : le serveur ne peut pas ralentir une attaque (le client
 *       la joue lui-même) ; un coup porté trop tôt après le précédent perd donc des dégâts, comme une attaque
 *       qui n'a pas eu le temps de reprendre son élan. Il faut {@value #RECOVERY_SUN} s en plein soleil et
 *       {@value #RECOVERY_STARVING} s affamé (le plus long des deux) pour frapper à pleine force ; un coup porté
 *       aussitôt ne fait que {@value #MIN_FACTOR} fois ses dégâts. Les cibles d'un même coup (balayage) comptent
 *       ensemble.</li>
 * </ul>
 * Multiplié avant les réductions d'armure et de garde, après les filtres qui annulent un coup, comme l'argent.
 */
public final class VampireDamageSystem extends DamageEventSystem {

    static final float SUN_VULNERABILITY = 1.5f;
    static final float RECOVERY_SUN = 0.9f;
    static final float RECOVERY_STARVING = 0.7f;
    static final float MIN_FACTOR = 0.3f;
    /** Coups reçus dans cet intervalle (ms) : même attaque, plusieurs cibles. */
    private static final long SAME_SWING_MS = 60;

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
        return EntityStatMap.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled()) {
            return;
        }
        Ref<EntityStore> target = chunk.getReferenceTo(index);
        Vampire victim = Vampires.of(target, buffer);
        if (victim != null) {
            float multiplier = SilverDamageSystem.vampireMultiplier(damage, buffer);
            if (!isOwnBurn(damage)) {
                multiplier *= 1f + (SUN_VULNERABILITY - 1f) * victim.sun;
            }
            damage.setAmount(damage.getAmount() * multiplier);
        }

        if (damage.getAmount() > 0f && damage.getSource() instanceof Damage.EntitySource source && !(source instanceof Damage.ProjectileSource)
                && damage.getMetaObject(Damage.INTERACTION_TYPE) != null) {
            Ref<EntityStore> attackerRef = source.getRef();
            Vampire attacker = attackerRef == null || attackerRef.equals(target) ? null : Vampires.of(attackerRef, buffer);
            if (attacker != null) {
                damage.setAmount(damage.getAmount() * attackFactor(attacker));
            }
        }
    }

    /** Brûlure du soleil ou de la lumière purificatrice : déjà dosée par {@link VampireSystem}, pas amplifiée. */
    private static boolean isOwnBurn(Damage damage) {
        int cause = damage.getDamageCauseIndex();
        return cause == DamageCause.getAssetMap().getIndexOrDefault(VampireSystem.SUN_CAUSE, -2)
                || cause == DamageCause.getAssetMap().getIndexOrDefault(VampireSystem.PURIFYING_CAUSE, -2);
    }

    /** Part des dégâts d'un coup du vampire, selon le temps écoulé depuis son coup précédent. */
    private static float attackFactor(Vampire attacker) {
        float recovery = Math.max(RECOVERY_SUN * attacker.sun,
                attacker.getStage() == BloodStage.STARVING ? RECOVERY_STARVING : 0f);
        long now = System.currentTimeMillis();
        long elapsedMs = now - attacker.lastHitMillis;
        if (elapsedMs < SAME_SWING_MS) {
            return attacker.lastHitFactor;
        }
        attacker.lastHitMillis = now;
        float factor = recovery <= 0f ? 1f
                : Math.max(MIN_FACTOR, Math.min(1f, elapsedMs / 1000f / recovery));
        attacker.lastHitFactor = factor;
        return factor;
    }
}
