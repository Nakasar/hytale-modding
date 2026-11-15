package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Convois des avant-postes : la production du matin part à pied vers le dépôt du village, portée par deux ou trois
 * villageois de l'avant-poste. Le convoi suit la ligne droite de l'entrée de l'avant-poste au dépôt ; sa progression
 * (en blocs) est sauvée dans {@link AnnexState}.
 * <ul>
 *   <li>Un joueur à moins de {@value #SPAWN_RADIUS} blocs du convoi : les porteurs sont de vrais PNJ qui marchent (point
 *       d'attache {@value #LEAD} blocs devant eux, sur la ligne) ; la progression est celle du porteur de tête.</li>
 *   <li>Personne près de lui : pas de PNJ, le convoi avance seul à {@value #SPEED} blocs/s.</li>
 *   <li>Un porteur tué lâche sa part de la cargaison au sol. Tué par un joueur : malus de réputation violent
 *       ({@value #KILL_PENALTY}, en plus de celui du meurtre d'un villageois) auprès du village. Plus de porteur : la
 *       livraison du jour est perdue, le convoi suivant part le lendemain matin.</li>
 *   <li>Arrivé : la cargaison restante entre au dépôt (dès que son coffre est chargé).</li>
 * </ul>
 */
public final class Convoys {

    /** Malus de réputation de plus quand un joueur tue un porteur. */
    public static final int KILL_PENALTY = -80;
    static final int SPAWN_RADIUS = 64;
    static final int LEAD = 10;
    static final double SPEED = 3.0;
    private static final double ARRIVE = 4.0;
    private static final float STUCK_SECONDS = 30f;
    private static final int HOP = 8;
    private static final int WATCHED = 24;
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    /** Un porteur : son village, son avant-poste. */
    record Porter(String village, String workshop) {
    }

    private static final Map<Ref<EntityStore>, Porter> PORTERS = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<String, List<Ref<EntityStore>>> BY_CONVOY = new ConcurrentHashMap<>();
    /** Par convoi : {meilleure progression vue, secondes sans avancer}. */
    private static final Map<String, double[]> STUCK = new ConcurrentHashMap<>();

    private Convoys() {
    }

    /** Porteurs selon le niveau de l'avant-poste. */
    static int porters(int level) {
        return level >= 2 ? 3 : 2;
    }

    /** Le convoi du matin part (la livraison du jour est comptée faite) ; false si le village n'a pas de dépôt. */
    static boolean start(Store<EntityStore> store, Village village, Workshop w, AnnexState a, int cargo) {
        if (village.deposit() == null || cargo <= 0) {
            return false;
        }
        int level = Math.max(1, village.workshop(w.getId()).level());
        a.setDeliveryDay(GameClock.day(store));
        a.startConvoy(cargo, porters(level));
        LOGGER.atInfo().log("Nakasar Peuples : convoi de %s (%d porteurs, %d objets) vers %s", w.getId(), porters(level), cargo, village.name());
        return true;
    }

    /** Le pas d'un convoi en route (toutes les 2 s environ, joueurs connectés). */
    static void step(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a, List<Vector3d> players, float dt) {
        String key = key(village, w);
        double[] to = to(village);
        double[] from = from(w, a, to);
        double length = Math.hypot(to[0] - from[0], to[1] - from[1]);
        List<Ref<EntityStore>> refs = alive(key);
        if (a.convoyAt() >= length - ARRIVE) {
            arrive(world, store, village, w, a, key);
            return;
        }
        double[] here = point(from, to, length, a.convoyAt());
        if (!near(players, here[0], here[1], SPAWN_RADIUS)) {
            despawn(store, key);
            a.setConvoyAt(Math.min(length, a.convoyAt() + SPEED * dt));
            return;
        }
        if (refs.isEmpty()) {
            spawn(world, store, village, w, a, key, from, to, length);
            return;
        }
        // Progression : le porteur de tête, projeté sur la ligne.
        double best = a.convoyAt();
        for (Ref<EntityStore> ref : refs) {
            Vector3d at = Requests.position(store, ref);
            if (at != null) {
                double t = ((at.x() - from[0]) * (to[0] - from[0]) + (at.z() - from[1]) * (to[1] - from[1])) / Math.max(1e-6, length);
                best = Math.max(best, Math.min(length, t));
            }
        }
        double lead = best;
        double[] stuck = STUCK.computeIfAbsent(key, k -> new double[] {lead, 0});
        if (best > stuck[0] + 1) {
            stuck[0] = best;
            stuck[1] = 0;
        } else {
            stuck[1] += dt;
        }
        if (stuck[1] >= STUCK_SECONDS && !near(players, here[0], here[1], WATCHED)) {
            // Coincés (rivière, falaise) et personne ne les voit : un saut le long de la ligne.
            best = Math.min(length, best + HOP);
            double[] hop = point(from, to, length, best);
            for (int i = 0; i < refs.size(); i++) {
                Vector3d spot = ground(world, a, hop, from, to, length, i);
                store.putComponent(refs.get(i), Teleport.getComponentType(), new Teleport(spot, new Rotation3f(0f, 0f, 0f)));
            }
            stuck[0] = best;
            stuck[1] = 0;
        }
        a.setConvoyAt(best);
        double[] ahead = point(from, to, length, Math.min(length, best + LEAD));
        for (int i = 0; i < refs.size(); i++) {
            NPCEntity npc = store.getComponent(refs.get(i), NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(ground(world, a, ahead, from, to, length, i));
            }
        }
    }

    private static void spawn(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a, String key,
                              double[] from, double[] to, double length) {
        VillageLayout.Job[] workers = w.annex().workers();
        if (workers.length == 0) {
            return;
        }
        VillageLayout.Job job = workers[0];
        double[] here = point(from, to, length, a.convoyAt());
        double[] ahead = point(from, to, length, Math.min(length, a.convoyAt() + LEAD));
        List<Ref<EntityStore>> refs = new ArrayList<>();
        for (int i = 0; i < a.convoyPorters(); i++) {
            Vector3d spot = ground(world, a, here, from, to, length, i);
            Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, job.role(), null, spot, new Rotation3f(0f, 0f, 0f));
            if (spawned == null || spawned.first() == null) {
                LOGGER.atWarning().log("Nakasar Peuples : porteur '%s' du convoi %s impossible à poser", job.role(), w.getId());
                continue;
            }
            Ref<EntityStore> ref = spawned.first();
            store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
            NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(ground(world, a, ahead, from, to, length, i));
            }
            Villagers.enlist(ref, village.id(), "CV_" + w.getId() + "_" + i, job.dialogue());
            PORTERS.put(ref, new Porter(village.id(), w.getId()));
            refs.add(ref);
        }
        BY_CONVOY.put(key, refs);
        STUCK.remove(key);
    }

    private static void arrive(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a, String key) {
        VillageLayout.Material lot = w.annex().delivery();
        ItemContainer chest = Villages.depositChest(world, village);
        if (chest == null && lot != null) {
            // Dépôt pas chargé : le convoi attend au village, il livrera quand un joueur s'en approchera.
            return;
        }
        if (lot != null) {
            chest.addItemStack(new ItemStack(lot.itemId(), a.convoyCargo()));
        }
        despawn(store, key);
        LOGGER.atInfo().log("Nakasar Peuples : le convoi de %s livre %d %s au dépôt de %s", w.getId(), a.convoyCargo(),
                lot == null ? "?" : lot.itemId(), village.name());
        a.endConvoy();
    }

    /** Le PNJ `ref` est un porteur de convoi. */
    public static boolean isPorter(Ref<EntityStore> ref) {
        return ref != null && PORTERS.containsKey(ref);
    }

    /**
     * Un porteur est mort (système de mort, avant le retrait du PNJ) : sa part tombe au sol à `where` ; tué par
     * `killer`, malus violent. Le travail se fait après le tick.
     */
    public static void died(World world, Ref<EntityStore> ref, Vector3d where, PlayerRef killer) {
        Porter p = PORTERS.remove(ref);
        if (p == null) {
            return;
        }
        world.execute(() -> {
            Store<EntityStore> store = world.getEntityStore().getStore();
            Village village = Villages.registry(world).byId(p.village());
            Workshop w = Workshop.get(p.workshop());
            String key = p.village() + "/" + p.workshop();
            List<Ref<EntityStore>> refs = BY_CONVOY.get(key);
            if (refs != null) {
                refs.remove(ref);
            }
            AnnexState a = village == null ? null : village.annex(p.workshop());
            if (a == null || w == null || !a.convoy()) {
                return;
            }
            int share = a.convoyPorters() <= 1 ? a.convoyCargo() : (a.convoyCargo() + a.convoyPorters() - 1) / a.convoyPorters();
            VillageLayout.Material lot = w.annex().delivery();
            if (lot != null && share > 0 && where != null) {
                for (Holder<EntityStore> drop : ItemComponent.generateItemDrops(store, List.of(new ItemStack(lot.itemId(), share)),
                        new Vector3d(where).add(0, 0.5, 0), new Rotation3f())) {
                    store.addEntity(drop, AddReason.SPAWN);
                }
            }
            a.loseConvoyPorter(share);
            Message building = Message.translation(w.nameKey());
            if (!a.convoy()) {
                a.endConvoy();
                despawn(store, key);
                Chantiers.announce(world, village, Message.translation(Annexes.KEYS + "convoy.lost").param("building", building),
                        null, NotificationStyle.Danger);
            } else {
                Chantiers.announce(world, village, Message.translation(Annexes.KEYS + "convoy.porter").param("building", building)
                        .param("left", a.convoyPorters()), null, NotificationStyle.Warning);
            }
            Ref<EntityStore> killerRef = killer == null ? null : killer.getReference();
            if (killerRef != null && killerRef.isValid()) {
                Reputations.change(world, store, killerRef, killer, village, KILL_PENALTY, Annexes.KEYS + "convoy.reason");
            }
        });
    }

    // ---- Géométrie ----

    /** Départ : sur la ligne de la fondation au dépôt, juste hors de l'emprise de l'avant-poste. */
    private static double[] from(Workshop w, AnnexState a, double[] to) {
        double x = a.x() + 0.5;
        double z = a.z() + 0.5;
        double length = Math.hypot(to[0] - x, to[1] - z);
        if (length < 1) {
            return new double[] {x, z};
        }
        double dx = (to[0] - x) / length;
        double dz = (to[1] - z) / length;
        int[] r = Annexes.worldRect(w, a);
        for (int i = 0; i < 64 && x >= r[0] - 2 && x <= r[1] + 3 && z >= r[2] - 2 && z <= r[3] + 3; i++) {
            x += dx;
            z += dz;
        }
        return new double[] {x, z};
    }

    private static double[] to(Village village) {
        int[] d = village.deposit();
        return new double[] {d[0] + 0.5, d[2] + 0.5};
    }

    private static double[] point(double[] from, double[] to, double length, double at) {
        double f = length <= 0 ? 1 : Math.max(0, Math.min(1, at / length));
        return new double[] {from[0] + (to[0] - from[0]) * f, from[1] + (to[1] - from[1]) * f};
    }

    /** Place du porteur `i` autour du point `p` : en file, décalés sur le côté pour ne pas s'empiler. */
    private static Vector3d ground(World world, AnnexState a, double[] p, double[] from, double[] to, double length, int i) {
        double dx = (to[0] - from[0]) / Math.max(1e-6, length);
        double dz = (to[1] - from[1]) / Math.max(1e-6, length);
        double side = (i % 2 == 0 ? 1 : -1) * 1.5 * ((i + 1) / 2);
        double back = 1.5 * i;
        int x = (int) Math.floor(p[0] - dx * back - dz * side);
        int z = (int) Math.floor(p[1] - dz * back + dx * side);
        return Villagers.groundAt(world, x, z, a.ground() + 1);
    }

    private static boolean near(List<Vector3d> players, double x, double z, int range) {
        for (Vector3d p : players) {
            double dx = p.x() - x;
            double dz = p.z() - z;
            if (dx * dx + dz * dz <= (double) range * range) {
                return true;
            }
        }
        return false;
    }

    /** Porteurs encore vivants du convoi (ceux d'un tronçon déchargé ont disparu : ils seront reposés). */
    private static List<Ref<EntityStore>> alive(String key) {
        List<Ref<EntityStore>> refs = BY_CONVOY.get(key);
        if (refs == null) {
            return List.of();
        }
        refs.removeIf(ref -> {
            if (ref.isValid()) {
                return false;
            }
            PORTERS.remove(ref);
            Villagers.discharge(ref);
            return true;
        });
        return refs;
    }

    private static void despawn(Store<EntityStore> store, String key) {
        List<Ref<EntityStore>> refs = BY_CONVOY.remove(key);
        STUCK.remove(key);
        if (refs == null) {
            return;
        }
        for (Ref<EntityStore> ref : refs) {
            PORTERS.remove(ref);
            Villagers.discharge(ref);
            if (ref.isValid()) {
                store.removeEntity(ref, RemoveReason.REMOVE);
            }
        }
    }

    private static String key(Village village, Workshop w) {
        return village.id() + "/" + w.getId();
    }

    /** Oublie les porteurs (rechargement du mod) ; les convois reprendront sans PNJ puis les reposeront. */
    public static void clearAll() {
        PORTERS.clear();
        BY_CONVOY.clear();
        STUCK.clear();
    }
}
