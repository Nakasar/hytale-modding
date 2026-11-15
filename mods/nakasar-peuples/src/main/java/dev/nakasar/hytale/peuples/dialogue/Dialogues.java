package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.People;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le déroulé d'un dialogue, partagé par la fenêtre ({@link DialoguePage}) et le tchat (secours de l'étape 1 tant que la
 * page .ui du mod n'est pas confirmée en jeu : {@code /village parler <id> tchat} puis {@code /village repondre <n>}).
 */
public final class Dialogues {

    public static final String KEYS = "nakasar_peuples.dialogue.";

    /** Où en est un joueur dans un dialogue mené par le tchat. */
    record ChatSession(String dialogueId, String nodeId) {
    }

    private static final Map<UUID, ChatSession> CHAT = new ConcurrentHashMap<>();

    private Dialogues() {
    }

    /** Ce que donne le choix d'une réponse. */
    public record Outcome(boolean chosen, DialogueNode next, boolean closed) {
        static Outcome refused() {
            return new Outcome(false, null, false);
        }
    }

    /**
     * Le joueur choisit la réponse `index` du nœud `node` : conditions, puis effets dans l'ordre (le premier qui échoue
     * arrête la suite et le dialogue reste sur le nœud), puis nœud suivant (null : la fenêtre se ferme).
     */
    public static Outcome choose(Dialogue dialogue, DialogueNode node, int index, DialogueContext context) {
        DialogueResponse[] responses = node.responses();
        if (index < 0 || index >= responses.length || !context.valid()) {
            return Outcome.refused();
        }
        DialogueResponse response = responses[index];
        if (!response.available(context)) {
            if (response.failKey() != null) {
                context.playerRef().sendMessage(Message.translation(response.failKey()));
            }
            return Outcome.refused();
        }
        boolean closedByEffect = false;
        for (DialogueEffect effect : response.effects()) {
            if (effect == null) {
                continue;
            }
            if (!effect.apply(context)) {
                return Outcome.refused();
            }
            closedByEffect |= effect.closesDialogue();
        }
        DialogueNode next = closedByEffect ? null : dialogue.node(response.next());
        return new Outcome(true, next, next == null);
    }

    /** Ouvre le dialogue `dialogue` au joueur dans la fenêtre du mod (thread du monde), sans PNJ en face (commande). */
    public static void openPage(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Dialogue dialogue) {
        openPage(world, store, ref, playerRef, dialogue, null);
    }

    /**
     * Ouvre le dialogue `dialogue` au joueur dans la fenêtre du mod (thread du monde). Avec le PNJ `npc` qui parle, la
     * fenêtre montre son portrait et la caméra cadre le joueur et le PNJ ({@link DialogueCamera}).
     */
    public static void openPage(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Dialogue dialogue,
                                Ref<EntityStore> npc) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        DialogueContext context = DialogueContext.of(world, store, ref, playerRef);
        DialogueNode start = dialogue.start(context);
        if (player == null || start == null) {
            return;
        }
        CHAT.remove(playerRef.getUuid());
        DialoguePage page = new DialoguePage(playerRef, dialogue, start, Portraits.of(store, npc));
        player.getPageManager().openCustomPage(ref, store, page);
        // Après l'ouverture : remplacer une fenêtre de dialogue déjà ouverte rend d'abord sa caméra (onDismiss).
        if (player.getPageManager().getCustomPage() != page) {
            return;
        }
        if (npc != null && npc.isValid()) {
            // Le PNJ s'arrête et se tourne vers le joueur tant que la fenêtre est ouverte.
            DialogueFacing.start(npc, ref);
            page.facing(npc, ref);
        }
        if (DialogueCamera.frame(world, store, ref, playerRef, npc)) {
            page.cameraFramed();
        }
    }

    /** Ouvre le dialogue dans le tchat (secours) : réplique et réponses numérotées. */
    public static void openChat(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Dialogue dialogue) {
        DialogueContext context = DialogueContext.of(world, store, ref, playerRef);
        DialogueNode start = dialogue.start(context);
        if (start == null) {
            return;
        }
        CHAT.put(playerRef.getUuid(), new ChatSession(dialogue.getId(), start.id()));
        printNode(dialogue, start, context);
        Message aside = dev.nakasar.hytale.peuples.village.Absences.aside(dialogue, context);
        if (aside != null) {
            playerRef.sendMessage(aside.color("#c9b98f"));
        }
    }

    /** Réponse `number` (1 à 4, 0 : partir) au dialogue en cours dans le tchat. */
    public static void answerChat(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, int number) {
        ChatSession session = CHAT.get(playerRef.getUuid());
        Dialogue dialogue = session == null ? null : Dialogue.get(session.dialogueId());
        DialogueNode node = dialogue == null ? null : dialogue.node(session.nodeId());
        if (node == null) {
            playerRef.sendMessage(Message.translation(KEYS + "noChat"));
            return;
        }
        if (number == 0) {
            CHAT.remove(playerRef.getUuid());
            playerRef.sendMessage(Message.translation(KEYS + "left"));
            return;
        }
        DialogueContext context = DialogueContext.of(world, store, ref, playerRef);
        Outcome outcome = choose(dialogue, node, number - 1, context);
        if (!outcome.chosen()) {
            return;
        }
        if (outcome.closed()) {
            CHAT.remove(playerRef.getUuid());
            playerRef.sendMessage(Message.translation(KEYS + "ended"));
            return;
        }
        CHAT.put(playerRef.getUuid(), new ChatSession(dialogue.getId(), outcome.next().id()));
        printNode(dialogue, outcome.next(), context);
    }

    public static void forget(UUID player) {
        CHAT.remove(player);
    }

    public static void clearAll() {
        CHAT.clear();
    }

    /** En-tête du PNJ : nom, métier. */
    public static Message header(Dialogue dialogue) {
        Message name = dialogue.npcNameKey() == null ? Message.raw("?") : Message.translation(dialogue.npcNameKey());
        if (dialogue.roleKey() == null) {
            return name;
        }
        return Message.translation(KEYS + "header").param("name", name).param("role", Message.translation(dialogue.roleKey()));
    }

    /**
     * En-tête avec la pastille de rang (maquette du dialogue : « peuple · rang ») quand le dialogue a un peuple : rang
     * dans le village où se trouve le joueur, sinon auprès du peuple.
     */
    public static Message header(Dialogue dialogue, DialogueContext context) {
        People people = People.byId(dialogue.people());
        if (people == null || !context.valid()) {
            return header(dialogue);
        }
        Rank rank = context.village() != null && context.village().people() == people
                ? Reputations.rank(context.store(), context.ref(), context.village())
                : Reputations.peopleRank(context.store(), context.ref(), people);
        return Message.translation(KEYS + "headerRank").param("header", header(dialogue))
                .param("people", Message.translation(people.nameKey())).param("rank", Message.translation(rank.nameKey()));
    }

    /**
     * Pastille de rang de la fenêtre (« peuple · rang ») : rang dans le village où se trouve le joueur s'il est de ce
     * peuple, sinon auprès du peuple ; null si le dialogue n'a pas de peuple.
     */
    public static Message standing(Dialogue dialogue, DialogueContext context) {
        People people = People.byId(dialogue.people());
        if (people == null || !context.valid()) {
            return null;
        }
        Rank rank = context.village() != null && context.village().people() == people
                ? Reputations.rank(context.store(), context.ref(), context.village())
                : Reputations.peopleRank(context.store(), context.ref(), people);
        return Message.translation(KEYS + "standing").param("people", Message.translation(people.nameKey()))
                .param("rank", Message.translation(rank.nameKey()));
    }

    /** Texte d'une réponse grisée : sa condition, ou « indisponible ». */
    public static Message failText(DialogueResponse response) {
        return Message.translation(response.failKey() != null ? response.failKey() : KEYS + "unavailable");
    }

    private static void printNode(Dialogue dialogue, DialogueNode node, DialogueContext context) {
        PlayerRef player = context.playerRef();
        player.sendMessage(header(dialogue, context).bold(true).color("#e8c46a"));
        player.sendMessage(Message.translation(KEYS + "quote").param("text", Message.translation(node.textKey())));
        DialogueResponse[] responses = node.responses();
        for (int i = 0; i < responses.length; i++) {
            DialogueResponse r = responses[i];
            if (r == null) {
                continue;
            }
            Message text = Message.translation(r.textKey());
            if (r.available(context)) {
                Message line = Message.translation(KEYS + "chatResponse").param("number", i + 1).param("text", text);
                if (r.hintKey() != null) {
                    line = Message.translation(KEYS + "chatResponseHint").param("number", i + 1).param("text", text)
                            .param("hint", Message.translation(r.hintKey()));
                }
                player.sendMessage(line);
            } else {
                player.sendMessage(Message.translation(KEYS + "chatResponseLocked").param("number", i + 1).param("text", text)
                        .param("condition", failText(r)).color("#8a8a8a"));
            }
        }
        player.sendMessage(Message.translation(KEYS + "chatLeave"));
    }
}
