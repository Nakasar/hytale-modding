package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.DialogueContext;
import dev.nakasar.hytale.peuples.request.Criers;
import dev.nakasar.hytale.peuples.request.GameClock;

import java.util.ArrayList;
import java.util.List;

/**
 * Les PNJ du village tués aujourd'hui (GDD, Villageois et métiers : « un PNJ tué réapparaît au prochain matin ») : le
 * tableau les liste avec l'heure de leur retour, et les autres PNJ du village en parlent en ouvrant leur dialogue.
 */
public final class Absences {

    public static final String KEYS = "nakasar_peuples.absent.";
    /** Au-delà, la liste dit « et N autres » : la réplique tient sur deux lignes. */
    static final int MAX_NAMES = 3;

    private Absences() {
    }

    /** Dialogues des PNJ absents du village : postes fixes (crieur, marchand, chef), puis métiers. */
    public static List<String> dialogues(Store<EntityStore> store, Village village) {
        List<String> out = new ArrayList<>(Criers.absent(store, village));
        for (String id : Villagers.absent(store, village)) {
            if (!out.contains(id)) {
                out.add(id);
            }
        }
        out.removeIf(id -> Dialogue.get(id) == null);
        return out;
    }

    /** Heures (arrondies au-dessus) jusqu'au prochain matin, {@value GameClock#MORNING} h. */
    public static int hoursUntilMorning(Store<EntityStore> store) {
        int hour = GameClock.hour(store);
        if (hour < 0) {
            return 24;
        }
        return Math.floorMod(GameClock.MORNING - hour - 1, 24) + 1;
    }

    /** Lignes du tableau : l'en-tête avec l'heure du retour, puis un PNJ par ligne (nom, métier). Vide si personne. */
    public static List<Message> boardLines(Store<EntityStore> store, Village village) {
        List<Message> lines = new ArrayList<>();
        List<String> ids = dialogues(store, village);
        if (ids.isEmpty()) {
            return lines;
        }
        lines.add(Message.translation(KEYS + "board").param("morning", GameClock.MORNING).param("hours", hoursUntilMorning(store)));
        for (String id : ids) {
            Dialogue d = Dialogue.get(id);
            Message name = Message.translation(d.npcNameKey());
            Message who = d.roleKey() == null ? name
                    : Message.translation("nakasar_peuples.dialogue.header").param("name", name).param("role", Message.translation(d.roleKey()));
            lines.add(Message.translation(KEYS + "boardLine").param("who", who));
        }
        return lines;
    }

    /**
     * Les absents en un paragraphe pour le pied du panneau (BoardPage) : « Absents, de retour à 6 h (dans 9 h) : Rosée,
     * Puisatière · Trèfle, Éleveur… » ; null si personne ne manque. Une ligne par absent débordait de la fenêtre.
     */
    public static Message boardSummary(Store<EntityStore> store, Village village) {
        List<String> ids = dialogues(store, village);
        if (ids.isEmpty()) {
            return null;
        }
        Message body = Message.translation(KEYS + "board").param("morning", GameClock.MORNING).param("hours", hoursUntilMorning(store));
        for (int i = 0; i < ids.size(); i++) {
            Dialogue d = Dialogue.get(ids.get(i));
            Message name = Message.translation(d.npcNameKey());
            body.insert(i == 0 ? " " : " · ");
            body.insert(d.roleKey() == null ? name
                    : Message.translation("nakasar_peuples.dialogue.header").param("name", name).param("role", Message.translation(d.roleKey())));
        }
        return body;
    }

    /**
     * Ce que dit `speaker` des absents de son village en ouvrant le dialogue, dans la voix de son peuple ; null si
     * personne ne manque, ou si le joueur n'est pas dans un village de ce peuple.
     */
    public static Message aside(Dialogue speaker, DialogueContext context) {
        Village village = context.village();
        People people = People.byId(speaker.people());
        if (village == null || people == null || village.people() != people || !context.valid()) {
            return null;
        }
        List<String> ids = dialogues(context.store(), village);
        ids.remove(speaker.getId());
        if (ids.isEmpty()) {
            return null;
        }
        return Message.translation(KEYS + "voice." + people.id()).param("who", names(ids));
    }

    /** « A », « A et B », « A, B et C », « A, B et N autres ». */
    static Message names(List<String> ids) {
        List<Message> names = new ArrayList<>();
        for (String id : ids) {
            names.add(Message.translation(Dialogue.get(id).npcNameKey()));
        }
        if (names.size() == 1) {
            return names.get(0);
        }
        if (names.size() > MAX_NAMES) {
            return Message.translation(KEYS + "others").param("a", names.get(0)).param("b", names.get(1))
                    .param("count", names.size() - 2);
        }
        Message out = names.get(0);
        for (int i = 1; i < names.size() - 1; i++) {
            out = Message.translation(KEYS + "comma").param("a", out).param("b", names.get(i));
        }
        return Message.translation(KEYS + "and").param("a", out).param("b", names.get(names.size() - 1));
    }
}
