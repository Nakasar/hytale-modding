package dev.nakasar.hytale.vampires.silver;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.GameMode;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_TakeArrow"} : prend une flèche dans l'inventaire du tireur pour l'encocher ou la charger,
 * une flèche en argent s'il en a, sinon une flèche simple ({@code Weapon_Arrow_Crude}). Échoue (branche
 * {@code Failed}) s'il n'a ni l'une ni l'autre.
 *
 * <p>Remplace le {@code ModifyInventory} qui retirait {@code Weapon_Arrow_Crude} dans les arcs et arbalètes
 * (vanilla et en argent, voir {@code tools/generate_silver_weapons.py}). Comme lui, ne prend rien à un joueur qui
 * n'est pas en mode Aventure. La flèche prise est notée dans {@link ArrowQuiver} pour savoir, au tir, si le
 * projectile est en argent.
 */
public class TakeArrowInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_TakeArrow";

    public static final BuilderCodec<TakeArrowInteraction> CODEC = BuilderCodec
            .builder(TakeArrowInteraction.class, TakeArrowInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Retire une fleche (en argent d'abord, sinon simple) de l'inventaire du tireur.")
            .build();

    public TakeArrowInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> shooter = context.getOwningEntity();
        if (buffer == null || shooter == null || !shooter.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        if (!survival(buffer, shooter)) {
            return;
        }
        CombinedItemContainer inventory =
                InventoryComponent.getCombined(buffer, shooter, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        if (inventory.removeItemStack(new ItemStack(ArrowQuiver.SILVER_ARROW, 1), true, true).succeeded()) {
            ArrowQuiver.load(shooter, true);
        } else if (inventory.removeItemStack(new ItemStack(ArrowQuiver.CRUDE_ARROW, 1), true, true).succeeded()) {
            ArrowQuiver.load(shooter, false);
        } else {
            context.getState().state = InteractionState.Failed;
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement : le client reprend l'état (réussite ou échec) envoyé par le serveur.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }

    /** Faux pour un joueur hors du mode Aventure, qui tire sans consommer de flèches. */
    static boolean survival(CommandBuffer<EntityStore> buffer, Ref<EntityStore> shooter) {
        Player player = buffer.getComponent(shooter, Player.getComponentType());
        return player == null || player.getGameMode() == GameMode.Adventure;
    }
}
