package dev.nakasar.hytale.vampires.invisibility;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.component.Intangible;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.data.AbilityAttributeBinding;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.rune.AbilityAttributes;
import org.joml.Vector3d;

import java.util.function.Consumer;

/**
 * {@code "Type": "Nakasar_Invisibility"} : rend le lanceur invisible tant qu'il reste immobile, {@code Duration}
 * secondes au plus. Il disparaît pour les autres joueurs et les PNJ cessent de le voir : le jeu ne fait pas
 * détecter une entité {@code Intangible} par les capteurs des PNJ ({@code EntityDetectionUtil}), et
 * {@link InvisibilitySystem} efface le lanceur des cibles qu'ils avaient déjà. Effet de bord du jeu : une entité
 * intangible ne prend pas de dégâts, d'où la fin de l'invisibilité dès que le lanceur bouge ou frappe.
 *
 * <p>Clés JSON :
 * <ul>
 *   <li>{@code Duration} (float, défaut 30) : durée maximale en secondes ;</li>
 *   <li>{@code DurationAttribute} (string) : attribut d'ability qui remplace {@code Duration} ;</li>
 *   <li>{@code EffectId} (string, optionnel) : effet de statut posé pendant l'invisibilité (icône, teinte).</li>
 * </ul>
 */
public class InvisibilityInteraction extends SimpleInstantInteraction implements AbilityAttributeBinding {

    public static final String TYPE_ID = "Nakasar_Invisibility";

    public static final BuilderCodec<InvisibilityInteraction> CODEC = BuilderCodec
            .builder(InvisibilityInteraction.class, InvisibilityInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Rend le lanceur invisible tant qu'il reste immobile.")
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree maximale en secondes de l'invisibilite.")
            .add()
            .append(new KeyedCodec<>("DurationAttribute", Codec.STRING), (i, v) -> i.durationAttribute = v, i -> i.durationAttribute)
            .documentation("Attribut d'ability qui remplace Duration quand le lancer en porte un.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut pose pendant l'invisibilite (optionnel).")
            .add()
            .build();

    protected float duration = 30f;
    protected String durationAttribute;
    protected String effectId;

    public InvisibilityInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> caster = AbilityAttributes.caster(context);
        TransformComponent transform = buffer == null || caster == null || !caster.isValid()
                ? null : buffer.getComponent(caster, TransformComponent.getComponentType());
        float seconds = transform == null ? 0
                : AbilityAttributes.resolve(context, caster, buffer, durationAttribute, duration);
        if (seconds <= 0) {
            context.getState().state = InteractionState.Failed;
            return;
        }

        Vector3d position = transform.getPosition();
        Invisibility invisibility = buffer.getComponent(caster, Invisibility.getComponentType());
        boolean fresh = invisibility == null;
        if (fresh) {
            invisibility = new Invisibility();
            invisibility.intangibleByUs = !buffer.getArchetype(caster).contains(Intangible.getComponentType());
            if (invisibility.intangibleByUs) {
                buffer.putComponent(caster, Intangible.getComponentType(), Intangible.INSTANCE);
            }
        }
        invisibility.remaining = seconds;
        invisibility.settle = InvisibilitySystem.SETTLE;
        invisibility.anchorX = position.x;
        invisibility.anchorY = position.y;
        invisibility.anchorZ = position.z;

        if (effectId != null && !effectId.isBlank()) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            EffectControllerComponent effects = buffer.getComponent(caster, EffectControllerComponent.getComponentType());
            if (effect != null && effects != null) {
                effects.addEffect(caster, effect, seconds, OverlapBehavior.OVERWRITE, buffer);
                invisibility.effectId = effectId;
            } else if (effect == null) {
                VampiresPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            }
        }
        if (fresh) {
            buffer.putComponent(caster, Invisibility.getComponentType(), invisibility);
        }
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
