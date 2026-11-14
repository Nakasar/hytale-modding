package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Peuples_OpenBoard"} : utiliser le tableau d'un village ouvre sa page ({@link VillageBoard}).
 * Le village est celui dont le tableau est le bloc visé ; un panneau posé à la main hors d'un village le dit.
 */
public class OpenBoardInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Peuples_OpenBoard";

    public static final BuilderCodec<OpenBoardInteraction> CODEC = BuilderCodec
            .builder(OpenBoardInteraction.class, OpenBoardInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Ouvre le tableau du village dont ce bloc est le tableau.")
            .build();

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        BlockPosition target = context.getTargetBlock();
        if (buffer == null || ref == null || !ref.isValid() || target == null) {
            return;
        }
        PlayerRef playerRef = buffer.getComponent(ref, PlayerRef.getComponentType());
        if (playerRef == null) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        int x = target.x;
        int y = target.y;
        int z = target.z;
        world.execute(() -> {
            if (!ref.isValid()) {
                return;
            }
            Village village = Villages.registry(world).byBoard(x, y, z);
            if (village == null) {
                playerRef.sendMessage(Message.translation(Villages.MESSAGES + "boardOrphan"));
                return;
            }
            VillageBoard.open(world, world.getEntityStore().getStore(), ref, playerRef, village);
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
