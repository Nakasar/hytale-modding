package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.annex.Convoys;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Quête de village « Baliser une route » ({@link RequestType#ROUTE}, Kevin, 15 novembre 2026) : le village demande au
 * joueur de relier par des balises de route ({@link Routes}) un de ses avant-postes, ou un village voisin qui n'est pas
 * rival, à moins de {@code MaxDistance} blocs. La cible est la plus proche qui n'est pas encore reliée. Le village donne
 * {@code ItemId} × {@code Quantity} (des balises) pour commencer. La quête est remplie dès que la route est complète, où
 * que soit le joueur ; la tâche dit combien de blocs il reste à baliser.
 * <p>
 * Les bouts de la route sont ceux des déplacements qui l'emprunteront : sortie de l'avant-poste et dépôt du village
 * (comme le convoi, {@link Convoys#ends}), ou cœur à cœur entre deux villages (comme les voyageurs du monde vivant).
 */
public final class RouteQuests {

    private static final String ANNEX = "annex:";
    private static final String VILLAGE = "village:";
    /** Au moins tant de blocs de mieux avant de dire au joueur où en est la route. */
    private static final int ANNOUNCE_STEP = 24;

    /** Ce qui manque à la route de chaque demande, gardé tant que les balises ne changent pas. */
    private static final Map<PlayerRequest, double[]> GAPS = Collections.synchronizedMap(new WeakHashMap<>());

    private RouteQuests() {
    }

    /** Une cible : son id ({@code annex:<bâtiment>} ou {@code village:<id>}), ses deux bouts et son nom. */
    record Target(String id, double[] ends, Message name, double x, double z) {
    }

    /** Vrai si le village a quelque chose à relier. */
    static boolean available(World world, Village village, RequestTemplate t) {
        return choose(world, village, t) != null;
    }

    /** La cible la plus proche du village qui n'est pas encore reliée, ou null. */
    static Target choose(World world, Village village, RequestTemplate t) {
        Target best = null;
        double bestDistance = Double.MAX_VALUE;
        double min = (double) t.minDistance() * t.minDistance();
        double max = (double) t.maxDistance() * t.maxDistance();
        for (AnnexState a : village.annexes()) {
            Target target = annex(village, a);
            if (target != null) {
                double d = village.horizontalDistanceSquared(target.x(), target.z());
                if (d < bestDistance && unlinked(world, target)) {
                    best = target;
                    bestDistance = d;
                }
            }
        }
        for (Village v : Villages.registry(world).all()) {
            if (v.id().equals(village.id()) || v.people() == village.people().rival()) {
                continue;
            }
            double d = village.horizontalDistanceSquared(v.x(), v.z());
            if (d >= min && d <= max && d < bestDistance) {
                Target target = village(village, v);
                if (unlinked(world, target)) {
                    best = target;
                    bestDistance = d;
                }
            }
        }
        return best;
    }

    /** Prépare la demande prise : sa cible ; faux si plus rien n'est à relier. */
    static boolean prepare(World world, PlayerRef player, Village village, RequestTemplate t, PlayerRequest r) {
        Target target = choose(world, village, t);
        if (target == null) {
            player.sendMessage(Message.translation(Requests.KEYS + "route.noTarget"));
            return false;
        }
        r.setTarget(target.id());
        return true;
    }

    /** La demande vient d'être prise : les balises pour commencer. */
    static void started(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PlayerRequest r, RequestTemplate t) {
        if (t.itemId() != null && t.quantity() > 0) {
            Requests.give(store, ref, new ItemStack(t.itemId(), t.quantity()));
            player.sendMessage(Message.translation(Requests.KEYS + "route.kit").param("count", t.quantity()));
        }
    }

    /** Une fois par seconde : remplie quand la route est complète ; le joueur apprend où elle en est. */
    static void step(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                     PlayerRequest r, Village village) {
        Target target = target(world, village, r);
        if (target == null) {
            Requests.fail(world, store, ref, player, data, r, Requests.KEYS + "route.gone");
            return;
        }
        int gap = gap(world, r, target);
        if (gap <= 0) {
            player.sendMessage(Message.translation(Requests.KEYS + "route.done").param("place", target.name()));
            Requests.fulfil(world, store, ref, player, data, r);
            return;
        }
        int last = r.count();
        if (last == 0) {
            r.setCount(gap);
        } else if (gap <= last - ANNOUNCE_STEP) {
            r.setCount(gap);
            NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(Requests.KEYS + "route.progress")
                    .param("place", target.name()).param("gap", gap), NotificationStyle.Default);
        } else if (gap > last) {
            r.setCount(gap);
        }
    }

    /** Ligne de tâche : la cible (distance, direction) et ce qui reste à baliser. */
    static Message task(World world, PlayerRequest r, RequestTemplate t, Village village, Vector3d from) {
        Target target = target(world, village, r);
        Message m = Message.translation(t.taskKey());
        if (target == null) {
            return m.param("place", "?").param("gap", "?").param("distance", "?").param("direction", "?");
        }
        m = m.param("place", target.name()).param("gap", gap(world, r, target));
        if (from != null) {
            double dx = target.x() - from.x();
            double dz = target.z() - from.z();
            return m.param("distance", (int) Math.round(Math.sqrt(dx * dx + dz * dz)))
                    .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(dx, dz)));
        }
        return m.param("distance", "?").param("direction", "?");
    }

    // ---- Cibles ----

    private static Target target(World world, Village village, PlayerRequest r) {
        String id = r.target();
        if (id == null) {
            return null;
        }
        if (id.startsWith(ANNEX)) {
            String w = id.substring(ANNEX.length());
            for (AnnexState a : village.annexes()) {
                if (a.id().equals(w)) {
                    return annex(village, a);
                }
            }
            return null;
        }
        if (id.startsWith(VILLAGE)) {
            Village v = Villages.registry(world).byId(id.substring(VILLAGE.length()));
            return v == null || v.id().equals(village.id()) ? null : village(village, v);
        }
        return null;
    }

    private static Target annex(Village village, AnnexState a) {
        Workshop w = Workshop.get(a.id());
        if (w == null || !w.isAnnex() || !a.built()) {
            return null;
        }
        return new Target(ANNEX + a.id(), Convoys.ends(village, w, a), Message.translation(w.nameKey()), a.x() + 0.5, a.z() + 0.5);
    }

    private static Target village(Village from, Village to) {
        return new Target(VILLAGE + to.id(), new double[] {from.x() + 0.5, from.z() + 0.5, to.x() + 0.5, to.z() + 0.5},
                Message.raw(to.name()), to.x() + 0.5, to.z() + 0.5);
    }

    private static boolean unlinked(World world, Target target) {
        double[] e = target.ends();
        return Routes.gap(world, e[0], e[1], e[2], e[3]) > 0;
    }

    /** Blocs qui restent à baliser (arrondi au-dessus), recalculé quand une balise est posée ou retirée. */
    private static int gap(World world, PlayerRequest r, Target target) {
        int version = Villages.registry(world).beaconVersion();
        double[] cached = GAPS.get(r);
        if (cached == null || cached[0] != version) {
            double[] e = target.ends();
            cached = new double[] {version, Routes.gap(world, e[0], e[1], e[2], e[3])};
            GAPS.put(r, cached);
        }
        return (int) Math.ceil(cached[1]);
    }
}
