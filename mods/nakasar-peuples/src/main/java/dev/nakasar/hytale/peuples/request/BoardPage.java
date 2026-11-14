package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomPageLifetime;
import com.hypixel.hytale.protocol.packets.interface_.CustomUIEventBindingType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.InteractiveCustomUIPage;
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Le tableau du village à boutons (maquette /mnt/project-files/peuples/maquettes/tableau_village.png) : à gauche les
 * trois demandes du jour (titre, avancement ou récompense, bouton Prendre ou Abandonner), à droite l'état du village
 * (même texte que la page texte du tableau) et « Rendre » pour les objets portés. Mise en page {@value #LAYOUT} du pack,
 * bâtie sur les modèles vanilla de {@code Common.ui} (cadre décoré, boutons, bouton retour), comme les pages vanilla
 * BlockLorePage et ConfirmationPage d'Assets.zip.
 *
 * <p>Secours si la page ne s'affiche pas : utiliser le panneau accroupi (page texte vanilla) et
 * {@code /village demandes}, {@code prendre}, {@code rendre}, {@code abandonner}.
 */
public final class BoardPage extends InteractiveCustomUIPage<BoardPage.Event> {

    public static final String LAYOUT = "Pages/Nakasar/Peuples/BoardPage.ui";
    private static final String KEYS = "nakasar_peuples.boardPage.";

    /** Donnée d'un clic : {@code Take0..2}, {@code Abandon0..2}, {@code TurnIn}, {@code Text}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;

    public BoardPage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    /** Ouvre le tableau à boutons du village (thread du monde). */
    public static void open(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        Requests.refresh(store, village);
        player.getPageManager().openCustomPage(ref, store, new BoardPage(playerRef, village));
    }

    // Les libellés (Label) reçoivent leur texte par « .TextSpans », comme les pages vanilla (BlockLorePage,
    // ConfirmationPage, RespawnPage) : un message composé (Message.empty() + insert, cas du texte d'état) envoyé
    // sur « .Text » fait planter le client (« No parameterless constructor defined for type 'System.String' »).
    // Les boutons (TextButton) gardent « .Text » avec une simple traduction, comme ConfirmationPage : sur « .Text »,
    // un paramètre Message n'est pas remplacé par le client (le bouton afficherait « {text} »).
    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        cmd.append(LAYOUT);
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(Villages.MESSAGES + "boardOrphan"));
            return;
        }
        cmd.set("#PageTitle.TextSpans", Message.translation("nakasar_peuples.board.title").param("name", village.name()));
        cmd.set("#RequestsHeader.TextSpans", Message.translation(KEYS + "requests"));
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        VillageRequest[] board = village.requests();
        for (int i = 0; i < Requests.SLOTS; i++) {
            VillageRequest request = i < board.length ? board[i] : null;
            String n = Integer.toString(i);
            RequestTemplate t = request == null ? null : request.template();
            if (t == null) {
                cmd.set("#Request" + n + ".Visible", false);
                continue;
            }
            cmd.set("#Request" + n + ".Visible", true);
            cmd.set("#Title" + n + ".TextSpans", Message.translation(KEYS + "title").param("number", i + 1)
                    .param("type", Message.translation(t.type().nameKey())).param("title", Requests.title(t)));
            Requests.Status status = Requests.status(data, request);
            Message detail;
            Message action;
            String event;
            switch (status) {
                case TAKEN -> {
                    PlayerRequest mine = data.request(request.id());
                    detail = Requests.task(store, playerRef, mine, t, village, Requests.position(store, ref));
                    action = Message.translation(KEYS + "abandon");
                    event = "Abandon" + n;
                }
                case DONE -> {
                    detail = Message.translation(KEYS + "done");
                    action = null;
                    event = null;
                }
                default -> {
                    if (Requests.slotOpen(store, ref, village, i)) {
                        detail = Requests.reward(t, village);
                        action = Message.translation(KEYS + "take");
                        event = "Take" + n;
                    } else {
                        detail = Message.translation(KEYS + "locked").param("rank",
                                Message.translation(dev.nakasar.hytale.peuples.reputation.Rank.TOLERE.nameKey()));
                        action = null;
                        event = null;
                    }
                }
            }
            cmd.set("#Detail" + n + ".TextSpans", detail);
            cmd.set("#Action" + n + ".Visible", action != null);
            if (action != null) {
                cmd.set("#Action" + n + ".Text", action);
                events.addEventBinding(CustomUIEventBindingType.Activating, "#Action" + n, EventData.of("Action", event));
            }
        }
        cmd.set("#StateText.TextSpans", VillageBoard.body(world, village, store, ref));
        cmd.set("#TurnIn.Text", Message.translation(KEYS + "turnIn"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#TurnIn", EventData.of("Action", "TurnIn"));
        cmd.set("#TextVersion.Text", Message.translation(KEYS + "textVersion"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#TextVersion", EventData.of("Action", "Text"));
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, Event data) {
        if (data == null || data.action == null) {
            return;
        }
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        if (village == null) {
            close();
            return;
        }
        String action = data.action;
        if (action.startsWith("Take")) {
            Requests.take(world, store, ref, playerRef, village, slot(action, "Take"));
        } else if (action.startsWith("Abandon")) {
            int slot = slot(action, "Abandon");
            VillageRequest[] board = village.requests();
            if (slot >= 0 && slot < board.length && board[slot] != null) {
                Requests.abandon(world, store, ref, playerRef, board[slot].id());
            }
        } else if (action.equals("TurnIn")) {
            Requests.turnIn(world, store, ref, playerRef, village);
        } else if (action.equals("Text")) {
            VillageBoard.open(world, store, ref, playerRef, village);
            return;
        }
        rebuild();
    }

    private static int slot(String action, String prefix) {
        try {
            return Integer.parseInt(action.substring(prefix.length()));
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
