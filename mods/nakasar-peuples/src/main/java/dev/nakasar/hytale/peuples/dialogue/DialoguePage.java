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

import java.util.List;

/**
 * La fenêtre de dialogue, en bas de l'écran (maquette /mnt/project-files/peuples/maquettes/dialogue_bas_ecran.png) :
 * nom, métier et rang du joueur auprès du peuple dans l'en-tête, la réplique, quatre réponses numérotées au plus avec
 * leur effet (ou leur condition si elles sont grisées), le portrait du PNJ à droite et « Partir » dessous. La moitié haute
 * de l'écran reste à la scène, que la caméra de dialogue ({@link DialogueCamera}) cadre quand un PNJ parle.
 * Mise en page {@value #LAYOUT} livrée par le pack du mod (Common/UI/Custom/), bâtie sur les modèles vanilla de
 * Common.ui (@DecoratedContainer, @PanelSeparatorFancy, @SmallSecondaryTextButton), remplie et écoutée par le Java
 * comme les pages vanilla (BlockLorePage, MemoriesPage pour le portrait AssetImage). Secours : le dialogue par le tchat
 * ({@link Dialogues#openChat}).
 */
public final class DialoguePage extends InteractiveCustomUIPage<DialoguePage.Event> {

    public static final String LAYOUT = "Pages/Nakasar/Peuples/DialoguePage.ui";
    private static final String LEAVE = "Leave";
    private static final String LOCKED_COLOR = "#c49a6c";
    private static final String LOCKED_TEXT_COLOR = "#7c838c";

    /** Donnée d'un clic : l'index de la réponse, ou {@value #LEAVE}. */
    public static final class Event {
        public static final BuilderCodec<Event> CODEC = BuilderCodec.builder(Event.class, Event::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .add()
                .build();

        String action;
    }

    private final Dialogue dialogue;
    private final DialogueNode start;
    private final String portrait;
    /** Nœud affiché ; null quand la réponse choisie fermait le dialogue mais que le PNJ a parlé ({@link #said}). */
    private DialogueNode node;
    /** Ce que le PNJ vient de dire en réponse au dernier choix, affiché sous sa réplique. */
    private List<Message> said = List.of();
    private boolean camera;
    private Ref<EntityStore> npc;
    private Ref<EntityStore> talker;
    /** L'habitant que montre le PNJ (générations de villageois) : son nom remplace celui du dialogue. */
    private dev.nakasar.hytale.peuples.population.Population.Identity identity;

    public DialoguePage(PlayerRef playerRef, Dialogue dialogue, DialogueNode start) {
        this(playerRef, dialogue, start, null);
    }

    /** `portrait` : chemin AssetImage du portrait du PNJ ({@link Portraits}), null pour aucun. */
    public DialoguePage(PlayerRef playerRef, Dialogue dialogue, DialogueNode start, String portrait) {
        super(playerRef, CustomPageLifetime.CanDismiss, Event.CODEC);
        this.dialogue = dialogue;
        this.start = start;
        this.portrait = portrait;
        this.node = start;
    }

    void identity(dev.nakasar.hytale.peuples.population.Population.Identity identity) {
        this.identity = identity;
    }

    /** Ce que le PNJ dit déjà à l'ouverture, sous sa première réplique. */
    void said(List<Message> lines) {
        said = lines == null ? List.of() : List.copyOf(lines);
    }

    /** Le PNJ `npc` fait face à `talker` ({@link DialogueFacing}) : il sera libéré à la fermeture. */
    void facing(Ref<EntityStore> npc, Ref<EntityStore> talker) {
        this.npc = npc;
        this.talker = talker;
    }

    /** La caméra de dialogue a été posée pour cette fenêtre : elle sera rendue à sa fermeture. */
    void cameraFramed() {
        camera = true;
    }

    // Libellés en « .TextSpans » (message composé ou vide sur « .Text » : plantage du client), bouton Partir en « .Text »
    // avec une traduction sans paramètre Message (non remplacé par le client), comme les pages vanilla (voir BoardPage).
    // Les réponses sont des Button vanilla portant des Label : pas de texte de bouton imbriqué.
    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmd, UIEventBuilder events, Store<EntityStore> store) {
        cmd.append(LAYOUT);
        World world = store.getExternalData().getWorld();
        DialogueContext context = DialogueContext.of(world, store, ref, playerRef);
        cmd.set("#NpcName.TextSpans", identity != null ? identity.name()
                : dialogue.npcNameKey() == null ? Message.raw("?") : Message.translation(dialogue.npcNameKey()));
        cmd.set("#NpcRole.Visible", dialogue.roleKey() != null);
        cmd.set("#NpcRole.TextSpans", dialogue.roleKey() == null ? Message.raw(" ") : Message.translation(dialogue.roleKey()));
        Message standing = Dialogues.standing(dialogue, context);
        cmd.set("#Standing.Visible", standing != null);
        cmd.set("#Standing.TextSpans", standing == null ? Message.raw(" ") : standing);
        cmd.set("#PortraitFrame.Visible", portrait != null);
        if (portrait != null) {
            cmd.set("#Portrait.AssetPath", portrait);
        }
        // Paroles du dernier choix (où va le Klops, une rumeur, un refus...) sous la réplique ; seules si le PNJ n'a
        // plus de réplique (réponse qui fermait le dialogue) : le joueur les lit avant de partir.
        Message line = DialogueSpeech.withSaid(node == null ? null : Message.translation(node.textKey()), said);
        cmd.set("#Line.TextSpans", line == null ? Message.raw(" ") : line);
        // À l'ouverture, le PNJ parle des PNJ du village tués aujourd'hui (ils reviennent au matin).
        Message aside = node == start ? dev.nakasar.hytale.peuples.village.Absences.aside(dialogue, context) : null;
        if (aside == null && node == start && identity != null) {
            aside = identity.about();
        }
        cmd.set("#Aside.Visible", aside != null);
        cmd.set("#Aside.TextSpans", aside == null ? Message.raw(" ") : aside);
        DialogueResponse[] responses = node == null ? new DialogueResponse[0] : node.responses();
        for (int i = 0; i < Dialogue.MAX_RESPONSES; i++) {
            DialogueResponse r = i < responses.length ? responses[i] : null;
            String answer = "#Answer" + i;
            cmd.set(answer + ".Visible", r != null);
            if (r == null) {
                continue;
            }
            boolean available = r.available(context);
            cmd.set(answer + ".Disabled", !available);
            Message text = Message.translation(r.textKey());
            Message hint;
            if (available) {
                hint = r.hintKey() == null ? null : Message.translation(Dialogues.KEYS + "pageHint").param("hint", Message.translation(r.hintKey()));
            } else {
                text = text.color(LOCKED_TEXT_COLOR);
                hint = Message.translation(Dialogues.KEYS + "pageLockedShort").param("condition", Dialogues.failText(r)).color(LOCKED_COLOR);
            }
            cmd.set("#Text" + i + ".TextSpans", text);
            cmd.set("#Hint" + i + ".Visible", hint != null);
            cmd.set("#Hint" + i + ".TextSpans", hint == null ? Message.raw(" ") : hint);
            events.addEventBinding(CustomUIEventBindingType.Activating, answer, EventData.of("Action", Integer.toString(i)));
        }
        cmd.set("#Leave.Text", Message.translation(Dialogues.KEYS + "leave"));
        events.addEventBinding(CustomUIEventBindingType.Activating, "#Leave", EventData.of("Action", LEAVE));
    }

    /** Fermeture par Échap, par « Partir », par un effet ou par une autre fenêtre ouverte à sa place : caméra rendue, PNJ libéré. */
    @Override
    public void onDismiss(Ref<EntityStore> ref, Store<EntityStore> store) {
        super.onDismiss(ref, store);
        releaseCamera();
    }

    /** Caméra rendue au joueur, PNJ libéré (il reprend sa vie). */
    private void releaseCamera() {
        if (npc != null) {
            DialogueFacing.stop(npc, talker);
            npc = null;
        }
        if (camera) {
            camera = false;
            DialogueCamera.reset(playerRef);
        }
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, Event data) {
        if (data == null || data.action == null || LEAVE.equals(data.action)) {
            releaseCamera();
            close();
            return;
        }
        if (node == null) {
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
            said = outcome.said();
            rebuild();
            return;
        }
        if (outcome.closed() && !outcome.closedByEffect() && !outcome.said().isEmpty()) {
            // La réponse terminait le dialogue, mais le PNJ a répondu : la fenêtre reste ouverte sur ses paroles.
            node = null;
            said = outcome.said();
            rebuild();
            return;
        }
        if (outcome.closed()) {
            // Une autre page (boutique, tableau) remplace la fenêtre : ce que le PNJ a dit part au tchat.
            DialogueSpeech.flush(playerRef, outcome.said());
            releaseCamera();
            // Un effet a pu ouvrir une autre page (tableau) : ne fermer que si la fenêtre affichée est encore celle-ci.
            Player player = store.getComponent(ref, Player.getComponentType());
            if (player == null || player.getPageManager().getCustomPage() == this) {
                close();
            }
            return;
        }
        node = outcome.next();
        said = outcome.said();
        rebuild();
    }
}
