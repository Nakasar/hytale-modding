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
import com.hypixel.hytale.server.core.entity.entities.player.pages.InteractiveCustomUIPage;
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;

import java.util.List;

/**
 * Le choix de la spécialité d'un bâtiment de métier (étape 3 ; maquette « choix de spécialité » du GDD) : une carte
 * par spécialité (icône vanilla, nom, ce qu'elle change), la spécialité en place marquée, un bouton Choisir ou Se
 * reconvertir. Le choix vaut pour tout le village ({@link Workshops#chooseSpecialty}). Mise en page par peuple
 * ({@code WorkshopSpecialtyPage_<Peuple>.ui}, {@code tools/generate_workshop_ui.py}).
 */
public final class WorkshopSpecialtyPage extends InteractiveCustomUIPage<WorkshopSpecialtyPage.Event> {

    private static final String LAYOUT = "Pages/Nakasar/Peuples/WorkshopSpecialtyPage.ui";
    private static final String KEYS = Workshops.KEYS;
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    private static final int CARDS = 3;

    /** Donnée d'un clic : {@code Choose0..2}, {@code Back}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;
    private final String workshopId;

    public WorkshopSpecialtyPage(PlayerRef playerRef, Village village, Workshop workshop) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
        this.workshopId = workshop.getId();
    }

    /** Ouvre le choix de spécialité du bâtiment (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village, Workshop workshop) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        if (workshop.specialties().length == 0) {
            playerRef.sendMessage(Message.translation(KEYS + "specialtyNone"));
            return;
        }
        player.getPageManager().openCustomPage(ref, store, new WorkshopSpecialtyPage(playerRef, village, workshop));
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id())
                ? "Pages/Nakasar/Peuples/WorkshopSpecialtyPage_" + people.id() + ".ui" : LAYOUT;
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
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "specialtyTitle").param("building", Message.translation(w.nameKey())));
        cmd.set("#Intro.TextSpans", Message.translation(KEYS + "specialtyIntro"));
        Message block = Workshops.specialtyBlock(store, ref, village, state);
        Workshop.Specialty[] specs = w.specialties();
        for (int i = 0; i < CARDS; i++) {
            String n = Integer.toString(i);
            Workshop.Specialty spec = i < specs.length ? specs[i] : null;
            cmd.set("#Spec" + n + ".Visible", spec != null);
            if (spec == null) {
                continue;
            }
            boolean current = spec.id().equals(state.specialty());
            if (spec.icon() != null) {
                cmd.set("#SpecIcon" + n + ".ItemId", spec.icon());
            }
            cmd.set("#SpecName" + n + ".TextSpans", Message.translation(spec.nameKey()));
            cmd.set("#SpecLine" + n + ".TextSpans", Message.translation(spec.lineKey()));
            cmd.set("#SpecStripe" + n + ".Visible", current);
            Message stateLine = current ? Message.translation(KEYS + "specialtyCurrent") : block;
            cmd.set("#SpecState" + n + ".TextSpans", stateLine == null ? Message.empty() : stateLine);
            boolean can = !current && block == null;
            cmd.set("#SpecChoose" + n + ".Visible", can);
            if (can) {
                cmd.set("#SpecChoose" + n + ".Text", Message.translation(KEYS + (state.specialty() == null ? "specialtyPick" : "specialtyReconvert")));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#SpecChoose" + n, EventData.of("Action", "Choose" + n));
            }
        }
        cmd.set("#Rule.TextSpans", Message.translation(KEYS + "specialtyRule")
                .param("rank", Message.translation(Workshops.SPECIALTY_RANK.nameKey())).param("days", Workshops.RECONVERT_DAYS));
        cmd.set("#Back.Text", Message.translation(KEYS + "specialtyBack"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Back", EventData.of("Action", "Back"));
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
        if (data.action.startsWith("Choose")) {
            int i;
            try {
                i = Integer.parseInt(data.action.substring("Choose".length()));
            } catch (NumberFormatException e) {
                return;
            }
            Workshop.Specialty[] specs = w.specialties();
            if (i >= 0 && i < specs.length && Workshops.chooseSpecialty(world, store, ref, playerRef, village, w, specs[i].id())) {
                WorkshopPage.open(world, store, ref, playerRef, village, w, false);
                return;
            }
            rebuild();
        } else if (data.action.equals("Back")) {
            WorkshopPage.open(world, store, ref, playerRef, village, w, false);
        }
    }
}
