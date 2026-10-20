package dev.nakasar.hytale.fractals.combat;

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
 * {@code "Type": "Nakasar_Fractal_StunSelf"} : le boss reste étourdi {@code Seconds} secondes ({@link BossStun}, effet
 * {@code EffectId}, défaut {@value BossStun#EFFECT}) : fenêtre de punition après une attaque qui l'épuise.
 */
public class StunSelfInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_StunSelf";

    public static final BuilderCodec<StunSelfInteraction> CODEC = BuilderCodec
            .builder(StunSelfInteraction.class, StunSelfInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Etourdit le boss lui-meme quelques secondes (IA gelee, effet visible).")
            .append(new KeyedCodec<>("Seconds", Codec.FLOAT), (i, v) -> i.seconds = v, i -> i.seconds).add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId).add()
            .build();

    protected float seconds = 2f;
    protected String effectId = BossStun.EFFECT;

    public StunSelfInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> self = owner != null && owner.isValid() ? owner : context.getEntity();
        if (buffer == null || self == null || !self.isValid() || seconds <= 0f) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        world.execute(() -> BossStun.stun(world, world.getEntityStore().getStore(), self, seconds, effectId));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
