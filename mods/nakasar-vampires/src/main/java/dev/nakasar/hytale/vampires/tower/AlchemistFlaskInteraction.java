package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_AlchemistFlask"} : l'Alchimiste lance ses fioles. Chaque joueur proche reçoit une zone
 * annoncée au sol, qui éclate deux secondes plus tard selon l'élément de la fiole ({@link AlchemistSystem}).
 */
public class AlchemistFlaskInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_AlchemistFlask";

    public static final BuilderCodec<AlchemistFlaskInteraction> CODEC = BuilderCodec
            .builder(AlchemistFlaskInteraction.class, AlchemistFlaskInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("L'Alchimiste lance une fiole élémentaire vers chaque joueur proche (zones annoncées).")
            .build();

    public AlchemistFlaskInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> alchemist = context.getEntity();
        if (buffer == null || alchemist == null || !alchemist.isValid()) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        world.execute(() -> AlchemistSystem.throwFlasks(world, alchemist));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
