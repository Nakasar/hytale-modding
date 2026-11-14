package dev.nakasar.hytale.peuples.outpost;

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
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.trork.WarPaint;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Fenêtre « Fonder un avant-poste » (maquette /mnt/project-files/peuples/maquettes/avant_poste.png), ouverte par la
 * Pierre de fondation : où la pierre est posée, les cinq avant-postes (nom, description, condition cochée ou non, bouton
 * Choisir), puis « Fonder l'avant-poste » et « Annuler ». Mise en page {@value #LAYOUT}, mêmes règles que
 * {@code BoardPage} : libellés par {@code .TextSpans}, boutons par {@code .Text} avec une traduction simple.
 */
public final class OutpostPage extends InteractiveCustomUIPage<OutpostPage.Event> {

    public static final String LAYOUT = "Pages/Nakasar/Peuples/OutpostPage.ui";
    private static final String KEYS = Outposts.KEYS;
    private static final String OK_COLOR = "#7fc97f";
    private static final String NO_COLOR = "#d97a6c";

    /** Donnée d'un clic : {@code Choose0..4}, {@code Found}, {@code Cancel}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final int x;
    private final int z;
    private People chosen;

    public OutpostPage(PlayerRef playerRef, int x, int z) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.x = x;
        this.z = z;
    }

    /** Ouvre la fenêtre pour une pierre posée en (x, z) (thread du monde). */
    public static void open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, int x, int z) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player != null) {
            player.getPageManager().openCustomPage(ref, store, new OutpostPage(playerRef, x, z));
        }
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        cmd.append(LAYOUT);
        World world = store.getExternalData().getWorld();
        cmd.set("#PageTitle.TextSpans", Message.translation(KEYS + "title"));
        Village near = nearest(world);
        cmd.set("#Where.TextSpans", near == null
                ? Message.translation(KEYS + "whereAlone").param("x", x).param("z", z)
                : Message.translation(KEYS + "where").param("x", x).param("z", z).param("village", near.name())
                        .param("distance", (int) Math.sqrt((near.x() - x) * (double) (near.x() - x)
                                + (near.z() - z) * (double) (near.z() - z))));
        People[] peoples = People.values();
        for (int i = 0; i < OPTIONS; i++) {
            String n = Integer.toString(i);
            People p = i < peoples.length ? peoples[i] : null;
            cmd.set("#Option" + n + ".Visible", p != null);
            if (p == null) {
                continue;
            }
            cmd.set("#Name" + n + ".TextSpans", Message.translation(KEYS + "option." + p.id()));
            cmd.set("#Desc" + n + ".TextSpans", Message.translation(KEYS + "option." + p.id() + ".desc"));
            cmd.set("#Cond" + n + ".TextSpans", condition(store, ref, p));
            boolean allowed = Outposts.allowed(store, ref, p);
            cmd.set("#Choose" + n + ".Visible", allowed);
            if (allowed) {
                cmd.set("#Choose" + n + ".Text", Message.translation(KEYS + (p == chosen ? "chosen" : "choose")));
                events.addEventBinding(CustomUIEventBindingType.Activating, "#Choose" + n, EventData.of("Action", "Choose" + n));
            }
        }
        cmd.set("#Footer.TextSpans", Message.translation(KEYS + "footer"));
        cmd.set("#Found.Text", Message.translation(KEYS + "found"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Found", EventData.of("Action", "Found"));
        cmd.set("#Cancel.Text", Message.translation(KEYS + "cancel"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Cancel", EventData.of("Action", "Cancel"));
    }

    /** Nombre de lignes de la mise en page (#Option0..4). */
    static final int OPTIONS = 5;

    private static Message condition(Store<EntityStore> store, Ref<EntityStore> ref, People p) {
        Message people = Message.translation(p.nameKey());
        if (Reputations.peopleRank(store, ref, p) == Rank.CHAMPION) {
            return Message.translation(KEYS + "ok").param("people", people).color(OK_COLOR);
        }
        if (p == People.TRORK) {
            return WarPaint.worn(store, ref)
                    ? Message.translation(KEYS + "okPaint").color(OK_COLOR)
                    : Message.translation(KEYS + "needTrork").color(NO_COLOR);
        }
        return Message.translation(KEYS + "need").param("people", people).color(NO_COLOR);
    }

    private Village nearest(World world) {
        Village best = null;
        double bestD = Double.MAX_VALUE;
        for (Village v : Villages.registry(world).all()) {
            double d = (v.x() - x) * (double) (v.x() - x) + (v.z() - z) * (double) (v.z() - z);
            if (d < bestD) {
                bestD = d;
                best = v;
            }
        }
        return best;
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, Event data) {
        if (data == null || data.action == null) {
            return;
        }
        String action = data.action;
        if (action.equals("Cancel")) {
            close();
            return;
        }
        if (action.equals("Found")) {
            World world = store.getExternalData().getWorld();
            if (Outposts.found(world, store, ref, playerRef, chosen, x, z)) {
                close();
                return;
            }
        } else if (action.startsWith("Choose")) {
            try {
                int i = Integer.parseInt(action.substring("Choose".length()));
                People[] peoples = People.values();
                if (i >= 0 && i < peoples.length && Outposts.allowed(store, ref, peoples[i])) {
                    chosen = peoples[i];
                }
            } catch (NumberFormatException ignored) {
                // Clic inconnu : rien.
            }
        }
        rebuild();
    }
}
