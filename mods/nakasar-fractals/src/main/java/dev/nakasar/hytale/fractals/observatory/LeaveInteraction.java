package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import dev.nakasar.hytale.fractals.party.FractalRuns;

/**
 * {@code "Type": "Nakasar_Fractal_Leave"} : pierre de retour d'une fractale, ramène le joueur à l'Observatoire de son
 * groupe. Sert aussi à {@code /fractale quitter}.
 */
public class LeaveInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Leave";

    public static final BuilderCodec<LeaveInteraction> CODEC = BuilderCodec
            .builder(LeaveInteraction.class, LeaveInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Pierre de retour : quitte la fractale pour l'Observatoire.")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        leave(world, playerRef);
    }

    /** Ramène le joueur à l'Observatoire s'il est dans une fractale, sinon le prévient. */
    public static void leave(World world, PlayerRef playerRef) {
        if (FractalCatalog.fractalOf(world) == null) {
            playerRef.sendMessage(Message.translation(Observatory.MESSAGES + "notInFractal"));
            return;
        }
        // Le store peut être en plein traitement : on part juste après.
        world.execute(() -> {
            Ref<EntityStore> ref = playerRef.getReference();
            if (ref != null && ref.isValid() && FractalRuns.leave(ref, world.getEntityStore().getStore())) {
                playerRef.sendMessage(Message.translation(Observatory.MESSAGES + "left.fractal"));
            }
        });
    }
}
