package dev.nakasar.hytale.peuples.command;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.OptionalArg;
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
import dev.nakasar.hytale.peuples.request.BoardPage;
import dev.nakasar.hytale.peuples.request.Criers;
import dev.nakasar.hytale.peuples.request.PlayerRequest;
import dev.nakasar.hytale.peuples.request.RequestTemplate;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.request.VillageRequest;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.reputation.Shops;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.raid.Raids;
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
 *   <li>{@code drapeaux}, {@code oublier} : drapeaux de dialogue du joueur, et leur remise à zéro ;</li>
 *   <li>étape 3 : {@code demandes} (tableau à boutons), {@code mesdemandes}, {@code prendre <n>}, {@code rendre},
 *   {@code abandonner <n>} ; opérateurs : {@code demande <modèle> [case]} (pose ce modèle au tableau),
 *   {@code renouveler} (nouveau tirage des trois cases) ;</li>
 *   <li>étape 4 : {@code reputation} (rang, jauges et droits dans le village le plus proche), {@code troc} (meilleure
 *   échoppe ouverte au rang) ; opérateurs : {@code rep <valeur>} (réputation de village), {@code reppeuple <valeur>}
 *   (réputation de peuple) ;</li>
 *   <li>étape 5 : {@code chantier} (état du chantier ou de ce qu'attend le prochain), {@code metiers} (villageois à
 *   métier) ; opérateurs : {@code lancer} (ouvre le chantier sans jauge ni matériaux), {@code finir} (finit le chantier
 *   en cours), {@code bruler [bâtiment]} (brûle un bâtiment, le village perd un palier) ; {@code palier <n>} bâtit
 *   maintenant sur-le-champ ce qui manque jusqu'au palier n ;</li>
 *   <li>étape 6 : {@code raid} (raid attendu ou en cours, bilan du dernier), {@code chaine} (étape de la chaîne du peuple) ;
 *   opérateurs : {@code raidlancer} (raid tout de suite, de jour aussi), {@code raidfinir <gagne|perdu>} (bilan tout de
 *   suite), {@code raidannuler}, {@code raidprevoir} (raid attendu cette nuit), {@code chaineetape <0-5>} (étapes de
 *   chaîne faites).</li>
 * </ul>
 */
public final class VillageCommand extends AbstractCommandCollection {

    public static final String ADMIN = "nakasar.peuples.admin";
    static final String KEYS = "nakasar_peuples.command.";
    static final String PLAYERS = "hytale:Adventurer";

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
        addSubCommand(new RequestsCommand());
        addSubCommand(new MyRequestsCommand());
        addSubCommand(new TakeCommand());
        addSubCommand(new TurnInCommand());
        addSubCommand(new AbandonCommand());
        addSubCommand(new ForceRequestCommand());
        addSubCommand(new RedrawCommand());
        addSubCommand(new ReputationCommand());
        addSubCommand(new SetReputationCommand(false));
        addSubCommand(new SetReputationCommand(true));
        addSubCommand(new TradeCommand());
        addSubCommand(new ChantierCommand());
        addSubCommand(new StartChantierCommand());
        addSubCommand(new FinishChantierCommand());
        addSubCommand(new BurnCommand());
        addSubCommand(new JobsCommand());
        addSubCommand(new RaidCommand());
        addSubCommand(new RaidStartCommand());
        addSubCommand(new RaidFinishCommand());
        addSubCommand(new RaidCancelCommand());
        addSubCommand(new RaidScheduleCommand());
        addSubCommand(new ChainCommand());
        addSubCommand(new ChainStepCommand());
        addSubCommand(new ZoneOneCommands.KlopsCommand());
        addSubCommand(new ZoneOneCommands.WarPaintCommand());
        ZoneCommands.all().forEach(this::addSubCommand);
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
        private final OptionalArg<String> people = withOptionalArg("peuple", KEYS + "generate.people", ArgTypes.STRING);

        GenerateCommand() {
            super("generer", KEYS + "generate.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            // Étape 7 : « /village generer trork » pose un camp trork.
            People p = people.get(context) == null ? People.KWEEBEC : People.byId(people.get(context));
            if (p == null) {
                player.sendMessage(Message.translation(Villages.MESSAGES + "unknownPeople").param("people", people.get(context)));
                return;
            }
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
                Raids.cancel(world, village);
                Criers.remove(store, village.id());
                Villagers.remove(store, village.id());
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
            if (village == null) {
                return;
            }
            int target = tier.get(context);
            Chantiers.buildNow(world, village, target, pasted -> {
                Villagers.forgetGround();
                if (pasted < 0) {
                    player.sendMessage(Message.translation(Chantiers.KEYS + "busy"));
                    return;
                }
                player.sendMessage(Message.translation(Villages.MESSAGES + "tierSet").param("name", village.name())
                        .param("tier", Message.translation(Tiers.nameKey(village.tier()))));
                player.sendMessage(Message.translation(Chantiers.KEYS + "builtNow").param("count", pasted));
            });
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
                player.sendMessage(VillageBoard.body(world, village, store, ref));
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

    // ---- Demandes (étape 3) ----

    private static final class RequestsCommand extends PlayerCommand {
        RequestsCommand() {
            super("demandes", KEYS + "requests.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                BoardPage.open(world, store, ref, player, village);
            }
        }
    }

    private static final class MyRequestsCommand extends PlayerCommand {
        MyRequestsCommand() {
            super("mesdemandes", KEYS + "mine.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            PeuplesPlayer state = PeuplesPlayer.get(store, ref);
            List<PlayerRequest> mine = state == null ? List.of() : state.requests();
            player.sendMessage(Message.translation(KEYS + "mine.header").param("count", mine.size()));
            Vector3d at = Requests.position(store, ref);
            for (PlayerRequest r : mine) {
                RequestTemplate t = r.template();
                Village village = Villages.registry(world).byId(r.villageId());
                if (t == null || village == null) {
                    continue;
                }
                int slot = Requests.slotOf(village, r.id());
                player.sendMessage(Message.translation(KEYS + "mine.line").param("village", village.name())
                        .param("slot", slot < 0 ? "-" : Integer.toString(slot + 1)).param("title", Requests.title(t))
                        .param("task", Requests.task(r, t, at, Requests.target(player, r, t, village))));
            }
        }
    }

    private static final class TakeCommand extends PlayerCommand {
        private final RequiredArg<Integer> number = withRequiredArg("numero", KEYS + "take.arg", ArgTypes.INTEGER);

        TakeCommand() {
            super("prendre", KEYS + "take.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Requests.refresh(store, village);
                Requests.take(world, store, ref, player, village, number.get(context) - 1);
            }
        }
    }

    private static final class TurnInCommand extends PlayerCommand {
        TurnInCommand() {
            super("rendre", KEYS + "turnIn.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Requests.turnIn(world, store, ref, player, village);
            }
        }
    }

    private static final class AbandonCommand extends PlayerCommand {
        private final RequiredArg<Integer> number = withRequiredArg("numero", KEYS + "take.arg", ArgTypes.INTEGER);

        AbandonCommand() {
            super("abandonner", KEYS + "abandon.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            int slot = number.get(context) - 1;
            VillageRequest[] board = village.requests();
            if (slot < 0 || slot >= board.length || board[slot] == null
                    || !Requests.abandon(world, store, ref, player, board[slot].id())) {
                player.sendMessage(Message.translation(KEYS + "abandon.none").param("slot", slot + 1));
            }
        }
    }

    private static final class ForceRequestCommand extends AbstractPlayerCommand {
        private final RequiredArg<String> template = withRequiredArg("modele", KEYS + "force.arg", ArgTypes.STRING);
        private final OptionalArg<Integer> slot = withOptionalArg("case", KEYS + "force.slot", ArgTypes.INTEGER);

        ForceRequestCommand() {
            super("demande", KEYS + "force.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            RequestTemplate t = RequestTemplate.get(template.get(context));
            if (t == null) {
                player.sendMessage(Message.translation(KEYS + "force.unknown").param("id", template.get(context)));
                return;
            }
            Requests.refresh(store, village);
            Integer n = slot.get(context);
            int index = n == null ? 0 : n - 1;
            if (index < 0 || index >= Requests.SLOTS) {
                player.sendMessage(Message.translation(Requests.KEYS + "noSuchSlot").param("slot", index + 1));
                return;
            }
            Requests.force(store, village, index, t);
            player.sendMessage(Message.translation(KEYS + "force.done").param("slot", index + 1).param("title", Requests.title(t))
                    .param("name", village.name()));
        }
    }

    private static final class RedrawCommand extends AbstractPlayerCommand {
        RedrawCommand() {
            super("renouveler", KEYS + "redraw.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            Requests.refresh(store, village);
            for (int i = 0; i < Requests.SLOTS; i++) {
                Requests.redraw(store, village, i);
            }
            player.sendMessage(Message.translation(KEYS + "redraw.done").param("name", village.name()));
        }
    }

    // ---- Réputation (étape 4) ----

    private static final class ReputationCommand extends PlayerCommand {
        ReputationCommand() {
            super("reputation", KEYS + "reputation.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            Reputations.Standing standing = Reputations.standing(store, ref, village);
            player.sendMessage(Message.raw(village.name()).bold(true).color("#e8c46a"));
            player.sendMessage(Message.translation(KEYS + "reputation.rank").param("rank", Reputations.describe(standing.rank(), standing.value())));
            player.sendMessage(Message.translation(KEYS + "reputation.village").param("rank", Reputations.describe(standing.villageRank(), standing.village())));
            player.sendMessage(Message.translation(KEYS + "reputation.people").param("people", Message.translation(village.people().nameKey()))
                    .param("rank", Reputations.describe(standing.peopleRank(), standing.people())));
            player.sendMessage(Message.translation(KEYS + "reputation.perks").param("perks", Message.translation(standing.rank().perksKey())));
            String shop = Shops.best(village, standing.rank());
            player.sendMessage(Message.translation(shop == null ? KEYS + "reputation.noShop" : KEYS + "reputation.shop")
                    .param("shop", shop == null ? "" : shop));
        }
    }

    private static final class SetReputationCommand extends AbstractPlayerCommand {
        private final RequiredArg<Integer> value = withRequiredArg("valeur", KEYS + "rep.arg", ArgTypes.INTEGER);
        private final boolean people;

        SetReputationCommand(boolean people) {
            super(people ? "reppeuple" : "rep", KEYS + (people ? "reppeople.desc" : "rep.desc"));
            this.people = people;
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            int v = value.get(context);
            if (people) {
                Reputations.setPeople(store, ref, village.people(), v);
            } else {
                Reputations.setVillage(store, ref, player, village, v);
            }
            Reputations.Standing standing = Reputations.standing(store, ref, village);
            player.sendMessage(Message.translation(KEYS + "rep.done").param("name", village.name())
                    .param("village", standing.village()).param("people", standing.people())
                    .param("rank", Message.translation(standing.rank().nameKey())));
        }
    }

    private static final class TradeCommand extends PlayerCommand {
        TradeCommand() {
            super("troc", KEYS + "trade.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Shops.open(store, ref, player, village, Shops.best(village, Reputations.rank(store, ref, village)));
            }
        }
    }

    private static final class ChantierCommand extends PlayerCommand {
        ChantierCommand() {
            super("chantier", KEYS + "chantier.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            player.sendMessage(Message.raw(village.name()).bold(true).color("#e8c46a"));
            player.sendMessage(Message.translation(Villages.MESSAGES + "listLine").param("name", village.name())
                    .param("people", Message.translation(village.people().nameKey()))
                    .param("tier", Message.translation(Tiers.nameKey(village.tier())))
                    .param("x", village.x()).param("y", village.y()).param("z", village.z()));
            List<Message> lines = VillageBoard.chantierLines(world, store, village);
            if (lines.isEmpty()) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "none"));
            }
            lines.forEach(player::sendMessage);
            Chantiers.Block blocker = Chantiers.blocker(world, village, false);
            if (blocker != Chantiers.Block.NONE && blocker != Chantiers.Block.ACTIVE) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "blocker." + blocker.name()));
            }
        }
    }

    private static final class StartChantierCommand extends AbstractPlayerCommand {
        StartChantierCommand() {
            super("lancer", KEYS + "start.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            Chantiers.Block blocker = Chantiers.start(world, village, true, state -> {
                Villagers.forgetGround();
                player.sendMessage(Message.translation(Chantiers.KEYS + "startedCommand").param("count", state.buildings().length)
                        .param("skipped", state.skipped().length));
            });
            if (blocker != Chantiers.Block.NONE) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "blocker." + blocker.name()));
            }
        }
    }

    private static final class FinishChantierCommand extends AbstractPlayerCommand {
        FinishChantierCommand() {
            super("finir", KEYS + "finish.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            if (village.chantier() == null) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "none"));
                return;
            }
            if (!Chantiers.finish(world, village, Villagers::forgetGround)) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "busy"));
            }
        }
    }

    private static final class BurnCommand extends AbstractPlayerCommand {
        private final OptionalArg<String> building = withOptionalArg("batiment", KEYS + "burn.arg", ArgTypes.STRING);

        BurnCommand() {
            super("bruler", KEYS + "burn.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            var burnt = Chantiers.burn(world, village, building.get(context), true);
            Villagers.forgetGround();
            if (burnt == null) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "burnNothing"));
            }
        }
    }

    private static final class JobsCommand extends PlayerCommand {
        JobsCommand() {
            super("metiers", KEYS + "jobs.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            var layout = Chantiers.layout(village);
            if (layout == null) {
                player.sendMessage(Message.translation(Chantiers.KEYS + "noLayout"));
                return;
            }
            var present = Villagers.jobs(village);
            player.sendMessage(Message.translation(Chantiers.KEYS + "jobs.header").param("name", village.name()));
            for (var job : layout.jobs()) {
                String state;
                if (job.tier() > village.tier()) {
                    state = "jobs.tier";
                } else if (!job.building().isEmpty() && !village.isStanding(job.building())) {
                    state = "jobs.noBuilding";
                } else {
                    state = Boolean.TRUE.equals(present.get(job.id())) ? "jobs.here" : "jobs.away";
                }
                player.sendMessage(Message.translation(Chantiers.KEYS + "jobs.line")
                        .param("job", Message.translation("nakasar_peuples.job." + job.id()))
                        .param("state", Message.translation(Chantiers.KEYS + state).param("tier", Message.translation(Tiers.nameKey(job.tier())))
                                .param("building", job.building().isEmpty() ? Message.raw("-") : Message.translation(Chantiers.buildingKey(job.building())))));
            }
            for (var e : present.entrySet()) {
                if (e.getKey().startsWith("chantier:")) {
                    player.sendMessage(Message.translation(Chantiers.KEYS + "jobs.helper")
                            .param("building", Message.translation(Chantiers.buildingKey(e.getKey().substring("chantier:".length())))));
                }
            }
        }
    }

    // ---- Étape 6 : raids et chaîne ----

    private static final class RaidCommand extends PlayerCommand {
        RaidCommand() {
            super("raid", KEYS + "raid.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            player.sendMessage(Message.raw(village.name()).bold(true).color("#e8c46a"));
            player.sendMessage(Raids.status(store, village));
            Message last = Raids.lastReport(village);
            if (last != null) {
                player.sendMessage(last);
            }
        }
    }

    private static final class RaidStartCommand extends AbstractPlayerCommand {
        RaidStartCommand() {
            super("raidlancer", KEYS + "raidStart.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null && !Raids.startNow(world, village)) {
                player.sendMessage(Message.translation(Raids.KEYS + "command.cannotStart"));
            }
        }
    }

    private static final class RaidFinishCommand extends AbstractPlayerCommand {
        private final RequiredArg<String> outcome = withRequiredArg("issue", KEYS + "raidFinish.arg", ArgTypes.STRING);

        RaidFinishCommand() {
            super("raidfinir", KEYS + "raidFinish.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            String o = outcome.get(context).toLowerCase(java.util.Locale.ROOT);
            boolean victory = o.startsWith("g") || o.startsWith("w");
            if (!Raids.finishNow(world, village, victory)) {
                player.sendMessage(Message.translation(Raids.KEYS + "command.noRaid"));
            }
        }
    }

    private static final class RaidCancelCommand extends AbstractPlayerCommand {
        RaidCancelCommand() {
            super("raidannuler", KEYS + "raidCancel.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Raids.cancel(world, village);
                player.sendMessage(Message.translation(Raids.KEYS + "command.cancelled").param("village", village.name()));
            }
        }
    }

    private static final class RaidScheduleCommand extends AbstractPlayerCommand {
        RaidScheduleCommand() {
            super("raidprevoir", KEYS + "raidSchedule.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village != null) {
                Raids.schedule(village, dev.nakasar.hytale.peuples.request.GameClock.day(store), "Command");
                player.sendMessage(Raids.status(store, village));
            }
        }
    }

    /** Étapes de chaîne : drapeaux {@code <Peuple>_Chain_<n>}. */
    private static String chainFlag(Village village, int step) {
        return village.people().id() + "_Chain_" + step;
    }

    private static final class ChainCommand extends PlayerCommand {
        ChainCommand() {
            super("chaine", KEYS + "chain.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            dev.nakasar.hytale.peuples.player.PeuplesPlayer data = dev.nakasar.hytale.peuples.player.PeuplesPlayer.ensure(store, ref);
            int done = 0;
            while (done < 5 && data.hasFlag(chainFlag(village, done + 1))) {
                done++;
            }
            player.sendMessage(Message.translation("nakasar_peuples.chain.status")
                    .param("people", Message.translation(village.people().nameKey())).param("done", done)
                    .param("next", Message.translation("nakasar_peuples.chain." + village.people().id() + ".step" + Math.min(5, done + 1))));
        }
    }

    private static final class ChainStepCommand extends AbstractPlayerCommand {
        private final RequiredArg<Integer> steps = withRequiredArg("etapes", KEYS + "chainStep.arg", ArgTypes.INTEGER);

        ChainStepCommand() {
            super("chaineetape", KEYS + "chainStep.desc");
            requirePermission(ADMIN);
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village village = nearest(world, player);
            if (village == null) {
                return;
            }
            int n = Math.max(0, Math.min(5, steps.get(context)));
            dev.nakasar.hytale.peuples.player.PeuplesPlayer data = dev.nakasar.hytale.peuples.player.PeuplesPlayer.ensure(store, ref);
            for (int i = 1; i <= 5; i++) {
                data.setFlag(chainFlag(village, i), i <= n);
            }
            player.sendMessage(Message.translation("nakasar_peuples.chain.set").param("done", n));
        }
    }
}
