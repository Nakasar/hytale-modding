package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.ResourceType;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le socle du monde vivant entre les villages (proposition « Un monde vivant entre les villages », 15 novembre 2026) :
 * le registre sauvegardé ({@link WorldLifeRegistry}), le budget de PNJ, les camps des combats ({@link #side}), les PNJ
 * à qui l'on parle ({@link #talker}) et ceux dont la mort compte ({@link #mortal}).
 *
 * <p>Simulation à deux vitesses, reprise des convois des avant-postes : un voyageur, une caravane, une bande est un
 * état sauvé ; à moins de {@value #REAL_RANGE} blocs d'un joueur il devient un vrai PNJ (non sauvegardé), sinon il
 * avance seul. Au plus {@value #PER_PLAYER} PNJ du monde vivant par joueur connecté et {@value #PER_WORLD} par monde.
 *
 * <p>Règles permanentes : tous les rôles sont {@code Nakasar_Peuples_*} (amicaux : régénération vanilla
 * hors combat ; hostiles : aucune, {@code VillageNoRegenSystem}) ; aucun PNJ n'est posé dans l'eau, la lave ou un bloc ({@link #ground}).
 */
public final class WorldLife {

    public static final String KEYS = "nakasar_peuples.world.";
    /** Un état devient un vrai PNJ à moins de cette distance d'un joueur. */
    public static final int REAL_RANGE = 64;
    public static final int PER_PLAYER = 12;
    public static final int PER_WORLD = 40;
    /** Pas de téléportation (PNJ coincé) sous les yeux d'un joueur à moins de cette distance. */
    public static final int WATCHED = 24;

    /** Un camp dans un combat du monde vivant : même clé et équipes différentes = ennemis ; même équipe = alliés. */
    public record Side(String key, int team) {
    }

    /** Un PNJ du monde vivant à qui l'on parle. */
    @FunctionalInterface
    public interface Talker {
        void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc);
    }

    /** Un PNJ du monde vivant dont la mort compte (thread du monde, après le tick). */
    @FunctionalInterface
    public interface Mortal {
        void died(World world, Ref<EntityStore> npc, Vector3d where, PlayerRef killer);
    }

    private static ResourceType<EntityStore, WorldLifeRegistry> resourceType;
    private static final Map<Ref<EntityStore>, Boolean> NPCS = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<Ref<EntityStore>, Side> SIDES = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<Ref<EntityStore>, Talker> TALKERS = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<Ref<EntityStore>, Mortal> MORTALS = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Joueur -> PNJ du monde vivant à qui il parle (les effets de dialogue le lisent). */
    private static final Map<UUID, Ref<EntityStore>> TALKING = new ConcurrentHashMap<>();

    private WorldLife() {
    }

    public static void setResourceType(ResourceType<EntityStore, WorldLifeRegistry> type) {
        resourceType = type;
    }

    public static WorldLifeRegistry registry(World world) {
        return world.getEntityStore().getStore().getResource(resourceType);
    }

    // ---- PNJ ----

    /** Nombre de PNJ du monde vivant encore en vie. */
    public static int alive() {
        synchronized (NPCS) {
            NPCS.keySet().removeIf(ref -> !ref.isValid());
            return NPCS.size();
        }
    }

    /** Vrai si `count` PNJ de plus tiennent dans le budget ({@value #PER_PLAYER} par joueur, {@value #PER_WORLD} au plus). */
    public static boolean budget(World world, int count) {
        int players = world.getPlayerRefs().size();
        return alive() + count <= Math.min(PER_WORLD, PER_PLAYER * Math.max(1, players));
    }

    /**
     * Pose un PNJ du monde vivant (non sauvegardé, point d'attache à sa place). Null si le rôle ne peut pas être posé.
     */
    public static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at, float yaw) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, yaw, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples (monde vivant) : impossible de poser '%s' en %.0f %.0f %.0f",
                    role, at.x(), at.y(), at.z());
            return null;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(new Vector3d(at));
        }
        NPCS.put(ref, Boolean.TRUE);
        return ref;
    }

    /** Retire un PNJ du monde vivant et oublie tout ce qui le concerne. */
    public static void remove(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref == null) {
            return;
        }
        forget(ref);
        if (ref.isValid()) {
            store.removeEntity(ref, RemoveReason.REMOVE);
        }
    }

    public static void forget(Ref<EntityStore> ref) {
        NPCS.remove(ref);
        SIDES.remove(ref);
        TALKERS.remove(ref);
        MORTALS.remove(ref);
        forgetInModules(ref);
    }

    /** Les tables d'identité des modules (voyageur, aubergiste, campeur...) oublient ce PNJ. */
    private static void forgetInModules(Ref<EntityStore> ref) {
        Travellers.forget(ref);
        Inns.forget(ref);
        Hamlets.forget(ref);
        HamletTrips.forget(ref);
        Garrisons.forget(ref);
        Camps.forget(ref);
        Calendar.forget(ref);
        Surroundings.forget(ref);
    }

    /** Oublie le camp de combat d'une entité qui n'est pas un PNJ du monde vivant (porteur de convoi). */
    public static void unside(Ref<EntityStore> ref) {
        SIDES.remove(ref);
    }

    private static final Map<String, Integer> DAILY = new ConcurrentHashMap<>();

    /**
     * Plafond quotidien d'un joueur pour `what` (dons, offrandes) : rend combien il peut encore donner aujourd'hui
     * (au plus `max`) ; {@link #spend} compte ce qu'il a donné. Les jours passés sont oubliés.
     */
    public static int allowance(UUID player, String what, long day, int max) {
        String suffix = "|" + day;
        DAILY.keySet().removeIf(k -> !k.endsWith(suffix));
        return Math.max(0, max - DAILY.getOrDefault(player + "|" + what + suffix, 0));
    }

    public static void spend(UUID player, String what, long day, int count) {
        DAILY.merge(player + "|" + what + "|" + day, count, Integer::sum);
    }

    public static boolean isWorldNpc(Ref<EntityStore> ref) {
        return ref != null && NPCS.containsKey(ref);
    }

    /** Déplace le point d'attache du PNJ. */
    public static void leash(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d to) {
        if (ref == null || !ref.isValid()) {
            return;
        }
        NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null) {
            Vector3d leash = npc.getLeashPoint();
            if (leash == null || leash.distanceSquared(to) > 0.25) {
                npc.setLeashPoint(new Vector3d(to));
            }
        }
    }

    public static void side(Ref<EntityStore> ref, String key, int team) {
        if (ref != null) {
            SIDES.put(ref, new Side(key, team));
        }
    }

    public static Side sideOf(Ref<EntityStore> ref) {
        return ref == null ? null : SIDES.get(ref);
    }

    public static void talker(Ref<EntityStore> ref, Talker talker) {
        if (ref != null) {
            TALKERS.put(ref, talker);
        }
    }

    public static void mortal(Ref<EntityStore> ref, Mortal mortal) {
        if (ref != null) {
            MORTALS.put(ref, mortal);
        }
    }

    /** Vrai si le PNJ est un PNJ du monde vivant à qui l'on parle. */
    public static boolean hasTalker(Ref<EntityStore> npc) {
        return npc != null && TALKERS.containsKey(npc);
    }

    /** Un joueur a utilisé le PNJ `npc` : rend vrai si c'est un PNJ du monde vivant (son dialogue s'ouvre). */
    public static boolean talk(World world, Store<EntityStore> store, Ref<EntityStore> user, PlayerRef player, Ref<EntityStore> npc) {
        Talker talker = npc == null ? null : TALKERS.get(npc);
        if (talker == null) {
            return false;
        }
        TALKING.put(player.getUuid(), npc);
        talker.talk(world, store, user, player, npc);
        return true;
    }

    /** PNJ du monde vivant à qui le joueur parle (ou a parlé en dernier), ou null. */
    public static Ref<EntityStore> talkingTo(UUID player) {
        Ref<EntityStore> ref = TALKING.get(player);
        return ref != null && ref.isValid() ? ref : null;
    }

    /** La mort d'un PNJ (système de mort) : rend vrai si elle concernait le monde vivant. */
    public static boolean died(World world, Ref<EntityStore> ref, Vector3d where, PlayerRef killer) {
        Mortal mortal = MORTALS.remove(ref);
        boolean ours = NPCS.containsKey(ref);
        if (mortal != null) {
            world.execute(() -> {
                mortal.died(world, ref, where, killer);
                forgetInModules(ref);
            });
        } else if (ours) {
            forgetInModules(ref);
        }
        if (ours) {
            NPCS.remove(ref);
            SIDES.remove(ref);
            TALKERS.remove(ref);
        }
        return ours || mortal != null;
    }

    // ---- Lieux et joueurs ----

    /** Positions des joueurs du monde. */
    public static List<Vector3d> players(World world, Store<EntityStore> store) {
        List<Vector3d> out = new ArrayList<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, p.getReference());
            if (at != null) {
                out.add(at);
            }
        }
        return out;
    }

    public static boolean near(List<Vector3d> players, double x, double z, double range) {
        for (Vector3d p : players) {
            double dx = p.x() - x;
            double dz = p.z() - z;
            if (dx * dx + dz * dz <= range * range) {
                return true;
            }
        }
        return false;
    }

    /** Joueurs à moins de `range` blocs (horizontaux) de (x, z). */
    public static List<PlayerRef> playersNear(World world, Store<EntityStore> store, double x, double z, double range) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, p.getReference());
            if (at != null && (at.x() - x) * (at.x() - x) + (at.z() - z) * (at.z() - z) <= range * range) {
                out.add(p);
            }
        }
        return out;
    }

    /** Joueur le plus proche de (x, z) à moins de `range`, ou null. */
    public static PlayerRef nearestPlayer(World world, Store<EntityStore> store, double x, double z, double range) {
        PlayerRef best = null;
        double bestD = range * range;
        for (PlayerRef p : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, p.getReference());
            if (at == null) {
                continue;
            }
            double d = (at.x() - x) * (at.x() - x) + (at.z() - z) * (at.z() - z);
            if (d <= bestD) {
                bestD = d;
                best = p;
            }
        }
        return best;
    }

    /** Message à tous les joueurs à moins de `range` blocs de (x, z) (tchat et notification). */
    public static void announce(World world, Store<EntityStore> store, double x, double z, double range, Message message,
                                NotificationStyle style) {
        for (PlayerRef p : playersNear(world, store, x, z, range)) {
            p.sendMessage(message);
            if (style != null) {
                NotificationUtil.sendNotification(p.getPacketHandler(), message, style);
            }
        }
    }

    /**
     * Point sûr pour les pieds près de (x, z) : jamais dans l'eau, la lave ou un bloc (Terrain.safeSpot), sinon null
     * (terrain pas chargé ou rien de sûr à moins de `radius` blocs).
     */
    public static Vector3d ground(World world, int x, int z, int radius) {
        int[] safe = new Terrain(world).safeSpot(x, z, radius);
        return safe == null ? null : new Vector3d(safe[0] + 0.5, safe[1], safe[2] + 0.5);
    }

    /** Distance horizontale entre deux villages. */
    public static double distance(Village a, Village b) {
        return Math.hypot(a.x() - b.x(), a.z() - b.z());
    }

    /** Village le plus proche de (x, z), tous peuples, à moins de `range` (ou null). */
    public static Village nearestVillage(World world, double x, double z, double range) {
        Village best = null;
        double bestD = range * range;
        for (Village v : Villages.registry(world).all()) {
            double d = v.horizontalDistanceSquared(x, z);
            if (d <= bestD) {
                bestD = d;
                best = v;
            }
        }
        return best;
    }

    // ---- Objets ----

    /** Retire jusqu'à `max` objets dont l'id passe `test` de l'inventaire du joueur ; rend le nombre retiré. */
    public static int take(Store<EntityStore> store, Ref<EntityStore> ref, java.util.function.Predicate<String> test, int max) {
        com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer inv =
                com.hypixel.hytale.server.core.inventory.InventoryComponent.getCombined(store, ref,
                        com.hypixel.hytale.server.core.inventory.InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        int left = max;
        for (short slot = 0; slot < inv.getCapacity() && left > 0; slot++) {
            com.hypixel.hytale.server.core.inventory.ItemStack stack = inv.getItemStack(slot);
            if (com.hypixel.hytale.server.core.inventory.ItemStack.isEmpty(stack) || !test.test(stack.getItemId())) {
                continue;
            }
            int n = Math.min(left, stack.getQuantity());
            inv.removeItemStackFromSlot(slot, n);
            left -= n;
        }
        return max - left;
    }

    /** Nombre d'objets dont l'id passe `test` dans l'inventaire du joueur. */
    public static int count(Store<EntityStore> store, Ref<EntityStore> ref, java.util.function.Predicate<String> test) {
        return com.hypixel.hytale.server.core.inventory.InventoryComponent.getCombined(store, ref,
                        com.hypixel.hytale.server.core.inventory.InventoryComponent.HOTBAR_STORAGE_BACKPACK)
                .countItemStacks(s -> !com.hypixel.hytale.server.core.inventory.ItemStack.isEmpty(s) && test.test(s.getItemId()));
    }

    /** Vrai pour la nourriture vanilla (offrandes de fête, dons aux réfugiés). */
    public static boolean isFood(String itemId) {
        return itemId != null && itemId.startsWith("Food_");
    }

    /** Oublie tous les PNJ (rechargement du mod) : les états sauvés les reposeront. */
    public static void clearAll() {
        Walk.clearAll();
        Links.clearAll();
        dev.nakasar.hytale.peuples.annex.LandPath.clear();
        Travellers.clearAll();
        Ambushes.clearAll();
        Relations.clearAll();
        Inns.clearAll();
        Hamlets.clearAll();
        HamletTrips.clearAll();
        Garrisons.clearAll();
        Sieges.clearAll();
        Camps.clearAll();
        Surroundings.clearAll();
        Hunts.clearAll();
        Calendar.clearAll();
        NPCS.clear();
        SIDES.clear();
        TALKERS.clear();
        MORTALS.clear();
        TALKING.clear();
        DAILY.clear();
    }
}
