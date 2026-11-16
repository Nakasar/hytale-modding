package dev.nakasar.hytale.peuples.world;

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
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.request.BoardPage;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.List;

/**
 * L'onglet « Monde » du panneau du village (Kevin, 16 novembre 2026) : ce que le monde vivant fait autour de ce village,
 * en quatre cartes :
 * <ul>
 *   <li><b>Sur les routes</b> : voyageurs partis du village ou qui y viennent (où ils en sont), escarmouches en cours,
 *   prévues aujourd'hui ou la dernière, avec chaque voisin ;</li>
 *   <li><b>Voisins</b> : chaque village relié (distance, direction, relation, trêve, route balisée ou non, auberge) ;</li>
 *   <li><b>Au village</b> : fête des moissons, foire si elle se tient ici, raid annoncé, campements des alentours ;</li>
 *   <li><b>Dans le monde</b> : prochaine foire (où et quand), migration en cours ou prochaine.</li>
 * </ul>
 * Mise en page par peuple ({@code WorldPage_<Peuple>.ui}, {@code tools/generate_workshop_ui.py}).
 */
public final class WorldPage extends InteractiveCustomUIPage<WorldPage.Event> {

    public static final String KEYS = WorldLife.KEYS + "page.";
    private static final String LAYOUT = "Pages/Nakasar/Peuples/WorldPage.ui";
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    /** Lignes au plus par carte (la carte ne défile pas). */
    private static final int MAX_LINES = 6;
    private static final int MAX_NEIGHBOURS = 5;

    /** Donnée d'un clic : {@code Back}. */
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
        cmd.set("#Back.Text", Message.translation(KEYS + "back"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Back", EventData.of("Action", "Back"));
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "orphan"));
            return;
        }
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "title").param("village", village.name()));
        cmd.set("#Intro.TextSpans", Message.translation(KEYS + "intro").param("day", GameClock.day(store) + 1)
                .param("hour", GameClock.hour(store)));
        card(cmd, 0, "roads", roads(world, store, village));
        card(cmd, 1, "neighbours", neighbours(world, store, village));
        card(cmd, 2, "village", here(world, store, village));
        card(cmd, 3, "world", everywhere(world, store, village));
    }

    private static void card(UICommandBuilder cmd, int i, String title, List<Message> lines) {
        cmd.set("#CardTitle" + i + ".TextSpans", Message.translation(KEYS + title + ".title"));
        if (lines.isEmpty()) {
            lines.add(Message.translation(KEYS + title + ".none"));
        }
        Message body = Message.empty();
        int n = Math.min(lines.size(), MAX_LINES);
        for (int k = 0; k < n; k++) {
            if (k > 0) {
                body.insert("\n");
            }
            body.insert(Message.translation(KEYS + "bullet").param("line", lines.get(k)));
        }
        if (lines.size() > MAX_LINES) {
            body.insert("\n");
            body.insert(Message.translation(KEYS + "more").param("count", lines.size() - MAX_LINES));
        }
        cmd.set("#CardBody" + i + ".TextSpans", body);
    }

    // ---- Sur les routes ----

    static List<Message> roads(World world, Store<EntityStore> store, Village v) {
        List<Message> out = new ArrayList<>();
        for (Travellers.Traveller t : Travellers.all(world)) {
            boolean leaving = v.id().equals(t.from());
            if (!leaving && !v.id().equals(t.to())) {
                continue;
            }
            Village other = Villages.registry(world).byId(leaving ? t.to() : t.from());
            Links.Link link = Links.of(world, t.from(), t.to());
            if (other == null || link == null) {
                continue;
            }
            int length = (int) Math.round(link.length());
            int at = (int) Math.round(Math.min(t.at, link.length()));
            out.add(Message.translation(KEYS + (leaving ? "roads.out" : "roads.in"))
                    .param("kind", Message.translation(Travellers.KEYS + "kind." + t.kind().key()))
                    .param("village", other.name()).param("at", at).param("length", length).param("left", Math.max(0, length - at))
                    .param("direction", direction(v, other.x(), other.z())));
        }
        long day = GameClock.day(store);
        for (Links.Link l : Links.of(world, v)) {
            Village other = l.other(v.id());
            if (Relations.fighting(l.key())) {
                double[] mid = l.middle();
                out.add(Message.translation(KEYS + "roads.skirmish").param("village", other.name())
                        .param("direction", direction(v, mid[0], mid[1])));
                continue;
            }
            int hour = Relations.pendingHour(world, l.key(), day);
            if (hour >= 0) {
                out.add(Message.translation(KEYS + "roads.skirmishSoon").param("village", other.name()).param("hour", hour));
                continue;
            }
            Object[] last = Relations.last(world, l.key());
            if (last != null && day - (Long) last[0] <= Links.WINDOW_DAYS) {
                String winner = (String) last[1];
                Village w = winner == null ? null : Villages.registry(world).byId(winner);
                out.add(Message.translation(KEYS + (w == null ? "roads.skirmishDraw" : "roads.skirmishWon"))
                        .param("village", other.name()).param("winner", w == null ? "?" : w.name())
                        .param("when", when(day - (Long) last[0], true)));
            }
        }
        return out;
    }

    // ---- Voisins ----

    static List<Message> neighbours(World world, Store<EntityStore> store, Village v) {
        List<Message> out = new ArrayList<>();
        long day = GameClock.day(store);
        for (Links.Link l : Links.of(world, v)) {
            if (out.size() >= MAX_NEIGHBOURS) {
                break;
            }
            Village other = l.other(v.id());
            int value = Relations.value(world, l.a(), l.b());
            Message extras = Message.empty();
            if (Relations.truce(world, l.a(), l.b(), day)) {
                extras.insert(Message.translation(KEYS + "neighbours.truce"));
            }
            boolean road = Routes.gap(world, v.x() + 0.5, v.z() + 0.5, other.x() + 0.5, other.z() + 0.5) <= 0;
            extras.insert(Message.translation(KEYS + (road ? "neighbours.road" : "neighbours.noRoad")));
            Inns.Inn inn = Inns.get(world, l.key());
            if (inn != null && inn.open()) {
                extras.insert(Message.translation(KEYS + "neighbours.inn").param("level", inn.level()));
            }
            out.add(Message.translation(KEYS + "neighbours.line").param("village", other.name())
                    .param("people", Message.translation(other.people().nameKey()))
                    .param("distance", (int) Math.round(l.length())).param("direction", direction(v, other.x(), other.z()))
                    .param("state", Message.translation(Relations.KEYS + "state." + Relations.state(value))).param("value", value)
                    .param("extras", extras));
        }
        return out;
    }

    // ---- Au village ----

    static List<Message> here(World world, Store<EntityStore> store, Village v) {
        List<Message> out = new ArrayList<>();
        long day = GameClock.day(store);
        if (Calendar.running("feast", v)) {
            out.add(Message.translation(KEYS + "village.feastNow"));
        } else if (Calendar.hasFarm(v)) {
            long d = Calendar.upcoming(world, store, "feast", Calendar.FEAST_EVERY, 3);
            out.add(Message.translation(KEYS + "village.feast").param("when", when(d - day, false)).param("hour", Calendar.FEAST_HOUR));
        } else {
            out.add(Message.translation(KEYS + "village.noFeast"));
        }
        if (Calendar.running("fair", v)) {
            out.add(Message.translation(KEYS + "village.fairNow"));
        } else {
            Object[] fair = fair(world, store);
            if (fair != null && fair[0] instanceof Village h && h.id().equals(v.id())) {
                out.add(Message.translation(KEYS + "village.fair").param("when", when((Long) fair[1], false))
                        .param("hour", Calendar.FAIR_HOUR));
            }
        }
        out.add(Raids.status(store, v));
        for (Camps.Camp c : Camps.all(world)) {
            if (v.id().equals(c.village())) {
                out.add(Message.translation(KEYS + "village.camp")
                        .param("type", Message.translation(Camps.KEYS + "type." + c.type().key()))
                        .param("distance", (int) Math.round(Math.hypot(c.x() - v.x(), c.z() - v.z())))
                        .param("direction", direction(v, c.x(), c.z())));
            }
        }
        return out;
    }

    // ---- Dans le monde ----

    static List<Message> everywhere(World world, Store<EntityStore> store, Village v) {
        List<Message> out = new ArrayList<>();
        long day = GameClock.day(store);
        Village fairNow = null;
        for (Village other : Villages.registry(world).all()) {
            if (Calendar.running("fair", other)) {
                fairNow = other;
            }
        }
        if (fairNow != null) {
            out.add(Message.translation(KEYS + "world.fairNow").param("village", fairNow.name())
                    .param("distance", distance(v, fairNow.x(), fairNow.z())).param("direction", direction(v, fairNow.x(), fairNow.z())));
        } else {
            Object[] fair = fair(world, store);
            if (fair != null && fair[0] != null) {
                Village host = (Village) fair[0];
                out.add(Message.translation(KEYS + (host.id().equals(v.id()) ? "world.fairHere" : "world.fair")).param("village", host.name())
                        .param("when", when((Long) fair[1], false)).param("hour", Calendar.FAIR_HOUR)
                        .param("distance", distance(v, host.x(), host.z())).param("direction", direction(v, host.x(), host.z())));
            } else {
                out.add(Message.translation(KEYS + "world.noFair"));
            }
        }
        double[] herd = Calendar.herdAt();
        if (herd != null) {
            out.add(Message.translation(KEYS + "world.migrationNow").param("distance", distance(v, herd[0], herd[1]))
                    .param("direction", direction(v, herd[0], herd[1])));
        } else {
            long d = Calendar.upcoming(world, store, "migration", Calendar.MIGRATION_EVERY, 5);
            out.add(Message.translation(KEYS + "world.migration").param("when", when(d - day, false)));
        }
        int feasts = 0;
        for (Village other : Villages.registry(world).all()) {
            if (!other.id().equals(v.id()) && Calendar.running("feast", other)) {
                feasts++;
            }
        }
        if (feasts > 0) {
            out.add(Message.translation(KEYS + "world.feasts").param("count", feasts));
        }
        int travellers = Travellers.all(world).size();
        out.add(Message.translation(KEYS + "world.travellers").param("count", travellers).param("camps", Camps.all(world).size()));
        return out;
    }

    // ---- Outils ----

    /** Village de la prochaine foire (pas en cours) et dans combien de jours, ou null. */
    private static Object[] fair(World world, Store<EntityStore> store) {
        long day = GameClock.day(store);
        long d = Calendar.upcoming(world, store, "fair", Calendar.FAIR_EVERY, 7);
        Object[] f = Calendar.nextFair(world, d);
        return f == null ? null : new Object[] {f[0], d - day};
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
        if (data.action.equals("Back")) {
            BoardPage.open(world, store, ref, playerRef, village);
            return;
        }
        rebuild();
    }
}
