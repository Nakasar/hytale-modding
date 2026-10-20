package dev.nakasar.hytale.fractals.command;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractCommandCollection;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.observatory.LeaveInteraction;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.party.FractalCatalog;

/**
 * {@code /fractale} : secours des blocs de l'Observatoire, ouvert aux joueurs (groupe {@code hytale:Adventurer}).
 * <ul>
 *   <li>{@code niveau <n>} : règle le niveau (meneur, dans l'Observatoire) ;</li>
 *   <li>{@code groupe} : le cercle d'harmonisation, le niveau et le meneur ;</li>
 *   <li>{@code lancer <fractale>} : envoie le cercle dans la fractale (meneur, dans l'Observatoire) ;</li>
 *   <li>{@code quitter} : quitte la fractale pour l'Observatoire.</li>
 * </ul>
 */
public final class FractalCommand extends AbstractCommandCollection {

    private static final String KEYS = "nakasar_fractals.command.";

    public FractalCommand() {
        super("fractale", KEYS + "desc");
        setPermissionGroups("hytale:Adventurer");
        addSubCommand(new LevelCommand());
        addSubCommand(new GroupCommand());
        addSubCommand(new LaunchCommand());
        addSubCommand(new LeaveCommand());
    }

    private static final class LevelCommand extends AbstractPlayerCommand {
        private final RequiredArg<Integer> level = withRequiredArg("niveau", KEYS + "level.arg", ArgTypes.INTEGER);

        LevelCommand() {
            super("niveau", KEYS + "level.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Observatory.setLevel(world, player, level.get(context));
        }
    }

    private static final class GroupCommand extends AbstractPlayerCommand {
        GroupCommand() {
            super("groupe", KEYS + "group.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            player.sendMessage(FractalCatalog.isObservatory(world) ? Observatory.describe(world)
                    : Message.translation("nakasar_fractals.observatory.notHere"));
        }
    }

    private static final class LaunchCommand extends AbstractPlayerCommand {
        private final RequiredArg<String> fractal = withRequiredArg("fractale", KEYS + "launch.arg", ArgTypes.STRING);

        LaunchCommand() {
            super("lancer", KEYS + "launch.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Observatory.launch(world, player, fractal.get(context));
        }
    }

    private static final class LeaveCommand extends AbstractPlayerCommand {
        LeaveCommand() {
            super("quitter", KEYS + "leave.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            LeaveInteraction.leave(world, player);
        }
    }
}
