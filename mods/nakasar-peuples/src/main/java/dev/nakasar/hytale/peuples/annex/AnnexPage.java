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
import dev.nakasar.hytale.peuples.request.BoardPage;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.workshop.Workshops;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * L'onglet « Avant-postes » du panneau du village : les six avant-postes de métier du peuple (état, coût, place),
 * avec le bouton qui remet la fondation. Mise en page par peuple ({@code AnnexPage_<Peuple>.ui},
 * {@code tools/generate_workshop_ui.py}). Toute la logique est dans {@link Annexes}.
 */
public final class AnnexPage extends InteractiveCustomUIPage<AnnexPage.Event> {

    private static final String LAYOUT = "Pages/Nakasar/Peuples/AnnexPage.ui";
    private static final String KEYS = Annexes.KEYS;
    private static final List<String> THEMED = List.of("Kweebec", "Trork", "Feran", "Renonce", "Slothian");
    private static final int CARDS = 6;

    /** Donnée d'un clic : {@code Grant0..5}, {@code Back}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final String villageId;

    public AnnexPage(PlayerRef playerRef, Village village) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.villageId = village.id();
    }

    /** Ouvre l'onglet des avant-postes du village (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        if (Annexes.catalog(village).isEmpty()) {
            playerRef.sendMessage(Message.translation(KEYS + "none"));
            return;
        }
        player.getPageManager().openCustomPage(ref, store, new AnnexPage(playerRef, village));
    }

    static String layout(People people) {
        return people != null && THEMED.contains(people.id()) ? "Pages/Nakasar/Peuples/AnnexPage_" + people.id() + ".ui" : LAYOUT;
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
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "page.title").param("village", village.name()));
        VillageLayout layout = Chantiers.layout(village);
        int min = (layout == null ? 64 : layout.radius()) + Annexes.VILLAGE_GAP;
        Message block = Annexes.block(store, ref, village);
        cmd.set("#Intro.TextSpans", block != null ? block
                : Message.translation(KEYS + "page.intro").param("min", min).param("max", Annexes.MAX_DISTANCE));
        List<Workshop> catalog = Annexes.catalog(village);
        for (int i = 0; i < CARDS; i++) {
            if (i >= catalog.size()) {
                cmd.set("#Annex" + i + ".Visible", false);
                continue;
            }
            card(cmd, events, world, store, village, catalog.get(i), i, block == null);
        }
        cmd.set("#Rule.TextSpans", Message.translation(KEYS + "page.rule").param("tier", Message.translation(Tiers.nameKey(Annexes.MIN_TIER)))
                .param("rank", Message.translation(Annexes.GRANT_RANK.nameKey())));
        cmd.set("#Back.Text", Message.translation(KEYS + "page.back"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Back", EventData.of("Action", "Back"));
    }

    private static void card(UICommandBuilder cmd, UIEventBuilder events, World world, Store<EntityStore> store, Village village,
                             Workshop w, int i, boolean allowed) {
        String n = Integer.toString(i);
        if (w.icon() != null) {
            cmd.set("#AnnexIcon" + n + ".ItemId", w.icon());
        }
        cmd.set("#AnnexName" + n + ".TextSpans", Message.translation(w.nameKey()));
        cmd.set("#AnnexRole" + n + ".TextSpans", Message.translation(KEYS + "role." + w.annex().type()));
        AnnexState a = village.annex(w.getId());
        cmd.set("#AnnexState" + n + ".TextSpans", stateLine(world, store, village, w, a));
        String button = null;
        if (allowed) {
            if (a == null) {
                button = "page.grant";
            } else if (a.granted() && a.grantedDay() != GameClock.day(store)) {
                button = "page.regive";
            }
        }
        cmd.set("#AnnexAction" + n + ".Visible", button != null);
        if (button != null) {
            cmd.set("#AnnexAction" + n + ".Text", Message.translation(KEYS + button));
            events.addEventBinding(CustomUIEventBindingType.Activating, "#AnnexAction" + n, EventData.of("Action", "Grant" + n));
        }
    }

    /** État de l'avant-poste en une phrase : à fonder (coût, manque), fondation remise, travaux, debout. */
    static Message stateLine(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a) {
        if (a == null) {
            Map<String, Integer> cost = new LinkedHashMap<>();
            for (VillageLayout.Material m : w.annex().materials()) {
                cost.merge(m.itemId(), m.quantity(), Integer::sum);
            }
            Map<String, Integer> missing = Annexes.missing(world, village, w);
            if (missing == null || missing.isEmpty()) {
                return Message.translation(KEYS + "state.cost").param("list", Annexes.materialList(cost));
            }
            return Message.translation(KEYS + "state.costMissing").param("list", Annexes.materialList(cost))
                    .param("missing", Annexes.materialList(missing));
        }
        if (a.granted()) {
            return Message.translation(KEYS + "state.granted").param("player", a.ownerName() == null ? "?" : a.ownerName())
                    .param("rule", Message.translation(KEYS + "hint." + w.annex().rule()));
        }
        if (a.working()) {
            return Message.translation(KEYS + "state.working").param("hours", Annexes.hoursLeft(store, a))
                    .param("x", a.x()).param("z", a.z());
        }
        int level = village.workshop(w.getId()).level();
        if (a.convoy()) {
            return Message.translation(KEYS + "state.convoy").param("level", Message.translation(Workshops.KEYS + "levelShort." + level))
                    .param("porters", a.convoyPorters()).param("x", a.x()).param("z", a.z());
        }
        return Message.translation(KEYS + "state.built").param("level", Message.translation(Workshops.KEYS + "levelShort." + level))
                .param("x", a.x()).param("z", a.z());
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
        if (action.startsWith("Grant")) {
            List<Workshop> catalog = Annexes.catalog(village);
            int i;
            try {
                i = Integer.parseInt(action.substring("Grant".length()));
            } catch (NumberFormatException e) {
                i = -1;
            }
            if (i >= 0 && i < catalog.size()) {
                Annexes.grant(world, store, ref, playerRef, village, catalog.get(i));
            }
        } else if (action.equals("Back")) {
            BoardPage.open(world, store, ref, playerRef, village);
            return;
        }
        rebuild();
    }
}
