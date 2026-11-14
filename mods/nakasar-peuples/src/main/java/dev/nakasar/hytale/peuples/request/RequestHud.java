package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.protocol.FormattedMessage;
import com.hypixel.hytale.protocol.Objective;
import com.hypixel.hytale.protocol.ObjectiveTask;
import com.hypixel.hytale.protocol.packets.assets.TrackOrUpdateObjective;
import com.hypixel.hytale.protocol.packets.assets.UntrackObjective;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le suivi des demandes à l'écran, par les paquets du système d'objectifs vanilla ({@code TrackOrUpdateObjective},
 * {@code UntrackObjective}) que le client affiche à droite de l'écran (GDD, maquette du HUD). Le serveur n'y crée pas
 * d'objectif vanilla : c'est le Java des demandes qui compte, ces paquets ne servent qu'à l'affichage, avec un titre et
 * une ligne de tâche calculés à chaque mise à jour (distance et direction comprises).
 *
 * <p>Essai de l'étape 3 (« rendu HUD à vérifier ») : si le client n'affiche rien, le tableau, le tchat et les
 * notifications donnent les mêmes informations.
 */
public final class RequestHud {

    private record Sent(FormattedMessage title, FormattedMessage description, FormattedMessage task, int current, int needed) {
    }

    /** Dernier suivi envoyé, par « joueur|suivi », pour n'envoyer que les changements. */
    private static final Map<String, Sent> SENT = new ConcurrentHashMap<>();

    private RequestHud() {
    }

    private static String key(PlayerRef player, UUID hud) {
        return player.getUuid() + "|" + hud;
    }

    /**
     * Affiche ou met à jour le suivi `hud` du joueur : titre, description (village et récompense) et une tâche avec
     * son avancement. N'envoie rien si rien n'a changé depuis le dernier envoi, sauf `force`.
     */
    public static void track(PlayerRef player, UUID hud, Message title, Message description, Message task, int current,
                             int needed, boolean force) {
        int shown = Math.max(0, Math.min(current, needed));
        Sent sent = new Sent(title.getFormattedMessage(), description.getFormattedMessage(), task.getFormattedMessage(), shown, needed);
        String key = key(player, hud);
        if (!force && sent.equals(SENT.get(key))) {
            return;
        }
        SENT.put(key, sent);
        ObjectiveTask[] tasks = {new ObjectiveTask(sent.task(), shown, needed)};
        Objective objective = new Objective(hud, sent.title(), sent.description(), null, tasks);
        player.getPacketHandler().writeNoCache(new TrackOrUpdateObjective(objective));
    }

    /** Retire le suivi `hud` de l'écran du joueur. */
    public static void untrack(PlayerRef player, UUID hud) {
        SENT.remove(key(player, hud));
        player.getPacketHandler().writeNoCache(new UntrackObjective(hud));
    }

    /** Oublie ce qui a été envoyé au joueur (reconnexion : tout sera renvoyé). */
    public static void forget(UUID player) {
        String prefix = player + "|";
        SENT.keySet().removeIf(k -> k.startsWith(prefix));
    }

    public static void clearAll() {
        SENT.clear();
    }
}
