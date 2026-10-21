package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Fractal_Harmonize"} : résonateur du cercle d'harmonisation. Le meneur envoie le cercle dans
 * la fractale de la console de sélection, au niveau de son diapason ({@link Observatory#harmonize}).
 */
public class HarmonizeInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Harmonize";

    public static final BuilderCodec<HarmonizeInteraction> CODEC = BuilderCodec
            .builder(HarmonizeInteraction.class, HarmonizeInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Resonateur du cercle : le meneur lance la fractale harmonisee a la console.")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        Observatory.harmonize(world, playerRef);
    }
}
