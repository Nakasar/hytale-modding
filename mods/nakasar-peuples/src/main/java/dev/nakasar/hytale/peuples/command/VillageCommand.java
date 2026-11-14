package dev.nakasar.hytale.peuples.command;

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
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageNames;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.List;

/**
 * {@code /village} : commande de test du socle (étape 1 du plan). Les joueurs (groupe {@code hytale:Adventurer})
 * consultent et parlent ; fonder, effacer et régler un village demandent la permission {@value #ADMIN} (opérateurs).
 * <ul>
 *   <li>{@code fonder <nom> <peuple>} : cœur sous les pieds, dépôt à 2 blocs à l'est, tableau à 2 blocs à l'ouest ;</li>
 *   <li>{@code generer} (étape 2) : bâtit un village kweebec complet (plan {@code Kweebec_Oak}, palier 0) centré sous
 *   les pieds, terrain aplani ;</li>
 *   <li>{@code site} : nom, position, distance et direction du village le plus proche, à toute distance ;</li>
 *   <li>{@code effacer} : retire le village le plus proche (cœur et tableau ; le dépôt reste avec son contenu) ;</li>
 *   <li>{@code essor <n>}, {@code palier <n>} : règle la jauge et le palier du village le plus proche ;</li>
 *   <li>{@code info}, {@code tableau}, {@code liste} : état du village le plus proche, son tableau, tous les villages ;</li>
 *   <li>{@code parler <dialogue>} : ouvre un dialogue dans la fenêtre du mod ; {@code tchat <dialogue>} : le même dans le
 *   tchat, puis {@code repondre <n>} (0 : partir) ;</li>
 *   <li>{@code drapeaux}, {@code oublier} : drapeaux de dialogue du joueur, et leur remise à zéro.</li>
 * </ul>
 */
public final class VillageCommand extends AbstractCommandCollection {

    public static final String ADMIN = "nakasar.peuples.admin";
    private static final String KEYS = "nakasar_peuples.command.";
    private static final String PLAYERS = "hytale:Adventurer";

    public VillageCommand() {
        super("village", KEYS + "desc");
        setPermissionGroups(PLAYERS);
        addSubCommand(new FoundCommand());
        addSubCommand(new GenerateCommand());
        addSubCommand(new SiteCommand());
        addSubCommand(new DissolveCommand());
        addSubCommand(new EssorCommand());
        addSubCommand(new TierCommand());
        addSubCommand(new InfoCommand());
        addSubCommand(new BoardCommand());
        addSubCommand(new ListCommand());
        addSubCommand(new TalkCommand());
        addSubCommand(new ChatTalkCommand());
        addSubCommand(new AnswerCommand());
        addSubCommand(new FlagsCommand());
        addSubCommand(new ForgetCommand());
    }

    /** Sous-commande ouverte aux joueurs. */
    private abstract static class PlayerCommand extends AbstractPlayerCommand {
        PlayerCommand(String name, String description) {
            super(name, description);
            setPermissionGroups(PLAYERS);
        }
    }

    /** Village le plus proche du joueur (dans {@value Villages#RADIUS} blocs), ou null avec un message. */
    static Village nearest(World world, PlayerRef player) {
        Vector3d at = player.getTransform().getPosition();
        Village village = Villages.registry(world).nearest(at.x(), at.y(), at.z(), Villages.RADIUS);
        if (village == null) {
            player.sendMessage(Message.translation(Villages.MESSAGES + "none").param("radius", Villages.RADIUS));
        }
        return village;
    }

    private static final class FoundCommand extends AbstractPlayerCommand {
        private final RequiredArg<String> name = withRequiredArg("nom", KEYS + "found.name", ArgTypes.STRING);
        private final RequiredArg<String> people = withRequiredArg("peuple", KEYS + "found.people", ArgTypes.STRING);

        FoundCommand() {
            super("fonder", KEYS + "found.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            People p = People.byId(people.get(context));
            if (p == null) {
                player.sendMessage(Message.translation(Villages.MESSAGES + "unknownPeople").param("people", people.get(context)));
                return;
            }
            Vector3d at = player.getTransform().getPosition();
            String villageName = name.get(context).replace('_', ' ');
            Villages.Founding founding = Villages.found(world, villageName, p, (int) Math.floor(at.x()), (int) Math.floor(at.y()),
                    (int) Math.floor(at.z()));
            if (founding.village() == null) {
                player.sendMessage(founding.error());
                return;
            }
            Village v = founding.village();
            player.sendMessage(Message.translation(Villages.MESSAGES + "founded").param("name", v.name())
                    .param("people", Message.translation(p.nameKey())).param("x", v.x()).param("y", v.y()).param("z", v.z()));
        }
    }

    private static final class GenerateCommand extends AbstractPlayerCommand {
        GenerateCommand() {
            super("generer", KEYS + "generate.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            People p = People.KWEEBEC;
            VillageLayout layout = VillageLayout.get(p.layout());
            if (layout == null) {
                player.sendMessage(Message.translation(Villages.MESSAGES + "layoutMissing").param("layout", p.layout()));
                return;
            }
            Vector3d at = player.getTransform().getPosition();
            int x = (int) Math.floor(at.x());
            int z = (int) Math.floor(at.z());
            String villageName = VillageNames.pick(world, p);
            player.sendMessage(Message.translation(Villages.MESSAGES + "generating").param("name", villageName));
            world.execute(() -> VillageBuilder.generate(world, layout, villageName, x, z, false, result -> {
                if (result.village() == null) {
                    player.sendMessage(result.error());
                    return;
                }
                Village v = result.village();
                player.sendMessage(Message.translation(Villages.MESSAGES + "generated").param("name", v.name())
                        .param("count", v.built().length).param("x", v.x()).param("y", v.y()).param("z", v.z()));
            }));
        }
    }

    private static final class SiteCommand extends AbstractPlayerCommand {
        SiteCommand() {
            super("site", KEYS + "site.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Vector3d at = player.getTransform().getPosition();
            Village best = null;
            double bestD = Double.MAX_VALUE;
            for (Village v : Villages.registry(world).all()) {
                double d = v.horizontalDistanceSquared(at.x(), at.z());
                if (d < bestD) {
                    bestD = d;
                    best = v;
                }
            }
            if (best == null) {
                player.sendMessage(Message.translation(Villages.MESSAGES + "noneInWorld"));
                return;
            }
            double dx = best.x() - at.x();
            double dz = best.z() - at.z();
            player.sendMessage(Message.translation(Villages.MESSAGES + "siteLine").param("name", best.name())
                    .param("x", best.x()).param("y", best.y()).param("z", best.z())
                    .param("distance", (int) Math.round(Math.sqrt(bestD)))
                    .param("direction", Message.translation(Villages.MESSAGES + "dir." + direction(dx, dz))));
        }

        /** Point cardinal de (dx, dz) : nord = -Z, est = +X. */
        static String direction(double dx, double dz) {
            String[] dirs = {"e", "se", "s", "sw", "w", "nw", "n", "ne"};
            double angle = Math.atan2(dz, dx);
            int i = (int) Math.floorMod(Math.round(angle / (Math.PI / 4)), 8L);
            return dirs[i];
        }
    }

    private static final class DissolveCommand extends AbstractPlayerCommand {
        DissolveCommand() {
            super("effacer", KEYS + "dissolve.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Villages.dissolve(world, village);
                player.sendMessage(Message.translation(Villages.MESSAGES + "dissolved").param("name", village.name()));
            }
        }
    }

    private static final class EssorCommand extends AbstractPlayerCommand {
        private final RequiredArg<Integer> amount = withRequiredArg("quantite", KEYS + "essor.arg", ArgTypes.INTEGER);

        EssorCommand() {
            super("essor", KEYS + "essor.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                int gained = Villages.addEssor(village, amount.get(context));
                player.sendMessage(Message.translation(Villages.MESSAGES + "essorGained").param("amount", gained).param("name", village.name()));
            }
        }
    }

    private static final class TierCommand extends AbstractPlayerCommand {
        private final RequiredArg<Integer> tier = withRequiredArg("palier", KEYS + "tier.arg", ArgTypes.INTEGER);

        TierCommand() {
            super("palier", KEYS + "tier.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Villages.setTier(village, tier.get(context));
                player.sendMessage(Message.translation(Villages.MESSAGES + "tierSet").param("name", village.name())
                        .param("tier", Message.translation(Tiers.nameKey(village.tier()))));
            }
        }
    }

    private static final class InfoCommand extends PlayerCommand {
        InfoCommand() {
            super("info", KEYS + "info.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                player.sendMessage(Message.raw(village.name()).bold(true).color("#e8c46a"));
                player.sendMessage(VillageBoard.body(world, village));
                if (!Villages.heartPresent(world, village)) {
                    player.sendMessage(Message.translation(Villages.MESSAGES + "heartMissing"));
                }
            }
        }
    }

    private static final class BoardCommand extends PlayerCommand {
        BoardCommand() {
            super("tableau", KEYS + "board.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                VillageBoard.open(world, store, ref, player, village);
            }
        }
    }

    private static final class ListCommand extends PlayerCommand {
        ListCommand() {
            super("liste", KEYS + "list.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            List<Village> all = Villages.registry(world).all();
            player.sendMessage(Message.translation(Villages.MESSAGES + "listHeader").param("count", all.size()));
            for (Village v : all) {
                player.sendMessage(Message.translation(Villages.MESSAGES + "listLine").param("name", v.name())
                        .param("people", Message.translation(v.people().nameKey()))
                        .param("tier", Message.translation(Tiers.nameKey(v.tier())))
                        .param("x", v.x()).param("y", v.y()).param("z", v.z()));
            }
        }
    }

    /** Dialogue d'id `id`, ou null avec un message. */
    static Dialogue dialogue(PlayerRef player, String id) {
        Dialogue dialogue = Dialogue.get(id);
        if (dialogue == null) {
            player.sendMessage(Message.translation(Dialogues.KEYS + "unknown").param("id", id));
        }
        return dialogue;
    }

    private static final class TalkCommand extends PlayerCommand {
        private final RequiredArg<String> id = withRequiredArg("dialogue", KEYS + "talk.arg", ArgTypes.STRING);

        TalkCommand() {
            super("parler", KEYS + "talk.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Dialogue dialogue = dialogue(player, id.get(context));
            if (dialogue != null) {
                Dialogues.openPage(world, store, ref, player, dialogue);
            }
        }
    }

    private static final class ChatTalkCommand extends PlayerCommand {
        private final RequiredArg<String> id = withRequiredArg("dialogue", KEYS + "talk.arg", ArgTypes.STRING);

        ChatTalkCommand() {
            super("tchat", KEYS + "chat.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Dialogue dialogue = dialogue(player, id.get(context));
            if (dialogue != null) {
                Dialogues.openChat(world, store, ref, player, dialogue);
            }
        }
    }

    private static final class AnswerCommand extends PlayerCommand {
        private final RequiredArg<Integer> number = withRequiredArg("numero", KEYS + "answer.arg", ArgTypes.INTEGER);

        AnswerCommand() {
            super("repondre", KEYS + "answer.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Dialogues.answerChat(world, store, ref, player, number.get(context));
        }
    }

    private static final class FlagsCommand extends PlayerCommand {
        FlagsCommand() {
            super("drapeaux", KEYS + "flags.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            PeuplesPlayer state = PeuplesPlayer.get(store, ref);
            String flags = state == null || state.flags().isEmpty() ? "-" : String.join(", ", state.flags());
            player.sendMessage(Message.translation(KEYS + "flags.list").param("flags", flags));
        }
    }

    private static final class ForgetCommand extends PlayerCommand {
        ForgetCommand() {
            super("oublier", KEYS + "forget.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            PeuplesPlayer state = PeuplesPlayer.get(store, ref);
            if (state != null) {
                state.clearFlags();
            }
            player.sendMessage(Message.translation(KEYS + "forget.done"));
        }
    }
}
