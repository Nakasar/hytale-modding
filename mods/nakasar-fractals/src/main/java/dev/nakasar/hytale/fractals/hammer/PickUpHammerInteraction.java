package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Fractal_PickUpHammer"} : interaction Use d'un marteau du culte posé au sol
 * ({@link HammerDropSystem}). L'entité d'objet est retirée et le marteau donné au joueur ; {@link HammerSystem} lui
 * fait alors payer le prix habituel en PV.
 */
public class PickUpHammerInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_PickUpHammer";

    public static final BuilderCodec<PickUpHammerInteraction> CODEC = BuilderCodec
            .builder(PickUpHammerInteraction.class, PickUpHammerInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Ramasse le marteau du culte visé au sol.")
            .build();

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getOwningEntity();
        Ref<EntityStore> target = context.getTargetEntity();
        if (buffer == null || player == null || !player.isValid() || target == null || !target.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        ItemComponent item = buffer.getComponent(target, ItemComponent.getComponentType());
        ItemStack stack = item == null ? null : item.getItemStack();
        if (stack == null || !Hammer.ID.equals(stack.getItemId())) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        if (Hammer.carries(buffer, player)) {
            PlayerRef playerRef = buffer.getComponent(player, PlayerRef.getComponentType());
            if (playerRef != null) {
                playerRef.sendMessage(Message.translation("nakasar_fractals_cliffside.hammer.have"));
            }
            context.getState().state = InteractionState.Failed;
            return;
        }
        buffer.tryRemoveEntity(target, RemoveReason.REMOVE);
        Hammer.give(buffer, player);
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
