package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.stage.Stages;

/**
 * {@code "Type": "Nakasar_Fractal_SurveyGear", "Gear": "Grapple|Parachute|Powder|Flare"} : clic droit avec un objet
 * de l'équipement de prospection ; mené par {@link SurveyGear} dans le Ressac silencieux, sans effet ailleurs.
 */
public class SurveyGearInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_SurveyGear";

    public static final BuilderCodec<SurveyGearInteraction> CODEC = BuilderCodec
            .builder(SurveyGearInteraction.class, SurveyGearInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Equipement de prospection du Ressac silencieux (grappin, parachute, poudre, fusee).")
            .append(new KeyedCodec<>("Gear", Codec.STRING), (i, v) -> i.gear = v, i -> i.gear)
            .documentation("Grapple, Parachute, Powder ou Flare.").add()
            .build();

    private String gear;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        if (buffer == null || ref == null || !ref.isValid() || gear == null) {
            return;
        }
        PlayerRef player = buffer.getComponent(ref, PlayerRef.getComponentType());
        World world = buffer.getExternalData().getWorld();
        if (player == null || !(Stages.of(world) instanceof SilentSurf surf)) {
            return;
        }
        world.execute(() -> {
            if (ref.isValid()) {
                surf.gear(world, world.getEntityStore().getStore(), player, gear);
            }
        });
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
