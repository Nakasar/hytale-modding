package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Fractal_OpenArch", "Fractal": "<Id>"} : pierre d'une arche de l'Observatoire. Le meneur y
 * envoie tout le cercle d'harmonisation, au niveau du cadran ({@link Observatory#launch}).
 */
public class OpenArchInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_OpenArch";

    public static final BuilderCodec<OpenArchInteraction> CODEC = BuilderCodec
            .builder(OpenArchInteraction.class, OpenArchInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Arche de l'Observatoire : le meneur envoie le cercle dans la fractale.")
            .append(new KeyedCodec<>("Fractal", Codec.STRING), (i, v) -> i.fractal = v, i -> i.fractal)
            .documentation("Id de la fractale (FractalCatalog).").add()
            .build();

    private String fractal;

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        Observatory.launch(world, playerRef, fractal);
    }
}
