package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

/**
 * {@code "Type": "Nakasar_Fractal_Dial"} : cadran de l'Astrolabe. Le meneur monte le niveau du groupe d'un cran,
 * accroupi il le descend (1 à 100).
 */
public class DialInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Dial";

    public static final BuilderCodec<DialInteraction> CODEC = BuilderCodec
            .builder(DialInteraction.class, DialInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Cadran de l'Astrolabe : niveau suivant, accroupi niveau precedent (meneur seulement).")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        if (!FractalCatalog.isObservatory(world)) {
            Observatory.checkLeader(world, playerRef);   // prévient le joueur
            return;
        }
        MovementStatesComponent movement = buffer.getComponent(player, MovementStatesComponent.getComponentType());
        boolean down = movement != null && movement.getMovementStates() != null && movement.getMovementStates().crouching;
        int level = Observatory.state(world).level() + (down ? -1 : 1);
        Observatory.setLevel(world, playerRef, level);
    }
}
