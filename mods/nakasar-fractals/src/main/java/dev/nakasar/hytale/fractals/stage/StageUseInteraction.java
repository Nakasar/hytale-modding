package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Fractal_Use", "Action": "…"} : bloc utilisable d'une fractale (consoles, batteries,
 * pylônes…). Nos instances refusent les coups sur les blocs ; l'interaction « Utiliser », elle, passe. L'action est
 * remise au déroulé de la fractale ({@link FractalStage#use}), hors du système en cours.
 */
public class StageUseInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Use";

    public static final BuilderCodec<StageUseInteraction> CODEC = BuilderCodec
            .builder(StageUseInteraction.class, StageUseInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Bloc utilisable d'une fractale ; l'action est menee par le Java de la fractale.")
            .append(new KeyedCodec<>("Action", Codec.STRING), (i, v) -> i.action = v, i -> i.action)
            .documentation("Nom de l'action (console, batterie...).").add()
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
        FractalStage stage = Stages.of(world);
        BlockPosition target = context.getTargetBlock();
        if (player == null || stage == null || target == null) {
            return;
        }
        int x = target.x;
        int y = target.y;
        int z = target.z;
        world.execute(() -> {
            if (ref.isValid()) {
                stage.use(world, world.getEntityStore().getStore(), ref, player, action, x, y, z);
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
