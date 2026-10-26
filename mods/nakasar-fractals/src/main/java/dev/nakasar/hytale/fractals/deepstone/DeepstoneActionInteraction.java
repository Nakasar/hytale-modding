package dev.nakasar.hytale.fractals.deepstone;

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
 * {@code "Type": "Nakasar_Fractal_DeepstoneAction", "Action": "Light"} : clic droit avec la Lumière de Deldrimor
 * ({@link DeepLight}) ; sans effet hors de Pierre-Profonde.
 */
public class DeepstoneActionInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_DeepstoneAction";

    public static final BuilderCodec<DeepstoneActionInteraction> CODEC = BuilderCodec
            .builder(DeepstoneActionInteraction.class, DeepstoneActionInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Objets de Pierre-Profonde : liberer la Lumiere de Deldrimor.")
            .append(new KeyedCodec<>("Action", Codec.STRING), (i, v) -> i.action = v, i -> i.action)
            .documentation("Light.").add()
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
        if (player == null || !(Stages.of(world) instanceof Deepstone deepstone)) {
            return;
        }
        world.execute(() -> {
            if (ref.isValid()) {
                deepstone.action(world, world.getEntityStore().getStore(), player, action);
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
