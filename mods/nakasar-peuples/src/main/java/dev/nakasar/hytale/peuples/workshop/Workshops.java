package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.PlayerRequest;
import dev.nakasar.hytale.peuples.request.RequestTemplate;
import dev.nakasar.hytale.peuples.request.RequestType;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.request.VillageRequest;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les bâtiments de métier d'un village (GDD des bâtiments de métier, étape 1) : quels bâtiments sont ouverts, leurs
 * commandes du jour (tirées à {@value GameClock#MORNING} h comme celles du tableau, 2 par bâtiment, 3 au niveau III),
 * le savoir-faire qu'elles donnent, et le panneau posé devant chaque bâtiment. Tout se passe sur le thread du monde.
 *
 * <p>Les commandes sont des {@link RequestTemplate} ordinaires (mêmes types, même suivi, même dépôt) marqués
 * {@code Workshop} : seule leur fin diffère ({@link #fulfilled}), le savoir-faire allant au bâtiment en plus de l'essor
 * au village, une fois par commande comme l'essor d'une demande du tableau.
 */
public final class Workshops {

    public static final String KEYS = "nakasar_peuples.workshop.";
    /** Niveau le plus haut d'un bâtiment. */
    public static final int MAX_LEVEL = 3;
    /** Demandes et commandes qu'un joueur peut suivre à la fois (hors étapes de chaîne), tous tableaux confondus. */
    public static final int MAX_FOLLOWED = 3;
    /** Rang à partir duquel on prend une commande de bâtiment. */
    public static final Rank TAKE_RANK = Rank.TOLERE;
    /** Rang qu'il faut pour choisir ou changer la spécialité d'un bâtiment (étape 3 ; Kevin : « Ami suffira »). */
    public static final Rank SPECIALTY_RANK = Rank.AMI;
    /** Niveau où se choisit la spécialité. */
    public static final int SPECIALTY_LEVEL = 2;
    /** Jours de jeu entre deux reconversions d'un bâtiment. */
    public static final int RECONVERT_DAYS = 7;

    private Workshops() {
    }

    /** Savoir-faire qu'il faut au niveau `level` pour passer au suivant (0 au niveau III). */
    public static int threshold(int level) {
        return switch (level) {
            case 1 -> 200;
            case 2 -> 400;
            default -> 0;
        };
    }

    /** Commandes du jour au niveau `level`. */
    public static int slots(int level) {
        return level >= 3 ? 3 : 2;
    }

    /** Palier du village qu'il faut pour que le bâtiment atteigne le niveau `level` (II au village, III au bourg). */
    public static int tierFor(int level) {
        return level <= 1 ? 0 : level;
    }

    /** Bâtiments de métier du village (debout ou non), d'après son plan. */
    public static List<Workshop> all(Village village) {
        return Workshop.forLayout(village.layout());
    }

    /**
     * Le bâtiment est ouvert : son bâtiment du plan est debout et son métier existe au palier du village (le villageois
     * peut être absent jusqu'au matin, le panneau reste ouvert).
     */
    public static boolean open(Village village, Workshop w) {
        if (!village.isStanding(w.building())) {
            return false;
        }
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return false;
        }
        for (VillageLayout.Job job : layout.jobs()) {
            if (job.id().equals(w.job())) {
                return job.tier() <= village.tier();
            }
        }
        return false;
    }

    /** Bâtiments ouverts du village. */
    public static List<Workshop> opened(Village village) {
        List<Workshop> out = new ArrayList<>();
        for (Workshop w : all(village)) {
            if (open(village, w)) {
                out.add(w);
            }
        }
        return out;
    }

    /** Métier du plan qui tient le bâtiment, ou null. */
    public static VillageLayout.Job job(Village village, Workshop w) {
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return null;
        }
        for (VillageLayout.Job job : layout.jobs()) {
            if (job.id().equals(w.job())) {
                return job;
            }
        }
        return null;
    }

    // ---- Le pas d'un village : tirage du matin et panneaux ----

    /** Tire les commandes du jour des bâtiments ouverts et pose leurs panneaux manquants (chaque seconde, RequestSystem). */
    public static void refresh(World world, Store<EntityStore> store, Village village) {
        if (village.layout() == null) {
            return;
        }
        long now = GameClock.seconds(store);
        for (Workshop w : opened(village)) {
            WorkshopState state = village.workshop(w.getId());
            if (state.upgrading() && now >= state.upgradeEnd()) {
                finishUpgrade(world, store, village, w, state);
            }
            draw(store, village, w, state, false);
            if (!state.hasBoard()) {
                placeBoard(world, village, w, state);
            } else if (!RAISED.contains(village.id() + "/" + w.getId()) && raiseBoard(world, village, state)) {
                RAISED.add(village.id() + "/" + w.getId());
            }
        }
    }

    /** Tire les commandes du jour si le matin est passé (ou si `force`). Rend vrai si le panneau a changé. */
    public static boolean draw(Store<EntityStore> store, Village village, Workshop w, WorkshopState state, boolean force) {
        long day = GameClock.day(store);
        int slots = slots(state.level());
        if (!force && state.requestDay() == day && state.requests().length == slots) {
            return false;
        }
        Random random = new Random(village.id().hashCode() * 31L + w.getId().hashCode() * 17L + day);
        VillageRequest[] drawn = new VillageRequest[slots];
        List<String> used = new ArrayList<>();
        for (int i = 0; i < slots; i++) {
            RequestTemplate t = pick(state, w, random, used);
            if (t != null) {
                drawn[i] = new VillageRequest(UUID.randomUUID().toString(), t.getId(), day);
                used.add(t.getId());
            }
        }
        state.setRequests(drawn, day);
        return true;
    }

    /** Remplace la commande de la case `slot` (remplie). */
    public static void redraw(Store<EntityStore> store, Village village, Workshop w, WorkshopState state, int slot) {
        List<String> used = new ArrayList<>();
        for (VillageRequest r : state.requests()) {
            if (r != null) {
                used.add(r.templateId());
            }
        }
        RequestTemplate t = pick(state, w, ThreadLocalRandom.current(), used);
        state.setRequest(slot, t == null ? null : new VillageRequest(UUID.randomUUID().toString(), t.getId(), GameClock.day(store)));
    }

    /** Une commande au poids, d'abord parmi celles pas encore au panneau. */
    private static RequestTemplate pick(WorkshopState state, Workshop w, Random random, List<String> used) {
        List<RequestTemplate> all = RequestTemplate.forWorkshop(w.getId(), state.level(), state.specialty());
        List<RequestTemplate> pool = new ArrayList<>();
        for (RequestTemplate t : all) {
            if (!used.contains(t.getId())) {
                pool.add(t);
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

    /** Panneaux déjà vérifiés par {@link #raiseBoard} depuis le chargement du mod. */
    private static final java.util.Set<String> RAISED = java.util.concurrent.ConcurrentHashMap.newKeySet();
    /** Blocs pleins (racines, mousse, souches) que le panneau peut enjamber au-dessus du sol. */
    private static final int STAND_CLIMB = 3;

    /**
     * Pose le panneau du bâtiment à la place du plan, si la case (ou une voisine le long de la face) est libre ou ne
     * porte que de la végétation non pleine : on n'écrase jamais un bloc plein. Kevin (2026-11-15) : posé au niveau de
     * la terre, le panneau s'enfonçait sous les racines et la mousse des villages kweebecs ; il se pose maintenant sur
     * le premier bloc plein du dessus ({@link #standY}). Sans effet tant que la zone n'est pas chargée.
     */
    static void placeBoard(World world, Village village, Workshop w, WorkshopState state) {
        int[] spot = w.board();
        if (spot == null) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        int yaw = spot.length > 2 ? spot[2] : 0;
        // Décalages le long de la face : est-ouest pour une face nord ou sud (lacets 0, 2), nord-sud sinon.
        boolean alongX = yaw == 0 || yaw == 2;
        Terrain terrain = new Terrain(world);
        for (int d : new int[] {0, 1, -1}) {
            int x = village.x() + spot[0] + (alongX ? d : 0);
            int z = village.z() + spot[1] + (alongX ? 0 : d);
            int y = standY(chunks, terrain, x, z);
            if (y == UNLOADED_SPOT) {
                return;
            }
            if (y == Terrain.NONE) {
                continue;
            }
            if (Blocks.set(chunks, x, y, z, village.people().boardBlock(), yaw)) {
                state.setBoard(x, y, z);
                PeuplesPlugin.get().getLogger().atInfo().log("Peuples : panneau du bâtiment %s posé en %d %d %d (%s)",
                        w.getId(), x, y, z, village.name());
                return;
            }
        }
    }

    private static final int UNLOADED_SPOT = Integer.MIN_VALUE + 1;

    /**
     * Hauteur où poser le panneau dans la colonne (x, z) : au-dessus du sol et des blocs pleins posés dessus (racines,
     * mousse, au plus {@value #STAND_CLIMB}), sur une case vide ou de végétation non pleine. {@link Terrain#NONE} si la
     * colonne ne convient pas (tronc, mur), {@link #UNLOADED_SPOT} si elle n'est pas chargée.
     */
    static int standY(ChunkStore chunks, Terrain terrain, int x, int z) {
        int ground = terrain.surface(x, z);
        if (ground == Terrain.NONE) {
            return UNLOADED_SPOT;
        }
        int y = ground + 1;
        for (int climb = 0; climb <= STAND_CLIMB; climb++, y++) {
            if (Blocks.id(chunks, x, y, z) == Blocks.UNLOADED) {
                return UNLOADED_SPOT;
            }
            if (Blocks.solid(chunks, x, y, z)) {
                continue;
            }
            String current = Blocks.name(chunks, x, y, z);
            return current == null || Terrain.isVegetation(current) ? y : Terrain.NONE;
        }
        return Terrain.NONE;
    }

    /**
     * Remonte un panneau déjà posé trop bas (avant le correctif du 2026-11-15, il a pris la place d'une racine ou d'un
     * bloc de mousse) : tant qu'au moins deux de ses voisins ont un bloc plein à son niveau, on rebouche sa case avec le
     * bloc d'un voisin et le panneau monte d'un cran (au plus {@value #STAND_CLIMB}). Rend faux tant que la zone
     * n'est pas chargée (à revoir), vrai une fois vérifié.
     */
    static boolean raiseBoard(World world, Village village, WorkshopState state) {
        int[] at = state.board();
        ChunkStore chunks = world.getChunkStore();
        String board = village.people().boardBlock();
        if (Blocks.id(chunks, at[0], at[1], at[2]) == Blocks.UNLOADED) {
            return false;
        }
        if (!Blocks.is(Blocks.name(chunks, at[0], at[1], at[2]), board)) {
            return true;
        }
        int yaw = Blocks.rotation(chunks, at[0], at[1], at[2]);
        int y = at[1];
        for (int climb = 0; climb < STAND_CLIMB; climb++) {
            String filler = neighbourFill(chunks, at[0], y, at[2]);
            String above = Blocks.name(chunks, at[0], y + 1, at[2]);
            if (filler == null || Blocks.id(chunks, at[0], y + 1, at[2]) == Blocks.UNLOADED
                    || !(above == null || Terrain.isVegetation(above) && !Blocks.solid(chunks, at[0], y + 1, at[2]))) {
                break;
            }
            Blocks.set(chunks, at[0], y, at[2], filler, 0);
            y++;
        }
        if (y != at[1]) {
            Blocks.set(chunks, at[0], y, at[2], board, yaw);
            state.setBoard(at[0], y, at[2]);
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples : panneau remonté de %d en %d %d %d (%s)", y - at[1], at[0], y, at[2],
                    village.name());
        }
        return true;
    }

    /** Bloc plein partagé par au moins deux des quatre voisins de (x, y, z), ou null. */
    private static String neighbourFill(ChunkStore chunks, int x, int y, int z) {
        java.util.Map<String, Integer> count = new java.util.HashMap<>();
        for (int[] d : new int[][] {{1, 0}, {-1, 0}, {0, 1}, {0, -1}}) {
            if (Blocks.solid(chunks, x + d[0], y, z + d[1])) {
                count.merge(Blocks.name(chunks, x + d[0], y, z + d[1]), 1, Integer::sum);
            }
        }
        int total = count.values().stream().mapToInt(Integer::intValue).sum();
        if (total < 2) {
            return null;
        }
        return count.entrySet().stream().max(java.util.Map.Entry.comparingByValue()).map(java.util.Map.Entry::getKey).orElse(null);
    }

    // ---- Ce que voit et fait un joueur ----

    /** Bâtiment dont le panneau est en (x, y, z) dans ce village, ou null. */
    public static Workshop atBoard(Village village, int x, int y, int z) {
        WorkshopState state = village.workshopAt(x, y, z);
        return state == null ? null : Workshop.get(state.id());
    }

    /** Vrai si le joueur peut prendre les commandes du bâtiment (rang Toléré). */
    public static boolean canTake(Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        return Reputations.rank(store, ref, village).atLeast(TAKE_RANK);
    }

    /** Demandes et commandes suivies par le joueur, hors étapes de chaîne (qui n'expirent pas). */
    public static int followed(PeuplesPlayer state) {
        int n = 0;
        for (PlayerRequest r : state.requests()) {
            if (r.expires() != Long.MAX_VALUE) {
                n++;
            }
        }
        return n;
    }

    /** Le joueur prend la commande de la case `slot` du bâtiment. Rend vrai si elle est prise. */
    public static boolean take(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                               Workshop w, int slot) {
        if (!open(village, w)) {
            player.sendMessage(Message.translation(KEYS + "notHere"));
            return false;
        }
        WorkshopState ws = village.workshop(w.getId());
        draw(store, village, w, ws, false);
        VillageRequest[] board = ws.requests();
        if (slot < 0 || slot >= board.length || board[slot] == null || board[slot].template() == null) {
            player.sendMessage(Message.translation(Requests.KEYS + "noSuchSlot").param("slot", slot + 1));
            return false;
        }
        if (!canTake(store, ref, village)) {
            player.sendMessage(Message.translation(KEYS + "locked").param("rank", Message.translation(TAKE_RANK.nameKey())));
            return false;
        }
        VillageRequest request = board[slot];
        RequestTemplate t = request.template();
        PeuplesPlayer state = PeuplesPlayer.ensure(store, ref);
        switch (Requests.status(state, request)) {
            case TAKEN -> {
                player.sendMessage(Message.translation(Requests.KEYS + "alreadyTaken").param("title", Requests.title(t)));
                return false;
            }
            case DONE -> {
                player.sendMessage(Message.translation(Requests.KEYS + "alreadyDone").param("title", Requests.title(t)));
                return false;
            }
            default -> {
            }
        }
        int count = followed(state);
        if (count >= MAX_FOLLOWED) {
            player.sendMessage(Message.translation(KEYS + "limit").param("count", count));
            return false;
        }
        return Requests.start(world, store, ref, player, state, village, t, request.id(), GameClock.expiryFromNow(store));
    }

    /**
     * Une commande de bâtiment est remplie ({@link Requests#fulfil}) : si elle est encore au panneau, le bâtiment gagne
     * son savoir-faire (borné à la jauge du niveau), le village son essor, et la case reçoit une nouvelle commande.
     * Rend l'essor réellement gagné (0 si un autre joueur l'a déjà remplie).
     */
    public static int fulfilled(World world, Store<EntityStore> store, PlayerRef player, Village village, RequestTemplate t, String requestId) {
        Workshop w = Workshop.get(t.workshop());
        if (w == null) {
            return 0;
        }
        WorkshopState ws = village.workshop(w.getId());
        if (t.master()) {
            // Commande de maître : une fois pour le village, si elle est bien celle du niveau en cours.
            if (!requestId.equals(masterId(village, w, ws)) || ws.masterDone()) {
                return 0;
            }
            ws.setMasterDone(true);
            Message m = Message.translation(KEYS + "masterDone").param("building", Message.translation(w.nameKey()))
                    .param("player", player.getUsername());
            Chantiers.announce(world, village, m, null, NotificationStyle.Success);
            return Villages.addEssor(village, t.essor());
        }
        int slot = ws.slotOf(requestId);
        if (slot < 0) {
            return 0;
        }
        int gained = Villages.addEssor(village, t.essor());
        int max = threshold(ws.level());
        if (max > 0 && t.knowledge() > 0) {
            int before = ws.knowledge();
            ws.setKnowledge(Math.min(max, before + t.knowledge()));
            int added = ws.knowledge() - before;
            if (added > 0) {
                Message name = Message.translation(w.nameKey());
                Message m = Message.translation(KEYS + "knowledgeGained").param("building", name).param("knowledge", added)
                        .param("value", ws.knowledge()).param("max", max);
                player.sendMessage(m);
                if (ws.knowledge() >= max) {
                    Message ready = Message.translation(KEYS + "knowledgeReady").param("building", name)
                            .param("level", Message.translation(KEYS + "levelShort." + (ws.level() + 1)));
                    Chantiers.announce(world, village, ready, null, NotificationStyle.Success);
                }
            }
        }
        redraw(store, village, w, ws, slot);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : commande %s du bâtiment %s remplie par %s (%s, savoir-faire %d/%d)",
                t.getId(), w.getId(), player.getUsername(), village.name(), ws.knowledge(), max);
        return gained;
    }

    // ---- Montée de niveau (étape 2) : commande de maître puis chantier d'amélioration ----

    /** Id (par village, bâtiment, niveau et reconversion) de la commande de maître du niveau en cours. */
    public static String masterId(Village village, Workshop w, WorkshopState state) {
        return "master-" + village.id() + "-" + w.getId() + "-" + state.level() + "-" + state.round();
    }

    /** Commande de maître du niveau en cours, ou null. */
    public static RequestTemplate master(Workshop w, WorkshopState state) {
        return RequestTemplate.master(w.getId(), state.level(), state.specialty());
    }

    /** Ce qui manque au bâtiment pour son prochain niveau. */
    public enum Next { MAX, KNOWLEDGE, TIER, MASTER, MATERIALS, WORKS }

    /** Prochaine étape de la montée de niveau du bâtiment. */
    public static Next next(Village village, WorkshopState state) {
        if (state.level() >= MAX_LEVEL) {
            return Next.MAX;
        }
        if (state.upgrading()) {
            return Next.WORKS;
        }
        if (state.knowledge() < threshold(state.level())) {
            return Next.KNOWLEDGE;
        }
        if (village.tier() < tierFor(state.level() + 1)) {
            return Next.TIER;
        }
        return state.masterDone() ? Next.MATERIALS : Next.MASTER;
    }

    /** Le joueur prend la commande de maître (jauge pleine, palier du village atteint, rang Toléré). */
    public static boolean takeMaster(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, Workshop w) {
        WorkshopState ws = village.workshop(w.getId());
        if (next(village, ws) != Next.MASTER) {
            player.sendMessage(Message.translation(KEYS + "masterNotYet"));
            return false;
        }
        if (!canTake(store, ref, village)) {
            player.sendMessage(Message.translation(KEYS + "locked").param("rank", Message.translation(TAKE_RANK.nameKey())));
            return false;
        }
        RequestTemplate t = master(w, ws);
        if (t == null) {
            player.sendMessage(Message.translation(KEYS + "masterMissing"));
            return false;
        }
        PeuplesPlayer state = PeuplesPlayer.ensure(store, ref);
        String id = masterId(village, w, ws);
        if (state.request(id) != null) {
            player.sendMessage(Message.translation(Requests.KEYS + "alreadyTaken").param("title", Requests.title(t)));
            return false;
        }
        // Comme une étape de chaîne : elle n'expire pas et ne compte pas dans les 3 suivies.
        return Requests.start(world, store, ref, player, state, village, t, id, Long.MAX_VALUE);
    }

    /** Matériaux qui manquent au dépôt pour le chantier d'amélioration (id → quantité), ou null si le dépôt manque. */
    public static java.util.Map<String, Integer> missing(World world, Village village, Workshop.Upgrade up) {
        java.util.Map<String, Integer> deposit = Villages.depositContents(world, village);
        if (deposit == null) {
            return null;
        }
        java.util.Map<String, Integer> out = new java.util.LinkedHashMap<>();
        for (VillageLayout.Material m : up.materials()) {
            int have = deposit.getOrDefault(m.itemId(), 0);
            if (have < m.quantity()) {
                out.put(m.itemId(), m.quantity() - have);
            }
        }
        return out;
    }

    /** Lance le chantier d'amélioration : matériaux pris au dépôt, travaux pendant {@code Hours} heures de jeu. */
    public static boolean startUpgrade(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, Workshop w) {
        WorkshopState ws = village.workshop(w.getId());
        if (next(village, ws) != Next.MATERIALS) {
            player.sendMessage(Message.translation(KEYS + "upgradeNotYet"));
            return false;
        }
        if (!canTake(store, ref, village)) {
            player.sendMessage(Message.translation(KEYS + "locked").param("rank", Message.translation(TAKE_RANK.nameKey())));
            return false;
        }
        Workshop.Upgrade up = w.upgrade(ws.level() + 1);
        if (up == null) {
            return false;
        }
        java.util.Map<String, Integer> missing = missing(world, village, up);
        if (missing == null) {
            player.sendMessage(Message.translation("nakasar_peuples.board.depositMissing"));
            return false;
        }
        if (!missing.isEmpty()) {
            Message list = Message.empty();
            boolean first = true;
            for (java.util.Map.Entry<String, Integer> e : missing.entrySet()) {
                if (!first) {
                    list.insert(", ");
                }
                first = false;
                list.insert(Message.translation(KEYS + "materialLine").param("count", e.getValue())
                        .param("item", dev.nakasar.hytale.peuples.village.VillageBoard.itemName(e.getKey())));
            }
            player.sendMessage(Message.translation(KEYS + "upgradeMissing").param("list", list));
            return false;
        }
        com.hypixel.hytale.server.core.inventory.container.ItemContainer chest = Villages.depositChest(world, village);
        for (VillageLayout.Material m : up.materials()) {
            Requests.take(chest, m.itemId(), m.quantity());
        }
        long now = GameClock.seconds(store);
        ws.startUpgrade(now, now + up.hours() * 3600L);
        Message m = Message.translation(KEYS + "upgradeStarted").param("building", Message.translation(w.nameKey()))
                .param("level", Message.translation(KEYS + "levelShort." + up.level())).param("hours", up.hours());
        Chantiers.announce(world, village, m, null, NotificationStyle.Default);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : chantier du bâtiment %s vers le niveau %d lancé par %s (%s)",
                w.getId(), up.level(), player.getUsername(), village.name());
        return true;
    }

    /** Fin du chantier d'amélioration : niveau suivant, jauge à zéro, commandes retirées, décor posé, annonce. */
    public static void finishUpgrade(World world, Store<EntityStore> store, Village village, Workshop w, WorkshopState ws) {
        int level = Math.min(MAX_LEVEL, ws.level() + 1);
        ws.clearUpgrade();
        ws.setLevel(level);
        ws.setKnowledge(0);
        ws.setMasterDone(false);
        draw(store, village, w, ws, true);
        Workshop.Upgrade up = w.upgrade(level);
        if (up != null && ws.hasBoard()) {
            placeDecor(world, ws.board(), up.decor());
        }
        Message name = Message.translation(w.nameKey());
        Message levelName = Message.translation(KEYS + "level." + level);
        Chantiers.announce(world, village, Message.translation(KEYS + "levelUp").param("building", name).param("level", levelName),
                Message.translation(KEYS + "levelUpTitle").param("building", name).param("level", levelName), NotificationStyle.Success);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : bâtiment %s au niveau %d (%s)", w.getId(), level, village.name());
    }

    /** Pose le décor vanilla d'un niveau ({@code "dx dy dz lacet Bloc"} relatifs au panneau), seulement dans l'air. */
    static void placeDecor(World world, int[] origin, String[] decor) {
        ChunkStore chunks = world.getChunkStore();
        for (String line : decor) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            try {
                int x = origin[0] + Integer.parseInt(p[0]);
                int y = origin[1] + Integer.parseInt(p[1]);
                int z = origin[2] + Integer.parseInt(p[2]);
                int rot = Integer.parseInt(p[3]);
                String current = Blocks.name(chunks, x, y, z);
                if (Blocks.id(chunks, x, y, z) != Blocks.UNLOADED && (current == null || Terrain.isVegetation(current))
                        && Blocks.name(chunks, x, y - 1, z) != null) {
                    Blocks.set(chunks, x, y, z, p[4], rot);
                }
            } catch (NumberFormatException ignored) {
                // Ligne mal formée : ValidateAssets la signale.
            }
        }
    }

    // ---- Spécialités (étape 3) ----

    /** Pourquoi le joueur ne peut pas (re)choisir la spécialité : clé de message, ou null s'il le peut. */
    public static Message specialtyBlock(Store<EntityStore> store, Ref<EntityStore> ref, Village village, WorkshopState ws) {
        if (ws.level() < SPECIALTY_LEVEL) {
            return Message.translation(KEYS + "specialtyLevel");
        }
        if (!Reputations.rank(store, ref, village).atLeast(SPECIALTY_RANK)) {
            return Message.translation(KEYS + "specialtyRank").param("rank", Message.translation(SPECIALTY_RANK.nameKey()));
        }
        if (ws.upgrading()) {
            return Message.translation(KEYS + "specialtyWorks");
        }
        int left = reconvertDaysLeft(store, ws);
        if (ws.specialty() != null && left > 0) {
            return Message.translation(KEYS + "specialtyCooldown").param("days", left);
        }
        return null;
    }

    /** Jours avant la prochaine reconversion possible (0 : maintenant). */
    public static int reconvertDaysLeft(Store<EntityStore> store, WorkshopState ws) {
        if (ws.reconverted() == Long.MIN_VALUE) {
            return 0;
        }
        return (int) Math.max(0, ws.reconverted() + RECONVERT_DAYS - GameClock.day(store));
    }

    /**
     * Le joueur choisit la spécialité `specialtyId` du bâtiment (niveau II, rang Ami), pour tout le village. Changer une
     * spécialité déjà choisie est une reconversion : une fois tous les {@value #RECONVERT_DAYS} jours, le savoir-faire du
     * niveau retombe à 0 et la commande de maître est à refaire. Les bêtes de l'enclos changent aussitôt.
     */
    public static boolean chooseSpecialty(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                          Workshop w, String specialtyId) {
        WorkshopState ws = village.workshop(w.getId());
        Workshop.Specialty spec = w.specialty(specialtyId);
        if (spec == null) {
            player.sendMessage(Message.translation(KEYS + "specialtyUnknown").param("id", String.valueOf(specialtyId)));
            return false;
        }
        if (spec.id().equals(ws.specialty())) {
            return false;
        }
        Message block = specialtyBlock(store, ref, village, ws);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        Workshop twin = twinWith(village, w, spec.id());
        if (twin != null) {
            player.sendMessage(Message.translation(KEYS + "specialtyTwin").param("building", Message.translation(twin.nameKey())));
            return false;
        }
        boolean reconvert = ws.specialty() != null;
        ws.setSpecialty(spec.id());
        if (reconvert) {
            ws.setReconverted(GameClock.day(store));
            ws.setKnowledge(0);
            ws.setMasterDone(false);
            ws.nextRound();
        }
        draw(store, village, w, ws, true);
        Livestock.changed(store, village, w);
        Message m = Message.translation(KEYS + (reconvert ? "specialtyConverted" : "specialtyChosen"))
                .param("player", player.getUsername()).param("building", Message.translation(w.nameKey()))
                .param("specialty", Message.translation(spec.nameKey()));
        Chantiers.announce(world, village, m, null, NotificationStyle.Success);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : %s choisit la spécialité %s pour %s (%s, reconversion %s)",
                player.getUsername(), spec.id(), w.getId(), village.name(), reconvert);
        return true;
    }

    /**
     * Les élevages du même genre (enclos de base et deuxièmes élevages des emplacements libres) qui ont déjà la
     * spécialité `specialtyId` : le premier trouvé, ou null. GDD : chaque élevage a une spécialité différente.
     */
    public static Workshop twinWith(Village village, Workshop w, String specialtyId) {
        String root = w.twin() != null ? w.twin() : w.getId();
        for (Workshop other : Workshop.forLayout(village.layout())) {
            if (other == w || !(root.equals(other.getId()) || root.equals(other.twin()))) {
                continue;
            }
            if (!village.isBuilt(other.building())) {
                continue;
            }
            if (specialtyId.equals(village.workshop(other.getId()).specialty())) {
                return other;
            }
        }
        return null;
    }

    // ---- Boutiques et Part de l'Hôte (étape 4) ----

    /** Rang qui ouvre le lot quotidien de la Part de l'Hôte (niveau III). */
    public static final Rank SHARE_RANK = Rank.HOTE;

    /** Niveau de boutique ouvert par le rang : Toléré I, Ami II, Hôte (et au-delà) III ; 0 en dessous de Toléré. */
    public static int rankLevel(Rank rank) {
        if (rank.atLeast(Rank.HOTE)) {
            return 3;
        }
        if (rank.atLeast(Rank.AMI)) {
            return 2;
        }
        return rank.atLeast(Rank.TOLERE) ? 1 : 0;
    }

    /** Niveau de boutique que voit le joueur : son rang, sans dépasser le niveau du bâtiment (0 : fermée). */
    public static int shopLevel(Store<EntityStore> store, Ref<EntityStore> ref, Village village, WorkshopState ws) {
        return Math.min(ws.level(), rankLevel(Reputations.rank(store, ref, village)));
    }

    /** Boutique du niveau `level` du bâtiment : celle de la spécialité aux niveaux II et III, sinon la base. */
    public static String shop(Workshop w, WorkshopState ws, int level) {
        if (level <= 0) {
            return null;
        }
        Workshop.Specialty spec = level >= 2 ? w.specialty(ws.specialty()) : null;
        String id = spec == null ? null : spec.shop(level);
        return id != null ? id : w.baseShop();
    }

    /** Vrai si la boutique tient : son villageois est là (il revient au matin). */
    public static boolean keeperPresent(Village village, Workshop w) {
        VillageLayout.Job job = job(village, w);
        return job != null && dev.nakasar.hytale.peuples.village.Villagers.present(village, job.id());
    }

    /** Ouvre la boutique du bâtiment au niveau que voit le joueur. Thread du monde. */
    public static boolean openShop(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, Workshop w) {
        WorkshopState ws = village.workshop(w.getId());
        if (!keeperPresent(village, w)) {
            player.sendMessage(Message.translation(KEYS + "shopAbsent").param("hour", GameClock.MORNING));
            return false;
        }
        String id = shop(w, ws, shopLevel(store, ref, village, ws));
        if (id == null) {
            player.sendMessage(Message.translation(KEYS + "shopRank").param("rank", Message.translation(Rank.TOLERE.nameKey())));
            return false;
        }
        return dev.nakasar.hytale.peuples.reputation.Shops.open(store, ref, player, village, id);
    }

    /** Lot du jour de la Part de l'Hôte, ou null (niveau III avec une spécialité qui en a un). */
    public static Workshop.Specialty shareSpecialty(Workshop w, WorkshopState ws) {
        Workshop.Specialty spec = ws.level() >= 3 ? w.specialty(ws.specialty()) : null;
        return spec != null && spec.shareItem() != null ? spec : null;
    }

    /** Pourquoi le joueur ne peut pas prendre sa Part de l'Hôte, ou null s'il le peut. */
    public static Message shareBlock(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, Workshop w) {
        WorkshopState ws = village.workshop(w.getId());
        if (shareSpecialty(w, ws) == null) {
            return Message.translation(KEYS + "shareLevel");
        }
        if (!Reputations.rank(store, ref, village).atLeast(SHARE_RANK)) {
            return Message.translation(KEYS + "shareRank").param("rank", Message.translation(SHARE_RANK.nameKey()));
        }
        if (ws.shareTaken(GameClock.day(store), player.getUuid().toString())) {
            return Message.translation(KEYS + "shareTaken").param("hour", GameClock.MORNING);
        }
        return null;
    }

    /**
     * Le joueur prend son lot du jour dans la caisse de la Part de l'Hôte (GDD, étape 4 ; Kevin : « une caisse où le
     * bâtiment dépose chaque matin un petit lot de sa production pour les Hôtes ») : niveau III, rang Hôte, un lot par
     * joueur et par jour de jeu. Le lot tombe à ses pieds si son inventaire est plein. Thread du monde.
     */
    public static boolean takeShare(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, Workshop w) {
        Message block = shareBlock(store, ref, player, village, w);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        WorkshopState ws = village.workshop(w.getId());
        Workshop.Specialty spec = shareSpecialty(w, ws);
        ws.takeShare(GameClock.day(store), player.getUuid().toString());
        Requests.give(store, ref, new com.hypixel.hytale.server.core.inventory.ItemStack(spec.shareItem(), spec.shareQuantity()));
        notify(player, Message.translation(KEYS + "shareGiven").param("quantity", spec.shareQuantity())
                .param("item", dev.nakasar.hytale.peuples.village.VillageBoard.itemName(spec.shareItem())), NotificationStyle.Success);
        return true;
    }

    // ---- Spécialités de garde en raid (étape 5) ----

    /** Renfort d'un village en raid : gardes de plus au cœur, points où poster des gardes, PV des gardes. */
    public record RaidBonus(int guards, List<int[]> posts, float health) {
        public static final RaidBonus NONE = new RaidBonus(0, List.of(), 1f);
    }

    /**
     * Renfort des spécialités de garde du village : pour chaque bâtiment ouvert au niveau II ou plus avec une spécialité
     * qui a un effet en raid. Au niveau III, ses gardes (au cœur ou postés) prennent +1. Les PV se multiplient.
     * Les postes sont le centre du bâtiment, en coordonnées du monde (x, z).
     */
    public static RaidBonus raidBonus(Village village) {
        int guards = 0;
        float health = 1f;
        List<int[]> posts = new ArrayList<>();
        VillageLayout layout = Chantiers.layout(village);
        for (Workshop w : opened(village)) {
            WorkshopState ws = village.workshop(w.getId());
            Workshop.Specialty spec = ws.level() >= SPECIALTY_LEVEL ? w.specialty(ws.specialty()) : null;
            Workshop.Raid raid = spec == null ? null : spec.raid();
            if (raid == null) {
                continue;
            }
            int extra = ws.level() >= 3 ? 1 : 0;
            if (raid.guards() > 0) {
                guards += raid.guards() + extra;
            }
            health *= raid.health();
            if (raid.posted() > 0 && layout != null) {
                for (VillageLayout.Building b : layout.buildings()) {
                    if (b.id().equals(w.building())) {
                        int[] r = b.rect();
                        int cx = village.x() + Math.floorDiv(r[0] + r[1], 2);
                        int cz = village.z() + Math.floorDiv(r[2] + r[3], 2);
                        for (int i = 0; i < raid.posted() + extra; i++) {
                            posts.add(new int[] {cx, cz});
                        }
                    }
                }
            }
        }
        return guards == 0 && posts.isEmpty() && health == 1f ? RaidBonus.NONE : new RaidBonus(guards, posts, health);
    }

    /** Ligne de type d'une commande pour la version texte. */
    static Message typeName(RequestType type) {
        return Message.translation(type.nameKey());
    }

    /** Notification courte au joueur. */
    static void notify(PlayerRef player, Message m, NotificationStyle style) {
        NotificationUtil.sendNotification(player.getPacketHandler(), m, style);
    }
}
