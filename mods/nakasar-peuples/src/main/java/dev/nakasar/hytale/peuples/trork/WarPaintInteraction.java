package dev.nakasar.hytale.peuples.trork;

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

/**
 * {@code "Type": "Nakasar_Peuples_WarPaint"} : clic secondaire avec le pot de Peinture de guerre en main, la peinture
 * est mise ou ôtée ({@link WarPaint#toggle}). Le pot n'est pas consommé.
 */
public class WarPaintInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Peuples_WarPaint";

    public static final BuilderCodec<WarPaintInteraction> CODEC = BuilderCodec
            .builder(WarPaintInteraction.class, WarPaintInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Met ou ôte la Peinture de guerre trork.")
            .build();

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        if (buffer == null || ref == null || !ref.isValid()) {
            return;
        }
        PlayerRef player = buffer.getComponent(ref, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        world.execute(() -> {
            if (ref.isValid()) {
                WarPaint.toggle(world.getEntityStore().getStore(), ref, player);
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
