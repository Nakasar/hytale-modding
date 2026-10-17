package dev.nakasar.hytale.runes.interaction;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.data.AbilityAttributeBinding;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;
import dev.nakasar.hytale.runes.RunesPlugin;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;

import java.lang.reflect.Field;
import java.util.function.Consumer;

/**
 * {@code "Type": "Nakasar_Dominate"} : rend le PNJ ciblé amical envers le lanceur pendant {@code Duration}
 * secondes, via la mémoire d'attitude de son rôle (le même mécanisme que l'action de rôle
 * {@code OverrideAttitude}). Un PNJ amical cesse de considérer le lanceur comme une cible.
 *
 * <p>Clés JSON :
 * <ul>
 *   <li>{@code Duration} (float, défaut 6) : durée en secondes ;</li>
 *   <li>{@code DurationAttribute} (string) : attribut d'ability qui remplace {@code Duration} ;</li>
 *   <li>{@code EffectId} (string, optionnel) : effet de statut appliqué à la cible pour la même durée
 *       (retour visuel) ;</li>
 *   <li>{@code Attitude} (string, défaut {@code Friendly}) : {@code Friendly}, {@code Neutral}, {@code Ignore},
 *       {@code Revered} ou {@code Hostile}.</li>
 * </ul>
 * Échoue (branche {@code Failed}) si la cible n'est pas un PNJ.
 */
public class DominateInteraction extends SimpleInstantInteraction implements AbilityAttributeBinding {

    public static final String TYPE_ID = "Nakasar_Dominate";

    public static final BuilderCodec<DominateInteraction> CODEC = BuilderCodec
            .builder(DominateInteraction.class, DominateInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Rend le PNJ cible amical envers le lanceur pendant Duration secondes.")
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree en secondes de la domination.")
            .add()
            .append(new KeyedCodec<>("DurationAttribute", Codec.STRING), (i, v) -> i.durationAttribute = v, i -> i.durationAttribute)
            .documentation("Attribut d'ability qui remplace Duration quand le lancer en porte un.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut applique a la cible pour la meme duree (optionnel).")
            .add()
            .append(new KeyedCodec<>("Attitude", Attitude.CODEC), (i, v) -> i.attitude = v, i -> i.attitude)
            .documentation("Attitude imposee envers le lanceur (defaut Friendly).")
            .add()
            .build();

    protected float duration = 6f;
    protected String durationAttribute;
    protected String effectId;
    protected Attitude attitude = Attitude.FRIENDLY;

    public DominateInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> target = context.getTargetEntity();
        Ref<EntityStore> caster = AbilityAttributes.caster(context);
        if (buffer == null || target == null || !target.isValid() || caster == null || !caster.isValid()) {
            fail(context);
            return;
        }
        NPCEntity npc = buffer.getComponent(target, NPCEntity.getComponentType());
        WorldSupport worldSupport = npc == null ? null : WorldSupport.get(target, buffer);
        if (worldSupport == null) {
            fail(context);
            return;
        }

        float seconds = AbilityAttributes.resolve(context, caster, buffer, durationAttribute, duration);
        if (seconds <= 0) {
            fail(context);
            return;
        }

        if (!overrideAttitude(worldSupport, caster, seconds)) {
            fail(context);
            return;
        }

        if (effectId != null && !effectId.isBlank()) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            EffectControllerComponent effects = buffer.getComponent(target, EffectControllerComponent.getComponentType());
            if (effect != null && effects != null) {
                effects.addEffect(target, effect, seconds, OverlapBehavior.OVERWRITE, buffer, caster);
            } else if (effect == null) {
                RunesPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            }
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public void collectAbilityAttributes(Consumer<String> out) {
        AbilityAttributeBinding.collect(out, durationAttribute);
    }

    /**
     * {@link WorldSupport#overrideAttitude} suppose que le rôle a demandé une mémoire d'attitude
     * ({@code requireAttitudeOverrideMemory}, fait par l'action {@code OverrideAttitude}). Pour les rôles
     * qui ne l'ont jamais demandée la map est {@code null} : on la crée par réflexion <em>avant</em> l'appel,
     * pour ne jamais laisser une NPE partielle derrière nous. {@code WorldSupport.tick} fait expirer les
     * entrées de cette map comme les autres.
     */
    private boolean overrideAttitude(WorldSupport support, Ref<EntityStore> caster, float seconds) {
        if (!ensureAttitudeMemory(support)) {
            RunesPlugin.get().getLogger().atWarning().log(
                    "%s : impossible d'initialiser la memoire d'attitude du PNJ, domination ignoree", TYPE_ID);
            return false;
        }
        support.overrideAttitude(caster, attitude, seconds);
        return true;
    }

    private static volatile Field attitudeMemoryField;

    private static boolean ensureAttitudeMemory(WorldSupport support) {
        try {
            Field field = attitudeMemoryField;
            if (field == null) {
                field = WorldSupport.class.getDeclaredField("attitudeOverrideMemory");
                field.setAccessible(true);
                attitudeMemoryField = field;
            }
            if (field.get(support) == null) {
                field.set(support, new Int2ObjectOpenHashMap<>());
            }
            return true;
        } catch (ReflectiveOperationException | RuntimeException e) {
            RunesPlugin.get().getLogger().atWarning().withCause(e).log("%s : reflexion sur WorldSupport impossible", TYPE_ID);
            return false;
        }
    }

    private static void fail(InteractionContext context) {
        context.getState().state = InteractionState.Failed;
    }
}
