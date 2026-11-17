package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.BlockLorePage;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * {@code "Type": "Nakasar_Peuples_ReadTomb"} : lire une tombe du cimetière d'un village ({@link Cemetery}) ouvre son
 * épitaphe (page texte vanilla BlockLore) : nom, âge, métier, cause de la mort, parents et parrain.
 */
public class ReadTombInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Peuples_ReadTomb";

    public static final BuilderCodec<ReadTombInteraction> CODEC = BuilderCodec
            .builder(ReadTombInteraction.class, ReadTombInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Tombe d'un habitant : ouvre son épitaphe.")
            .build();

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        BlockPosition target = context.getTargetBlock();
        if (buffer == null || ref == null || !ref.isValid() || target == null) {
            return;
        }
        PlayerRef playerRef = buffer.getComponent(ref, PlayerRef.getComponentType());
        if (playerRef == null) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        int x = target.x;
        int y = target.y;
        int z = target.z;
        world.execute(() -> {
            if (ref.isValid()) {
                read(world, world.getEntityStore().getStore(), ref, playerRef, x, y, z);
            }
        });
    }

    private static void read(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, int x, int y, int z) {
        String k = Population.KEYS + "tomb.";
        Inhabitant h = null;
        Village village = null;
        for (Village v : Villages.registry(world).all()) {
            Inhabitant found = Population.applies(v) ? Cemetery.at(v, x, y, z) : null;
            if (found != null) {
                h = found;
                village = v;
                break;
            }
        }
        Player player = store.getComponent(ref, Player.getComponentType());
        if (player == null) {
            return;
        }
        Message title;
        Message body = Message.empty();
        if (h == null) {
            title = Message.translation(k + "unknownTitle");
            body.insert(Message.translation(k + "unknown"));
        } else {
            PopulationState p = village.population();
            title = h.fullName();
            body.insert(Message.translation(k + "lived").param("age", Population.ageText(h.died() - h.born()))
                    .param("village", village.name()));
            body.insert("\n\n");
            body.insert(h.diedJob() == null || h.diedJob().isEmpty() ? Message.translation(k + "noPost")
                    : Message.translation(k + "post").param("post", Population.postName(village, h.diedJob())));
            body.insert("\n\n");
            body.insert(Message.translation(k + "cause." + (h.cause() == null ? "age" : h.cause())));
            body.insert("\n\n");
            body.insert(h.parents().length > 0 ? Message.translation(k + "parents").param("parents", Population.parentsText(p, h))
                    : Message.translation(k + (h.founder() ? "founder" : "arrived")));
            if (h.godparentName() != null) {
                body.insert("\n\n");
                body.insert(Message.translation(k + "godparent").param("player", h.godparentName()));
            }
            long ago = Math.max(0, GameClock.day(store) - h.died());
            body.insert("\n\n");
            body.insert(Message.translation(k + "ago").param("days", ago));
        }
        player.getPageManager().openCustomPage(ref, store, new BlockLorePage(playerRef, title, body, BlockLorePage.TextAlignment.Left));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
