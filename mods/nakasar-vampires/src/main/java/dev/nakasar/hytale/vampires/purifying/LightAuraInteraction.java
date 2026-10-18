package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.data.AbilityAttributeBinding;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.rune.AbilityAttributes;

import java.util.function.Consumer;

/**
 * {@code "Type": "Nakasar_LightAura"} : entoure le lanceur d'une aura de feu purificateur pendant {@code Duration}
 * secondes. Les morts-vivants (groupe {@value PurifyingFireSystem#UNDEAD_GROUP} : vampires, zombies, squelettes,
 * fantômes) le fuient comme une torche de purification qu'il porterait : mêmes rayons, même brûlure s'ils restent
 * trop près ({@link PurifyingFireSystem}, {@link PurifyingSteeringSystem}). Le lanceur éclaire comme la torche.
 *
 * <p>Relancée pendant l'aura, elle la prolonge. Clés JSON :
 * <ul>
 *   <li>{@code Duration} (float, défaut 8) : durée en secondes ;</li>
 *   <li>{@code DurationAttribute} (string) : attribut d'ability qui remplace {@code Duration} ;</li>
 *   <li>{@code EffectId} (string, optionnel) : effet de statut posé pour la même durée (particules, icône).</li>
 * </ul>
 */
public class LightAuraInteraction extends SimpleInstantInteraction implements AbilityAttributeBinding {

    public static final String TYPE_ID = "Nakasar_LightAura";

    public static final BuilderCodec<LightAuraInteraction> CODEC = BuilderCodec
            .builder(LightAuraInteraction.class, LightAuraInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Aura de feu purificateur autour du lanceur : les morts-vivants le fuient.")
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree en secondes de l'aura.")
            .add()
            .append(new KeyedCodec<>("DurationAttribute", Codec.STRING), (i, v) -> i.durationAttribute = v, i -> i.durationAttribute)
            .documentation("Attribut d'ability qui remplace Duration quand le lancer en porte un.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut pose sur le lanceur pour la meme duree (optionnel).")
            .add()
            .build();

    protected float duration = 8f;
    protected String durationAttribute;
    protected String effectId;

    public LightAuraInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> caster = AbilityAttributes.caster(context);
        if (buffer == null || caster == null || !caster.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        float seconds = AbilityAttributes.resolve(context, caster, buffer, durationAttribute, duration);
        if (seconds <= 0) {
            context.getState().state = InteractionState.Failed;
            return;
        }

        LightAura aura = buffer.getComponent(caster, LightAura.getComponentType());
        if (aura != null) {
            aura.remaining = Math.max(aura.remaining, seconds);
        } else {
            aura = new LightAura();
            aura.remaining = seconds;
            ColorLight light = torchLight();
            if (light != null) {
                DynamicLight current = buffer.getComponent(caster, DynamicLight.getComponentType());
                aura.previousLight = current == null || current.getColorLight() == null
                        ? null : new ColorLight(current.getColorLight());
                aura.lightByUs = true;
                buffer.putComponent(caster, DynamicLight.getComponentType(), new DynamicLight(new ColorLight(light)));
            }
            buffer.putComponent(caster, LightAura.getComponentType(), aura);
        }

        if (effectId != null && !effectId.isBlank()) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            EffectControllerComponent effects = buffer.getComponent(caster, EffectControllerComponent.getComponentType());
            if (effect != null && effects != null) {
                effects.addEffect(caster, effect, aura.remaining, OverlapBehavior.OVERWRITE, buffer);
            } else if (effect == null) {
                VampiresPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            }
        }
    }

    /** La lumière de la torche de feu purificateur (bloc {@value PurifyingFireSystem#TORCH}). */
    private static ColorLight torchLight() {
        BlockType torch = BlockType.getAssetMap().getAsset(PurifyingFireSystem.TORCH);
        return torch == null ? null : torch.getLight();
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }

    @Override
    public void collectAbilityAttributes(Consumer<String> out) {
        AbilityAttributeBinding.collect(out, durationAttribute);
    }
}
