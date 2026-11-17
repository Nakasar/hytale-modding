package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomPageLifetime;
import com.hypixel.hytale.protocol.packets.interface_.CustomUIEventBindingType;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.InteractiveCustomUIPage;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.BoardTabs;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * L'onglet « Commerce » du panneau du village (routes commerciales, Kevin, 16 novembre 2026) : les neuf luxes (en accès,
 * du terroir, manquants) et ce que demande le palier suivant ; les routes ouvertes avec leurs cases d'export et
 * d'import (un clic fait défiler le catalogue), le niveau, le crédit et la fermeture ; les partenaires possibles
 * (ouvrir une route) ; l'étal des importations (acheter un petit lot pris au dépôt contre une faveur).
 * Mise en page par peuple ({@code TradePage_<Peuple>.ui}, {@code tools/generate_trade.py}).
 */
public final class TradePage extends InteractiveCustomUIPage<TradePage.Event> {

    private static final String LAYOUT = "Pages/Nakasar/Peuples/TradePage.ui";
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    /** Lignes de l'onglet (tools/generate_trade.py ROUTES, CANDIDATES, STALL). */
    private static final int ROUTES = 3;
    private static final int CANDIDATES = 3;
    private static final int STALL = 4;
    private static final int CASES = 3;
    private static final String OK = "#9ed36a";
    private static final String MUTED = "#7f93a8";
    private static final String GOLD = "#e8c46a";
    static final String KEYS = TradeRoutes.KEYS + "page.";
    public static final String TAB = KEYS + "tab";

    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;
    private final List<String> routes = new ArrayList<>();
    private final List<String> candidates = new ArrayList<>();
    private final List<String> stall = new ArrayList<>();

    public TradePage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player != null) {
            player.getPageManager().openCustomPage(ref, store, new TradePage(playerRef, village));
        }
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/TradePage_" + people.id() + ".ui" : LAYOUT;
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        cmd.append(layout(village == null ? null : village.people()));
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(WorldPage.KEYS + "orphan"));
            return;
        }
        long day = GameClock.day(store);
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "title").param("village", village.name()));
        BoardTabs.fill(cmd, events, store, village);
        luxuries(cmd, world, village, day);
        routes(cmd, events, world, village, day);
        candidates(cmd, events, world, village, day);
        stall(cmd, events, world, village, day);
        cmd.set("#Rule.TextSpans", Message.translation(KEYS + "rule").param("offering", TradeRoutes.OFFERING)
                .param("credit", TradeRoutes.CREDIT_PER_FAVOUR));
    }

    // ---- Luxes ----

    private void luxuries(UICommandBuilder cmd, World world, Village v, long day) {
        int count = TradeAccess.count(world, v, day);
        int target = Math.min(3, v.tier() + 1);
        Message need = v.tier() >= 3 ? Message.translation(KEYS + "lux.settler").param("need", TradeAccess.SETTLER)
                : Message.translation(KEYS + "lux.next").param("tier", Message.translation(dev.nakasar.hytale.peuples.village.Tiers.nameKey(target)))
                .param("need", TradeAccess.needAt(target));
        cmd.set("#LuxHeader.TextSpans", Message.translation(KEYS + "lux.header").param("count", count).param("total", TradeGoods.LUXURIES.size()));
        cmd.set("#LuxLine.TextSpans", Message.translation(KEYS + "lux.line").param("need", need).param("bonus", TradeAccess.bonus(world, v, day)));
        TradeGoods.Luxury own = TradeGoods.terroir(v.people());
        for (int i = 0; i < TradeGoods.LUXURIES.size(); i++) {
            TradeGoods.Luxury l = TradeGoods.LUXURIES.get(i);
            cmd.set("#LuxIcon" + i + ".ItemId", l.item());
            long until = TradeAccess.until(world, v, l.item());
            Message mark;
            String colour;
            if (l == own && v.tier() >= 2) {
                mark = Message.translation(KEYS + "lux.terroir");
                colour = GOLD;
            } else if (until >= day) {
                mark = Message.translation(KEYS + "lux.days").param("days", until - day + 1);
                colour = OK;
            } else if (!TradeGoods.allowed(v.people(), l.item())) {
                mark = Message.translation(KEYS + "lux.never");
                colour = MUTED;
            } else {
                mark = Message.translation(KEYS + "lux.missing");
                colour = MUTED;
            }
            cmd.set("#LuxMark" + i + ".TextSpans", mark);
            cmd.set("#LuxMark" + i + ".Style.TextColor", colour);
        }
    }

    // ---- Routes ----

    private static Message itemName(String item) {
        return item == null ? Message.translation(KEYS + "case.empty") : Message.translation(TradeGoods.itemKey(item));
    }

    private void routes(UICommandBuilder cmd, UIEventBuilder events, World world, Village v, long day) {
        List<TradeRoutes.Route> list = TradeRoutes.of(world, v);
        routes.clear();
        cmd.set("#RoutesHeader.TextSpans", Message.translation(KEYS + "routes").param("count", list.size())
                .param("slots", TradeRoutes.slots(world, v, day)));
        cmd.set("#NoRoute.Visible", list.isEmpty());
        if (list.isEmpty()) {
            cmd.set("#NoRoute.TextSpans", Message.translation(KEYS + (v.tier() < 1 ? "noRouteTier" : "noRoute")));
        }
        for (int i = 0; i < ROUTES; i++) {
            String n = Integer.toString(i);
            if (i >= list.size()) {
                cmd.set("#Route" + n + ".Visible", false);
                continue;
            }
            TradeRoutes.Route r = list.get(i);
            routes.add(r.key());
            Village o = TradeRoutes.village(world, r.other(v.id()));
            cmd.set("#Route" + n + ".Visible", true);
            cmd.set("#RouteName" + n + ".TextSpans", Message.translation(KEYS + "route.name").param("partner", o == null ? Message.raw("?") : TradeRoutes.name(world, o))
                    .param("level", Message.translation(KEYS + "level." + r.level())));
            Message state;
            if (r.suspended()) {
                state = Message.translation(KEYS + "route.suspended").param("days", Math.max(0, TradeRoutes.BREAK_DAYS - (day - r.suspendedSince())));
            } else {
                state = Message.translation(KEYS + "route.state").param("next", Math.max(0, r.next() - day)).param("arrivals", r.arrivals())
                        .param("lost", r.lost()).param("credit", r.credit(v.id())).param("deficit", TradeRoutes.deficit(r, v.id()));
            }
            if (r.auto()) {
                state = Message.translation(KEYS + "route.auto").param("state", state);
            }
            cmd.set("#RouteState" + n + ".TextSpans", state);
            cmd.set("#RouteOutLabel" + n + ".TextSpans", Message.translation(KEYS + "route.out"));
            cmd.set("#RouteInLabel" + n + ".TextSpans", Message.translation(KEYS + "route.in"));
            List<String> out = r.exportsOf(v.id());
            List<String> in = r.importsOf(v.id());
            for (int j = 0; j < CASES; j++) {
                boolean open = j < r.level();
                String o1 = "#RouteOut" + n + "_" + j;
                String i1 = "#RouteIn" + n + "_" + j;
                cmd.set(o1 + ".Visible", open);
                cmd.set(i1 + ".Visible", open);
                if (open) {
                    cmd.set(o1 + ".Text", itemName(j < out.size() ? out.get(j) : null));
                    cmd.set(i1 + ".Text", itemName(j < in.size() ? in.get(j) : null));
                    events.addEventBinding(CustomUIEventBindingType.Activating, o1, EventData.of("Action", "Out" + n + "_" + j));
                    events.addEventBinding(CustomUIEventBindingType.Activating, i1, EventData.of("Action", "In" + n + "_" + j));
                }
            }
            boolean raise = r.level() < TradeRoutes.MAX_LEVEL;
            cmd.set("#RouteRaise" + n + ".Visible", raise);
            if (raise) {
                cmd.set("#RouteRaise" + n + ".Text", Message.translation(KEYS + "button.raise").param("count", TradeRoutes.RAISE_OFFERING));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#RouteRaise" + n, EventData.of("Action", "Raise" + n));
            }
            cmd.set("#RoutePay" + n + ".Text", Message.translation(KEYS + "button.pay").param("credit", TradeRoutes.CREDIT_PER_FAVOUR));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#RoutePay" + n, EventData.of("Action", "Pay" + n));
            cmd.set("#RouteClose" + n + ".Text", Message.translation(KEYS + "button.close"));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#RouteClose" + n, EventData.of("Action", "Close" + n));
        }
    }

    // ---- Partenaires ----

    private void candidates(UICommandBuilder cmd, UIEventBuilder events, World world, Village v, long day) {
        List<Village> list = TradeRoutes.candidates(world, v);
        candidates.clear();
        cmd.set("#CandHeader.TextSpans", Message.translation(KEYS + "candidates"));
        cmd.set("#NoCand.Visible", list.isEmpty());
        if (list.isEmpty()) {
            cmd.set("#NoCand.TextSpans", Message.translation(KEYS + "noCandidate").param("max", Links.MAX_LENGTH));
        }
        for (int i = 0; i < CANDIDATES; i++) {
            String n = Integer.toString(i);
            if (i >= list.size()) {
                cmd.set("#Cand" + n + ".Visible", false);
                continue;
            }
            Village o = list.get(i);
            candidates.add(o.id());
            cmd.set("#Cand" + n + ".Visible", true);
            int dist = (int) Math.round(TradeRoutes.distance(v, o));
            cmd.set("#CandName" + n + ".TextSpans", Message.translation(KEYS + "candidate").param("partner", TradeRoutes.name(world, o))
                    .param("distance", dist).param("dir", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(o.x() - v.x(), o.z() - v.z()))));
            cmd.set("#CandOpen" + n + ".Text", Message.translation(KEYS + "button.open").param("count", TradeRoutes.OFFERING));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#CandOpen" + n, EventData.of("Action", "Open" + n));
        }
    }

    // ---- Étal ----

    /** Petit lot de l'étal : la moitié d'un chargement de niveau I (8 communes, 3 fines, 1 luxe). */
    static int stallLot(String item) {
        return Math.max(1, TradeGoods.grade(item).load(1) / 2);
    }

    private void stall(UICommandBuilder cmd, UIEventBuilder events, World world, Village v, long day) {
        stall.clear();
        Map<String, Integer> deposit = Villages.depositContents(world, v);
        for (String item : TradeAccess.items(world, v, day).keySet()) {
            if (deposit != null && deposit.getOrDefault(item, 0) >= stallLot(item) && stall.size() < STALL) {
                stall.add(item);
            }
        }
        cmd.set("#StallHeader.TextSpans", Message.translation(KEYS + "stall"));
        cmd.set("#NoStall.Visible", stall.isEmpty());
        if (stall.isEmpty()) {
            cmd.set("#NoStall.TextSpans", Message.translation(KEYS + (deposit == null ? "stallFar" : "stallEmpty")));
        }
        for (int i = 0; i < STALL; i++) {
            String n = Integer.toString(i);
            boolean shown = i < stall.size();
            cmd.set("#Stall" + n + ".Visible", shown);
            if (!shown) {
                continue;
            }
            String item = stall.get(i);
            cmd.set("#StallIcon" + n + ".ItemId", item);
            cmd.set("#StallBuy" + n + ".Text", Message.translation(KEYS + "button.buy").param("count", stallLot(item)));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#StallBuy" + n, EventData.of("Action", "Buy" + n));
        }
    }

    private Message buy(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, String item) {
        if (!Reputations.rank(store, ref, v).atLeast(Rank.TOLERE)) {
            return Message.translation(TradeRoutes.KEYS + "why.rankTolere").param("village", v.name());
        }
        ItemContainer chest = Villages.depositChest(world, v);
        int lot = stallLot(item);
        if (chest == null || TradeGoods.stock(chest, item) < lot) {
            return Message.translation(KEYS + "stallEmpty");
        }
        String favour = v.people().favorItem();
        if (WorldLife.count(store, ref, favour::equals) < 1) {
            return Message.translation(TradeRoutes.KEYS + "why.offering").param("count", 1);
        }
        WorldLife.take(store, ref, favour::equals, 1);
        int got = Requests.take(chest, item, lot);
        Requests.give(store, ref, new ItemStack(item, got));
        return null;
    }

    // ---- Clics ----

    private static int index(String action, String prefix) {
        try {
            return Integer.parseInt(action.substring(prefix.length()));
        } catch (NumberFormatException | IndexOutOfBoundsException e) {
            return -1;
        }
    }

    private TradeRoutes.Route route(World world, int i) {
        return i >= 0 && i < routes.size() ? TradeRoutes.get(world, routes.get(i)) : null;
    }

    /** Case suivante : l'objet après celui de la case dans le catalogue de l'expéditeur, puis « vide ». */
    private Message cycle(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village board, String action, boolean export) {
        String body = action.substring(export ? 3 : 2);
        int cut = body.indexOf('_');
        if (cut <= 0) {
            return null;
        }
        TradeRoutes.Route r = route(world, index(body.substring(0, cut), ""));
        int j = index(body.substring(cut + 1), "");
        if (r == null || j < 0) {
            return null;
        }
        Village sender = export ? board : TradeRoutes.village(world, r.other(board.id()));
        Village receiver = export ? TradeRoutes.village(world, r.other(board.id())) : board;
        if (sender == null || receiver == null) {
            return null;
        }
        long day = GameClock.day(store);
        List<String> items = new ArrayList<>();
        for (String item : TradeCatalogue.of(world, sender, r.key(), day).keySet()) {
            if (TradeGoods.allowed(receiver.people(), item)) {
                items.add(item);
            }
        }
        List<String> cases = r.exportsOf(sender.id());
        String current = j < cases.size() ? cases.get(j) : null;
        int at = current == null ? -1 : items.indexOf(current);
        String next = null;
        for (int k = at + 1; k < items.size(); k++) {
            if (!cases.contains(items.get(k))) {
                next = items.get(k);
                break;
            }
        }
        if (next == null && current == null && items.isEmpty()) {
            return Message.translation(KEYS + "nothing").param("village", TradeRoutes.name(world, sender));
        }
        return TradeRoutes.setCase(world, store, ref, board, r, sender, j, next);
    }

    private void tell(Message m, boolean ok) {
        playerRef.sendMessage(m);
        NotificationUtil.sendNotification(playerRef.getPacketHandler(), m, ok ? NotificationStyle.Success : NotificationStyle.Warning);
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
        if (BoardTabs.handle(action, world, store, ref, playerRef, village)) {
            return;
        }
        Message why = null;
        Message done = null;
        if (action.startsWith("Out")) {
            why = cycle(world, store, ref, village, action, true);
        } else if (action.startsWith("In")) {
            why = cycle(world, store, ref, village, action, false);
        } else if (action.startsWith("Raise")) {
            TradeRoutes.Route r = route(world, index(action, "Raise"));
            if (r != null) {
                why = TradeRoutes.raise(world, store, ref, village, r);
                done = Message.translation(KEYS + "raised");
            }
        } else if (action.startsWith("Pay")) {
            TradeRoutes.Route r = route(world, index(action, "Pay"));
            if (r != null) {
                why = TradeRoutes.payCredit(world, store, ref, village, r);
                done = Message.translation(KEYS + "paid").param("credit", TradeRoutes.CREDIT_PER_FAVOUR);
            }
        } else if (action.startsWith("Close")) {
            TradeRoutes.Route r = route(world, index(action, "Close"));
            if (r != null) {
                why = TradeRoutes.close(world, store, ref, village, r);
            }
        } else if (action.startsWith("Open")) {
            int i = index(action, "Open");
            Village o = i >= 0 && i < candidates.size() ? TradeRoutes.village(world, candidates.get(i)) : null;
            if (o != null) {
                why = TradeRoutes.open(world, store, ref, village, o);
            }
        } else if (action.startsWith("Buy")) {
            int i = index(action, "Buy");
            if (i >= 0 && i < stall.size()) {
                why = buy(world, store, ref, village, stall.get(i));
                done = Message.translation(KEYS + "bought").param("count", stallLot(stall.get(i))).param("item", itemName(stall.get(i)));
            }
        }
        if (why != null) {
            tell(why, false);
        } else if (done != null) {
            tell(done, true);
        }
        rebuild();
    }
}
