package dev.nakasar.hytale.fractals.sirensreef;

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
 * {@code "Type": "Nakasar_Fractal_ReefAction", "Action": "Throw|Ripple|Scatter|Ice"} : clic droit avec le trésor maudit
 * ({@link CursedTreasure}) ou un boulet du canon des ombres ({@link ShadowCannon}) ; sans effet hors du Récif de la Sirène.
 */
public class ReefActionInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_ReefAction";

    public static final BuilderCodec<ReefActionInteraction> CODEC = BuilderCodec
            .builder(ReefActionInteraction.class, ReefActionInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Objets du Recif de la Sirene : lancer le tresor maudit, tirer un boulet du canon des ombres.")
            .append(new KeyedCodec<>("Action", Codec.STRING), (i, v) -> i.action = v, i -> i.action)
            .documentation("Throw, Ripple, Scatter ou Ice.").add()
            .build();

    private String action;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        if (buffer == null || ref == null || !ref.isValid() || action == null) {
            return;
        }
        PlayerRef player = buffer.getComponent(ref, PlayerRef.getComponentType());
        World world = buffer.getExternalData().getWorld();
        if (player == null || !(Stages.of(world) instanceof SirensReef reef)) {
            return;
        }
        world.execute(() -> {
            if (ref.isValid()) {
                reef.action(world, world.getEntityStore().getStore(), player, action);
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
