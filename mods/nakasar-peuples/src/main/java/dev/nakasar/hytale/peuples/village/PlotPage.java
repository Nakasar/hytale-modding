package dev.nakasar.hytale.peuples.village;

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
import dev.nakasar.hytale.peuples.request.BoardPage;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.workshop.Workshops;

import java.util.List;
import java.util.Map;

/**
 * La page « Emplacements » du panneau du village (étape 6, maquette 3 du GDD) : les deux terrains libres (état, projet,
 * chantier, démolition) puis le catalogue des projets du peuple pour le terrain sélectionné. Mise en page par peuple
 * ({@code PlotPage_<Peuple>.ui}, {@code tools/generate_workshop_ui.py}). Toute la logique est dans {@link Plots}.
 */
public final class PlotPage extends InteractiveCustomUIPage<PlotPage.Event> {

    private static final String LAYOUT = "Pages/Nakasar/Peuples/PlotPage.ui";
    private static final String KEYS = Plots.KEYS;
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    private static final int CARDS = 2;
    private static final int PROJECTS = 5;

    /** Donnée d'un clic : {@code Select0..1}, {@code Action0..1}, {@code Choose0..4}, {@code Clear}, {@code Back}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;
    private int selected;

    public PlotPage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
        // Le premier terrain ouvert sans bâtiment, sinon E1.
        VillageLayout.Plot[] plots = Plots.plots(village);
        for (int i = 0; i < plots.length && i < CARDS; i++) {
            PlotState s = village.plot(plots[i].id());
            if (Plots.isOpen(village, plots[i]) && (s.project() == null || !village.isBuilt(s.project()))) {
                selected = i;
                break;
            }
        }
    }

    /** Ouvre la page des emplacements du village (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        if (Plots.plots(village).length == 0) {
            playerRef.sendMessage(Message.translation(KEYS + "none"));
            return;
        }
        player.getPageManager().openCustomPage(ref, store, new PlotPage(playerRef, village));
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/PlotPage_" + people.id() + ".ui" : LAYOUT;
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
        VillageLayout.Plot[] plots = Plots.plots(village);
        if (selected >= plots.length) {
            selected = 0;
        }
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "page.title").param("village", village.name()));
        cmd.set("#Intro.TextSpans", Message.translation(KEYS + "page.intro"));
        for (int i = 0; i < CARDS; i++) {
            if (i >= plots.length) {
                cmd.set("#Plot" + i + ".Visible", false);
                continue;
            }
            card(cmd, events, world, store, village, plots[i], i);
        }
        if (plots.length > 0) {
            catalog(cmd, events, store, ref, village, plots[selected]);
        }
        cmd.set("#Rule.TextSpans", Message.translation(KEYS + "page.rule").param("rank", Message.translation(Plots.CHOOSE_RANK.nameKey()))
                .param("days", Plots.DEMOLISH_DAYS));
        cmd.set("#Back.Text", Message.translation(KEYS + "page.back"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Back", EventData.of("Action", "Back"));
    }

    private void card(UICommandBuilder cmd, UIEventBuilder events, World world, Store<EntityStore> store, Village village,
                      VillageLayout.Plot plot, int i) {
        String n = Integer.toString(i);
        PlotState s = village.plot(plot.id());
        cmd.set("#PlotStripe" + n + ".Visible", i == selected);
        cmd.set("#PlotName" + n + ".TextSpans", Message.translation(KEYS + "page.plot").param("plot", plot.id()));
        cmd.set("#PlotState" + n + ".TextSpans", stateLine(world, store, village, plot, s));
        cmd.set("#PlotSelect" + n + ".Text", Message.translation(KEYS + (i == selected ? "page.selected" : "page.select")));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#PlotSelect" + n, EventData.of("Action", "Select" + n));
        String action = null;
        if (Plots.isOpen(village, plot) && !s.working() && s.project() != null) {
            action = village.isBuilt(s.project()) ? "page.demolish" : "page.start";
        }
        // Kevin (2026-11-15) : chantier en cours = bouton grisé « Chantier en cours » avec le temps restant.
        boolean busy = Plots.isOpen(village, plot) && s.working();
        cmd.set("#PlotAction" + n + ".Visible", action != null || busy);
        cmd.set("#PlotAction" + n + ".Disabled", busy);
        if (busy) {
            long left = Math.max(0, s.end() - GameClock.seconds(store));
            cmd.set("#PlotAction" + n + ".Text", Message.translation(KEYS + "page.busy").param("hours", (int) Math.ceil(left / 3600.0)));
        }
        if (action != null) {
            cmd.set("#PlotAction" + n + ".Text", Message.translation(KEYS + action));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#PlotAction" + n, EventData.of("Action", "Action" + n));
        }
    }

    /** État du terrain en une phrase : fermé, libre, projet choisi (matériaux), chantier, bâti. */
    static Message stateLine(World world, Store<EntityStore> store, Village village, VillageLayout.Plot plot, PlotState s) {
        if (!Plots.isOpen(village, plot)) {
            return Message.translation(KEYS + "state.locked").param("tier", Message.translation(Tiers.nameKey(plot.tier())));
        }
        if (s.project() == null) {
            int days = Plots.demolishDaysLeft(store, s);
            return days > 0 ? Message.translation(KEYS + "state.freeCooldown").param("days", days)
                    : Message.translation(KEYS + "state.free");
        }
        Message name = Message.translation(Chantiers.buildingKey(s.project()));
        if (s.working()) {
            long left = Math.max(0, s.end() - GameClock.seconds(store));
            return Message.translation(KEYS + "state.working").param("building", name).param("hours", (int) Math.ceil(left / 3600.0));
        }
        if (village.isBuilt(s.project())) {
            Workshop w = Plots.workshop(village, s.project());
            int level = w == null ? 1 : village.workshop(w.getId()).level();
            int days = Plots.demolishDaysLeft(store, s);
            Message line = Message.translation(KEYS + "state.built").param("building", name)
                    .param("level", Message.translation(Workshops.KEYS + "levelShort." + level));
            if (days > 0) {
                line.insert(" ").insert(Message.translation(KEYS + "state.demolishIn").param("days", days));
            }
            return line;
        }
        Map<String, Integer> missing = Plots.missing(world, village, plot);
        Message materials = Plots.materialList(materialsOf(plot));
        if (missing == null) {
            return Message.translation(KEYS + "state.chosenNoDeposit").param("building", name).param("list", materials);
        }
        if (missing.isEmpty()) {
            return Message.translation(KEYS + "state.ready").param("building", name).param("list", materials)
                    .param("hours", plot.hours());
        }
        return Message.translation(KEYS + "state.chosen").param("building", name).param("list", materials)
                .param("missing", Plots.materialList(missing));
    }

    private static Map<String, Integer> materialsOf(VillageLayout.Plot plot) {
        Map<String, Integer> out = new java.util.LinkedHashMap<>();
        for (VillageLayout.Material m : plot.materials()) {
            out.merge(m.itemId(), m.quantity(), Integer::sum);
        }
        return out;
    }

    private void catalog(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Ref<EntityStore> ref, Village village,
                         VillageLayout.Plot plot) {
        cmd.set("#CatalogHeader.TextSpans", Message.translation(KEYS + "page.catalog").param("plot", plot.id()));
        PlotState s = village.plot(plot.id());
        boolean locked = s.working() || (s.project() != null && village.isBuilt(s.project()));
        boolean allowed = Plots.block(store, ref, village, plot) == null;
        List<VillageLayout.Building> projects = Plots.projects(village, plot.id());
        for (int j = 0; j < PROJECTS; j++) {
            String n = Integer.toString(j);
            if (j >= projects.size()) {
                cmd.set("#Proj" + n + ".Visible", false);
                continue;
            }
            VillageLayout.Building b = projects.get(j);
            Workshop w = Plots.workshop(village, b.id());
            if (w != null && w.icon() != null) {
                cmd.set("#ProjIcon" + n + ".ItemId", w.icon());
            }
            cmd.set("#ProjName" + n + ".TextSpans", Message.translation(Chantiers.buildingKey(b.id())));
            String project = Plots.projectId(b);
            boolean chosen = b.id().equals(s.project());
            boolean taken = !chosen && !Plots.repeatable(project) && Plots.takenElsewhere(village, plot.id(), project);
            cmd.set("#ProjLine" + n + ".TextSpans", projectLine(village, w, taken));
            String button = null;
            if (allowed && !locked) {
                button = chosen ? "page.clear" : taken ? null : s.project() == null ? "page.choose" : "page.switch";
            }
            cmd.set("#ProjChoose" + n + ".Visible", button != null);
            if (button != null) {
                cmd.set("#ProjChoose" + n + ".Text", Message.translation(KEYS + button));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#ProjChoose" + n,
                        EventData.of("Action", chosen ? "Clear" : "Choose" + n));
            }
        }
    }

    /** Le villageois du projet et ses spécialités (ou « déjà sur l'autre terrain »). */
    private static Message projectLine(Village village, Workshop w, boolean taken) {
        if (taken) {
            return Message.translation(KEYS + "page.taken");
        }
        if (w == null) {
            return Message.empty();
        }
        Message specs = Message.empty();
        Workshop.Specialty[] all = w.specialties();
        for (int i = 0; i < all.length; i++) {
            if (i > 0) {
                specs.insert(" / ");
            }
            specs.insert(Message.translation(all[i].nameKey()));
        }
        Message keeper = Message.translation("nakasar_peuples.job." + w.job());
        return Message.translation(KEYS + "page.projectLine").param("job", keeper).param("specialties", specs);
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
        VillageLayout.Plot[] plots = Plots.plots(village);
        VillageLayout.Plot plot = selected < plots.length ? plots[selected] : null;
        String action = data.action;
        if (action.startsWith("Select")) {
            int i = index(action, "Select");
            if (i >= 0 && i < plots.length) {
                selected = i;
            }
        } else if (action.startsWith("Action")) {
            int i = index(action, "Action");
            if (i >= 0 && i < plots.length) {
                selected = i;
                PlotState s = village.plot(plots[i].id());
                if (s.project() != null && village.isBuilt(s.project())) {
                    Plots.demolish(world, store, ref, playerRef, village, plots[i]);
                } else {
                    Plots.start(world, store, ref, playerRef, village, plots[i]);
                }
            }
        } else if (action.startsWith("Choose") && plot != null) {
            int j = index(action, "Choose");
            List<VillageLayout.Building> projects = Plots.projects(village, plot.id());
            if (j >= 0 && j < projects.size()) {
                Plots.choose(world, store, ref, playerRef, village, plot, projects.get(j).id());
            }
        } else if (action.equals("Clear") && plot != null) {
            Plots.clear(store, ref, playerRef, village, plot);
        } else if (action.equals("Back")) {
            BoardPage.open(world, store, ref, playerRef, village);
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
