package dev.nakasar.hytale.fractals.observatory;

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
 * Base des blocs utilisables de l'Observatoire et des fractales (cadran, arches, pupitre, pierre de retour) : la
 * chaîne n'agit que côté serveur, pour un joueur.
 */
abstract class PlayerInteraction extends SimpleInstantInteraction {

    @Override
    protected final void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getEntity();
        if (buffer == null || player == null || !player.isValid()) {
            return;
        }
        PlayerRef playerRef = buffer.getComponent(player, PlayerRef.getComponentType());
        if (playerRef != null) {
            use(buffer, player, playerRef, buffer.getExternalData().getWorld());
        }
    }

    /** Le joueur a utilisé le bloc. */
    protected abstract void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world);

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
