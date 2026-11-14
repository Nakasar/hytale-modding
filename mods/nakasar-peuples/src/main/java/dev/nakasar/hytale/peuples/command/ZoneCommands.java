package dev.nakasar.hytale.peuples.command;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.AbstractCommand;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.OptionalArg;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.zone.Climate;
import dev.nakasar.hytale.peuples.zone.Hive;
import dev.nakasar.hytale.peuples.zone.ZoneSeeder;
import dev.nakasar.hytale.peuples.zone.Zones;
import org.joml.Vector3d;

import java.util.List;

/**
 * Commandes de l'étape 8 (zones 2 et 3), sous {@code /village} :
 * <ul>
 *   <li>{@code zone} : la zone du joueur, ce que son climat lui fait, la ruche, les villages des zones ;</li>
 *   <li>{@code ruche [points]} (ops) : l'état de la ruche, ou ses points fixés ;</li>
 *   <li>{@code semer <peuple>} (ops) : cherche tout de suite un site dans la zone du peuple et y pose son village ;</li>
 *   <li>{@code climat <soif|froid|aucun>} (ops) : impose au joueur le climat d'une zone, où qu'il soit (essai).</li>
 * </ul>
 */
final class ZoneCommands {

    private static final String KEYS = VillageCommand.KEYS;

    private ZoneCommands() {
    }

    static List<AbstractCommand> all() {
        return List.of(new ZoneCommand(), new HiveCommand(), new SeedCommand(), new ClimateCommand());
    }

    private static final class ZoneCommand extends AbstractPlayerCommand {
        ZoneCommand() {
            super("zone", KEYS + "zone.desc");
            setPermissionGroups(VillageCommand.PLAYERS);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Vector3d at = player.getTransform().getPosition();
            String name = Zones.name(world, (int) Math.floor(at.x()), (int) Math.floor(at.z()));
            Integer forced = Climate.forced(player.getUuid());
            player.sendMessage(Message.translation(KEYS + "zone.where").param("zone", name == null ? "?" : name)
                    .param("forced", forced == null ? "" : " (climat imposé : zone " + forced + ")"));
            player.sendMessage(Climate.describe(store, player));
            player.sendMessage(Hive.describe(world));
            for (People p : ZoneSeeder.PEOPLES) {
                Village v = Villages.registry(world).all().stream().filter(x -> x.people() == p).findFirst().orElse(null);
                player.sendMessage(v == null
                        ? Message.translation(KEYS + "zone.noVillage").param("people", Message.translation(p.nameKey()))
                        : Message.translation(KEYS + "zone.village").param("people", Message.translation(p.nameKey()))
                                .param("name", v.name()).param("x", v.x()).param("z", v.z()));
            }
        }
    }

    private static final class HiveCommand extends AbstractPlayerCommand {
        private final OptionalArg<Integer> points = withOptionalArg("points", KEYS + "hive.arg", ArgTypes.INTEGER);

        HiveCommand() {
            super("ruche", KEYS + "hive.desc");
            requirePermission(VillageCommand.ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Integer n = points.get(context);
            if (n != null) {
                Hive.set(world, n);
            }
            player.sendMessage(Hive.describe(world));
        }
    }

    private static final class SeedCommand extends AbstractPlayerCommand {
        private final RequiredArg<String> people = withRequiredArg("peuple", KEYS + "seed.arg", ArgTypes.STRING);

        SeedCommand() {
            super("semer", KEYS + "seed.desc");
            requirePermission(VillageCommand.ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            People p = People.byId(people.get(context));
            if (p != People.FERAN && p != People.RENONCE) {
                player.sendMessage(Message.translation(KEYS + "seed.unknown").param("people", people.get(context)));
                return;
            }
            player.sendMessage(Message.translation(KEYS + "seed.searching").param("people", Message.translation(p.nameKey())));
            world.execute(() -> ZoneSeeder.start(world, p, true, v -> player.sendMessage(v == null
                    ? Message.translation(KEYS + "seed.failed").param("people", Message.translation(p.nameKey()))
                    : Message.translation(KEYS + "seed.done").param("name", v.name()).param("x", v.x()).param("y", v.y())
                            .param("z", v.z()))));
        }
    }

    private static final class ClimateCommand extends AbstractPlayerCommand {
        private final RequiredArg<String> mode = withRequiredArg("climat", KEYS + "climate.arg", ArgTypes.STRING);

        ClimateCommand() {
            super("climat", KEYS + "climate.desc");
            requirePermission(VillageCommand.ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            String m = mode.get(context).toLowerCase(java.util.Locale.ROOT);
            int zone = switch (m) {
                case "soif", "desert", "2" -> 2;
                case "froid", "givre", "3" -> 3;
                default -> 0;
            };
            Climate.force(player.getUuid(), zone);
            player.sendMessage(Message.translation(KEYS + "climate." + (zone == 2 ? "thirst" : zone == 3 ? "cold" : "off")));
        }
    }
}
