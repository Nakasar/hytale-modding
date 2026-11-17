package dev.nakasar.hytale.peuples.population;

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
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * L'onglet « Habitants » du panneau du village (générations de villageois) : le recensement, la liste des habitants
 * (stade, âge, poste ou vocation, foyer), le nouveau-né à nommer (Ami), le refuge et l'orientation d'un apprenti (Hôte),
 * et la chronique du village. Mise en page par peuple ({@code PeoplePage_<Peuple>.ui}, {@code tools/generate_population.py}).
 */
public final class PeoplePage extends InteractiveCustomUIPage<PeoplePage.Event> {

    private static final String LAYOUT = "Pages/Nakasar/Peuples/PeoplePage.ui";
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    private static final String K = Population.KEYS + "page.";
    /** Habitants par page de la liste, prénoms proposés, lignes de chronique. */
    static final int ROWS = 9;
    static final int NAMES = 3;
    static final int CHRONICLE = 7;
    private static final String WOUNDED = "#e8a07a";

    /** Donnée d'un clic : Prev, Next, Name0..2, Refuge, Orient0..8 (choisir l'apprenti), OrientPrev/Next/Apply, Tab*. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;
    private int page;
    private String apprentice;
    private int post;

    public PeoplePage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    /** Ouvre l'onglet des habitants (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        if (!Population.applies(village)) {
            playerRef.sendMessage(Message.translation(K + "none"));
            return;
        }
        player.getPageManager().openCustomPage(ref, store, new PeoplePage(playerRef, village));
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/PeoplePage_" + people.id() + ".ui" : LAYOUT;
    }

    /** Vivants dans l'ordre de la liste : anciens, adultes, apprentis, enfants, les plus âgés d'abord. */
    static List<Inhabitant> ordered(PopulationState p, long day) {
        List<Inhabitant> out = new ArrayList<>(p.living());
        out.sort(Comparator.comparingInt((Inhabitant h) -> -h.stage(day).ordinal()).thenComparingLong(Inhabitant::born));
        return out;
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        cmd.append(layout(village == null ? null : village.people()));
        if (village == null) {
            cmd.set("#PageTitle.TextSpans", Message.translation(K + "orphan"));
            return;
        }
        PopulationState p = Population.state(village);
        long day = GameClock.day(store);
        cmd.set("#PageTitle.TextSpans", Message.translation(K + "title").param("village", village.name()));
        census(cmd, village, p, day);
        rows(cmd, events, village, p, day);
        birth(cmd, events, world, village, p, day);
        refuge(cmd, events, village, p);
        orient(cmd, events, village, p, day);
        chronicle(cmd, village, p, day);
        cmd.set("#Rule.TextSpans", Message.translation(K + "rule").param("ami", Message.translation(Population.NAME_RANK.nameKey()))
                .param("hote", Message.translation(Population.HOST_RANK.nameKey())).param("year", Ages.YEAR));
        BoardTabs.fill(cmd, events, store, village);
    }

    private static void census(UICommandBuilder cmd, Village village, PopulationState p, long day) {
        Map<Ages.Stage, Integer> c = Population.census(village, day);
        cmd.set("#Census.TextSpans", Message.translation(K + "census").param("living", p.living().size())
                .param("children", c.get(Ages.Stage.CHILD)).param("apprentices", c.get(Ages.Stage.APPRENTICE))
                .param("adults", c.get(Ages.Stage.ADULT)).param("elders", c.get(Ages.Stage.ELDER))
                .param("beds", Population.totalBeds(village)));
        cmd.set("#ListHeader.TextSpans", Message.translation(K + "list"));
    }

    private void rows(UICommandBuilder cmd, UIEventBuilder events, Village village, PopulationState p, long day) {
        List<Inhabitant> all = ordered(p, day);
        int pages = Math.max(1, (all.size() + ROWS - 1) / ROWS);
        page = Math.max(0, Math.min(page, pages - 1));
        for (int i = 0; i < ROWS; i++) {
            int index = page * ROWS + i;
            String n = Integer.toString(i);
            if (index >= all.size()) {
                cmd.set("#Row" + n + ".Visible", false);
                continue;
            }
            Inhabitant h = all.get(index);
            cmd.set("#RowName" + n + ".TextSpans", h.fullName());
            cmd.set("#RowLine" + n + ".TextSpans", line(village, p, h, day));
            cmd.set("#RowLine" + n + ".Style.TextColor", h.convalescent(day) ? WOUNDED : "#96a9be");
            boolean orientable = h.stage(day) == Ages.Stage.APPRENTICE;
            cmd.set("#RowOrient" + n + ".Visible", orientable);
            if (orientable) {
                cmd.set("#RowOrient" + n + ".Text", Message.translation(K + (h.id().equals(apprentice) ? "orientSelected" : "orientSelect")));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#RowOrient" + n, EventData.of("Action", "Orient" + n));
            }
        }
        cmd.set("#PageLine.TextSpans", Message.translation(K + "pages").param("page", page + 1).param("pages", pages));
        cmd.set("#Prev.Text", Message.translation(K + "prev"));
        cmd.set("#Next.Text", Message.translation(K + "next"));
        cmd.set("#Prev.Disabled", page == 0);
        cmd.set("#Next.Disabled", page >= pages - 1);
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Prev", EventData.of("Action", "Prev"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Next", EventData.of("Action", "Next"));
    }

    /** Ligne d'un habitant pour {@code /village habitants}. */
    public static Message describe(Village village, Inhabitant h, long day) {
        return line(village, Population.state(village), h, day);
    }

    /** « Adulte, 3 ans · Gardien du puits · Maison du puits » (blessé, parrain...). */
    static Message line(Village village, PopulationState p, Inhabitant h, long day) {
        Ages.Stage stage = h.stage(day);
        Message what;
        if (h.hasJob()) {
            what = Population.postName(village, h.job());
        } else if (stage == Ages.Stage.APPRENTICE && !h.vocation().isEmpty()) {
            what = Message.translation(Population.KEYS + "about.apprentice").param("post", Population.postName(village, h.vocation()));
        } else if (stage == Ages.Stage.ELDER) {
            what = Message.translation(Population.KEYS + "about.retired");
        } else if (stage == Ages.Stage.CHILD) {
            what = Message.translation(Population.KEYS + "about.parents").param("parents", Population.parentsText(p, h));
        } else {
            what = Message.translation(K + "idle");
        }
        Message home = h.home().isEmpty() ? Message.translation(K + "noHome") : Message.translation(Chantiers.buildingKey(h.home()));
        Message out = Message.translation(K + "row").param("stage", Message.translation(Population.KEYS + "stage." + stage.key()))
                .param("age", Population.ageText(h.age(day))).param("what", what).param("home", home);
        if (h.convalescent(day)) {
            out = Message.translation(K + "rowWounded").param("line", out);
        }
        return out;
    }

    private static void birth(UICommandBuilder cmd, UIEventBuilder events, World world, Village village, PopulationState p, long day) {
        cmd.set("#BirthHeader.TextSpans", Message.translation(K + "birthHeader"));
        Inhabitant child = p.byId(p.newborn());
        boolean naming = child != null && child.alive() && day <= p.namingUntil();
        for (int i = 0; i < NAMES; i++) {
            String n = Integer.toString(i);
            boolean shown = naming && i < p.proposals().length;
            cmd.set("#Name" + n + ".Visible", shown);
            if (shown) {
                cmd.set("#Name" + n + ".Text", Message.raw(p.proposals()[i]));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#Name" + n, EventData.of("Action", "Name" + n));
            }
        }
        if (naming) {
            cmd.set("#BirthLine.TextSpans", Message.translation(K + "birthNaming").param("child", child.fullName())
                    .param("parents", Population.parentsText(p, child)).param("rank", Message.translation(Population.NAME_RANK.nameKey())));
            return;
        }
        int free = Math.max(0, Population.totalBeds(village) - p.living().size());
        Message why;
        if (day <= p.mourning()) {
            why = Message.translation(K + "birthMourning");
        } else if (village.burnt().length > 0) {
            why = Message.translation(K + "birthBurnt");
        } else if (free == 0) {
            why = Message.translation(K + "birthNoBed");
        } else {
            why = Message.translation(K + "birthHope").param("food", Population.BIRTH_FOOD);
        }
        cmd.set("#BirthLine.TextSpans", Message.translation(K + "birthNone").param("free", free).param("why", why));
    }

    private static void refuge(UICommandBuilder cmd, UIEventBuilder events, Village village, PopulationState p) {
        cmd.set("#RefugeHeader.TextSpans", Message.translation(K + "refugeHeader"));
        boolean tier = village.tier() >= Population.REFUGE_TIER;
        Message line;
        if (!tier) {
            line = Message.translation(K + "refugeTier").param("tier", Message.translation(Tiers.nameKey(Population.REFUGE_TIER)));
        } else if (Population.refugeOpen(village, p)) {
            line = Message.translation(K + "refugeSet").param("building", Message.translation(Chantiers.buildingKey(p.refuge())));
        } else {
            line = Message.translation(K + "refugeNone");
        }
        cmd.set("#RefugeLine.TextSpans", line);
        cmd.set("#Refuge.Visible", tier);
        cmd.set("#Refuge.Text", Message.translation(K + "refugeButton"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Refuge", EventData.of("Action", "Refuge"));
    }

    private void orient(UICommandBuilder cmd, UIEventBuilder events, Village village, PopulationState p, long day) {
        cmd.set("#OrientHeader.TextSpans", Message.translation(K + "orientHeader"));
        Inhabitant h = p.byId(apprentice);
        List<Population.Post> posts = Population.orientChoices(village);
        boolean ready = h != null && h.alive() && h.stage(day) == Ages.Stage.APPRENTICE && !posts.isEmpty();
        cmd.set("#OrientControls.Visible", ready);
        if (!ready) {
            apprentice = null;
            cmd.set("#OrientLine.TextSpans", Message.translation(K + "orientHint").param("days", Population.ORIENT_DAYS));
            return;
        }
        post = Math.floorMod(post, posts.size());
        Population.Post target = posts.get(post);
        cmd.set("#OrientLine.TextSpans", Message.translation(K + "orientLine").param("name", h.fullName())
                .param("now", h.vocation().isEmpty() ? Message.translation(Population.KEYS + "noPost") : Population.postName(village, h.vocation()))
                .param("post", target.name()));
        cmd.set("#OrientPrev.Text", Message.translation(K + "prev"));
        cmd.set("#OrientNext.Text", Message.translation(K + "next"));
        cmd.set("#OrientApply.Text", Message.translation(K + "orientApply"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#OrientPrev", EventData.of("Action", "OrientPrev"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#OrientNext", EventData.of("Action", "OrientNext"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#OrientApply", EventData.of("Action", "OrientApply"));
    }

    private static void chronicle(UICommandBuilder cmd, Village village, PopulationState p, long day) {
        cmd.set("#ChronicleHeader.TextSpans", Message.translation(K + "chronicle"));
        List<ChronicleEntry> all = p.chronicle();
        for (int i = 0; i < CHRONICLE; i++) {
            String n = Integer.toString(i);
            int index = all.size() - 1 - i;
            cmd.set("#Chron" + n + ".Visible", index >= 0);
            if (index >= 0) {
                cmd.set("#Chron" + n + ".TextSpans", Population.chronicleLine(village, p, all.get(index), day));
            }
        }
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, Event data) {
        String action = data == null ? null : data.action;
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).byId(villageId);
        if (action == null || village == null) {
            return;
        }
        if (BoardTabs.handle(action, world, store, ref, playerRef, village)) {
            return;
        }
        long day = GameClock.day(store);
        PopulationState p = Population.state(village);
        switch (action) {
            case "Prev" -> page--;
            case "Next" -> page++;
            case "Refuge" -> Population.cycleRefuge(store, ref, playerRef, village);
            case "OrientPrev" -> post--;
            case "OrientNext" -> post++;
            case "OrientApply" -> {
                List<Population.Post> posts = Population.orientChoices(village);
                if (apprentice != null && !posts.isEmpty()
                        && Population.orient(world, store, ref, playerRef, village, apprentice, posts.get(Math.floorMod(post, posts.size())).id())) {
                    apprentice = null;
                }
            }
            default -> {
                if (action.startsWith("Name")) {
                    Population.name(world, store, ref, playerRef, village, parse(action.substring(4)));
                } else if (action.startsWith("Orient")) {
                    int i = parse(action.substring(6));
                    List<Inhabitant> all = ordered(p, day);
                    int index = page * ROWS + i;
                    if (i >= 0 && index < all.size()) {
                        String id = all.get(index).id();
                        apprentice = id.equals(apprentice) ? null : id;
                        post = 0;
                    }
                } else {
                    return;
                }
            }
        }
        rebuild();
    }

    private static int parse(String s) {
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
