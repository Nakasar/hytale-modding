package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.server.core.Message;
import dev.nakasar.hytale.fractals.hammer.Hammer;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Fractal_CliffsideUse", "Action": "…"} : blocs utilisables de la Falaise. Nos instances
 * refusent les coups sur les blocs ; l'interaction « Utiliser » d'un bloc, elle, passe. Actions :
 * {@code Hammer_Rack} (prendre le marteau), {@code Cliffside_Lever} (couper un piège, {@link Traps}),
 * {@code Cage_Door} (forcer la porte d'une cage, {@link Cages}), {@code Hammer_Dropped} (ramasser le marteau
 * lâché au sol, {@link Hammer#pickUp}).
 */
public class CliffsideUseInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_CliffsideUse";

    public static final BuilderCodec<CliffsideUseInteraction> CODEC = BuilderCodec
            .builder(CliffsideUseInteraction.class, CliffsideUseInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Bloc utilisable de la Falaise : ratelier, levier ou porte de cage.")
            .append(new KeyedCodec<>("Action", Codec.STRING), (i, v) -> i.action = v, i -> i.action)
            .documentation("Hammer_Rack, Cliffside_Lever, Cage_Door ou Hammer_Dropped.").add()
            .build();

    private String action;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getEntity();
        if (buffer == null || ref == null || !ref.isValid() || action == null) {
            return;
        }
        PlayerRef player = buffer.getComponent(ref, PlayerRef.getComponentType());
        World world = buffer.getExternalData().getWorld();
        BlockPosition target = context.getTargetBlock();
        if (player == null || !Cliffside.isCliffside(world)) {
            return;
        }
        int x = target == null ? 0 : target.x;
        int y = target == null ? 0 : target.y;
        int z = target == null ? 0 : target.z;
        boolean located = target != null;
        // Hors du système en cours : la suite touche à l'inventaire, aux blocs et aux PNJ.
        world.execute(() -> {
            if (!ref.isValid()) {
                return;
            }
            Store<EntityStore> store = world.getEntityStore().getStore();
            Cliffside.State st = Cliffside.state(world);
            switch (action) {
                case "Hammer_Rack" -> Cliffside.takeHammer(world, store, ref, player);
                case "Cliffside_Lever" -> {
                    if (located) {
                        st.traps.pull(world, store, st, ref, player, x, y, z);
                    }
                }
                case "Cage_Door" -> {
                    if (located) {
                        st.cages.pry(world, store, st, player, x, y, z);
                    }
                }
                case "Hammer_Dropped" -> {
                    if (!located) {
                        return;
                    }
                    if (Hammer.carries(store, ref)) {
                        player.sendMessage(Message.translation("nakasar_fractals_cliffside.hammer.have"));
                    } else {
                        Hammer.pickUp(world, store, ref, x, y, z);
                    }
                }
                default -> {
                }
            }
        });
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
