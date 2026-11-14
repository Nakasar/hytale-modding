package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.block.components.ItemContainerBlock;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les demandes du tableau (GDD, section Les demandes du tableau ; étape 3 du plan) : tirage du matin, prise, dépôt,
 * avancement, récompense, abandon et fin. Tout se passe sur le thread du monde.
 *
 * <p>Règles du GDD : 3 demandes au tableau, tirées chaque matin parmi les modèles du peuple et du palier
 * ({@link RequestTemplate}) ; quand l'une est remplie, sa place reçoit une nouvelle demande. Une demande remplie compte
 * pour le joueur (faveurs, réputation de village et de peuple depuis l'étape 4) et pour le village (essor), mais le village ne gagne l'essor
 * qu'une fois : les autres joueurs qui l'avaient prise peuvent encore la finir jusqu'à son terme, pour eux seuls.
 */
public final class Requests {

    public static final int SLOTS = 3;
    /** Distance au dépôt (blocs) à laquelle ce qu'on y pose est crédité tout seul aux demandes du joueur. */
    public static final int DEPOSIT_RANGE = 6;
    /** Le captif est rendu quand il arrive à cette distance du cœur. */
    public static final int ESCORT_HOME = 14;

    public static final String KEYS = "nakasar_peuples.request.";

    private Requests() {
    }

    // ---- Tableau du village ----

    /** Tire les demandes du jour si le matin est passé depuis le dernier tirage ; rend vrai si le tableau a changé. */
    public static boolean refresh(Store<EntityStore> store, Village village) {
        long day = GameClock.day(store);
        if (village.requestDay() == day && village.requests().length == SLOTS) {
            return false;
        }
        Random random = new Random(village.id().hashCode() * 31L + day);
        VillageRequest[] drawn = new VillageRequest[SLOTS];
        List<RequestType> used = new ArrayList<>();
        List<String> usedTemplates = new ArrayList<>();
        for (int i = 0; i < SLOTS; i++) {
            RequestTemplate t = pick(village, random, used, usedTemplates);
            if (t != null) {
                drawn[i] = new VillageRequest(UUID.randomUUID().toString(), t.getId(), day);
                used.add(t.type());
                usedTemplates.add(t.getId());
            }
        }
        Villages.setRequests(village, drawn, day);
        return true;
    }

    /** Remplace la demande de la case `slot` par une nouvelle (demande remplie, ou tirage forcé). */
    public static void redraw(Store<EntityStore> store, Village village, int slot) {
        VillageRequest[] current = village.requests();
        List<RequestType> used = new ArrayList<>();
        List<String> usedTemplates = new ArrayList<>();
        for (int i = 0; i < current.length; i++) {
            if (i != slot && current[i] != null && current[i].template() != null) {
                used.add(current[i].template().type());
                usedTemplates.add(current[i].templateId());
            }
        }
        if (slot >= 0 && slot < current.length && current[slot] != null) {
            // On évite de retirer la même demande.
            usedTemplates.add(current[slot].templateId());
        }
        RequestTemplate t = pick(village, ThreadLocalRandom.current(), used, usedTemplates);
        Villages.setRequest(village, slot, t == null ? null : new VillageRequest(UUID.randomUUID().toString(), t.getId(), GameClock.day(store)));
    }

    /** Pose le modèle `template` dans la case `slot` (commande d'essai). */
    public static void force(Store<EntityStore> store, Village village, int slot, RequestTemplate template) {
        refresh(store, village);
        Villages.setRequest(village, slot, new VillageRequest(UUID.randomUUID().toString(), template.getId(), GameClock.day(store)));
    }

    /**
     * Un modèle au poids parmi ceux du peuple et du palier : d'abord un type pas encore au tableau, sinon un modèle
     * pas encore au tableau, sinon n'importe lequel.
     */
    private static RequestTemplate pick(Village village, Random random, List<RequestType> usedTypes, List<String> usedTemplates) {
        List<RequestTemplate> all = RequestTemplate.forVillage(village.people().id(), village.tier());
        List<RequestTemplate> pool = new ArrayList<>();
        for (RequestTemplate t : all) {
            if (!usedTypes.contains(t.type()) && !usedTemplates.contains(t.getId())) {
                pool.add(t);
            }
        }
        if (pool.isEmpty()) {
            for (RequestTemplate t : all) {
                if (!usedTemplates.contains(t.getId())) {
                    pool.add(t);
                }
            }
        }
        if (pool.isEmpty()) {
            pool = all;
        }
        int total = 0;
        for (RequestTemplate t : pool) {
            total += t.weight();
        }
        if (total <= 0) {
            return null;
        }
        int roll = random.nextInt(total);
        for (RequestTemplate t : pool) {
            roll -= t.weight();
            if (roll < 0) {
                return t;
            }
        }
        return pool.get(pool.size() - 1);
    }

    /** Case (0 à 2) de la demande `requestId` au tableau du village, ou -1 si elle n'y est plus. */
    public static int slotOf(Village village, String requestId) {
        VillageRequest[] requests = village.requests();
        for (int i = 0; i < requests.length; i++) {
            if (requests[i] != null && requests[i].id().equals(requestId)) {
                return i;
            }
        }
        return -1;
    }

    // ---- Ce que voit un joueur ----

    /**
     * Vrai si le joueur peut prendre la demande de la case `slot` (GDD, Par rang : l'étranger n'a droit qu'à une
     * demande simple, les trois s'ouvrent au rang toléré ; un honni peut encore se racheter par la première).
     */
    public static boolean slotOpen(Store<EntityStore> store, Ref<EntityStore> ref, Village village, int slot) {
        return slot == 0 || Reputations.rank(store, ref, village).atLeast(Rank.TOLERE);
    }

    /** État d'une demande du tableau pour un joueur. */
    public enum Status { AVAILABLE, TAKEN, DONE, MISSING }

    public static Status status(PeuplesPlayer player, VillageRequest request) {
        if (request == null || request.template() == null) {
            return Status.MISSING;
        }
        if (player != null && player.request(request.id()) != null) {
            return Status.TAKEN;
        }
        if (player != null && player.hasDone(request.id())) {
            return Status.DONE;
        }
        return Status.AVAILABLE;
    }

    /** Titre d'une demande ({count} et {item} pour récolte et fabrication). */
    public static Message title(RequestTemplate t) {
        Message m = Message.translation(t.titleKey()).param("needed", t.needed());
        if (t.itemId() != null) {
            m = m.param("item", VillageBoard.itemName(t.itemId()));
        }
        return m;
    }

    /** Récompense d'une demande : essor du village et faveurs du peuple. */
    public static Message reward(RequestTemplate t, Village village) {
        return Message.translation(KEYS + "reward").param("essor", t.essor()).param("favors", t.favors())
                .param("favor", VillageBoard.itemName(village.people().favorItem())).param("reputation", t.reputation());
    }

    /** Ligne de tâche d'une demande prise, vue depuis `from`, avec la distance et la direction de `target`. */
    public static Message task(PlayerRequest r, RequestTemplate t, Vector3d from, int[] target) {
        Message m = Message.translation(t.taskKey()).param("count", Math.min(r.progress(), r.needed())).param("needed", r.needed());
        if (t.itemId() != null) {
            m = m.param("item", VillageBoard.itemName(t.itemId()));
        }
        if (from != null && target != null) {
            double dx = target[0] + 0.5 - from.x();
            double dz = target[2] + 0.5 - from.z();
            m = m.param("distance", (int) Math.round(Math.sqrt(dx * dx + dz * dz)))
                    .param("direction", Message.translation(Villages.MESSAGES + "dir." + direction(dx, dz)));
        } else {
            m = m.param("distance", "?").param("direction", "?");
        }
        return m;
    }

    /**
     * Où mène la demande : le lieu tiré (repaire, guetteur, captif), sauf pour une escorte dont le captif suit déjà le
     * joueur (le cœur du village), et le cœur du village pour une défense ou un dépôt.
     */
    public static int[] target(PlayerRef player, PlayerRequest r, RequestTemplate t, Village village) {
        if (t.type().hasSite()) {
            if (t.type() == RequestType.ESCORT
                    && RequestSpawns.first(RequestSpawns.key(player.getUuid(), r.id()), RequestSpawns.Kind.CAPTIVE) != null) {
                return new int[] {village.x(), village.y(), village.z()};
            }
            return r.site();
        }
        return t.type().usesDeposit() ? village.deposit() : new int[] {village.x(), village.y(), village.z()};
    }

    /** Point cardinal de (dx, dz) : nord = -Z, est = +X. */
    public static String direction(double dx, double dz) {
        String[] dirs = {"e", "se", "s", "sw", "w", "nw", "n", "ne"};
        double angle = Math.atan2(dz, dx);
        int i = (int) Math.floorMod(Math.round(angle / (Math.PI / 4)), 8L);
        return dirs[i];
    }

    /** Envoie (ou met à jour) le suivi à l'écran de la demande `r`. */
    public static void showHud(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PlayerRequest r, boolean force) {
        RequestTemplate t = r.template();
        Village village = Villages.registry(world).byId(r.villageId());
        if (t == null || village == null) {
            return;
        }
        Vector3d at = position(store, ref);
        Message description = Message.translation(KEYS + "hudDescription").param("village", village.name())
                .param("reward", reward(t, village));
        Message task = task(r, t, at, target(player, r, t, village));
        if (t.type() == RequestType.DEFENSE && !GameClock.isNight(store)) {
            task = Message.translation(KEYS + "defense.waitNight").param("village", village.name());
        }
        RequestHud.track(player, r.hud(), title(t), description, task, r.progress(), r.needed(), force);
    }

    public static Vector3d position(Store<EntityStore> store, Ref<EntityStore> ref) {
        TransformComponent transform = ref == null || !ref.isValid() ? null : store.getComponent(ref, TransformComponent.getComponentType());
        return transform == null ? null : new Vector3d(transform.getPosition());
    }

    // ---- Actions du joueur ----

    /**
     * Le joueur prend la demande de la case `slot` (0 à 2) du village : il doit être dans le village, ne pas l'avoir
     * déjà prise ni remplie. Une livraison lui donne la missive. Rend vrai si la demande est prise.
     */
    public static boolean take(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, int slot) {
        refresh(store, village);
        VillageRequest[] board = village.requests();
        if (slot < 0 || slot >= board.length || board[slot] == null || board[slot].template() == null) {
            player.sendMessage(Message.translation(KEYS + "noSuchSlot").param("slot", slot + 1));
            return false;
        }
        VillageRequest request = board[slot];
        RequestTemplate t = request.template();
        if (!slotOpen(store, ref, village, slot)) {
            player.sendMessage(Message.translation(KEYS + "slotLocked").param("slot", slot + 1)
                    .param("rank", Message.translation(Rank.TOLERE.nameKey())));
            return false;
        }
        PeuplesPlayer state = PeuplesPlayer.ensure(store, ref);
        switch (status(state, request)) {
            case TAKEN -> {
                player.sendMessage(Message.translation(KEYS + "alreadyTaken").param("title", title(t)));
                return false;
            }
            case DONE -> {
                player.sendMessage(Message.translation(KEYS + "alreadyDone").param("title", title(t)));
                return false;
            }
            default -> {
            }
        }
        if (t.type() == RequestType.DELIVERY) {
            ItemStack missive = new ItemStack(village.people().missiveItem(), 1);
            CombinedItemContainer inventory = inventory(store, ref);
            if (!inventory.canAddItemStack(missive)) {
                player.sendMessage(Message.translation("nakasar_peuples.dialogue.inventoryFull"));
                return false;
            }
            inventory.addItemStack(missive);
        }
        PlayerRequest taken = new PlayerRequest(request.id(), village.id(), t.getId(), GameClock.expiryFromNow(store));
        if (t.type().hasSite()) {
            double angle = ThreadLocalRandom.current().nextDouble(0, Math.PI * 2);
            double distance = ThreadLocalRandom.current().nextDouble(t.minDistance(), t.maxDistance() + 1e-3);
            taken.setSite(village.x() + (int) Math.round(Math.cos(angle) * distance), PlayerRequest.NO_Y,
                    village.z() + (int) Math.round(Math.sin(angle) * distance));
        }
        state.addRequest(taken);
        player.sendMessage(Message.translation(KEYS + "taken").param("title", title(t)).param("village", village.name()));
        showHud(world, store, ref, player, taken, true);
        // Ce qui est déjà au dépôt compte tout de suite si le joueur est à côté.
        if (t.type().usesDeposit() && nearDeposit(store, ref, village)) {
            pullDeposit(world, store, ref, player, village, taken);
        }
        return true;
    }

    /** Le joueur abandonne sa demande `requestId` ; ses PNJ disparaissent, la missive est reprise. */
    public static boolean abandon(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String requestId) {
        PeuplesPlayer state = PeuplesPlayer.get(store, ref);
        PlayerRequest r = state == null ? null : state.request(requestId);
        if (r == null) {
            return false;
        }
        end(world, store, ref, player, state, r);
        RequestTemplate t = r.template();
        player.sendMessage(Message.translation(KEYS + "abandoned").param("title", t == null ? Message.raw(r.templateId()) : title(t)));
        return true;
    }

    /**
     * Rend au village les objets des demandes de récolte et de fabrication du joueur : d'abord ce qui est dans le
     * dépôt, puis ce qu'il porte. Rend le nombre d'objets crédités.
     */
    public static int turnIn(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village) {
        PeuplesPlayer state = PeuplesPlayer.get(store, ref);
        if (state == null) {
            return 0;
        }
        int credited = 0;
        boolean any = false;
        for (PlayerRequest r : new ArrayList<>(state.requests())) {
            RequestTemplate t = r.template();
            if (t == null || !r.villageId().equals(village.id()) || !t.type().usesDeposit()) {
                continue;
            }
            any = true;
            credited += pullDeposit(world, store, ref, player, village, r);
            if (state.request(r.id()) != null && !r.complete()) {
                int missing = r.needed() - r.progress();
                int taken = take(inventory(store, ref), t.itemId(), missing);
                if (taken > 0) {
                    credited += taken;
                    advance(world, store, ref, player, state, r, taken);
                }
            }
        }
        if (!any) {
            player.sendMessage(Message.translation(KEYS + "nothingToTurnIn"));
        } else if (credited == 0) {
            player.sendMessage(Message.translation(KEYS + "turnInNothing"));
        }
        return credited;
    }

    /** Vrai si le joueur est à moins de {@value #DEPOSIT_RANGE} blocs du dépôt du village. */
    public static boolean nearDeposit(Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        Vector3d at = position(store, ref);
        if (at == null) {
            return false;
        }
        int[] d = village.deposit();
        double dx = d[0] + 0.5 - at.x();
        double dy = d[1] + 0.5 - at.y();
        double dz = d[2] + 0.5 - at.z();
        return dx * dx + dy * dy + dz * dz <= DEPOSIT_RANGE * DEPOSIT_RANGE;
    }

    /** Retire du dépôt ce qui manque à la demande `r` (récolte, fabrication) et le crédite ; rend le nombre retiré. */
    public static int pullDeposit(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, PlayerRequest r) {
        RequestTemplate t = r.template();
        if (t == null || !t.type().usesDeposit() || r.complete()) {
            return 0;
        }
        ItemContainer chest = depositContainer(world, village);
        if (chest == null) {
            return 0;
        }
        int taken = take(chest, t.itemId(), r.needed() - r.progress());
        if (taken > 0) {
            PeuplesPlayer state = PeuplesPlayer.ensure(store, ref);
            advance(world, store, ref, player, state, r, taken);
        }
        return taken;
    }

    /** Coffre du dépôt du village, ou null s'il manque ou que sa section n'est pas chargée. */
    public static ItemContainer depositContainer(World world, Village village) {
        int[] d = village.deposit();
        if (!village.people().depositBlock().equals(Blocks.name(world.getChunkStore(), d[0], d[1], d[2]))) {
            return null;
        }
        ItemContainerBlock block = BlockModule.getComponent(ItemContainerBlock.getComponentType(), world, d[0], d[1], d[2]);
        return block == null ? null : block.getItemContainer();
    }

    /** Retire jusqu'à `max` objets `itemId` du conteneur ; rend le nombre retiré. */
    public static int take(ItemContainer container, String itemId, int max) {
        if (container == null || itemId == null || max <= 0) {
            return 0;
        }
        int available = container.countItemStacks(s -> !ItemStack.isEmpty(s) && itemId.equals(s.getItemId()));
        int count = Math.min(available, max);
        if (count <= 0) {
            return 0;
        }
        // Retrait pile par pile : les objets à durabilité (outils) ne se fusionnent pas avec un ItemStack neuf.
        int left = count;
        for (short slot = 0; slot < container.getCapacity() && left > 0; slot++) {
            ItemStack stack = container.getItemStack(slot);
            if (ItemStack.isEmpty(stack) || !itemId.equals(stack.getItemId())) {
                continue;
            }
            int n = Math.min(left, stack.getQuantity());
            container.internal_removeItemStack(slot, n);
            left -= n;
        }
        return count - left;
    }

    static CombinedItemContainer inventory(Store<EntityStore> store, Ref<EntityStore> ref) {
        return InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
    }

    // ---- Avancement et fin ----

    /** Ajoute `amount` à l'avancement de `r` ; la demande se remplit quand il atteint le besoin. */
    public static void advance(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer state,
                               PlayerRequest r, int amount) {
        if (amount <= 0 || state.request(r.id()) == null) {
            return;
        }
        r.setProgress(Math.min(r.needed(), r.progress() + amount));
        RequestTemplate t = r.template();
        if (r.complete()) {
            fulfil(world, store, ref, player, state, r);
            return;
        }
        if (t != null) {
            NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(KEYS + "progress")
                    .param("title", title(t)).param("count", r.progress()).param("needed", r.needed()), NotificationStyle.Default);
        }
        showHud(world, store, ref, player, r, false);
    }

    /**
     * La demande est remplie : faveurs au joueur (au sol s'il n'a plus de place), essor au village s'il ne l'a pas déjà
     * reçu pour cette demande, nouvelle demande à sa place au tableau.
     */
    public static void fulfil(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer state, PlayerRequest r) {
        RequestTemplate t = r.template();
        Village village = Villages.registry(world).byId(r.villageId());
        end(world, store, ref, player, state, r);
        state.markDone(r.id(), r.villageId());
        if (t == null || village == null) {
            return;
        }
        if (t.favors() > 0) {
            give(store, ref, new ItemStack(village.people().favorItem(), t.favors()));
        }
        // Réputation : pour chaque joueur qui remplit la demande, même si le village a déjà reçu l'essor (GDD).
        Reputations.change(world, store, ref, player, village, t.reputation(), KEYS + "reputationReason");
        int slot = slotOf(village, r.id());
        int gained = 0;
        if (slot >= 0) {
            gained = Villages.addEssor(village, t.essor());
            redraw(store, village, slot);
        }
        Message done = Message.translation(gained > 0 ? KEYS + "fulfilled" : KEYS + "fulfilledNoEssor")
                .param("title", title(t)).param("village", village.name()).param("essor", gained)
                .param("favors", t.favors()).param("favor", VillageBoard.itemName(village.people().favorItem()));
        player.sendMessage(done);
        NotificationUtil.sendNotification(player.getPacketHandler(), done, NotificationStyle.Success);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : demande %s remplie par %s au village %s (+%d essor)",
                t.getId(), player.getUsername(), village.name(), gained);
    }

    /** La demande a échoué (captif mort, nuit perdue) : elle se termine, le joueur pourra la reprendre au tableau. */
    public static void fail(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer state,
                            PlayerRequest r, String reasonKey) {
        RequestTemplate t = r.template();
        end(world, store, ref, player, state, r);
        Message m = Message.translation(reasonKey).param("title", t == null ? Message.raw(r.templateId()) : title(t));
        player.sendMessage(m);
        NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Warning);
    }

    /** Termine la demande : retirée du joueur, suivi retiré de l'écran, PNJ et missive retirés. */
    static void end(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer state, PlayerRequest r) {
        state.removeRequest(r);
        RequestHud.untrack(player, r.hud());
        RequestSpawns.remove(store, RequestSpawns.key(player.getUuid(), r.id()), null);
        RequestTemplate t = r.template();
        Village village = Villages.registry(world).byId(r.villageId());
        if (t != null && t.type() == RequestType.DELIVERY && village != null) {
            take(inventory(store, ref), village.people().missiveItem(), 1);
        }
    }

    /** Donne `stack` au joueur, ou le pose à ses pieds s'il n'a plus de place. */
    public static void give(Store<EntityStore> store, Ref<EntityStore> ref, ItemStack stack) {
        CombinedItemContainer inventory = inventory(store, ref);
        if (inventory.canAddItemStack(stack)) {
            inventory.addItemStack(stack);
            return;
        }
        Vector3d at = position(store, ref);
        if (at == null) {
            return;
        }
        for (Holder<EntityStore> drop : ItemComponent.generateItemDrops(store, List.of(stack), at.add(0, 0.5, 0), new Rotation3f())) {
            store.addEntity(drop, AddReason.SPAWN);
        }
    }
}
