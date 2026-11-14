package dev.nakasar.hytale.peuples.command;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.klops.Klops;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.trork.WarPaint;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/** Sous-commandes de l'étape 7 (camp trork, Peinture de guerre, Klops), à part de {@link VillageCommand}. */
final class ZoneOneCommands {

    private static final String KEYS = "nakasar_peuples.command.";
    private static final String PLAYERS = "hytale:Adventurer";

    private ZoneOneCommands() {
    }

    /** {@code /village klops} : où est le Klops aujourd'hui, où il sera demain, et le colis porté. */
    static final class KlopsCommand extends AbstractPlayerCommand {
        KlopsCommand() {
            super("klops", KEYS + "klops.desc");
            setPermissionGroups(PLAYERS);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            player.sendMessage(Klops.route(world, store, ref));
            String id = Klops.parcelDestination(PeuplesPlayer.get(store, ref));
            Village to = id == null ? null : Villages.registry(world).byId(id);
            if (to != null) {
                player.sendMessage(Message.translation(Klops.KEYS + "parcelFor").param("village", to.name()));
            }
        }
    }

    /** {@code /village peinture} (op) : donne le pot de Peinture de guerre, sans la chaîne trork. */
    static final class WarPaintCommand extends AbstractPlayerCommand {
        WarPaintCommand() {
            super("peinture", KEYS + "warPaint.desc");
            requirePermission(VillageCommand.ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Requests.give(store, ref, new ItemStack(WarPaint.ITEM, 1));
            player.sendMessage(Message.translation(WarPaint.KEYS + "given"));
        }
    }
}
