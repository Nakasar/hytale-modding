package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomPageLifetime;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.InteractiveCustomUIPage;
import com.hypixel.hytale.server.core.ui.Anchor;
import com.hypixel.hytale.server.core.ui.Value;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.raid.Raids;
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
 * L'onglet « Monde » du panneau du village (Kevin, 16 novembre 2026 ; maquette Claude Design « Panneau du village —
 * refonte ») : ce que le monde vivant fait autour de ce village.
 * <ul>
 *   <li>à gauche, la <b>boussole des voisins</b> (direction et distance, une couleur par relation, le troupeau et les
 *   campements du village), puis une fiche par voisin : relation, route balisée, auberge, trêve, dernière escarmouche ;</li>
 *   <li>à droite, <b>En ce moment</b> (escarmouche, raid, foire, fêtes, migration en cours), l'<b>agenda</b> des jours
 *   qui viennent (escarmouche attendue, raid, fête des moissons, foire, migration), et <b>Sur les routes</b> : les
 *   voyageurs partis du village ou qui y viennent, avec leur progression.</li>
 * </ul>
 * Mise en page par peuple ({@code WorldPage_<Peuple>.ui}, {@code tools/generate_workshop_ui.py}) : les tailles de la
 * boussole sont celles de COMPASS_* là-bas.
 */
public final class WorldPage extends InteractiveCustomUIPage<WorldPage.Event> {

    public static final String KEYS = WorldLife.KEYS + "page.";
    private static final String LAYOUT = "Pages/Nakasar/Peuples/WorldPage.ui";
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    private static final int NEIGHBOURS = 5;
    private static final int MARKS = 8;
    private static final int CAMPS = 2;
    private static final int AGENDA = 5;
    private static final int ROADS = 4;
    /** Boussole (generate_workshop_ui.py COMPASS_*) : côté, rayon du bord, décalage dans la colonne. */
    private static final int COMPASS_BOX = 230;
    private static final int COMPASS_RADIUS = 105;
    private static final int COMPASS_LEFT = 90;
    private static final int COMPASS_TOP = 6;
    private static final int MARK_WIDTH = 110;
    private static final int MARK_HEIGHT = 34;
    private static final int DOT = 14;
    private static final String[] MARK_KINDS = {"Ally", "Friendly", "Neutral", "Tense", "Rival", "Herd", "Camp"};
    private static final String[] STATES = {"Ally", "Friendly", "Neutral", "Tense", "Rival"};
    /** Une couleur par relation, la même que les marqueurs et les liserés (MARK_COLORS du générateur). */
    private static final String[] STATE_COLORS = {"#9ed36a", "#c9e08a", "#a9b8c8", "#e8b06a", "#f08a7a"};

    /** Donnée d'un clic : {@code Tab<X>}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;

    public WorldPage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    /** Ouvre l'onglet Monde du village (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player != null) {
            player.getPageManager().openCustomPage(ref, store, new WorldPage(playerRef, village));
        }
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/WorldPage_" + people.id() + ".ui" : LAYOUT;
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        cmd.append(layout(village == null ? null : village.people()));
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "orphan"));
            return;
        }
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "title").param("village", village.name()));
        BoardTabs.fill(cmd, events, store, village);
        long day = GameClock.day(store);
        List<Links.Link> links = new ArrayList<>(Links.of(world, village));
        links.sort(Comparator.comparingDouble(Links.Link::length));
        neighbours(cmd, world, village, links, day);
        compass(cmd, world, village, links);
        now(cmd, world, store, village, links);
        agenda(cmd, world, store, village, links, day);
        roads(cmd, world, village);
        cmd.set("#Totals.TextSpans", Message.translation(KEYS + "world.travellers").param("count", Travellers.all(world).size())
                .param("camps", Camps.all(world).size()));
    }

    // ---- Boussole ----

    private static void compass(UICommandBuilder cmd, World world, Village v, List<Links.Link> links) {
        int n = 0;
        for (Links.Link l : links) {
            if (n >= NEIGHBOURS) {
                break;
            }
            Village other = l.other(v.id());
            String kind = STATES[stateIndex(Relations.state(Relations.value(world, l.a(), l.b())))];
            mark(cmd, n++, v, other.x(), other.z(), kind, Message.raw(other.name()));
        }
        double[] herd = Calendar.herdAt();
        if (herd != null && distance(v, herd[0], herd[1]) <= Links.MAX_LENGTH) {
            mark(cmd, n++, v, herd[0], herd[1], "Herd", Message.translation(KEYS + "compass.herd"));
        }
        int camps = 0;
        for (Camps.Camp c : Camps.all(world)) {
            if (camps < CAMPS && n < MARKS && v.id().equals(c.village())) {
                mark(cmd, n++, v, c.x(), c.z(), "Camp", Message.translation(Camps.KEYS + "type." + c.type().key()));
                camps++;
            }
        }
        for (; n < MARKS; n++) {
            cmd.set("#Mark" + n + ".Visible", false);
        }
    }

    /** Place le marqueur `i` (son point au lieu, son nom dessous) et montre sa forme. */
    private static void mark(UICommandBuilder cmd, int i, Village v, double x, double z, String kind, Message name) {
        double dx = x - v.x();
        double dz = z - v.z();
        double d = Math.hypot(dx, dz);
        double r = radius(d);
        // Est à droite, sud en bas (Requests.direction : +z = sud).
        double px = COMPASS_LEFT + COMPASS_BOX / 2.0 + (d < 1 ? 0 : r * dx / d);
        double py = COMPASS_TOP + COMPASS_BOX / 2.0 + (d < 1 ? 0 : r * dz / d);
        Anchor a = new Anchor();
        a.setLeft(Value.of((int) Math.round(px - MARK_WIDTH / 2.0)));
        a.setTop(Value.of((int) Math.round(py - DOT / 2.0)));
        a.setWidth(Value.of(MARK_WIDTH));
        a.setHeight(Value.of(MARK_HEIGHT));
        cmd.setObject("#Mark" + i + ".Anchor", a);
        cmd.set("#Mark" + i + ".Visible", true);
        for (String k : MARK_KINDS) {
            cmd.set(String.format("#Mark%s%d.Visible", k, i), k.equals(kind));
        }
        cmd.set("#MarkName" + i + ".TextSpans", name);
    }

    /** Rayon sur la boussole : 1000 blocs aux trois quarts du bord, puis jusqu'au bord à 2400 blocs (Links.MAX_LENGTH). */
    static double radius(double blocks) {
        if (blocks <= 1000) {
            return COMPASS_RADIUS * 0.75 * blocks / 1000.0;
        }
        double t = Math.min(1.0, (blocks - 1000) / (Links.MAX_LENGTH - 1000.0));
        return COMPASS_RADIUS * (0.75 + 0.25 * t);
    }

    // ---- Voisins ----

    private static void neighbours(UICommandBuilder cmd, World world, Village v, List<Links.Link> links, long day) {
        cmd.set("#NeighboursTitle.TextSpans", Message.translation(KEYS + "neighbours.title"));
        cmd.set("#NeighboursNone.Visible", links.isEmpty());
        if (links.isEmpty()) {
            cmd.set("#NeighboursNone.TextSpans", Message.translation(KEYS + "neighbours.none"));
        }
        for (int i = 0; i < NEIGHBOURS; i++) {
            if (i >= links.size()) {
                cmd.set("#Nb" + i + ".Visible", false);
                continue;
            }
            Links.Link l = links.get(i);
            Village other = l.other(v.id());
            int value = Relations.value(world, l.a(), l.b());
            String state = Relations.state(value);
            int s = stateIndex(state);
            for (int k = 0; k < STATES.length; k++) {
                cmd.set(String.format("#Nb%s%d.Visible", STATES[k], i), k == s);
            }
            cmd.set("#NbName" + i + ".TextSpans", Message.raw(other.name()));
            cmd.set("#NbState" + i + ".TextSpans", Message.translation(Relations.KEYS + "state." + state));
            cmd.set("#NbState" + i + ".Style.TextColor", STATE_COLORS[s]);
            cmd.set("#NbLine" + i + ".TextSpans", Message.translation(KEYS + "neighbours.line")
                    .param("people", Message.translation(other.people().nameKey()))
                    .param("distance", (int) Math.round(l.length())).param("direction", direction(v, other.x(), other.z()))
                    .param("value", value));
            List<Message> extras = new ArrayList<>();
            boolean road = Routes.gap(world, v.x() + 0.5, v.z() + 0.5, other.x() + 0.5, other.z() + 0.5) <= 0;
            extras.add(Message.translation(KEYS + (road ? "neighbours.road" : "neighbours.noRoad")));
            Inns.Inn inn = Inns.get(world, l.key());
            if (inn != null && inn.open()) {
                extras.add(Message.translation(KEYS + "neighbours.inn").param("level", inn.level()));
            }
            if (Relations.truce(world, l.a(), l.b(), day)) {
                extras.add(Message.translation(KEYS + "neighbours.truce"));
            }
            Object[] last = Relations.last(world, l.key());
            if (last != null && day - (Long) last[0] <= Links.WINDOW_DAYS) {
                String winner = (String) last[1];
                String k = winner == null ? "neighbours.lastDraw" : winner.equals(v.id()) ? "neighbours.lastWon" : "neighbours.lastLost";
                extras.add(Message.translation(KEYS + k).param("when", when(day - (Long) last[0], true)));
            }
            cmd.set("#NbExtras" + i + ".TextSpans", join(extras));
        }
    }

    private static int stateIndex(String state) {
        return switch (state) {
            case "ally" -> 0;
            case "friendly" -> 1;
            case "tense" -> 3;
            case "rival" -> 4;
            default -> 2;
        };
    }

    // ---- En ce moment ----

    private static void now(UICommandBuilder cmd, World world, Store<EntityStore> store, Village v, List<Links.Link> links) {
        List<Message> out = new ArrayList<>();
        if (Raids.isActive(v)) {
            out.add(Message.translation(KEYS + "now.raid"));
        }
        for (Links.Link l : links) {
            if (Relations.fighting(l.key())) {
                double[] mid = l.middle();
                out.add(Message.translation(KEYS + "now.skirmish").param("village", l.other(v.id()).name())
                        .param("direction", direction(v, mid[0], mid[1])));
            }
        }
        if (Calendar.running("feast", v)) {
            out.add(Message.translation(KEYS + "now.feastHere"));
        }
        int feasts = 0;
        for (Village other : Villages.registry(world).all()) {
            if (!other.id().equals(v.id()) && Calendar.running("feast", other)) {
                feasts++;
            }
            if (Calendar.running("fair", other)) {
                out.add(other.id().equals(v.id()) ? Message.translation(KEYS + "now.fairHere")
                        : Message.translation(KEYS + "now.fair").param("village", other.name())
                        .param("distance", distance(v, other.x(), other.z())).param("direction", direction(v, other.x(), other.z())));
            }
        }
        if (feasts > 0) {
            out.add(Message.translation(KEYS + "now.feasts").param("count", feasts));
        }
        double[] herd = Calendar.herdAt();
        if (herd != null) {
            out.add(Message.translation(KEYS + "now.herd").param("distance", distance(v, herd[0], herd[1]))
                    .param("direction", direction(v, herd[0], herd[1])));
        }
        cmd.set("#Now.Visible", !out.isEmpty());
        if (!out.isEmpty()) {
            cmd.set("#NowTitle.TextSpans", Message.translation(KEYS + "now.title"));
            cmd.set("#NowText.TextSpans", join(out));
        }
    }

    // ---- Agenda ----

    /** Une ligne de l'agenda : dans combien de jours, à quelle heure (pour l'ordre), quand (texte), quoi, ici ou non. */
    private record Entry(long days, int hour, Message when, Message what, boolean here) {
    }

    private static void agenda(UICommandBuilder cmd, World world, Store<EntityStore> store, Village v, List<Links.Link> links, long day) {
        List<Entry> out = new ArrayList<>();
        for (Links.Link l : links) {
            int hour = Relations.pendingHour(world, l.key(), day);
            if (hour >= 0 && !Relations.fighting(l.key())) {
                out.add(new Entry(0, hour, when(0, false), Message.translation(KEYS + "agenda.skirmish")
                        .param("village", l.other(v.id()).name()).param("hour", hour), false));
            }
        }
        if (!Raids.isActive(v) && v.raid().scheduled()) {
            long d = Math.max(0, v.raid().night() - day);
            out.add(new Entry(d, GameClock.DUSK, d == 0 ? Message.translation(KEYS + "agenda.tonight") : when(d, false),
                    Message.translation(KEYS + "agenda.raid"), true));
        }
        if (!Calendar.running("feast", v) && Calendar.hasFarm(v)) {
            long d = Calendar.upcoming(world, store, "feast", Calendar.FEAST_EVERY, 3) - day;
            out.add(new Entry(d, Calendar.FEAST_HOUR, when(d, false),
                    Message.translation(KEYS + "agenda.feast").param("hour", Calendar.FEAST_HOUR), true));
        }
        boolean fairRunning = false;
        for (Village other : Villages.registry(world).all()) {
            fairRunning |= Calendar.running("fair", other);
        }
        Object[] fair = fairRunning ? null : fair(world, store);
        if (fair != null && fair[0] instanceof Village host) {
            long d = (Long) fair[1];
            boolean here = host.id().equals(v.id());
            out.add(new Entry(d, Calendar.FAIR_HOUR, when(d, false), here
                    ? Message.translation(KEYS + "agenda.fairHere").param("hour", Calendar.FAIR_HOUR)
                    : Message.translation(KEYS + "agenda.fair").param("village", host.name()).param("hour", Calendar.FAIR_HOUR)
                    .param("distance", distance(v, host.x(), host.z())).param("direction", direction(v, host.x(), host.z())), here));
        }
        if (Calendar.herdAt() == null) {
            long d = Calendar.upcoming(world, store, "migration", Calendar.MIGRATION_EVERY, 5) - day;
            out.add(new Entry(d, 0, when(d, false), Message.translation(KEYS + "agenda.migration"), false));
        }
        out.sort(Comparator.comparingLong(Entry::days).thenComparingInt(Entry::hour));
        // Ce qui manque pour une fête ou une foire, en dernier s'il reste de la place.
        if (!Calendar.hasFarm(v)) {
            out.add(new Entry(Long.MAX_VALUE, 0, Message.translation(KEYS + "agenda.never"), Message.translation(KEYS + "village.noFeast"), false));
        }
        if (!fairRunning && (fair == null || fair[0] == null)) {
            out.add(new Entry(Long.MAX_VALUE, 0, Message.translation(KEYS + "agenda.never"), Message.translation(KEYS + "world.noFair"), false));
        }
        cmd.set("#AgendaTitle.TextSpans", Message.translation(KEYS + "agenda.title"));
        cmd.set("#AgendaNone.Visible", out.isEmpty());
        if (out.isEmpty()) {
            cmd.set("#AgendaNone.TextSpans", Message.translation(KEYS + "agenda.none"));
        }
        for (int i = 0; i < AGENDA; i++) {
            if (i >= out.size()) {
                cmd.set("#Ag" + i + ".Visible", false);
                continue;
            }
            Entry e = out.get(i);
            cmd.set("#AgHere" + i + ".Visible", e.here());
            cmd.set("#AgWhen" + i + ".TextSpans", e.when());
            cmd.set("#AgWhen" + i + ".Style.TextColor", e.days() == Long.MAX_VALUE ? "#6f7d8c" : e.here() ? "#e8c46a" : "#b4c8c9");
            cmd.set("#AgText" + i + ".TextSpans", e.what());
        }
    }

    // ---- Sur les routes ----

    private static void roads(UICommandBuilder cmd, World world, Village v) {
        List<Travellers.Traveller> mine = new ArrayList<>();
        for (Travellers.Traveller t : Travellers.all(world)) {
            if (v.id().equals(t.from()) || v.id().equals(t.to())) {
                mine.add(t);
            }
        }
        // Les départs d'abord, puis les arrivées les plus proches.
        mine.sort(Comparator.comparing((Travellers.Traveller t) -> !v.id().equals(t.from())).thenComparingDouble(t -> -t.at));
        cmd.set("#RoadsTitle.TextSpans", Message.translation(KEYS + "roads.title"));
        cmd.set("#RoadsCount.TextSpans", mine.isEmpty() ? Message.raw(" ") : Message.translation(KEYS + "roads.count").param("count", mine.size()));
        cmd.set("#RoadsNone.Visible", mine.isEmpty());
        if (mine.isEmpty()) {
            cmd.set("#RoadsNone.TextSpans", Message.translation(KEYS + "roads.none"));
        }
        int n = 0;
        for (Travellers.Traveller t : mine) {
            if (n >= ROADS) {
                break;
            }
            boolean leaving = v.id().equals(t.from());
            Village other = Villages.registry(world).byId(leaving ? t.to() : t.from());
            Links.Link link = Links.of(world, t.from(), t.to());
            if (other == null || link == null) {
                continue;
            }
            int length = (int) Math.max(1, Math.round(link.length()));
            int at = (int) Math.round(Math.min(t.at, link.length()));
            cmd.set("#Tr" + n + ".Visible", true);
            cmd.set("#TrKind" + n + ".TextSpans", Message.translation(Travellers.KEYS + "kind." + t.kind().key()));
            cmd.set("#TrKind" + n + ".Style.TextColor", kindColor(t.kind()));
            cmd.set("#TrText" + n + ".TextSpans", Message.translation(KEYS + (leaving ? "roads.out" : "roads.in"))
                    .param("village", other.name()).param("direction", direction(v, other.x(), other.z())));
            cmd.set("#TrBar" + n + ".Value", (float) at / length);
            cmd.set("#TrLeft" + n + ".TextSpans", leaving
                    ? Message.translation(KEYS + "roads.outProgress").param("at", at).param("length", length)
                    : Message.translation(KEYS + "roads.inProgress").param("left", Math.max(0, length - at)));
            n++;
        }
        for (; n < ROADS; n++) {
            cmd.set("#Tr" + n + ".Visible", false);
        }
    }

    private static String kindColor(Travellers.Kind kind) {
        return switch (kind) {
            case CARAVAN -> "#e8c46a";
            case MERCHANT -> "#a9c4e6";
            case PILGRIM -> "#9ed36a";
            case MESSENGER -> "#d3d6db";
        };
    }

    // ---- Outils ----

    /** Village de la prochaine foire (pas en cours) et dans combien de jours, ou null. */
    private static Object[] fair(World world, Store<EntityStore> store) {
        long day = GameClock.day(store);
        long d = Calendar.upcoming(world, store, "fair", Calendar.FAIR_EVERY, 7);
        Object[] f = Calendar.nextFair(world, d);
        return f == null ? null : new Object[] {f[0], d - day};
    }

    private static Message join(List<Message> parts) {
        Message m = Message.empty();
        for (int k = 0; k < parts.size(); k++) {
            if (k > 0) {
                m.insert(" · ");
            }
            m.insert(parts.get(k));
        }
        return m;
    }

    private static Message when(long days, boolean past) {
        String p = past ? "ago." : "in.";
        if (days <= 0) {
            return Message.translation(KEYS + "when." + p + "today");
        }
        if (days == 1) {
            return Message.translation(KEYS + "when." + p + "one");
        }
        return Message.translation(KEYS + "when." + p + "days").param("days", days);
    }

    private static int distance(Village v, double x, double z) {
        return (int) Math.round(Math.hypot(x - v.x(), z - v.z()));
    }

    private static Message direction(Village v, double x, double z) {
        return Message.translation(Villages.MESSAGES + "dir." + Requests.direction(x - v.x(), z - v.z()));
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
        if (BoardTabs.handle(data.action, world, store, ref, playerRef, village)) {
            return;
        }
        rebuild();
    }
}
