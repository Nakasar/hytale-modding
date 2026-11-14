package dev.nakasar.hytale.peuples.dialogue;

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

/**
 * La fenêtre de dialogue (maquette /mnt/project-files/peuples/maquettes/dialogue.png) : nom et métier du PNJ, la
 * réplique, quatre réponses au plus avec leur ligne d'effet (ou leur condition si elles sont grisées), et « Partir ».
 * Mise en page {@value #LAYOUT} livrée par le pack du mod (Common/UI/Custom/), remplie et écoutée par le Java comme les
 * pages vanilla (BlockLorePage, DialogPage).
 *
 * <p>À vérifier en jeu (GDD) : que le client rende une page .ui livrée par un mod et que les clics remontent. Le
 * secours est le dialogue par le tchat ({@link Dialogues#openChat}).
 */
public final class DialoguePage extends InteractiveCustomUIPage<DialoguePage.Event> {

    public static final String LAYOUT = "Pages/Nakasar/Peuples/DialoguePage.ui";
    private static final String LEAVE = "Leave";

    /** Donnée d'un clic : l'index de la réponse, ou {@value #LEAVE}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final Dialogue dialogue;
    private DialogueNode node;

    public DialoguePage(PlayerRef playerRef, Dialogue dialogue, DialogueNode start) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.dialogue = dialogue;
        this.node = start;
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        cmd.append(LAYOUT);
        World world = store.getExternalData().getWorld();
        DialogueContext context = DialogueContext.of(world, store, ref, playerRef);
        cmd.set("#NpcName.Text", Dialogues.header(dialogue, context));
        cmd.set("#Line.Text", Message.translation(node.textKey()));
        DialogueResponse[] responses = node.responses();
        for (int i = 0; i < Dialogue.MAX_RESPONSES; i++) {
            DialogueResponse r = i < responses.length ? responses[i] : null;
            String answer = "#Answer" + i;
            String hint = "#Hint" + i;
            if (r == null) {
                cmd.set(answer + ".Visible", false);
                cmd.set(hint + ".Visible", false);
                continue;
            }
            cmd.set(answer + ".Visible", true);
            cmd.set(hint + ".Visible", true);
            Message text = Message.translation(Dialogues.KEYS + "pageResponse").param("number", i + 1)
                    .param("text", Message.translation(r.textKey()));
            cmd.set(answer + ".Text", text);
            if (r.available(context)) {
                cmd.set(hint + ".Text", r.hintKey() == null ? Message.empty() : Message.translation(r.hintKey()));
            } else {
                cmd.set(hint + ".Text", Message.translation(Dialogues.KEYS + "pageLocked").param("condition", Dialogues.failText(r)));
            }
            events.addEventBinding(CustomUIEventBindingType.Activating, answer, EventData.of("Action", Integer.toString(i)));
        }
        cmd.set("#Leave.Text", Message.translation(Dialogues.KEYS + "leave"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Leave", EventData.of("Action", LEAVE));
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, Event data) {
        if (data == null || data.action == null || LEAVE.equals(data.action)) {
            close();
            return;
        }
        int index;
        try {
            index = Integer.parseInt(data.action);
        } catch (NumberFormatException e) {
            return;
        }
        World world = store.getExternalData().getWorld();
        Dialogues.Outcome outcome = Dialogues.choose(dialogue, node, index, DialogueContext.of(world, store, ref, playerRef));
        if (!outcome.chosen()) {
            rebuild();
            return;
        }
        if (outcome.closed()) {
            // Un effet a pu ouvrir une autre page (tableau) : ne fermer que si la fenêtre affichée est encore celle-ci.
            Player player = store.getComponent(ref, Player.getComponentType());
            if (player == null || player.getPageManager().getCustomPage() == this) {
                close();
            }
            return;
        }
        node = outcome.next();
        rebuild();
    }
}
