package dev.nakasar.hytale.peuples.klops;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

/**
 * Le Klops errant (étape 7 ; GDD, Peuples de passage : « les Klops vont de village en village, troquent et portent des
 * colis »). Un seul Klops par monde : chaque jour de jeu, il s'arrête dans un autre village du mod (villages rangés par
 * id, jour modulo leur nombre), Kweebec ou Trork. Il ne se pose qu'à l'approche d'un joueur, à l'ouest du cœur, et
 * s'en va au changement de jour. Il n'est d'aucun peuple : neutre envers tous.
 *
 * <p>Son dialogue ({@value #DIALOGUE}) ouvre son troc ({@value #SHOP} : faveurs de tous les peuples contre rouages et
 * marchandises) et confie un colis ({@value #PARCEL}) pour un autre village : le joueur qui arrive à moins de
 * {@value #DELIVERY_REACH} blocs du cœur de ce village avec le colis le livre (drapeau {@code Klops_Parcel:<id>}) et
 * gagne {@value #COGS} rouages et {@value #REPUTATION} de réputation dans ce village.
 */
public final class Klops {

    public static final String ROLE = "Nakasar_Peuples_Klops_Wanderer";
    public static final String DIALOGUE = "Klops_Errant";
    public static final String SHOP = "Nakasar_Peuples_Klops";
    public static final String PARCEL = "Nakasar_Peuples_Klops_Parcel";
    public static final String COG = "Nakasar_Peuples_Favor_Klops";
    public static final String FLAG = "Klops_Parcel:";
    public static final String KEYS = "nakasar_peuples.klops.";

    public static final int RANGE = 48;
    public static final int DELIVERY_REACH = 12;
    public static final int COGS = 3;
    public static final int REPUTATION = 30;
    /** Poste du Klops, relatif au cœur (à l'ouest de la place, hors du tableau et du crieur). */
    private static final int SPOT_X = -4;
    private static final int SPOT_Z = 3;

    private static Ref<EntityStore> wanderer;
    private static String stopVillage;
    /** Jour où le Klops a été tué : il ne revient que le lendemain. */
    private static long killedDay = Long.MIN_VALUE;

    private Klops() {
    }

    /** Villages du monde, dans l'ordre de la tournée. */
    static List<Village> route(World world) {
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        villages.sort(Comparator.comparing(Village::id));
        return villages;
    }

    /** Village où le Klops s'arrête le jour `day`, ou null. */
    public static Village stop(World world, long day) {
        List<Village> villages = route(world);
        return villages.isEmpty() ? null : villages.get((int) Math.floorMod(day, (long) villages.size()));
    }

    public static synchronized boolean isWanderer(Ref<EntityStore> ref) {
        return ref != null && ref == wanderer;
    }

    /** Pas du Klops et des colis (thread du monde). */
    static synchronized void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        long day = GameClock.day(store);
        Village today = stop(world, day);
        if (wanderer != null && !wanderer.isValid() && today != null && today.id().equals(stopVillage)) {
            killedDay = day;
        }
        if (wanderer != null && (!wanderer.isValid() || today == null || !today.id().equals(stopVillage))) {
            despawn(store);
        }
        if (wanderer == null && today != null && killedDay != day && near(today, players)) {
            spawn(world, store, today);
        }
    }

    private static boolean near(Village village, List<Vector3d> players) {
        for (Vector3d p : players) {
            if (village.horizontalDistanceSquared(p.x(), p.z()) <= (double) RANGE * RANGE) {
                return true;
            }
        }
        return false;
    }

    private static void spawn(World world, Store<EntityStore> store, Village village) {
        int x = village.x() + SPOT_X;
        int z = village.z() + SPOT_Z;
        Terrain terrain = new Terrain(world);
        int[] safe = terrain.safeSpot(x, z, 6);
        int s = terrain.surface(x, z);
        Vector3d at = safe != null ? new Vector3d(safe[0] + 0.5, safe[1], safe[2] + 0.5)
                : new Vector3d(x + 0.5, s == Terrain.NONE ? village.y() : s + 1, z + 0.5);
        var spawned = NPCPlugin.get().spawnNPC(store, ROLE, null, at, new Rotation3f(0f, 0f, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de poser le Klops au village %s", village.name());
            return;
        }
        wanderer = spawned.first();
        stopVillage = village.id();
        store.ensureAndGetComponent(wanderer, EntityStore.REGISTRY.getNonSerializedComponentType());
        NPCEntity npc = store.getComponent(wanderer, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(new Vector3d(at));
        }
    }

    private static void despawn(Store<EntityStore> store) {
        if (wanderer != null && wanderer.isValid()) {
            store.removeEntity(wanderer, RemoveReason.REMOVE);
        }
        wanderer = null;
        stopVillage = null;
    }

    public static synchronized void clearAll() {
        wanderer = null;
        stopVillage = null;
    }

    // ---- Colis ----

    /** Village où le joueur doit livrer son colis, ou null. */
    public static String parcelDestination(PeuplesPlayer data) {
        if (data == null) {
            return null;
        }
        for (String flag : data.flags()) {
            if (flag.startsWith(FLAG)) {
                return flag.substring(FLAG.length());
            }
        }
        return null;
    }

    /**
     * Confie un colis au joueur pour un village autre que `from` (tiré au hasard). Rend faux (avec un message) s'il en
     * porte déjà un, s'il n'y a pas d'autre village ou si l'inventaire est plein.
     */
    public static boolean giveParcel(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village from) {
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        String current = parcelDestination(data);
        Village pending = current == null ? null : Villages.registry(world).byId(current);
        if (pending != null) {
            dev.nakasar.hytale.peuples.dialogue.DialogueSpeech.say(player, Message.translation(KEYS + "parcelAlready").param("village", pending.name()));
            return false;
        }
        List<Village> others = new ArrayList<>(route(world));
        others.removeIf(v -> from != null && v.id().equals(from.id()));
        if (others.isEmpty()) {
            dev.nakasar.hytale.peuples.dialogue.DialogueSpeech.say(player, Message.translation(KEYS + "parcelNowhere"));
            return false;
        }
        Village to = others.get(new Random().nextInt(others.size()));
        CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        ItemStack stack = new ItemStack(PARCEL, 1);
        if (!inventory.canAddItemStack(stack)) {
            dev.nakasar.hytale.peuples.dialogue.DialogueSpeech.say(player, Message.translation("nakasar_peuples.dialogue.inventoryFull"));
            return false;
        }
        inventory.addItemStack(stack);
        if (current != null) {
            data.setFlag(FLAG + current, false);
        }
        data.setFlag(FLAG + to.id(), true);
        dev.nakasar.hytale.peuples.dialogue.DialogueSpeech.say(player, describe(store, ref, to, KEYS + "parcelGiven"));
        return true;
    }

    /** « Pour {village} ({people}), à {distance} blocs, direction {direction}. » */
    public static Message describe(Store<EntityStore> store, Ref<EntityStore> ref, Village to, String key) {
        Vector3d at = Requests.position(store, ref);
        double dx = at == null ? 0 : to.x() - at.x();
        double dz = at == null ? 0 : to.z() - at.z();
        return Message.translation(key).param("village", to.name()).param("people", Message.translation(to.people().nameKey()))
                .param("distance", (int) Math.round(Math.hypot(dx, dz)))
                .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(dx, dz)));
    }

    /** Livraison : le joueur porte le colis près du cœur de son village de destination. */
    static void deliveries(World world, Store<EntityStore> store) {
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            PeuplesPlayer data = ref == null || !ref.isValid() ? null : PeuplesPlayer.get(store, ref);
            String id = parcelDestination(data);
            Village to = id == null ? null : Villages.registry(world).byId(id);
            if (id != null && to == null) {
                data.setFlag(FLAG + id, false); // village dissous : le colis n'a plus de destinataire
                continue;
            }
            Vector3d at = to == null ? null : Requests.position(store, ref);
            if (at == null || to.horizontalDistanceSquared(at.x(), at.z()) > (double) DELIVERY_REACH * DELIVERY_REACH) {
                continue;
            }
            CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
            if (!inventory.removeItemStack(new ItemStack(PARCEL, 1), true, true).succeeded()) {
                continue;
            }
            data.setFlag(FLAG + id, false);
            Requests.give(store, ref, new ItemStack(COG, COGS));
            Message m = Message.translation(KEYS + "delivered").param("village", to.name()).param("cogs", COGS);
            player.sendMessage(m);
            NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Success);
            Reputations.change(world, store, ref, player, to, REPUTATION, KEYS + "reason");
        }
    }

    /** Où le Klops est aujourd'hui et où il sera demain (récit, pour la commande). */
    public static Message route(World world, Store<EntityStore> store, Ref<EntityStore> ref) {
        return route(world, store, "route", "routeNone");
    }

    /** Où le Klops est aujourd'hui et où il sera demain, dit par le Klops lui-même (fenêtre de dialogue). */
    public static Message routeSaid(World world, Store<EntityStore> store) {
        return route(world, store, "routeSaid", "routeNoneSaid");
    }

    private static Message route(World world, Store<EntityStore> store, String key, String noneKey) {
        long day = GameClock.day(store);
        Village today = stop(world, day);
        Village tomorrow = stop(world, day + 1);
        if (today == null) {
            return Message.translation(KEYS + noneKey);
        }
        return Message.translation(KEYS + key).param("today", today.name()).param("tomorrow", tomorrow.name());
    }
}
