package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.effect.ActiveEntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.FractalsPlugin;

/** Dégâts en part des PV max et effets de statut posés par le Java des fractales (pièges, marteau, cages). */
public final class Hurt {

    private Hurt() {
    }

    /** Retire `part` (0..1) des PV max de l'entité, en dégâts {@code causeId} (source : le piège {@code causeId}). */
    public static void percent(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, float part, String causeId) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || part <= 0f) {
            return;
        }
        amount(store, ref, health.getMax() * part, causeId);
    }

    public static void amount(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, float amount, String causeId) {
        DamageCause cause = DamageCause.getAssetMap().getAsset(causeId);
        if (cause == null) {
            FractalsPlugin.get().getLogger().atWarning().log("Cause de dégâts '%s' introuvable", causeId);
            return;
        }
        DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource(causeId), cause, amount));
    }

    /** Pose l'effet `effectId` pendant `seconds` secondes (remplace le même effet en cours). */
    public static void effect(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId, float seconds) {
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effect == null) {
            FractalsPlugin.get().getLogger().atWarning().log("Effet '%s' introuvable", effectId);
        } else if (effects != null) {
            effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, store);
        }
    }

    /** Retire l'effet `effectId` s'il est actif (copie de {@code Vampires.removeEffect}). */
    public static void clear(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (index >= 0 && effects != null && effects.hasEffect(index)) {
            effects.removeEffect(ref, index, store);
        }
    }

    /** Secondes restantes de l'effet `effectId` sur l'entité (-1 s'il n'est pas actif). */
    public static float remaining(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        ActiveEntityEffect effect = index < 0 || effects == null ? null : effects.getActiveEffects().get(index);
        return effect == null ? -1f : effect.getRemainingDuration();
    }

    public static boolean has(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        return index >= 0 && effects != null && effects.hasEffect(index);
    }

    /** Part de vie restante (0..1), 0 si l'entité n'a pas de vie. */
    public static float healthFraction(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        return health == null ? 0f : health.get() / Math.max(1f, health.getMax());
    }
}
