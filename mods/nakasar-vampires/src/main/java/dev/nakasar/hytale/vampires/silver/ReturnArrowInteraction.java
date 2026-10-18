package dev.nakasar.hytale.vampires.silver;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_ReturnArrow"} : rend au tireur les dernières flèches prises par {@link TakeArrowInteraction}
 * (arc relâché sans tirer, arbalète déchargée en changeant d'objet), en argent pour celles qui l'étaient. Une flèche
 * non notée revient simple, comme avec le {@code ModifyInventory} vanilla remplacé.
 *
 * <p>Clé JSON : {@code Quantity} (int, défaut 1) : nombre de flèches rendues.
 */
public class ReturnArrowInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_ReturnArrow";

    public static final BuilderCodec<ReturnArrowInteraction> CODEC = BuilderCodec
            .builder(ReturnArrowInteraction.class, ReturnArrowInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Rend au tireur les dernieres fleches encochees ou chargees.")
            .append(new KeyedCodec<>("Quantity", Codec.INTEGER), (i, v) -> i.quantity = v, i -> i.quantity)
            .documentation("Nombre de fleches rendues.")
            .add()
            .build();

    protected int quantity = 1;

    public ReturnArrowInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> shooter = context.getOwningEntity();
        if (buffer == null || shooter == null || !shooter.isValid()) {
            return;
        }
        int silver = 0;
        for (int i = 0; i < quantity; i++) {
            if (ArrowQuiver.unload(shooter)) {
                silver++;
            }
        }
        if (!TakeArrowInteraction.survival(buffer, shooter)) {
            return;
        }
        var inventory = InventoryComponent.getCombined(buffer, shooter, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        if (silver > 0) {
            SimpleItemContainer.addOrDropItemStack(buffer, shooter, inventory,
                    new ItemStack(ArrowQuiver.SILVER_ARROW, silver));
        }
        if (quantity > silver) {
            SimpleItemContainer.addOrDropItemStack(buffer, shooter, inventory,
                    new ItemStack(ArrowQuiver.CRUDE_ARROW, quantity - silver));
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
