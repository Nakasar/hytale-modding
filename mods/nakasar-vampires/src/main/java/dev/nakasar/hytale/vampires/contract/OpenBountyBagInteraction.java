package dev.nakasar.hytale.vampires.contract;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.item.ItemModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.List;

/**
 * {@code "Type": "Nakasar_OpenBountyBag"} : ouvre le sac de prime tenu en main (lâché par la cible d'un contrat,
 * {@link ContractBounties}). Le sac est retiré de l'inventaire et sa liste de butin est tirée et donnée au joueur
 * (au sol si son sac est plein).
 *
 * <p>Clé JSON : {@code Droplist} (string) : liste de butin du contenu ({@code Server/Drops/Nakasar/Trophies}).
 */
public class OpenBountyBagInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_OpenBountyBag";

    public static final BuilderCodec<OpenBountyBagInteraction> CODEC = BuilderCodec
            .builder(OpenBountyBagInteraction.class, OpenBountyBagInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Ouvre un sac de prime : le retire et donne le contenu de sa liste de butin.")
            .append(new KeyedCodec<>("Droplist", Codec.STRING), (i, v) -> i.droplist = v, i -> i.droplist)
            .documentation("Liste de butin du contenu du sac.")
            .add()
            .build();

    protected String droplist;

    public OpenBountyBagInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getOwningEntity();
        ItemStack bag = context.getHeldItem();
        if (buffer == null || player == null || !player.isValid() || droplist == null || ItemStack.isEmpty(bag)) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        // Tirage avant de retirer le sac : une liste introuvable ou vide ne doit pas manger le sac.
        List<ItemStack> contents = ItemModule.get().getRandomItemDrops(droplist);
        var inventory = InventoryComponent.getCombined(buffer, player, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        if (contents == null || contents.isEmpty()
                || !inventory.removeItemStack(new ItemStack(bag.getItemId(), 1), true, true).succeeded()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        for (ItemStack stack : contents) {
            SimpleItemContainer.addOrDropItemStack(buffer, player, inventory, stack);
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
