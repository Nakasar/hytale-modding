package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_DrinkBlood"} : boire une fiole de sang. Un vampire gagne {@code Blood} de sa réserve ; un
 * vivant a la nausée (effet {@code NauseaEffectId}, {@code NauseaSeconds} secondes). Échoue (la fiole n'est pas bue)
 * si le buveur est un vampire déjà rassasié au maximum.
 */
public class DrinkBloodInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_DrinkBlood";

    public static final BuilderCodec<DrinkBloodInteraction> CODEC = BuilderCodec
            .builder(DrinkBloodInteraction.class, DrinkBloodInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Boit une fiole de sang : nourrit un vampire, ecoeure un vivant.")
            .append(new KeyedCodec<>("Blood", Codec.FLOAT), (i, v) -> i.blood = v, i -> i.blood)
            .documentation("Sang rendu au vampire (0 a 1 = toute la reserve).")
            .add()
            .append(new KeyedCodec<>("NauseaEffectId", Codec.STRING), (i, v) -> i.nauseaEffectId = v, i -> i.nauseaEffectId)
            .documentation("Effet pose sur un buveur qui n'est pas vampire.")
            .add()
            .append(new KeyedCodec<>("NauseaSeconds", Codec.FLOAT), (i, v) -> i.nauseaSeconds = v, i -> i.nauseaSeconds)
            .documentation("Duree de la nausee.")
            .add()
            .build();

    protected float blood = 0.35f;
    protected String nauseaEffectId = "Nakasar_Blood_Nausea";
    protected float nauseaSeconds = 12f;

    public DrinkBloodInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> drinker = context.getEntity();
        if (buffer == null || drinker == null || !drinker.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        Vampire vampire = Vampires.of(drinker, buffer);
        if (vampire == null) {
            if (nauseaEffectId != null && !nauseaEffectId.isBlank()) {
                Vampires.applyEffect(drinker, nauseaEffectId, nauseaSeconds, buffer);
            }
            return;
        }
        if (vampire.getBlood() >= 1f) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        vampire.addBlood(blood);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
