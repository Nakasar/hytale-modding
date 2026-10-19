package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;
import dev.nakasar.hytale.vampires.purifying.PurifyingFireSystem;
import dev.nakasar.hytale.vampires.silver.SilverDamageSystem;

/** Outils communs de la voie occulte : qui est vampire, qui a du sang, effets de statut. */
public final class Vampires {

    private Vampires() {
    }

    /** Le composant vampire du joueur, ou {@code null} s'il n'en est pas un. */
    public static Vampire of(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        return ref == null || !ref.isValid() || Vampire.getComponentType() == null
                ? null : accessor.getComponent(ref, Vampire.getComponentType());
    }

    public static boolean isVampire(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        return of(ref, accessor) != null;
    }

    /**
     * Vrai si l'entité est un être vivant dont on peut boire le sang : un joueur qui n'est pas vampire, ou un PNJ qui
     * n'est ni mort-vivant (groupe {@value PurifyingFireSystem#UNDEAD_GROUP}) ni vampire
     * (groupe {@value SilverDamageSystem#VAMPIRE_GROUP}). Il doit avoir de la vie et ne pas être mort.
     */
    public static boolean isLiving(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        if (ref == null || !ref.isValid() || accessor.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return false;
        }
        EntityStatMap stats = accessor.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || health.get() <= 0f) {
            return false;
        }
        if (accessor.getComponent(ref, Player.getComponentType()) != null) {
            return !isVampire(ref, accessor);
        }
        if (accessor.getComponent(ref, NPCEntity.getComponentType()) == null) {
            return false;
        }
        return !Allegiances.inGroup(ref, PurifyingFireSystem.UNDEAD_GROUP, accessor)
                && !Allegiances.inGroup(ref, SilverDamageSystem.VAMPIRE_GROUP, accessor);
    }

    /** Pose l'effet {@code effectId} pour {@code seconds} secondes (négatif : sans fin). Faux si l'effet manque. */
    static boolean applyEffect(Ref<EntityStore> ref, String effectId, float seconds,
                               ComponentAccessor<EntityStore> accessor) {
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
        EffectControllerComponent effects = accessor.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effect == null || effects == null) {
            if (effect == null) {
                VampiresPlugin.get().getLogger().atWarning().log("Voie occulte : effet '%s' introuvable", effectId);
            }
            return false;
        }
        int index = EntityEffect.getAssetMap().getIndex(effectId);
        if (seconds < 0f) {
            return effects.addInfiniteEffect(ref, index, effect, accessor);
        }
        return effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, accessor);
    }

    /** Retire l'effet {@code effectId} s'il est actif. */
    static void removeEffect(Ref<EntityStore> ref, String effectId, ComponentAccessor<EntityStore> accessor) {
        EffectControllerComponent effects = accessor.getComponent(ref, EffectControllerComponent.getComponentType());
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        if (effects != null && index >= 0 && effects.hasEffect(index)) {
            effects.removeEffect(ref, index, accessor);
        }
    }

    /** Vrai si l'effet {@code effectId} est actif sur l'entité. */
    static boolean hasEffect(Ref<EntityStore> ref, String effectId, ComponentAccessor<EntityStore> accessor) {
        EffectControllerComponent effects = accessor.getComponent(ref, EffectControllerComponent.getComponentType());
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        return effects != null && index >= 0 && effects.hasEffect(index);
    }
}
