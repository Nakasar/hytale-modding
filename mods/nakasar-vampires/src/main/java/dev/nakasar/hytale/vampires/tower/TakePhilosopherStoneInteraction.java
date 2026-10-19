package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.ItemUtils;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * {@code "Type": "Nakasar_TakePhilosopherStone"} : le piédestal du Bureau de l'Alchimiste donne à chaque joueur sa
 * propre pierre philosophale, une fois par instance de la tour. La pierre reste posée pour les autres joueurs.
 *
 * <p>Les joueurs servis sont notés par monde (l'instance est supprimée quand elle se vide, et sa liste avec). Sac plein :
 * rien n'est donné ni noté, la pierre attend.
 */
public class TakePhilosopherStoneInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_TakePhilosopherStone";
    private static final String MESSAGES = "nakasar_alchemist.stone.";

    public static final BuilderCodec<TakePhilosopherStoneInteraction> CODEC = BuilderCodec
            .builder(TakePhilosopherStoneInteraction.class, TakePhilosopherStoneInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Donne la pierre philosophale au joueur, une fois par instance.")
            .append(new KeyedCodec<>("ItemId", Codec.STRING), (i, v) -> i.itemId = v, i -> i.itemId)
            .documentation("Id de l'objet donné.").add()
            .build();

    /** Joueurs qui ont déjà pris leur pierre, par monde d'instance. */
    private static final Map<World, Set<UUID>> TAKEN = Collections.synchronizedMap(new WeakHashMap<>());

    private String itemId;

    public TakePhilosopherStoneInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getEntity();
        if (buffer == null || player == null || !player.isValid() || itemId == null
                || Item.getAssetMap().getAsset(itemId) == null) {
            return;
        }
        PlayerRef playerRef = buffer.getComponent(player, PlayerRef.getComponentType());
        TransformComponent transform = buffer.getComponent(player, TransformComponent.getComponentType());
        if (playerRef == null || transform == null) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        Set<UUID> taken = TAKEN.computeIfAbsent(world, w -> Collections.synchronizedSet(new HashSet<>()));
        if (taken.contains(playerRef.getUuid())) {
            playerRef.sendMessage(Message.translation(MESSAGES + "taken"));
            return;
        }
        CombinedItemContainer inventory = InventoryComponent.getCombined(buffer, player, InventoryComponent.EVERYTHING);
        ItemStack stone = new ItemStack(itemId, 1);
        if (!inventory.canAddItemStack(stone)) {
            playerRef.sendMessage(Message.translation(MESSAGES + "full"));
            return;
        }
        taken.add(playerRef.getUuid());
        ItemUtils.interactivelyPickupItem(player, stone, transform.getPosition(), buffer);
    }

    public static void clearAll() {
        TAKEN.clear();
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
