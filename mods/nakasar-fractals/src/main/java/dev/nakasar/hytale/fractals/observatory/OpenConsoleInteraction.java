package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.packets.interface_.Page;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.windows.ContainerWindow;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

/**
 * {@code "Type": "Nakasar_Fractal_OpenConsole"} : console de sélection de l'Observatoire. Ouvre ses deux emplacements
 * (noyau de fractale, diapason de niveau), les mêmes pour tous les joueurs, à côté de l'inventaire, comme l'Autel des
 * infusions. {@link HarmonyCircleSystem} annonce l'harmonisation dès que les deux sont posés.
 */
public class OpenConsoleInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_OpenConsole";

    public static final BuilderCodec<OpenConsoleInteraction> CODEC = BuilderCodec
            .builder(OpenConsoleInteraction.class, OpenConsoleInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Console de selection : noyau de fractale et diapason de niveau, partages par l'Observatoire.")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        if (!FractalCatalog.isObservatory(world)) {
            Observatory.checkLeader(world, playerRef);   // prévient le joueur
            return;
        }
        Observatory.State state = Observatory.state(world);
        buffer.run(store -> {
            Player playerComponent = player.isValid() ? store.getComponent(player, Player.getComponentType()) : null;
            if (playerComponent != null) {
                playerComponent.getPageManager().setPageWithWindows(player, store, Page.Bench, true,
                        new ContainerWindow(state.console));
            }
        });
    }
}
