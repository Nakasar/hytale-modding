package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomPageLifetime;
import com.hypixel.hytale.protocol.packets.interface_.CustomUIEventBindingType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.BlockLorePage;
import com.hypixel.hytale.server.core.entity.entities.player.pages.InteractiveCustomUIPage;
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.BoardPage;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.PlayerRequest;
import dev.nakasar.hytale.peuples.request.RequestTemplate;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.request.VillageRequest;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;

import java.util.ArrayList;
import java.util.List;

/**
 * Le panneau d'un bâtiment de métier (maquette « Enclos kweebec » du GDD), aux couleurs du peuple : une mise en page
 * par peuple ({@code WorkshopPage_<Peuple>.ui}, générée par {@code tools/generate_workshop_ui.py}). En haut le
 * bâtiment (icône, nom, niveau, villageois, spécialité) et sa jauge de savoir-faire, à gauche les commandes du jour en
 * cartes, à droite le prochain niveau et les offres, en bas le rang du joueur, Rendre et Version texte.
 *
 * <p>Comme {@link BoardPage} : libellés par {@code .TextSpans}, boutons par {@code .Text} avec une traduction simple.
 */
public final class WorkshopPage extends InteractiveCustomUIPage<WorkshopPage.Event> {

    public static final String LAYOUT = "Pages/Nakasar/Peuples/WorkshopPage.ui";
    private static final String KEYS = Workshops.KEYS;
    private static final String BOARD_PAGE = "nakasar_peuples.boardPage.";
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    /** Cartes de la mise en page (Workshops.slots au niveau III). */
    private static final int ORDERS = 3;
    private static final String OK = "#7ed957";

    /** Donnée d'un clic : {@code Take0..2}, {@code Abandon0..2}, {@code TurnIn}, {@code Text}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;
    private final String workshopId;

    public WorkshopPage(PlayerRef playerRef, Village village, Workshop workshop) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
        this.workshopId = workshop.getId();
    }

    /** Ouvre le panneau du bâtiment (thread du monde) ; `text` : la version texte (page vanilla BlockLore). */
    public static void open(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village,
                            Workshop workshop, boolean text) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        if (!Workshops.open(village, workshop)) {
            playerRef.sendMessage(Message.translation(KEYS + "notHere"));
            return;
        }
        Workshops.draw(store, village, workshop, village.workshop(workshop.getId()), false);
        if (text) {
            Message title = title(village, workshop);
            player.getPageManager().openCustomPage(ref, store,
                    new BlockLorePage(playerRef, title, textBody(store, ref, village, workshop), BlockLorePage.TextAlignment.Left));
            return;
        }
        player.getPageManager().openCustomPage(ref, store, new WorkshopPage(playerRef, village, workshop));
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/WorkshopPage_" + people.id() + ".ui" : LAYOUT;
    }

    static Message title(Village village, Workshop w) {
        return Message.translation(KEYS + "title").param("building", Message.translation(w.nameKey())).param("village", village.name());
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        Workshop w = Workshop.get(workshopId);
        cmd.append(layout(village == null ? null : village.people()));
        if (village == null || w == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "boardOrphan"));
            return;
        }
        WorkshopState state = village.workshop(w.getId());
        cmd.set("#PageTitle.TextSpans", title(village, w));
        band(cmd, events, village, w, state);
        orders(cmd, events, store, ref, village, state);
        info(cmd, events, store, ref, village, w, state);
        footer(cmd, events, store, ref, village);
    }

    private void band(UICommandBuilder cmd, UIEventBuilder events, Village village, Workshop w, WorkshopState state) {
        if (w.icon() != null) {
            cmd.set("#Icon.ItemId", w.icon());
        }
        cmd.set("#Name.TextSpans", Message.translation(w.nameKey()));
        cmd.set("#Level.TextSpans", Message.translation(KEYS + "level." + state.level()));
        cmd.set("#Keeper.TextSpans", keeperLine(village, w));
        Workshop.Specialty spec = w.specialty(state.specialty());
        cmd.set("#Specialty.TextSpans", spec == null ? Message.translation(KEYS + "noSpecialty") : Message.translation(spec.nameKey()));
        // Étape 3 : le choix de la spécialité s'ouvre au niveau II (la page dit ce qui manque : rang, délai).
        boolean choose = w.specialties().length > 0 && state.level() >= Workshops.SPECIALTY_LEVEL;
        cmd.set("#SpecialtyAction.Visible", choose);
        if (choose) {
            cmd.set("#SpecialtyAction.Text", Message.translation(KEYS + (spec == null ? "specialtyChoose" : "specialtyChange")));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#SpecialtyAction", EventData.of("Action", "Specialty"));
        }
        cmd.set("#KnowledgeCaption.TextSpans", Message.translation(KEYS + "knowledge"));
        int max = Workshops.threshold(state.level());
        if (max <= 0) {
            cmd.set("#KnowledgeValue.TextSpans", Message.translation(KEYS + "knowledgeMax"));
            cmd.set("#KnowledgeBar.Value", 1f);
            cmd.set("#KnowledgeHint.TextSpans", Message.translation(KEYS + "knowledgeTop"));
            return;
        }
        cmd.set("#KnowledgeValue.TextSpans", Message.translation(KEYS + "knowledgeValue").param("value", state.knowledge()).param("max", max));
        cmd.set("#KnowledgeBar.Value", fraction(state.knowledge(), max));
        Message next = Message.translation(KEYS + "levelShort." + (state.level() + 1));
        int tier = Workshops.tierFor(state.level() + 1);
        if (state.knowledge() < max) {
            cmd.set("#KnowledgeHint.TextSpans", Message.translation(KEYS + "knowledgeHint").param("left", max - state.knowledge()).param("level", next));
        } else if (village.tier() < tier) {
            cmd.set("#KnowledgeHint.TextSpans", Message.translation(KEYS + "knowledgeCapped").param("level", next)
                    .param("tier", Message.translation(Tiers.nameKey(tier))));
        } else {
            cmd.set("#KnowledgeHint.TextSpans", Message.translation(KEYS + "knowledgeFull").param("level", next));
        }
    }

    /** Le villageois du bâtiment : présent, ou de retour au matin. */
    static Message keeperLine(Village village, Workshop w) {
        VillageLayout.Job job = Workshops.job(village, w);
        if (job == null) {
            return Message.translation(KEYS + "keeperNone");
        }
        Message name = keeperName(job);
        if (Villagers.present(village, job.id())) {
            return Message.translation(KEYS + "keeper").param("name", name);
        }
        return Message.translation(KEYS + "keeperAbsent").param("name", name).param("hour", GameClock.MORNING);
    }

    /** Nom du villageois : celui de son dialogue, sinon le nom du métier. */
    static Message keeperName(VillageLayout.Job job) {
        Dialogue d = job.dialogue() == null || job.dialogue().isEmpty() ? null : Dialogue.get(job.dialogue());
        if (d != null && d.npcNameKey() != null) {
            return Message.translation(d.npcNameKey());
        }
        return Message.translation("nakasar_peuples.job." + job.id());
    }

    private void orders(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Ref<EntityStore> ref, Village village,
                        WorkshopState state) {
        cmd.set("#OrdersHeader.TextSpans", Message.translation(KEYS + "orders"));
        cmd.set("#OrdersRenew.TextSpans", Message.translation(KEYS + "renew").param("hour", GameClock.MORNING));
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        VillageRequest[] board = state.requests();
        boolean open = Workshops.canTake(store, ref, village);
        String favor = village.people().favorItem();
        int shown = 0;
        for (int i = 0; i < ORDERS; i++) {
            VillageRequest request = i < board.length ? board[i] : null;
            RequestTemplate t = request == null ? null : request.template();
            String n = Integer.toString(i);
            if (t == null) {
                cmd.set("#Order" + n + ".Visible", false);
                continue;
            }
            shown++;
            cmd.set("#Order" + n + ".Visible", true);
            cmd.set("#TypeIcon" + n + ".ItemId", BoardPage.typeIcon(t));
            cmd.set("#Type" + n + ".TextSpans", Message.translation(t.type().nameKey()));
            cmd.set("#Type" + n + ".Style.TextColor", BoardPage.typeColor(t.type()));
            cmd.set("#Title" + n + ".TextSpans", Requests.boardTitle(t));
            Requests.Status status = Requests.status(data, request);
            boolean taken = status == Requests.Status.TAKEN;
            boolean done = status == Requests.Status.DONE;
            boolean available = !taken && !done && open;
            boolean locked = !taken && !done && !open;
            cmd.set("#RewardBox" + n + ".Visible", available);
            cmd.set("#TaskBox" + n + ".Visible", taken);
            cmd.set("#Detail" + n + ".Visible", done || locked);
            cmd.set("#Lock" + n + ".Visible", locked);
            cmd.set("#Check" + n + ".Visible", taken || done);
            cmd.set("#Stripe" + n + ".Visible", !locked);
            cmd.set("#StripeOff" + n + ".Visible", locked);
            cmd.set("#Title" + n + ".Style.TextColor", locked ? "#6f7d8c" : "#e8c46a");
            String event = null;
            Message action = null;
            if (available) {
                cmd.set("#RewardCaption" + n + ".TextSpans", Message.translation(KEYS + "reward"));
                cmd.set("#Know" + n + ".TextSpans", Message.translation(KEYS + "knowledgePill").param("knowledge", t.knowledge()));
                cmd.set("#Essor" + n + ".TextSpans", Message.translation(BOARD_PAGE + "essorPill").param("essor", t.essor()));
                cmd.set("#Rep" + n + ".TextSpans", Message.translation(BOARD_PAGE + "repPill").param("reputation", t.reputation()));
                cmd.set("#Favor" + n + ".Visible", t.favors() > 0);
                cmd.set("#Favors" + n + ".Visible", t.favors() > 0);
                if (t.favors() > 0) {
                    cmd.set("#Favor" + n + ".ItemId", favor);
                    cmd.set("#Favors" + n + ".TextSpans", Message.translation(BOARD_PAGE + "favors").param("count", t.favors()));
                }
                action = Message.translation(BOARD_PAGE + "take");
                event = "Take" + n;
            } else if (taken) {
                PlayerRequest mine = data.request(request.id());
                cmd.set("#Task" + n + ".TextSpans", Requests.task(store, playerRef, mine, t, village, Requests.position(store, ref)));
                int needed = Math.max(1, t.needed());
                int progress = mine == null ? 0 : Math.min(needed, mine.progress());
                cmd.set("#Progress" + n + ".Value", fraction(progress, needed));
                cmd.set("#ProgressText" + n + ".TextSpans", Message.translation(BOARD_PAGE + "progress").param("have", progress).param("need", needed));
                action = Message.translation(BOARD_PAGE + "abandon");
                event = "Abandon" + n;
            } else if (done) {
                cmd.set("#Detail" + n + ".TextSpans", Message.translation(BOARD_PAGE + "done"));
                cmd.set("#Detail" + n + ".Style.TextColor", OK);
            } else {
                cmd.set("#Detail" + n + ".TextSpans", Message.translation(KEYS + "locked")
                        .param("rank", Message.translation(Workshops.TAKE_RANK.nameKey())));
            }
            cmd.set("#Action" + n + ".Visible", action != null);
            if (action != null) {
                cmd.set("#Action" + n + ".Text", action);
                events.addEventBinding(CustomUIEventBindingType.Activating, "#Action" + n, EventData.of("Action", event));
            }
        }
        cmd.set("#OrdersEmpty.Visible", shown == 0);
        if (shown == 0) {
            cmd.set("#OrdersEmpty.TextSpans", Message.translation(KEYS + "empty"));
        }
    }

    private void info(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Ref<EntityStore> ref, Village village, Workshop w, WorkshopState state) {
        cmd.set("#NextHeader.TextSpans", Message.translation(KEYS + "next"));
        Workshops.Next next = Workshops.next(village, state);
        Workshop.Upgrade up = w.upgrade(state.level() + 1);
        boolean mats = up != null && next == Workshops.Next.MATERIALS;
        cmd.set("#NextMats.Visible", mats);
        cmd.set("#WorksBar.Visible", next == Workshops.Next.WORKS);
        Message line = nextLine(village, state);
        String action = null;
        switch (next) {
            case MASTER -> {
                RequestTemplate t = Workshops.master(w, state);
                line = Message.translation(KEYS + "nextMaster").param("title", t == null ? Message.raw("?") : Requests.boardTitle(t));
                PeuplesPlayer data = PeuplesPlayer.get(store, playerRef.getReference());
                boolean mine = data != null && data.request(Workshops.masterId(village, w, state)) != null;
                if (mine) {
                    PlayerRequest r = data.request(Workshops.masterId(village, w, state));
                    line = Message.empty().insert(line).insert("\n").insert(Requests.task(store, playerRef, r, t, village,
                            Requests.position(store, playerRef.getReference())));
                } else {
                    action = "Master";
                }
            }
            case MATERIALS -> {
                line = Message.translation(KEYS + "nextMaterials").param("hours", up == null ? 12 : up.hours());
                action = "Upgrade";
                materials(cmd, store, village, up);
            }
            case WORKS -> {
                long now = GameClock.seconds(store);
                long left = Math.max(0, state.upgradeEnd() - now);
                line = Message.translation(KEYS + "works").param("hours", (int) Math.ceil(left / 3600.0));
                cmd.set("#WorksBar.Value", fraction(now - state.upgradeStart(), state.upgradeEnd() - state.upgradeStart()));
            }
            default -> {
            }
        }
        cmd.set("#NextLine.TextSpans", line);
        cmd.set("#NextAction.Visible", action != null);
        if (action != null) {
            cmd.set("#NextAction.Text", Message.translation(KEYS + (action.equals("Master") ? "takeMaster" : "startUpgrade")));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#NextAction", EventData.of("Action", action));
        }
        cmd.set("#OffersHeader.TextSpans", Message.translation(KEYS + "offers"));
        Message offers = offersLine(store, ref, village, w, state);
        cmd.set("#OffersLine.TextSpans", w.isPen() ? Message.empty().insert(offers).insert("\n\n").insert(beastsLine(village, w, state)) : offers);
        int level = Workshops.shopLevel(store, ref, village, state);
        boolean shop = level > 0 && Workshops.keeperPresent(village, w);
        cmd.set("#ShopAction.Visible", shop);
        if (shop) {
            cmd.set("#ShopAction.Text", Message.translation(KEYS + "shopButton").param("level", roman(level)));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#ShopAction", EventData.of("Action", "Shop"));
        }
        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        boolean share = player != null && Workshops.shareBlock(store, ref, player, village, w) == null;
        cmd.set("#ShareAction.Visible", share);
        if (share) {
            cmd.set("#ShareAction.Text", Message.translation(KEYS + "shareButton"));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#ShareAction", EventData.of("Action", "Share"));
        }
    }

    /** Chiffre romain d'un niveau (I à III). */
    static String roman(int level) {
        return level >= 3 ? "III" : level == 2 ? "II" : "I";
    }

    /**
     * Carte des offres : qui tient la boutique, le niveau que le rang du joueur ouvre, et la Part de l'Hôte au niveau III.
     */
    static Message offersLine(Store<EntityStore> store, Ref<EntityStore> ref, Village village, Workshop w, WorkshopState state) {
        VillageLayout.Job job = Workshops.job(village, w);
        Message name = job == null ? Message.translation(w.nameKey()) : keeperName(job);
        int level = Workshops.shopLevel(store, ref, village, state);
        Message line;
        if (!Workshops.keeperPresent(village, w)) {
            line = Message.translation(KEYS + "offersAbsent").param("name", name).param("hour", GameClock.MORNING);
        } else if (level <= 0) {
            line = Message.translation(KEYS + "offersRank").param("name", name).param("rank", Message.translation(Rank.TOLERE.nameKey()));
        } else {
            line = Message.translation(KEYS + "offersOpen").param("name", name).param("level", roman(level))
                    .param("max", roman(state.level()));
        }
        Message out = Message.empty().insert(line).insert("\n").insert(Message.translation(KEYS + "offersRule"));
        if (state.level() >= 2 && w.specialty(state.specialty()) == null && w.specialties().length > 0) {
            out = out.insert("\n").insert(Message.translation(KEYS + "offersNoSpecialty"));
        }
        Workshop.Specialty spec = Workshops.shareSpecialty(w, state);
        if (spec != null) {
            out = out.insert("\n").insert(Message.translation(KEYS + "shareLine").param("quantity", spec.shareQuantity())
                    .param("item", dev.nakasar.hytale.peuples.village.VillageBoard.itemName(spec.shareItem()))
                    .param("rank", Message.translation(Workshops.SHARE_RANK.nameKey())));
        }
        return out;
    }

    private static final int MATERIALS = 4;

    /** Ligne de l'enclos : bêtes présentes sur bêtes voulues, retour au matin, réputation perdue. */
    static Message beastsLine(Village village, Workshop w, WorkshopState state) {
        return Message.translation(KEYS + "beastsLine").param("count", Livestock.count(village, w))
                .param("max", w.livestockCount(state.level())).param("rep", -Livestock.KILL_REPUTATION);
    }

    private void materials(UICommandBuilder cmd, Store<EntityStore> store, Village village, Workshop.Upgrade up) {
        World world = store.getExternalData().getWorld();
        java.util.Map<String, Integer> deposit = Villages.depositContents(world, village);
        dev.nakasar.hytale.peuples.village.VillageLayout.Material[] list = up.materials();
        for (int j = 0; j < MATERIALS; j++) {
            boolean shown = j < list.length;
            cmd.set("#NMat" + j + ".Visible", shown);
            if (shown) {
                var m = list[j];
                int have = deposit == null ? 0 : Math.min(m.quantity(), deposit.getOrDefault(m.itemId(), 0));
                boolean ok = have >= m.quantity();
                cmd.set("#NMatIcon" + j + ".ItemId", m.itemId());
                cmd.set("#NMatOk" + j + ".Visible", ok);
                cmd.set("#NMatSlot" + j + ".Visible", !ok);
                cmd.set("#NMatCount" + j + ".TextSpans", Message.translation(BOARD_PAGE + "progress").param("have", have).param("need", m.quantity()));
                cmd.set("#NMatCount" + j + ".Style.TextColor", ok ? OK : "#e8c46a");
            }
        }
    }

    static Message nextLine(Village village, WorkshopState state) {
        if (state.level() >= Workshops.MAX_LEVEL) {
            return Message.translation(KEYS + "nextNone");
        }
        int level = state.level() + 1;
        Message name = Message.translation(KEYS + "levelShort." + level);
        Message line = Message.translation(KEYS + "nextLine").param("level", name).param("need", Workshops.threshold(state.level()));
        int tier = Workshops.tierFor(level);
        if (village.tier() < tier) {
            return Message.empty().insert(line).insert("\n").insert(Message.translation(KEYS + "nextTier").param("level", name)
                    .param("tier", Message.translation(Tiers.nameKey(tier))));
        }
        return line;
    }

    private void footer(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        Rank rank = Reputations.rank(store, ref, village);
        cmd.set("#RankLine.TextSpans", Message.translation("nakasar_peuples.board.rank").param("rank",
                Message.translation(rank.nameKey())));
        cmd.set("#TurnIn.Text", Message.translation(BOARD_PAGE + "turnIn"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#TurnIn", EventData.of("Action", "TurnIn"));
        cmd.set("#TextVersion.Text", Message.translation(BOARD_PAGE + "textVersion"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#TextVersion", EventData.of("Action", "Text"));
    }

    // ---- Version texte et tchat ----

    /** Texte du panneau pour la page vanilla BlockLore (accroupi). */
    static Message textBody(Store<EntityStore> store, Ref<EntityStore> ref, Village village, Workshop w) {
        WorkshopState state = village.workshop(w.getId());
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        boolean open = Workshops.canTake(store, ref, village);
        List<Message> lines = new ArrayList<>();
        lines.add(Message.translation(KEYS + "text.header").param("name", Message.translation(w.nameKey()))
                .param("level", Message.translation(KEYS + "levelShort." + state.level())));
        lines.add(keeperLine(village, w));
        Workshop.Specialty spec = w.specialty(state.specialty());
        lines.add(spec == null ? Message.translation(KEYS + "noSpecialty") : Message.translation(spec.nameKey()));
        if (w.isPen()) {
            lines.add(beastsLine(village, w, state));
        }
        lines.add(offersLine(store, ref, village, w, state));
        int max = Workshops.threshold(state.level());
        lines.add(max > 0 ? Message.translation(KEYS + "text.knowledge").param("value", state.knowledge()).param("max", max)
                : Message.translation(KEYS + "knowledgeTop"));
        lines.add(nextLine(village, state));
        lines.add(Message.empty());
        lines.add(Message.translation(KEYS + "orders"));
        VillageRequest[] board = state.requests();
        int n = 0;
        for (VillageRequest request : board) {
            RequestTemplate t = request == null ? null : request.template();
            if (t == null) {
                continue;
            }
            n++;
            String key = switch (Requests.status(data, request)) {
                case TAKEN -> "text.taken";
                case DONE -> "text.done";
                default -> open ? "text.available" : "text.locked";
            };
            lines.add(Message.translation(KEYS + "text.order").param("n", n).param("type", Message.translation(t.type().nameKey()))
                    .param("title", Requests.boardTitle(t)).param("state", Message.translation(KEYS + key)));
        }
        if (n == 0) {
            lines.add(Message.translation(KEYS + "empty"));
        }
        lines.add(Message.empty());
        lines.add(Message.translation(KEYS + "text.how").param("id", w.getId()));
        Message body = Message.empty();
        for (int i = 0; i < lines.size(); i++) {
            if (i > 0) {
                body.insert("\n");
            }
            body.insert(lines.get(i));
        }
        return body;
    }

    /** Ligne de tchat de {@code /village atelier} : les bâtiments de métier ouverts du village. */
    public static Message listLine(Village village) {
        List<Workshop> opened = Workshops.opened(village);
        if (opened.isEmpty()) {
            return Message.translation(KEYS + "listNone").param("village", village.name());
        }
        Message list = Message.empty();
        for (int i = 0; i < opened.size(); i++) {
            Workshop w = opened.get(i);
            WorkshopState state = village.workshop(w.getId());
            if (i > 0) {
                list.insert(", ");
            }
            list.insert(Message.translation(KEYS + "listEntry").param("id", w.getId()).param("name", Message.translation(w.nameKey()))
                    .param("level", Message.translation(KEYS + "levelShort." + state.level()))
                    .param("value", state.knowledge()).param("max", Workshops.threshold(state.level())));
        }
        return Message.translation(KEYS + "list").param("village", village.name()).param("list", list);
    }

    static float fraction(long value, long max) {
        return max <= 0 ? 1f : (float) Math.max(0, Math.min(1, (double) value / max));
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, Event data) {
        if (data == null || data.action == null) {
            return;
        }
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        Workshop w = Workshop.get(workshopId);
        if (village == null || w == null) {
            close();
            return;
        }
        String action = data.action;
        if (action.startsWith("Take")) {
            Workshops.take(world, store, ref, playerRef, village, w, slot(action, "Take"));
        } else if (action.startsWith("Abandon")) {
            int slot = slot(action, "Abandon");
            VillageRequest[] board = village.workshop(w.getId()).requests();
            if (slot >= 0 && slot < board.length && board[slot] != null) {
                Requests.abandon(world, store, ref, playerRef, board[slot].id());
            }
        } else if (action.equals("Master")) {
            Workshops.takeMaster(world, store, ref, playerRef, village, w);
        } else if (action.equals("Upgrade")) {
            Workshops.startUpgrade(world, store, ref, playerRef, village, w);
        } else if (action.equals("Shop")) {
            if (Workshops.openShop(store, ref, playerRef, village, w)) {
                return;
            }
        } else if (action.equals("Share")) {
            Workshops.takeShare(store, ref, playerRef, village, w);
        } else if (action.equals("Specialty")) {
            WorkshopSpecialtyPage.open(store, ref, playerRef, village, w);
            return;
        } else if (action.equals("TurnIn")) {
            Requests.turnIn(world, store, ref, playerRef, village);
        } else if (action.equals("Text")) {
            open(world, store, ref, playerRef, village, w, true);
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
