package dev.nakasar.hytale.peuples.annex;

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
import dev.nakasar.hytale.peuples.request.BoardTabs;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.workshop.Workshops;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * L'onglet « Ouvrages » du panneau du village (Kevin, 2026-11-16) : une carte par type d'infrastructure (ouvrages
 * comptés / limite, coût, bouton qui remet la fondation), puis la liste des ouvrages du village (état, Détruire en deux
 * clics, Reprendre un ouvrage pris, Relever une ruine) et des ouvrages rivaux que ce village peut attaquer (rang Hôte,
 * {@value Ouvrages#OFFERING} faveurs). Mise en page {@code OuvragePage_<Peuple>.ui} ({@code tools/generate_workshop_ui.py}).
 */
public final class OuvragePage extends InteractiveCustomUIPage<OuvragePage.Event> {

    private static final String LAYOUT = "Pages/Nakasar/Peuples/OuvragePage.ui";
    private static final String KEYS = Annexes.KEYS;
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    private static final int TYPES = 4;
    private static final int MATERIALS = 3;
    /** Lignes de la liste : WORKS_ROWS de tools/generate_workshop_ui.py. */
    public static final int ROWS = 16;
    private static final String OK = "#7ed957";
    private static final String MISSING = "#e8c46a";

    /** Donnée d'un clic : {@code Grant<i>}, {@code Row<i>}, ou un onglet. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    /** Une ligne : un ouvrage du monde et ce que son bouton fait (Destroy, Retake, Rebuild, Attack, ou null). */
    private record Row(Infrastructures.Work work, String action) {
    }

    private final String villageId;
    /** Ligne dont la destruction attend la confirmation (clé village/bâtiment), ou null. */
    private String confirm;
    private List<Row> rows = List.of();

    public OuvragePage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        if (Annexes.catalog(village, Workshop.Annex.INFRASTRUCTURE).isEmpty()) {
            playerRef.sendMessage(Message.translation(KEYS + "none"));
            return;
        }
        player.getPageManager().openCustomPage(ref, store, new OuvragePage(playerRef, village));
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/OuvragePage_" + people.id() + ".ui" : LAYOUT;
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        cmd.append(layout(village == null ? null : village.people()));
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "page.orphan"));
            return;
        }
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "works.title").param("village", village.name()));
        cmd.set("#Intro.TextSpans", Message.translation(KEYS + "works.intro"));
        List<Workshop> types = Annexes.catalog(village, Workshop.Annex.INFRASTRUCTURE);
        types.sort((a, b) -> Integer.compare(order(a), order(b)));
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        for (int i = 0; i < TYPES; i++) {
            String n = Integer.toString(i);
            if (i >= types.size()) {
                cmd.set("#Type" + n + ".Visible", false);
                continue;
            }
            Workshop w = types.get(i);
            if (w.icon() != null) {
                cmd.set("#TypeIcon" + n + ".ItemId", w.icon());
            }
            cmd.set("#TypeName" + n + ".TextSpans", Message.translation(w.nameKey()));
            int count = Annexes.counted(village, w).size();
            cmd.set("#TypeCount" + n + ".TextSpans", Message.translation(KEYS + "works.count").param("count", count)
                    .param("limit", w.annex().limit()).param("tier", Message.translation(Tiers.nameKey(w.annex().tier()))));
            cmd.set("#TypeRole" + n + ".TextSpans", Message.translation(KEYS + "role." + w.annex().type()));
            VillageLayout.Material[] materials = w.annex().materials();
            for (int j = 0; j < MATERIALS; j++) {
                String k = Integer.toString(i * MATERIALS + j);
                boolean shown = j < materials.length;
                cmd.set("#TypeMat" + k + ".Visible", shown);
                if (shown) {
                    VillageLayout.Material m = materials[j];
                    int have = deposit == null ? 0 : Math.min(m.quantity(), deposit.getOrDefault(m.itemId(), 0));
                    boolean ok = have >= m.quantity();
                    cmd.set("#TypeMatIcon" + k + ".ItemId", m.itemId());
                    cmd.set("#TypeMatOk" + k + ".Visible", ok);
                    cmd.set("#TypeMatSlot" + k + ".Visible", !ok);
                    cmd.set("#TypeMatCount" + k + ".TextSpans", Message.translation("nakasar_peuples.boardPage.progress")
                            .param("have", have).param("need", m.quantity()));
                    cmd.set("#TypeMatCount" + k + ".Style.TextColor", ok ? OK : MISSING);
                }
            }
            boolean pending = false;
            for (AnnexState a : Annexes.counted(village, w)) {
                pending |= a.granted();
            }
            boolean can = Annexes.block(store, ref, village, w.annex().tier()) == null && (pending || count < w.annex().limit());
            cmd.set("#TypeAction" + n + ".Visible", can);
            if (can) {
                cmd.set("#TypeAction" + n + ".Text", Message.translation(KEYS + (pending ? "page.regive" : "page.grant")));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#TypeAction" + n, EventData.of("Action", "Grant" + n));
            }
        }
        rows = rows(world, store, village);
        cmd.set("#ListEmpty.Visible", rows.isEmpty());
        cmd.set("#ListEmpty.TextSpans", Message.translation(KEYS + "works.empty"));
        for (int i = 0; i < ROWS; i++) {
            String n = Integer.toString(i);
            if (i >= rows.size()) {
                cmd.set("#Row" + n + ".Visible", false);
                continue;
            }
            row(cmd, events, world, store, village, rows.get(i), n);
        }
        cmd.set("#Rule.TextSpans", Message.translation(KEYS + "works.rule").param("rank", Message.translation(Annexes.GRANT_RANK.nameKey()))
                .param("offering", Ouvrages.OFFERING).param("days", Ouvrages.LOST_DAYS));
        BoardTabs.fill(cmd, events, store, village);
    }

    private static int order(Workshop w) {
        return switch (w.annex().type()) {
            case Infrastructures.TOWER -> 0;
            case Infrastructures.POST -> 1;
            case Infrastructures.FORT -> 2;
            default -> 3;
        };
    }

    /** Les ouvrages du village (posés), ceux qu'il occupe, puis les ouvrages rivaux qu'il peut attaquer. */
    private static List<Row> rows(World world, Store<EntityStore> store, Village village) {
        List<Row> out = new ArrayList<>();
        long day = GameClock.day(store);
        for (Infrastructures.Work w : Infrastructures.all(world)) {
            if (w.owner() != village) {
                continue;
            }
            AnnexState a = w.state();
            String action = null;
            if (a.occupied() && !a.lost()) {
                action = "Retake";
            } else if (a.ruined()) {
                action = "Rebuild";
            } else if (Annexes.destroyable(a)) {
                action = "Destroy";
            }
            out.add(new Row(w, action));
        }
        for (Infrastructures.Work w : Infrastructures.all(world)) {
            if (w.owner() != village && w.holder().equals(village.id())) {
                out.add(new Row(w, null));
            }
        }
        for (Infrastructures.Work w : Ouvrages.targets(world, village, day)) {
            out.add(new Row(w, "Attack"));
        }
        return out.size() > ROWS ? new ArrayList<>(out.subList(0, ROWS)) : out;
    }

    private void row(UICommandBuilder cmd, UIEventBuilder events, World world, Store<EntityStore> store, Village village, Row r, String n) {
        Infrastructures.Work w = r.work();
        AnnexState a = w.state();
        if (w.workshop().icon() != null) {
            cmd.set("#RowIcon" + n + ".ItemId", w.workshop().icon());
        }
        Village holder = Villages.registry(world).byId(w.holder());
        cmd.set("#RowName" + n + ".TextSpans", Message.translation(KEYS + "works.row").param("building", Message.translation(w.workshop().nameKey()))
                .param("owner", w.owner().name()).param("x", a.x()).param("z", a.z()));
        String key = Ouvrages.key(w);
        boolean confirming = "Destroy".equals(r.action()) && key.equals(confirm);
        cmd.set("#RowState" + n + ".TextSpans", confirming
                ? Message.translation(KEYS + "destroy.warn").param("building", Message.translation(w.workshop().nameKey())).param("refund", Annexes.REFUND_DIVISOR)
                : state(world, store, village, w, holder));
        String button = switch (r.action() == null ? "" : r.action()) {
            case "Destroy" -> confirming ? "page.destroyConfirm" : "page.destroy";
            case "Retake" -> a.besieged() ? null : "works.retake";
            case "Rebuild" -> a.cleared() ? "works.rebuild" : null;
            case "Attack" -> "works.attack";
            default -> null;
        };
        cmd.set("#RowAction" + n + ".Visible", button != null);
        if (button != null) {
            cmd.set("#RowAction" + n + ".Text", Message.translation(KEYS + button).param("offering", Ouvrages.OFFERING));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#RowAction" + n, EventData.of("Action", "Row" + n));
        }
    }

    /** État de l'ouvrage en une phrase. */
    private static Message state(World world, Store<EntityStore> store, Village village, Infrastructures.Work w, Village holder) {
        AnnexState a = w.state();
        Message level = Message.translation(Workshops.KEYS + "levelShort." + w.level());
        if (a.besieged()) {
            Village by = Villages.registry(world).byId(a.siegeBy());
            long left = Math.max(0, a.siegeArrive() - GameClock.seconds(store));
            return Message.translation(KEYS + (left > 0 ? "works.marching" : "works.besieged")).param("village", by == null ? "?" : by.name())
                    .param("hours", (left + 3599) / 3600).param("soldiers", a.siegeSoldiers());
        }
        if (a.ruined()) {
            return Message.translation(KEYS + (a.cleared() ? "works.ruin" : "works.ruinPending"))
                    .param("list", Annexes.materialList(Ouvrages.rebuildCost(w.workshop()))).param("hours", Ouvrages.REBUILD_HOURS);
        }
        if (a.working()) {
            return Message.translation(KEYS + "state.working").param("hours", Annexes.hoursLeft(store, a)).param("x", a.x()).param("z", a.z());
        }
        if (a.occupied()) {
            long days = GameClock.day(store) - a.occupiedDay();
            if (w.owner() != village) {
                return Message.translation(KEYS + "works.holding").param("owner", w.owner().name()).param("guards", a.garrison()).param("days", days);
            }
            return Message.translation(KEYS + (a.lost() ? "works.lostState" : "works.occupied")).param("village", holder == null ? "?" : holder.name())
                    .param("guards", a.garrison()).param("days", Math.max(0, Ouvrages.LOST_DAYS - days));
        }
        if (w.owner() != village) {
            return Message.translation(KEYS + "works.target").param("holder", holder == null ? "?" : holder.name()).param("guards", Ouvrages.defenders(w))
                    .param("level", level);
        }
        return Message.translation(KEYS + "works.standing").param("level", level).param("guards", Ouvrages.defenders(w));
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
        String asked = confirm;
        confirm = null;
        if (action.startsWith("Grant")) {
            List<Workshop> types = Annexes.catalog(village, Workshop.Annex.INFRASTRUCTURE);
            types.sort((a, b) -> Integer.compare(order(a), order(b)));
            int i = index(action, "Grant");
            if (i >= 0 && i < types.size()) {
                Annexes.grant(world, store, ref, playerRef, village, types.get(i));
            }
        } else if (action.startsWith("Row")) {
            int i = index(action, "Row");
            if (i >= 0 && i < rows.size()) {
                Row r = rows.get(i);
                Infrastructures.Work w = Ouvrages.find(world, r.work().owner().id(), r.work().workshop().getId());
                if (w != null && r.action() != null) {
                    Message why = null;
                    switch (r.action()) {
                        case "Destroy" -> {
                            if (Ouvrages.key(w).equals(asked)) {
                                Annexes.destroy(world, store, ref, playerRef, village, w.workshop());
                            } else {
                                confirm = Ouvrages.key(w);
                            }
                        }
                        case "Retake" -> why = Ouvrages.retake(world, store, ref, village, w);
                        case "Rebuild" -> Ouvrages.rebuild(world, store, ref, playerRef, village, w.workshop());
                        case "Attack" -> why = Ouvrages.request(world, store, ref, village, w);
                        default -> {
                        }
                    }
                    if (why != null) {
                        playerRef.sendMessage(why);
                    }
                }
            }
        } else if (BoardTabs.handle(action, world, store, ref, playerRef, village)) {
            return;
        }
        rebuild();
    }

    private static int index(String action, String prefix) {
        try {
            return Integer.parseInt(action.substring(prefix.length()));
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
