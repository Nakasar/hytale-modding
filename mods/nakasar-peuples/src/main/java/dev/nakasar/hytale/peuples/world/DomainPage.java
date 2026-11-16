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
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.request.BoardTabs;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * L'onglet « Domaine » du panneau du village (GDD de la conquête, Kevin, 16 novembre 2026) : le blason du village
 * (changé par un joueur Hôte), les couleurs du joueur (les porter, broder ses bannières vierges), puis les lieux-dits
 * à portée : propriétaire, influence du village, gardes, occupation, et les demandes d'ambassade (Ami) ou d'expédition
 * (Hôte). Mise en page par peuple ({@code DomainPage_<Peuple>.ui}, {@code tools/generate_workshop_ui.py} domain_page).
 */
public final class DomainPage extends InteractiveCustomUIPage<DomainPage.Event> {

    public static final String KEYS = Heraldry.KEYS + "page.";
    private static final String LAYOUT = "Pages/Nakasar/Peuples/DomainPage.ui";
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    /** Lieux-dits listés (generate_workshop_ui.py DOMAIN_ROWS). */
    private static final int ROWS = 7;
    private static final String MUTED = "#96a9be";

    /** Donnée d'un clic : couleurs et emblème, blason, couleurs du joueur, broderie, ambassade ou expédition d'une ligne, onglets. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;
    private int colour = -1;
    private int emblem = -1;
    private final List<String> rows = new ArrayList<>();

    public DomainPage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    /** Ouvre l'onglet Domaine du village (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player != null) {
            player.getPageManager().openCustomPage(ref, store, new DomainPage(playerRef, village));
        }
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/DomainPage_" + people.id() + ".ui" : LAYOUT;
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
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "title").param("village", village.name()));
        BoardTabs.fill(cmd, events, store, village);
        arms(cmd, events, world, store, village);
        colours(cmd, events, world, store, ref, village);
        holdings(cmd, events, world, store, ref, village);
    }

    // ---- Blason ----

    private void arms(UICommandBuilder cmd, UIEventBuilder events, World world, Store<EntityStore> store, Village v) {
        Heraldry.Arms current = Heraldry.of(world, v);
        if (colour < 0) {
            colour = current.colour();
            emblem = current.emblem();
        }
        Heraldry.Arms shown = new Heraldry.Arms(colour, emblem, current.changed());
        cmd.set("#ArmsHeader.TextSpans", Message.translation(KEYS + "arms"));
        cmd.set("#ArmsIcon.ItemId", shown.standard());
        cmd.set("#ArmsName.TextSpans", shown.name());
        cmd.set("#ArmsName.Style.TextColor", shown.hex());
        boolean changed = colour != current.colour() || emblem != current.emblem();
        long wait = Heraldry.wait(world, v, GameClock.day(store));
        Message hint = changed ? Message.translation(KEYS + "arms.pending").param("count", Heraldry.CHANGE_BOLTS)
                : wait > 0 ? Message.translation(Heraldry.KEYS + "arms.wait").param("days", wait)
                : Message.translation(KEYS + "arms.hint").param("count", Heraldry.CHANGE_BOLTS).param("days", Heraldry.CHANGE_DAYS);
        cmd.set("#ArmsHint.TextSpans", hint);
        for (String b : new String[] {"ColourPrev", "ColourNext", "EmblemPrev", "EmblemNext"}) {
            cmd.set("#" + b + ".Text", Message.translation(KEYS + "button." + b));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#" + b, EventData.of("Action", b));
        }
        cmd.set("#ArmsApply.Visible", changed);
        if (changed) {
            cmd.set("#ArmsApply.Text", Message.translation(KEYS + "button.apply"));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#ArmsApply", EventData.of("Action", "ArmsApply"));
        }
    }

    // ---- Couleurs du joueur ----

    private void colours(UICommandBuilder cmd, UIEventBuilder events, World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v) {
        cmd.set("#ColoursHeader.TextSpans", Message.translation(KEYS + "colours"));
        Village worn = Colours.of(world, store, ref);
        boolean ours = worn != null && worn.id().equals(v.id());
        Message line = worn == null ? Message.translation(KEYS + "colours.none")
                : ours ? Message.translation(KEYS + "colours.ours").param("village", v.name())
                : Message.translation(KEYS + "colours.other").param("village", worn.name());
        cmd.set("#ColoursLine.TextSpans", line);
        cmd.set("#ColoursToggle.Text", Message.translation(KEYS + (ours ? "button.dropColours" : "button.takeColours")));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#ColoursToggle", EventData.of("Action", "Colours"));
        int blanks = WorldLife.count(store, ref, Heraldry.BLANK::equals);
        cmd.set("#BannersLine.TextSpans", Message.translation(KEYS + "banners").param("count", blanks));
        cmd.set("#Embroider.Visible", ours && blanks > 0);
        if (ours && blanks > 0) {
            cmd.set("#Embroider.Text", Message.translation(KEYS + "button.embroider"));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#Embroider", EventData.of("Action", "Embroider"));
        }
    }

    // ---- Lieux-dits ----

    private void holdings(UICommandBuilder cmd, UIEventBuilder events, World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v) {
        long day = GameClock.day(store);
        List<Hamlets.Place> held = Allegiance.holdings(world, v);
        int council = Allegiance.councilLevel(v);
        cmd.set("#HoldHeader.TextSpans", Message.translation(KEYS + "holdings").param("count", held.size()).param("cap", Allegiance.cap(v))
                .param("council", council));
        List<Hamlets.Place> list = new ArrayList<>();
        for (Hamlets.Place h : Hamlets.all(world)) {
            if (h.stage() == Hamlets.BUILT && Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z())) <= Allegiance.RANGE) {
                list.add(h);
            }
        }
        list.sort(Comparator.comparingInt((Hamlets.Place h) -> {
            Village o = Allegiance.owner(world, h);
            return o != null && o.id().equals(v.id()) ? 0 : 1;
        }).thenComparingInt(h -> -Allegiance.influence(world, h, v)));
        rows.clear();
        cmd.set("#NoHamlet.Visible", list.isEmpty());
        if (list.isEmpty()) {
            cmd.set("#NoHamlet.TextSpans", Message.translation(KEYS + "none").param("range", Allegiance.RANGE));
        }
        for (int i = 0; i < ROWS; i++) {
            String n = Integer.toString(i);
            if (i >= list.size()) {
                cmd.set("#Row" + n + ".Visible", false);
                continue;
            }
            Hamlets.Place h = list.get(i);
            rows.add(h.id());
            cmd.set("#Row" + n + ".Visible", true);
            Hamlet type = h.type();
            if (type != null && type.icon() != null) {
                cmd.set("#RowIcon" + n + ".ItemId", type.icon());
            }
            int dist = (int) Math.round(Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z())));
            cmd.set("#RowName" + n + ".TextSpans", Message.translation(KEYS + "row.name").param("hamlet", h.name()).param("distance", dist)
                    .param("dir", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(h.x() - v.x(), h.z() - v.z()))));
            Village owner = Allegiance.owner(world, h);
            cmd.set("#RowOwner" + n + ".TextSpans", owner == null ? Message.translation(KEYS + "row.free")
                    : Message.translation(KEYS + "row.owner").param("village", owner.name()));
            cmd.set("#RowOwner" + n + ".Style.TextColor", owner == null ? MUTED : Heraldry.of(world, owner).hex());
            int inf = Allegiance.influence(world, h, v);
            Message state = Message.translation(KEYS + "row.influence").param("value", (inf > 0 ? "+" : "") + inf);
            if (owner != null) {
                state = Message.translation(KEYS + "row.state").param("influence", state).param("guards", Garrisons.count(world, h));
                if (Allegiance.occupied(world, h, day)) {
                    state = Message.translation(KEYS + "row.occupied").param("state", state)
                            .param("days", Allegiance.occupiedUntil(world, h) - day + 1);
                }
            }
            cmd.set("#RowState" + n + ".TextSpans", state);
            boolean mine = owner != null && owner.id().equals(v.id());
            boolean embassy = !mine && Embassies.blocked(world, h, v, day) == null;
            cmd.set("#RowEmbassy" + n + ".Visible", embassy);
            if (embassy) {
                cmd.set("#RowEmbassy" + n + ".Text", Message.translation(KEYS + "button.embassy").param("count", Embassies.OFFERING));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#RowEmbassy" + n, EventData.of("Action", "Embassy" + n));
            }
            boolean expedition = !mine && Sieges.blocked(world, h, v, day) == null;
            cmd.set("#RowExpedition" + n + ".Visible", expedition);
            if (expedition) {
                cmd.set("#RowExpedition" + n + ".Text", Message.translation(KEYS + "button.expedition").param("count", Sieges.OFFERING));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#RowExpedition" + n, EventData.of("Action", "Expedition" + n));
            }
        }
        cmd.set("#Rule.TextSpans", Message.translation(KEYS + "rule"));
    }

    private Hamlets.Place row(World world, String action, String prefix) {
        try {
            int i = Integer.parseInt(action.substring(prefix.length()));
            return i >= 0 && i < rows.size() ? Hamlets.get(world, rows.get(i)) : null;
        } catch (NumberFormatException e) {
            return null;
        }
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
        int[] own = Heraldry.emblemsOf(village.people().id());
        switch (action) {
            case "ColourPrev" -> colour = Math.floorMod(colour - 1, Heraldry.COLOUR_COUNT);
            case "ColourNext" -> colour = Math.floorMod(colour + 1, Heraldry.COLOUR_COUNT);
            case "EmblemPrev", "EmblemNext" -> {
                // Les emblèmes du peuple et l'étoile, dans l'ordre.
                int at = 0;
                for (int i = 0; i < own.length; i++) {
                    if (own[i] == emblem) {
                        at = i;
                    }
                }
                emblem = own[Math.floorMod(at + ("EmblemNext".equals(action) ? 1 : -1), own.length)];
            }
            case "ArmsApply" -> {
                Message why = Heraldry.change(world, store, ref, playerRef, village, colour, emblem);
                if (why != null) {
                    tell(why, false);
                }
            }
            case "Colours" -> tell(Colours.toggle(world, store, ref, village), true);
            case "Embroider" -> {
                int n = Colours.wears(store, ref, village) ? Heraldry.embroider(world, store, ref, village) : 0;
                tell(Message.translation(KEYS + "embroidered").param("count", n).param("arms", Heraldry.of(world, village).name()), n > 0);
            }
            default -> {
                if (action.startsWith("Embassy")) {
                    Hamlets.Place h = row(world, action, "Embassy");
                    Message why = h == null ? null : Embassies.request(world, store, ref, village, h);
                    if (h != null) {
                        tell(why != null ? why : Message.translation(KEYS + "embassy.sent").param("hamlet", h.name()), why == null);
                    }
                } else if (action.startsWith("Expedition")) {
                    Hamlets.Place h = row(world, action, "Expedition");
                    Message why = h == null ? null : Sieges.request(world, store, ref, village, h);
                    if (h != null) {
                        tell(why != null ? why : Message.translation(KEYS + "expedition.sent").param("hamlet", h.name()), why == null);
                    }
                }
            }
        }
        rebuild();
    }
}
