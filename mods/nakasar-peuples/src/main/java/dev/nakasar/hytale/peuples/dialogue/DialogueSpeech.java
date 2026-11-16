package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Ce qu'un PNJ dit en réponse à un choix de dialogue (où est le Klops demain, une rumeur, l'état du chantier, un refus...).
 * Pendant que {@link Dialogues#choose} applique les effets d'une réponse, {@link #say} garde ces lignes pour la fenêtre
 * de dialogue, qui les affiche sous la réplique du PNJ ; hors dialogue (commande, système du monde), elles vont au tchat.
 * Les retours du jeu (essor, réputation, notifications) restent dans le tchat : seules les paroles passent par ici.
 * Toujours sur le thread du monde, comme les effets.
 */
public final class DialogueSpeech {

    private record Capture(UUID player, List<Message> lines) {
    }

    private static final ThreadLocal<Capture> CAPTURE = new ThreadLocal<>();

    private DialogueSpeech() {
    }

    /** Le PNJ dit `line` au joueur : dans la fenêtre de dialogue si un choix est en cours pour lui, sinon dans le tchat. */
    public static void say(PlayerRef player, Message line) {
        if (line == null) {
            return;
        }
        Capture capture = CAPTURE.get();
        if (capture != null && player != null && capture.player().equals(player.getUuid())) {
            capture.lines().add(line);
        } else if (player != null) {
            player.sendMessage(line);
        }
    }

    /** Commence à garder les paroles adressées à `player` ; rend la liste qui les recevra. */
    static List<Message> begin(PlayerRef player) {
        List<Message> lines = new ArrayList<>();
        CAPTURE.set(new Capture(player.getUuid(), lines));
        return lines;
    }

    static void end() {
        CAPTURE.remove();
    }

    /** Envoie au tchat des paroles qu'aucune fenêtre n'affichera (dialogue fermé par une autre page, dialogue au tchat). */
    static void flush(PlayerRef player, List<Message> lines) {
        for (Message line : lines) {
            player.sendMessage(line);
        }
    }

    /** La réplique `line` suivie des paroles `said`, une par ligne (`line` null : les paroles seules). */
    static Message withSaid(Message line, List<Message> said) {
        if (said.isEmpty()) {
            return line;
        }
        Message out = Message.empty();
        boolean first = true;
        if (line != null) {
            out.insert(line);
            first = false;
        }
        for (Message s : said) {
            if (!first) {
                out.insert(Message.raw("\n"));
            }
            out.insert(s);
            first = false;
        }
        return out;
    }
}
