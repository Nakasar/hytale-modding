package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.request.Requests;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Jeux de recherche à durée limitée : cache-cache des enfants ({@link Surroundings}) et course de la foire
 * ({@link Calendar}). Le joueur doit passer à moins de {@value #REACH} blocs de chaque point (un enfant caché, un
 * drapeau) avant la fin du temps ; chaque point trouvé est annoncé, le dernier gagne.
 */
public final class Hunts {

    public static final double REACH = 3.0;

    /** Fin d'un jeu : `won` vrai si tout a été trouvé à temps ; `player` null s'il a quitté le monde. */
    @FunctionalInterface
    public interface End {
        void done(World world, Store<EntityStore> store, PlayerRef player, boolean won);
    }

    /** Un point à trouver : un PNJ (suivi) ou une place fixe ; `cleanup` le retire. */
    public static final class Spot {
        final Ref<EntityStore> npc;
        final Vector3d at;
        final Runnable cleanup;
        boolean found;

        public Spot(Ref<EntityStore> npc, Vector3d at, Runnable cleanup) {
            this.npc = npc;
            this.at = at;
            this.cleanup = cleanup;
        }
    }

    private record Hunt(String id, UUID player, List<Spot> spots, long end, String foundKey, End end_) {
    }

    private static final Map<String, Hunt> HUNTS = new ConcurrentHashMap<>();

    private Hunts() {
    }

    public static boolean running(String id) {
        return HUNTS.containsKey(id);
    }

    /** Le joueur a un jeu en cours. */
    public static boolean playing(UUID player) {
        for (Hunt h : HUNTS.values()) {
            if (h.player().equals(player)) {
                return true;
            }
        }
        return false;
    }

    public static void start(String id, PlayerRef player, List<Spot> spots, int seconds, String foundKey, End end) {
        HUNTS.put(id, new Hunt(id, player.getUuid(), new ArrayList<>(spots), System.currentTimeMillis() + seconds * 1000L, foundKey, end));
    }

    static void step(World world, Store<EntityStore> store) {
        for (Hunt h : new ArrayList<>(HUNTS.values())) {
            PlayerRef player = null;
            for (PlayerRef p : world.getPlayerRefs()) {
                if (p.getUuid().equals(h.player())) {
                    player = p;
                }
            }
            if (player == null) {
                finish(world, store, h, null, false);
                continue;
            }
            Vector3d me = Requests.position(store, player.getReference());
            int found = 0;
            for (Spot s : h.spots()) {
                if (!s.found && me != null) {
                    Vector3d at = s.npc != null && s.npc.isValid() ? Requests.position(store, s.npc) : s.at;
                    if (at != null && at.distanceSquared(me) <= REACH * REACH) {
                        s.found = true;
                        s.cleanup.run();
                        int n = (int) h.spots().stream().filter(x -> x.found).count();
                        Message m = Message.translation(h.foundKey()).param("found", n).param("total", h.spots().size());
                        NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Default);
                    }
                }
                if (s.found) {
                    found++;
                }
            }
            if (found == h.spots().size()) {
                finish(world, store, h, player, true);
            } else if (System.currentTimeMillis() > h.end()) {
                finish(world, store, h, player, false);
            }
        }
    }

    private static void finish(World world, Store<EntityStore> store, Hunt h, PlayerRef player, boolean won) {
        HUNTS.remove(h.id());
        for (Spot s : h.spots()) {
            if (!s.found) {
                s.cleanup.run();
            }
        }
        h.end_().done(world, store, player, won && player != null);
    }

    public static void clearAll() {
        HUNTS.clear();
    }
}
