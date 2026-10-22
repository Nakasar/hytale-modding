package dev.nakasar.hytale.fractals.defiance;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
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
 * {@code "Type": "Nakasar_Fractal_OpenDefiance"} : ouvre la barre de défiance du boss ({@link Defiance}) pendant
 * {@code Seconds} secondes, au début de la préparation d'une attaque : la briser à temps l'étourdit.
 */
public class OpenDefianceInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_OpenDefiance";

    public static final BuilderCodec<OpenDefianceInteraction> CODEC = BuilderCodec
            .builder(OpenDefianceInteraction.class, OpenDefianceInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Ouvre la barre de defiance du boss quelques secondes.")
            .append(new KeyedCodec<>("Seconds", Codec.FLOAT), (i, v) -> i.seconds = v, i -> i.seconds).add()
            .build();

    protected float seconds = 2f;

    public OpenDefianceInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> self = owner != null && owner.isValid() ? owner : context.getEntity();
        if (buffer == null || self == null || !self.isValid()) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        Defiance.open(world, self, seconds);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
