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
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Absences;
import dev.nakasar.hytale.peuples.village.ChantierState;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Le tableau du village à boutons (maquettes /mnt/project-files/peuples/maquettes/tableau-par-peuple/), aux couleurs du
 * peuple : une mise en page par peuple ({@code BoardPage_<Peuple>.ui}, générée par {@code tools/generate_board_ui.py},
 * emblème vanilla de la page des Souvenirs). En haut le bandeau du peuple (palier, devise, villageois, rang du joueur
 * et sa jauge), à gauche les trois demandes du jour en cartes (icône d'objet du type, récompenses, avancement), à
 * droite l'essor et le chantier (jauges, matériaux en icônes d'objets), le dépôt et l'alerte de raid.
 *
 * <p>Secours si la page ne s'affiche pas : « Version texte » (page texte vanilla, aussi en s'accroupissant devant le
 * panneau) et {@code /village demandes}, {@code prendre}, {@code rendre}, {@code abandonner}.
 */
public final class BoardPage extends InteractiveCustomUIPage<BoardPage.Event> {

    /** Mise en page neutre, pour un peuple sans thème. */
    public static final String LAYOUT = "Pages/Nakasar/Peuples/BoardPage.ui";
    private static final String KEYS = "nakasar_peuples.boardPage.";
    private static final String BOARD = "nakasar_peuples.board.";

    /** Peuples qui ont leur mise en page (thèmes de tools/generate_board_ui.py). */
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");

    // Nombre de cases de la mise en page (tools/generate_board_ui.py).
    private static final int MATERIALS = 5;
    private static final int BUILDINGS = 4;
    private static final int DEPOSIT = 9;

    private static final String OK = "#7ed957";
    private static final String MISSING = "#e8c46a";

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

    /** Mise en page du peuple, ou la neutre. */
    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/BoardPage_" + people.id() + ".ui" : LAYOUT;
    }

    // Les libellés (Label) reçoivent leur texte par « .TextSpans », comme les pages vanilla (BlockLorePage,
    // ConfirmationPage, RespawnPage) : un message composé envoyé sur « .Text » fait planter le client (« No
    // parameterless constructor defined for type 'System.String' »). Les boutons (TextButton) gardent « .Text » avec
    // une simple traduction sans paramètre Message (le client afficherait « {text} »). Icônes d'objets par
    // « #X.ItemId » et jauges par « #X.Value » (float), comme ItemRepairPage et MemoriesPage ; couleur d'un libellé
    // par « #X.Style.TextColor », comme BarterPage.
    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        cmd.append(layout(village == null ? null : village.people()));
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(Villages.MESSAGES + "boardOrphan"));
            return;
        }
        cmd.set("#PageTitle.TextSpans", Message.translation(BOARD + "title").param("name", village.name()));
        BoardTabs.fill(cmd, events, store, village);
        band(cmd, world, store, ref, village);
        requests(cmd, events, store, ref, village);
        state(cmd, world, store, village);
        footer(cmd, events, store, village);
    }

    /** Bandeau du peuple : palier, devise, villageois, rang du joueur et sa jauge. */
    private void band(UICommandBuilder cmd, World world, Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        People people = village.people();
        cmd.set("#PeopleTier.TextSpans", Message.translation(BOARD + "people")
                .param("people", Message.translation(people.nameKey())).param("tier", Message.translation(Tiers.nameKey(village.tier()))));
        cmd.set("#Motto.TextSpans", Message.translation(KEYS + "motto." + people.id()));
        int[] count = Villagers.count(village);
        cmd.set("#VillagersPill.Visible", count[1] > 0);
        if (count[1] > 0) {
            cmd.set("#Villagers.TextSpans", Message.translation(KEYS + "villagers").param("here", count[0]).param("total", count[1]));
        }
        Reputations.Standing standing = Reputations.standing(store, ref, village);
        Rank rank = standing.rank();
        int value = standing.value();
        cmd.set("#RankCaption.TextSpans", Message.translation(KEYS + "rankCaption"));
        cmd.set("#RankName.TextSpans", Message.translation(rank.nameKey()));
        cmd.set("#RankName.Style.TextColor", rankColor(rank));
        Rank next = rank.next();
        if (next == null) {
            cmd.set("#RankNext.TextSpans", Message.translation(KEYS + "rankMax").param("value", value));
            cmd.set("#RankBar.Value", 1f);
        } else {
            cmd.set("#RankNext.TextSpans", Message.translation(KEYS + "rankNext").param("value", value).param("max", next.min())
                    .param("rank", Message.translation(next.nameKey())));
            cmd.set("#RankBar.Value", fraction(value - rank.min(), next.min() - rank.min()));
        }
        cmd.set("#RankDetail.TextSpans", Message.translation(KEYS + "rankDetail").param("village", standing.village())
                .param("people", standing.people()).param("peopleName", Message.translation(people.nameKey())));
        cmd.set("#Perks.TextSpans", Message.translation(BOARD + "perks").param("perks", Message.translation(rank.perksKey())));
    }

    /** Les trois cartes des demandes du jour. */
    private void requests(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        cmd.set("#RequestsHeader.TextSpans", Message.translation(KEYS + "requests"));
        cmd.set("#RequestsRenew.TextSpans", Message.translation(KEYS + "renew").param("hour", GameClock.MORNING));
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        VillageRequest[] board = village.requests();
        String favor = village.people().favorItem();
        for (int i = 0; i < Requests.SLOTS; i++) {
            VillageRequest request = i < board.length ? board[i] : null;
            String n = Integer.toString(i);
            RequestTemplate t = request == null ? null : request.template();
            if (t == null) {
                cmd.set("#Request" + n + ".Visible", false);
                continue;
            }
            cmd.set("#Request" + n + ".Visible", true);
            cmd.set("#TypeIcon" + n + ".ItemId", typeIcon(t));
            cmd.set("#Type" + n + ".TextSpans", Message.translation(t.type().nameKey()));
            cmd.set("#Type" + n + ".Style.TextColor", typeColor(t.type()));
            // Kevin (2026-11-15) : titre seul, la quantité en pastille sur la case de l'objet (sinon le titre est coupé).
            cmd.set("#Title" + n + ".TextSpans", Requests.title(t));
            boolean qty = t.itemId() != null && t.needed() > 1;
            cmd.set("#Qty" + n + ".Visible", qty);
            if (qty) {
                cmd.set("#Qty" + n + ".TextSpans", Message.raw("×" + t.needed()));
            }
            Requests.Status status = Requests.status(data, request);
            boolean open = Requests.slotOpen(store, ref, village, i);
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
                cmd.set("#Essor" + n + ".TextSpans", Message.translation(KEYS + "essorPill").param("essor", t.essor()));
                cmd.set("#Rep" + n + ".TextSpans", Message.translation(KEYS + "repPill").param("reputation", t.reputation()));
                cmd.set("#Favor" + n + ".Visible", t.favors() > 0);
                cmd.set("#Favors" + n + ".Visible", t.favors() > 0);
                if (t.favors() > 0) {
                    cmd.set("#Favor" + n + ".ItemId", favor);
                    cmd.set("#Favors" + n + ".TextSpans", Message.translation(KEYS + "favors").param("count", t.favors()));
                }
                action = Message.translation(KEYS + "take");
                event = "Take" + n;
            } else if (taken) {
                PlayerRequest mine = data.request(request.id());
                cmd.set("#Task" + n + ".TextSpans", Requests.task(store, playerRef, mine, t, village, Requests.position(store, ref)));
                int needed = Math.max(1, t.needed());
                int progress = mine == null ? 0 : Math.min(needed, mine.progress());
                cmd.set("#Progress" + n + ".Value", fraction(progress, needed));
                cmd.set("#ProgressText" + n + ".TextSpans", Message.translation(KEYS + "progress").param("have", progress).param("need", needed));
                action = Message.translation(KEYS + "abandon");
                event = "Abandon" + n;
            } else if (done) {
                cmd.set("#Detail" + n + ".TextSpans", Message.translation(KEYS + "done"));
                cmd.set("#Detail" + n + ".Style.TextColor", OK);
            } else {
                cmd.set("#Detail" + n + ".TextSpans", Message.translation(KEYS + "locked")
                        .param("rank", Message.translation(Rank.TOLERE.nameKey())));
            }
            cmd.set("#Action" + n + ".Visible", action != null);
            if (action != null) {
                cmd.set("#Action" + n + ".Text", action);
                events.addEventBinding(CustomUIEventBindingType.Activating, "#Action" + n, EventData.of("Action", event));
            }
        }
    }

    /** Colonne de droite : essor, chantier (prochain ou en cours), dépôt, alerte de raid. */
    private void state(UICommandBuilder cmd, World world, Store<EntityStore> store, Village village) {
        Message tierName = Message.translation(Tiers.nameKey(village.tier()));
        cmd.set("#EssorHeader.TextSpans", Message.translation(KEYS + "essorHeader").param("tier", tierName));
        cmd.set("#EssorLabel.TextSpans", Message.translation(KEYS + "essor"));
        int threshold = Tiers.threshold(village.tier());
        ChantierState c = village.chantier();
        if (c != null) {
            cmd.set("#EssorValue.TextSpans", Message.translation(KEYS + "essorBuilding"));
            cmd.set("#EssorBar.Value", 1f);
            cmd.set("#EssorHint.TextSpans", Message.translation(KEYS + "essorHintBuilding"));
        } else if (threshold > 0) {
            cmd.set("#EssorValue.TextSpans", Message.translation(KEYS + "essorValue").param("essor", village.essor()).param("max", threshold));
            cmd.set("#EssorBar.Value", fraction(village.essor(), threshold));
            cmd.set("#EssorHint.TextSpans", village.essor() >= threshold
                    ? Message.translation(KEYS + "essorHintFull")
                    : Message.translation(KEYS + "essorHint").param("left", threshold - village.essor()));
        } else {
            cmd.set("#EssorValue.TextSpans", Message.translation(KEYS + "essorMax"));
            cmd.set("#EssorBar.Value", 1f);
            cmd.set("#EssorHint.TextSpans", Message.translation(BOARD + "maxTier"));
        }
        chantier(cmd, world, store, village, c);
        deposit(cmd, world, village);
        // Alerte : le raid en cours ou annoncé, et le bilan du dernier. Pas de raid chez les peuples jamais attaqués.
        boolean raided = Raids.raided(village.people());
        cmd.set("#Alert.Visible", raided);
        if (raided) {
            Message alert = Raids.status(store, village);
            Message last = Raids.lastReport(village);
            cmd.set("#AlertText.TextSpans", last == null ? alert : Message.empty().insert(alert).insert("\n").insert(last));
        }
    }

    /**
     * Bâtiment gêné, en une ligne courte : le panneau ne cite ni bloc ni coordonnées (la Version texte et
     * /village genes les donnent), pour garder la colonne lisible.
     */
    private static Message blockedShort(VillageLayout.Building b, Chantiers.Obstacles o) {
        return Message.translation(KEYS + "blockedShort").param("building", Message.translation(Chantiers.buildingKey(b.id())))
                .param("count", o.total());
    }

    private void chantier(UICommandBuilder cmd, World world, Store<EntityStore> store, Village village, ChantierState c) {
        VillageLayout layout = Chantiers.layout(village);
        List<Message> notes = new ArrayList<>();
        boolean next = c == null && layout != null && village.tier() < Tiers.MAX;
        cmd.set("#Materials.Visible", next);
        cmd.set("#ChantierInfo.Visible", next);
        cmd.set("#Works.Visible", c != null);
        cmd.set("#ChantierTitle.Visible", c != null || next);
        if (c != null) {
            Message tier = Message.translation(Tiers.nameKey(c.tier()));
            cmd.set("#ChantierTitle.TextSpans", Message.translation(KEYS + "chantierActive").param("tier", tier));
            long now = GameClock.seconds(store);
            long left = Math.max(0, c.end() - now);
            cmd.set("#WorksLine.TextSpans", Message.translation(KEYS + "worksLine").param("hours", (int) Math.ceil(left / 3600.0)));
            cmd.set("#WorksBar.Value", fraction(now - c.start(), c.end() - c.start()));
            String[] buildings = c.buildings();
            for (int k = 0; k < BUILDINGS; k++) {
                boolean shown = k < buildings.length;
                cmd.set("#Building" + k + ".Visible", shown);
                if (shown) {
                    boolean standing = village.isBuilt(buildings[k]) && !village.isBurnt(buildings[k]);
                    cmd.set("#BuildingDone" + k + ".Visible", standing);
                    cmd.set("#BuildingTodo" + k + ".Visible", !standing);
                    cmd.set("#BuildingName" + k + ".TextSpans", Message.translation(Chantiers.buildingKey(buildings[k])));
                    cmd.set("#BuildingName" + k + ".Style.TextColor", standing ? OK : "#c9d1d9");
                }
            }
            if (buildings.length > BUILDINGS) {
                notes.add(Message.translation(KEYS + "moreBuildings").param("count", buildings.length - BUILDINGS));
            }
            Map<VillageLayout.Building, Chantiers.Obstacles> blocked = Chantiers.blocked(world, village);
            for (String id : c.skipped()) {
                VillageLayout.Building b = layout == null ? null : layout.building(id);
                Chantiers.Obstacles o = b == null ? null : blocked.get(b);
                notes.add(o != null ? blockedShort(b, o)
                        : Message.translation(BOARD + "chantier.skippedClear").param("building", Message.translation(Chantiers.buildingKey(id))));
            }
        } else if (next) {
            int target = village.tier() + 1;
            cmd.set("#ChantierTitle.TextSpans", Message.translation(KEYS + "chantierNext").param("tier", Message.translation(Tiers.nameKey(target))));
            VillageLayout.Chantier spec = layout.chantier(target);
            VillageLayout.Material[] materials = spec == null ? new VillageLayout.Material[0] : spec.materials();
            Map<String, Integer> deposit = Villages.depositContents(world, village);
            for (int j = 0; j < MATERIALS; j++) {
                boolean shown = j < materials.length;
                cmd.set("#Mat" + j + ".Visible", shown);
                if (shown) {
                    VillageLayout.Material m = materials[j];
                    int have = deposit == null ? 0 : Math.min(m.quantity(), deposit.getOrDefault(m.itemId(), 0));
                    boolean ok = have >= m.quantity();
                    cmd.set("#MatIcon" + j + ".ItemId", m.itemId());
                    cmd.set("#MatOk" + j + ".Visible", ok);
                    cmd.set("#MatSlot" + j + ".Visible", !ok);
                    cmd.set("#MatCount" + j + ".TextSpans", Message.translation(KEYS + "progress").param("have", have).param("need", m.quantity()));
                    cmd.set("#MatCount" + j + ".Style.TextColor", ok ? OK : MISSING);
                }
            }
            if (spec != null) {
                cmd.set("#ChantierInfo.TextSpans", Message.translation(BOARD + "chantier.count")
                        .param("count", Chantiers.pending(layout, village, target).size()).param("hours", spec.hours()));
            } else {
                cmd.set("#ChantierInfo.Visible", false);
            }
            Map<VillageLayout.Building, Chantiers.Obstacles> blocked = Chantiers.blocked(world, village);
            blocked.forEach((b, o) -> notes.add(blockedShort(b, o)));
            if (!blocked.isEmpty()) {
                notes.add(Message.translation(KEYS + "blockedHint"));
            }
        }
        for (String id : village.burnt()) {
            notes.add(Message.translation(BOARD + "chantier.ruin").param("building", Message.translation(Chantiers.buildingKey(id))));
        }
        cmd.set("#ChantierNotes.Visible", !notes.isEmpty());
        if (!notes.isEmpty()) {
            cmd.set("#ChantierNotes.TextSpans", lines(notes));
        }
    }

    private void deposit(UICommandBuilder cmd, World world, Village village) {
        cmd.set("#DepositHeader.TextSpans", Message.translation(BOARD + "deposit"));
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        boolean empty = deposit == null || deposit.isEmpty();
        cmd.set("#DepEmpty.Visible", empty);
        if (empty) {
            cmd.set("#DepEmpty.TextSpans", Message.translation(BOARD + (deposit == null ? "depositMissing" : "depositEmpty")));
        }
        List<Map.Entry<String, Integer>> entries = empty ? List.of() : new ArrayList<>(deposit.entrySet());
        for (int k = 0; k < DEPOSIT; k++) {
            boolean shown = k < entries.size();
            cmd.set("#Dep" + k + ".Visible", shown);
            if (shown) {
                cmd.set("#DepIcon" + k + ".ItemId", entries.get(k).getKey());
                cmd.set("#DepCount" + k + ".TextSpans", Message.raw(Integer.toString(entries.get(k).getValue())));
            }
        }
        boolean more = entries.size() > DEPOSIT;
        cmd.set("#DepMore.Visible", more);
        if (more) {
            cmd.set("#DepMore.TextSpans", Message.translation(KEYS + "more").param("count", entries.size() - DEPOSIT));
        }
    }

    private void footer(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Village village) {
        List<Message> absent = Absences.boardLines(store, village);
        cmd.set("#Absent.TextSpans", absent.isEmpty() ? Message.translation(KEYS + "allHere") : lines(absent));
        cmd.set("#TurnIn.Text", Message.translation(KEYS + "turnIn"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#TurnIn", EventData.of("Action", "TurnIn"));
        cmd.set("#TextVersion.Text", Message.translation(KEYS + "textVersion"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#TextVersion", EventData.of("Action", "Text"));
    }

    /** Icône de la carte : l'objet demandé (récolte, artisanat), sinon un objet vanilla qui dit le type. */
    public static String typeIcon(RequestTemplate t) {
        if (t.type().usesDeposit() && t.itemId() != null) {
            return t.itemId();
        }
        return switch (t.type()) {
            case GATHER -> "Tool_Hatchet_Crude";
            case CRAFT -> "Bench_WorkBench";
            case HUNT -> "Weapon_Shortbow_Crude";
            case DELIVERY -> "Deco_Scroll";
            case ESCORT -> "Tool_Map";
            case DEFENSE -> "Weapon_Shield_Wood";
            case PLANT -> "Plant_Sapling_Oak";
            case CARAVAN -> "Furniture_Crude_Chest_Small";
            case HARVEST -> "Tool_Sickle_Crude";
            case DESTROY -> "Tool_Pickaxe_Crude";
            case BOSS -> "Weapon_Battleaxe_Stone_Trork";
            case ROUTE -> dev.nakasar.hytale.peuples.annex.Routes.KIT_BEACON;
        };
    }

    public static String typeColor(RequestType type) {
        return switch (type) {
            case DEFENSE -> "#e88a78";
            case HUNT -> "#e8b45a";
            case ESCORT, CARAVAN -> "#a9c4e6";
            case BOSS -> "#d98ae8";
            case DESTROY -> "#e8a05a";
            case DELIVERY -> "#d9c48a";
            case GATHER, PLANT, HARVEST -> "#9ed36a";
            case CRAFT -> "#c9b98f";
            case ROUTE -> "#e8c46a";
        };
    }

    static String rankColor(Rank rank) {
        return switch (rank) {
            case HONNI -> "#d9614c";
            case ETRANGER -> "#96a9be";
            case TOLERE -> "#c9b98f";
            case AMI -> "#9ed36a";
            case HOTE -> "#e8c46a";
            case CHAMPION -> "#c9a8f0";
        };
    }

    static float fraction(long value, long max) {
        return max <= 0 ? 1f : (float) Math.max(0, Math.min(1, (double) value / max));
    }

    private static Message lines(List<Message> lines) {
        Message body = Message.empty();
        for (int i = 0; i < lines.size(); i++) {
            if (i > 0) {
                body.insert("\n");
            }
            body.insert(lines.get(i));
        }
        return body;
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
        } else if (BoardTabs.handle(action, world, store, ref, playerRef, village)) {
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
