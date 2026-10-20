package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.GlobalSpawnProvider;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

/**
 * Barrières, points de retour et fin des fractales écrites après la Falaise (Inclassable, Volcanique) : mêmes gestes
 * que {@code cliffside.Cliffside}, qui garde les siens.
 */
public final class Gates {

    public static final String REWARD_CHEST = "Nakasar_Fractal_Reward_Chest";
    public static final String EXIT_STONE = "Nakasar_Fractal_Exit_Stone";

    private Gates() {
    }

    /** Retire les blocs de la barrière `cells` (éclats au milieu) et l'annonce par `messageKey` (null : rien). */
    public static void open(World world, Store<EntityStore> store, int[][] cells, String messageKey) {
        ChunkStore chunks = world.getChunkStore();
        for (int[] c : cells) {
            WorldBlocks.clear(chunks, c[0], c[1], c[2]);
        }
        int[] mid = cells[cells.length / 2];
        Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", new Vector3d(mid[0] + 0.5, mid[1], mid[2] + 0.5), 1.5f);
        if (messageKey != null) {
            Spawns.tellAll(world, Message.translation(messageKey));
        }
    }

    /** Déplace le point d'apparition du monde (réapparition, filet anti-chute). */
    public static void checkpoint(World world, double[] at, String messageKey) {
        world.getWorldConfig().setSpawnProvider(new GlobalSpawnProvider(new Transform(new Vector3d(at[0], at[1], at[2]), new Rotation3f())));
        world.getWorldConfig().markChanged();
        Spawns.tellAll(world, Message.translation(messageKey));
    }

    /** Fin de la fractale : coffre de récompense et pierre de sortie, partie terminée, titre. */
    public static void victory(World world, int[] chest, int[] exit, String titleKey, String subtitleKey) {
        ChunkStore chunks = world.getChunkStore();
        WorldBlocks.set(chunks, chest[0], chest[1], chest[2], REWARD_CHEST, 0);
        WorldBlocks.set(chunks, exit[0], exit[1], exit[2], EXIT_STONE, 0);
        FractalRuns.complete(world);
        EventTitleUtil.showEventTitleToWorld(Message.translation(titleKey), Message.translation(subtitleKey),
                EventTitleStyle.Major, null, 4f, 0.4f, 1f, world);
    }
}
