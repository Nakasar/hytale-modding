package dev.nakasar.hytale.peuples.review;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;

/**
 * {@code "Type": "Nakasar_Peuples_ReviewSign"} : utiliser le panneau d'un rectangle de la carte de revue
 * ({@link ReviewMap}) affiche à l'écran le bâtiment et son palier (titre d'événement vanilla), et dans le chat les
 * prefabs collés et les notes. Le panneau ne porte aucun texte (Kevin, 16 novembre 2026).
 */
public class ReviewSignInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Peuples_ReviewSign";

    public static final BuilderCodec<ReviewSignInteraction> CODEC = BuilderCodec
            .builder(ReviewSignInteraction.class, ReviewSignInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Affiche le bâtiment et le palier du rectangle de la carte de revue dont ce bloc est le panneau.")
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
            ReviewMap.Spot spot = ReviewMap.spotAtSign(world, x, y, z);
            if (spot == null) {
                playerRef.sendMessage(Message.translation(ReviewMap.KEYS + "signOrphan"));
                return;
            }
            Message[] m = ReviewMap.describe(spot);
            EventTitleUtil.showEventTitleToPlayer(playerRef, m[0], m[1], EventTitleStyle.Default, null, 3f, 0.2f, 0.5f);
            playerRef.sendMessage(Message.join(m[0], Message.raw(" · "), m[1]));
            playerRef.sendMessage(m[2]);
        });
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
