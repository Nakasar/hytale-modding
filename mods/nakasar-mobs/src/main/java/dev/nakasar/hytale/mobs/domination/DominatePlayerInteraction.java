package dev.nakasar.hytale.mobs.domination;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.mobs.MobsPlugin;

/**
 * {@code "Type": "Nakasar_DominatePlayer"} : le lanceur (le Comte Vampire) domine le joueur ciblé pendant
 * {@code Duration} secondes. Tant que dure l'effet, les coups et projectiles de ce joueur ne blessent plus le
 * lanceur ({@link DominationDamageFilter}) ; il peut toujours bouger et frapper les autres.
 *
 * <p>La cible est l'entité fournie par la chaîne (le {@code HitEntity} d'un {@code Selector}). Échoue
 * (branche {@code Failed}) si ce n'est pas un joueur.
 *
 * <p>Clés JSON :
 * <ul>
 *   <li>{@code Duration} (float, défaut 6) : durée en secondes ;</li>
 *   <li>{@code EffectId} (string, optionnel) : effet de statut appliqué au joueur pour la même durée
 *       (retour visuel, et nom de l'effet dans l'interface).</li>
 * </ul>
 */
public class DominatePlayerInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_DominatePlayer";

    public static final BuilderCodec<DominatePlayerInteraction> CODEC = BuilderCodec
            .builder(DominatePlayerInteraction.class, DominatePlayerInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Le lanceur domine le joueur cible : ses degats contre le lanceur sont annules pendant Duration secondes.")
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree en secondes de la domination.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut applique au joueur pour la meme duree (optionnel).")
            .add()
            .build();

    protected float duration = 6f;
    protected String effectId;

    public DominatePlayerInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> caster = context.getOwningEntity() != null ? context.getOwningEntity() : context.getEntity();
        Ref<EntityStore> target = context.getTargetEntity();
        if (buffer == null || caster == null || !caster.isValid() || target == null || !target.isValid()
                || target.equals(caster) || buffer.getComponent(target, Player.getComponentType()) == null
                || duration <= 0) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        Dominations.dominate(target, caster, duration);
        if (effectId != null && !effectId.isBlank()) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            EffectControllerComponent effects = buffer.getComponent(target, EffectControllerComponent.getComponentType());
            if (effect != null && effects != null) {
                effects.addEffect(target, effect, duration, OverlapBehavior.OVERWRITE, buffer, caster);
            } else if (effect == null) {
                MobsPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            }
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
