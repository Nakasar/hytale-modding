package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomUIEventBindingType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.annex.AnnexPage;
import dev.nakasar.hytale.peuples.annex.Annexes;
import dev.nakasar.hytale.peuples.annex.OuvragePage;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.village.PlotPage;
import dev.nakasar.hytale.peuples.village.Plots;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.world.DomainPage;
import dev.nakasar.hytale.peuples.world.WorldPage;

/**
 * Barre des onglets en haut du panneau du village (maquette Claude Design « Panneau du village — refonte », Kevin,
 * 16 novembre 2026) : Tableau, Projets, Production, Ouvrages, Monde, Domaine (conquête des lieux-dits), et l'heure du jeu. Chaque page du panneau porte la
 * même barre ({@code tab_strip} de {@code tools/generate_board_ui.py}) : l'onglet ouvert est un aplat
 * ({@code #Tab<X>On}), les autres des boutons ({@code #Tab<X>Button}). Les pages appellent {@link #fill} dans leur
 * {@code build} et {@link #handle} en tête de leur {@code handleDataEvent}.
 */
public final class BoardTabs {

    /** Action des boutons d'onglet : {@code Tab<X>}. */
    private static final String PREFIX = "Tab";

    private BoardTabs() {
    }

    /** Textes des onglets, ceux qui s'ouvrent ici, et l'heure. */
    public static void fill(UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store, Village village) {
        tab(cmd, events, "#TabBoardButton", "#TabBoardLabel", "Board", Message.translation(WorldPage.KEYS + "tab.board"));
        tab(cmd, events, "#TabPlotsButton", "#TabPlotsLabel", "Plots", Message.translation(Plots.KEYS + "button"));
        tab(cmd, events, "#TabAnnexesButton", "#TabAnnexesLabel", "Annexes", Message.translation(Annexes.KEYS + "button"));
        tab(cmd, events, "#TabWorksButton", "#TabWorksLabel", "Works", Message.translation(Annexes.KEYS + "works.tab"));
        tab(cmd, events, "#TabWorldButton", "#TabWorldLabel", "World", Message.translation(WorldPage.KEYS + "button"));
        tab(cmd, events, "#TabDomainButton", "#TabDomainLabel", "Domain", Message.translation(DomainPage.KEYS + "tab"));
        // Emplacements : seulement si le plan du village en a ; Avant-postes : si le peuple en a (l'onglet dit le palier).
        cmd.set("#TabPlots.Visible", village != null && Plots.plots(village).length > 0);
        cmd.set("#TabAnnexes.Visible", village != null && !Annexes.catalog(village).isEmpty());
        cmd.set("#TabWorks.Visible", village != null && !Annexes.catalog(village, Workshop.Annex.INFRASTRUCTURE).isEmpty());
        cmd.set("#Clock.TextSpans", Message.translation(WorldPage.KEYS + "clock").param("day", GameClock.day(store) + 1)
                .param("hour", GameClock.hour(store)));
    }

    private static void tab(UICommandBuilder cmd, UIEventBuilder events, String button, String label, String id, Message text) {
        cmd.set(button + ".Text", text);
        cmd.set(label + ".TextSpans", text);
        events.addEventBinding(CustomUIEventBindingType.Activating, button, EventData.of("Action", PREFIX + id));
    }

    /** Ouvre l'onglet demandé ; vrai si l'action était un onglet (la page appelante n'a plus rien à faire). */
    public static boolean handle(String action, World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef,
                                 Village village) {
        if (action == null || !action.startsWith(PREFIX)) {
            return false;
        }
        switch (action.substring(PREFIX.length())) {
            case "Board" -> BoardPage.open(world, store, ref, playerRef, village);
            case "Plots" -> PlotPage.open(store, ref, playerRef, village);
            case "Annexes" -> AnnexPage.open(store, ref, playerRef, village);
            case "Works" -> OuvragePage.open(store, ref, playerRef, village);
            case "World" -> WorldPage.open(store, ref, playerRef, village);
            case "Domain" -> DomainPage.open(store, ref, playerRef, village);
            default -> {
                return false;
            }
        }
        return true;
    }
}
