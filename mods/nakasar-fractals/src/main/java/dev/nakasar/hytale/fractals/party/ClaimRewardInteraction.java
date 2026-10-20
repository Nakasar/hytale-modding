package dev.nakasar.hytale.fractals.party;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.observatory.PlayerInteraction;
import dev.nakasar.hytale.fractals.progress.FractalProgress;

/**
 * {@code "Type": "Nakasar_Fractal_ClaimReward"} : coffre de fin de fractale, un par joueur. Chaque membre du groupe
 * parti de l'Observatoire ({@link FractalRuns.Run#members}) y prend une fois le coffre du rang du niveau
 * ({@code Nakasar_Fractal_Reward_Bag_<Rang>}), et débloque le niveau suivant s'il jouait à son plus haut niveau.
 */
public class ClaimRewardInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_ClaimReward";
    public static final String BAG_PREFIX = "Nakasar_Fractal_Reward_Bag_";
    private static final String MESSAGES = "nakasar_fractals_progress.";

    public static final BuilderCodec<ClaimRewardInteraction> CODEC = BuilderCodec
            .builder(ClaimRewardInteraction.class, ClaimRewardInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Coffre de fin de fractale : un coffre par membre du groupe, debloque le niveau suivant.")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        FractalRuns.Run run = FractalRuns.of(world);
        if (run == null) {
            playerRef.sendMessage(Message.translation(MESSAGES + "reward.lost"));
            return;
        }
        if (!FractalRuns.isComplete(world)) {
            playerRef.sendMessage(Message.translation(MESSAGES + "reward.notYet"));
            return;
        }
        if (!run.members().contains(playerRef.getUuid())) {
            playerRef.sendMessage(Message.translation(MESSAGES + "reward.notMember"));
            return;
        }
        if (!run.claimed().add(playerRef.getUuid())) {
            playerRef.sendMessage(Message.translation(MESSAGES + "reward.already"));
            return;
        }
        var inventory = InventoryComponent.getCombined(buffer, player, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        SimpleItemContainer.addOrDropItemStack(buffer, player, inventory,
                new ItemStack(BAG_PREFIX + Observatory.rankId(run.level()), 1));
        playerRef.sendMessage(Message.translation(MESSAGES + "reward.claimed").param("level", run.level()));
        // Le composant de progression peut manquer : ajout hors du traitement du store.
        buffer.run(store -> {
            if (!player.isValid()) {
                return;
            }
            int unlocked = FractalProgress.ensure(store, player).completeAt(run.level());
            if (unlocked > 0) {
                playerRef.sendMessage(Message.translation(MESSAGES + "unlocked").param("level", unlocked));
            }
        });
    }
}
