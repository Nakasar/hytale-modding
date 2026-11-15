package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.BlockLorePage;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;

/**
 * {@code "Type": "Nakasar_Peuples_EchoSpring"} : la Jarre de la Source de l'Écho ({@link EchoSpring}). L'utiliser
 * ouvre une page (page texte vanilla BlockLore) qui dit ce que fait la source, et remplit une Outre d'oasis
 * ({@link Climate#WATERSKIN}) par joueur et par jour de jeu (Kevin, 2026-11-15 : « ce qu'on doit faire avec n'est pas
 * clair »). Le jour du dernier remplissage est gardé dans les visites du joueur sous la clé {@value #DAY_KEY}.
 */
public class EchoSpringInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Peuples_EchoSpring";
    static final String DAY_KEY = "EchoSpring";
    /** Distance maximale entre la jarre et le centre inscrit de sa source. */
    private static final double JAR_REACH = 9;

    public static final BuilderCodec<EchoSpringInteraction> CODEC = BuilderCodec
            .builder(EchoSpringInteraction.class, EchoSpringInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Jarre de la Source de l'Écho : explique la source et donne l'Outre d'oasis du jour.")
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
        int z = target.z;
        world.execute(() -> {
            if (ref.isValid()) {
                use(world, world.getEntityStore().getStore(), ref, playerRef, x, z);
            }
        });
    }

    private static void use(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, int x, int z) {
        String k = EchoSpring.KEYS;
        if (EchoSpring.nearest(world, x + 0.5, z + 0.5, JAR_REACH) == null) {
            playerRef.sendMessage(Message.translation(k + "orphan"));
            return;
        }
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        long day = GameClock.day(store);
        Long last = data == null ? null : data.lastVisit(DAY_KEY);
        boolean fill = data != null && (last == null || last < day);
        if (fill) {
            data.setLastVisit(DAY_KEY, day);
            Requests.give(store, ref, new ItemStack(Climate.WATERSKIN, 1));
        }
        NotificationUtil.sendNotification(playerRef.getPacketHandler(), Message.translation(k + (fill ? "filled" : "alreadyFilled")),
                fill ? NotificationStyle.Success : NotificationStyle.Default);
        Player player = store.getComponent(ref, Player.getComponentType());
        if (player == null) {
            return;
        }
        Message body = Message.empty();
        body.insert(Message.translation(k + "body1"));
        body.insert("\n\n");
        body.insert(Message.translation(k + "body2").param("radius", Climate.SHELTER_RADIUS));
        body.insert("\n\n");
        body.insert(Message.translation(k + "body3"));
        body.insert("\n\n");
        body.insert(Message.translation(k + "body4"));
        player.getPageManager().openCustomPage(ref, store,
                new BlockLorePage(playerRef, Message.translation(k + "title"), body, BlockLorePage.TextAlignment.Left));
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
