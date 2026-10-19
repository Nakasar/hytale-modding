package dev.nakasar.hytale.vampires.elite;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;

/**
 * {@code "Type": "Nakasar_ApplyEffectToFoes"} : pose l'effet {@code EffectId} pendant {@code Duration} secondes sur
 * l'entité ciblée (le {@code HitEntity} d'un {@code Selector}), sauf sur le lanceur et ses alliés.
 *
 * <p>Le filtre de camp ({@code AllegianceDamageFilter}) n'annule que les dégâts : un {@code ApplyEffect} vanilla sous
 * un {@code AOECircle} toucherait aussi les alliés (la vague de froid du Spectre ralentissait ses propres fantômes).
 *
 * <p>Clés JSON : {@code EffectId} (string, requis), {@code Duration} (float, défaut 5).
 */
public class ApplyEffectToFoesInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_ApplyEffectToFoes";

    public static final BuilderCodec<ApplyEffectToFoesInteraction> CODEC = BuilderCodec
            .builder(ApplyEffectToFoesInteraction.class, ApplyEffectToFoesInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Pose un effet de statut sur la cible, sauf sur le lanceur et ses allies.")
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut a poser.")
            .add()
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree de l'effet en secondes.")
            .add()
            .build();

    protected String effectId;
    protected float duration = 5f;

    public ApplyEffectToFoesInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        Ref<EntityStore> victim = context.getTargetEntity();
        EntityEffect effect = effectId == null ? null : EntityEffect.getAssetMap().getAsset(effectId);
        if (effect == null) {
            VampiresPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            return;
        }
        if (buffer == null || victim == null || !victim.isValid() || victim.equals(caster)
                || buffer.getComponent(victim, DeathComponent.getComponentType()) != null
                || (caster != null && caster.isValid() && Allegiances.isCasterAlly(caster, victim, buffer))) {
            return;
        }
        EffectControllerComponent effects = buffer.getComponent(victim, EffectControllerComponent.getComponentType());
        if (effects != null) {
            effects.addEffect(victim, effect, duration, OverlapBehavior.OVERWRITE, buffer);
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
