package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * PNJ en conversation : tant que la fenêtre de dialogue est ouverte, le PNJ s'arrête et se tourne (corps et tête) vers
 * le joueur qui lui parle ({@link DialogueFacingSystem}). Rien n'est enregistré sur le PNJ (pas de {@code Frozen}) :
 * un arrêt du serveur en plein dialogue ne laisse aucun villageois figé.
 */
public final class DialogueFacing {

    /** Au-delà, la conversation est oubliée même si la fenêtre n'a pas signalé sa fermeture. */
    static final long MAX_NANOS = 10L * 60 * 1_000_000_000L;

    record Talk(Ref<EntityStore> player, long since) {
    }

    /** PNJ → joueur qui lui parle. Un second joueur qui l'aborde prend la place du premier. */
    static final Map<Ref<EntityStore>, Talk> TALKS = new ConcurrentHashMap<>();

    private DialogueFacing() {
    }

    public static void start(Ref<EntityStore> npc, Ref<EntityStore> player) {
        if (npc != null && player != null && npc.isValid()) {
            TALKS.put(npc, new Talk(player, System.nanoTime()));
        }
    }

    /** Fin de la conversation de `player` avec `npc` (sans effet si un autre joueur lui parle désormais). */
    public static void stop(Ref<EntityStore> npc, Ref<EntityStore> player) {
        if (npc != null) {
            TALKS.computeIfPresent(npc, (k, talk) -> talk.player().equals(player) ? null : talk);
        }
    }
}
