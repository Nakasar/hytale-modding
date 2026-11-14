package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;

/** Effets de statut et dégâts d'environnement des zones (copie de {@code combat/Hurt} du mod Fractales). */
final class Effects {

    private Effects() {
    }

    /** Retire `part` (0..1) des PV max, en dégâts d'environnement `causeId`. */
    static void percent(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, float part, String causeId) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        DamageCause cause = DamageCause.getAssetMap().getAsset(causeId);
        if (health == null || part <= 0f) {
            return;
        }
        if (cause == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : cause de dégâts '%s' introuvable", causeId);
            return;
        }
        DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource(causeId), cause, health.getMax() * part));
    }

    /** Pose l'effet `effectId` pendant `seconds` secondes (remplace le même effet en cours). */
    static void apply(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId, float seconds) {
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effect == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : effet '%s' introuvable", effectId);
        } else if (effects != null) {
            effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, store);
        }
    }

    static void clear(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (index >= 0 && effects != null && effects.hasEffect(index)) {
            effects.removeEffect(ref, index, store);
        }
    }

    static boolean has(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        return index >= 0 && effects != null && effects.hasEffect(index);
    }
}
