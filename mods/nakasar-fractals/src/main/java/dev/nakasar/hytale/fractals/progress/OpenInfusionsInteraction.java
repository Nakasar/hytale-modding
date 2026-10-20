package dev.nakasar.hytale.fractals.progress;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.packets.interface_.Page;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.windows.ContainerWindow;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.observatory.PlayerInteraction;

/**
 * {@code "Type": "Nakasar_Fractal_OpenInfusions"} : Autel des infusions. Ouvre les {@value FractalProgress#SLOTS}
 * emplacements d'infusion du joueur (les siens, quel que soit l'autel) à côté de son inventaire, comme l'établi des
 * runes vanilla ouvre ses emplacements de capacités, et lui rappelle sa résistance à l'agonie.
 */
public class OpenInfusionsInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_OpenInfusions";

    public static final BuilderCodec<OpenInfusionsInteraction> CODEC = BuilderCodec
            .builder(OpenInfusionsInteraction.class, OpenInfusionsInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Autel des infusions : ouvre les emplacements d'infusion du joueur.")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        // Ajout du composant et ouverture de la fenêtre hors du traitement du store, comme l'établi des runes.
        buffer.run(store -> {
            if (!player.isValid()) {
                return;
            }
            Player playerComponent = store.getComponent(player, Player.getComponentType());
            if (playerComponent == null) {
                return;
            }
            FractalProgress progress = FractalProgress.ensure(store, player);
            playerComponent.getPageManager().setPageWithWindows(player, store, Page.Bench, true,
                    new ContainerWindow(progress.infusions()));
            playerRef.sendMessage(Message.translation("nakasar_fractals_progress.infusions.open")
                    .param("resistance", progress.resistance()));
        });
    }
}
