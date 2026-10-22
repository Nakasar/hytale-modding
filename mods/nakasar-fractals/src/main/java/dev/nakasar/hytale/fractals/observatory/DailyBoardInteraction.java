package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.party.DailyFractals;
import dev.nakasar.hytale.fractals.progress.FractalProgress;

import java.util.List;

/**
 * {@code "Type": "Nakasar_Fractal_DailyBoard"} : tableau des fractales du jour, près de l'Archiviste. Liste au joueur
 * les fractales du jour, cochées s'il a déjà pris leur coffre aujourd'hui. Sert aussi à {@code /fractale jour}.
 */
public class DailyBoardInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_DailyBoard";

    public static final BuilderCodec<DailyBoardInteraction> CODEC = BuilderCodec
            .builder(DailyBoardInteraction.class, DailyBoardInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Tableau des fractales du jour : les liste au joueur.")
            .build();

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        show(buffer, player, playerRef);
    }

    public static void show(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player, PlayerRef playerRef) {
        FractalProgress progress = FractalProgress.get(accessor, player);
        List<String> done = progress == null ? List.of() : progress.dailyDone(DailyFractals.day());
        playerRef.sendMessage(DailyFractals.describe(done));
    }
}
