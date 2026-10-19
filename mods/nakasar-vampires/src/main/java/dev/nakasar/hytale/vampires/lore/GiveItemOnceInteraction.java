package dev.nakasar.hytale.vampires.lore;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.ItemUtils;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Donne un objet au joueur qui utilise le bloc, s'il n'en a pas déjà un : le tableau de contrats de la brèche
 * remet ainsi le premier contrat à chaque joueur, une seule fois tant qu'il le garde (multijoueur compris).
 * Ne fait rien si le sac est plein ou si l'objet n'existe pas (id pas encore créé, pack absent) : la suite de la chaîne ({@code Next},
 * la page de lore) s'ouvre quand même.
 */
public class GiveItemOnceInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_GiveItemOnce";

    public static final BuilderCodec<GiveItemOnceInteraction> CODEC = BuilderCodec
            .builder(GiveItemOnceInteraction.class, GiveItemOnceInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Donne un exemplaire de l'objet au joueur s'il n'en porte aucun.")
            .append(new KeyedCodec<>("ItemId", Codec.STRING), (i, v) -> i.itemId = v, i -> i.itemId)
            .documentation("Id de l'objet donné.").add()
            .build();

    private String itemId;

    public GiveItemOnceInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getEntity();
        if (buffer == null || player == null || !player.isValid() || itemId == null
                || buffer.getComponent(player, Player.getComponentType()) == null
                || Item.getAssetMap().getAsset(itemId) == null) {
            return;
        }
        CombinedItemContainer inventory = InventoryComponent.getCombined(buffer, player, InventoryComponent.EVERYTHING);
        int owned = inventory.countItemStacks(stack -> stack != null && itemId.equals(stack.getItemId()));
        ItemStack gift = new ItemStack(itemId, 1);
        TransformComponent transform = buffer.getComponent(player, TransformComponent.getComponentType());
        // Sac plein : rien. interactivelyPickupItem jetterait l'objet au sol, et l'objet au sol ne compte pas
        // dans l'inventaire : chaque usage en redonnerait un.
        if (owned == 0 && transform != null && inventory.canAddItemStack(gift)) {
            ItemUtils.interactivelyPickupItem(player, gift, transform.getPosition(), buffer);
        }
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
