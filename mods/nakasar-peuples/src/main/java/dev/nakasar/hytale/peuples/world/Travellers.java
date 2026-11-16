package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Étape 1 : les voyageurs sur les routes. Chaque matin, des marchands ambulants, des pèlerins, des messagers et des
 * caravanes partent d'un village vers un autre (au plus {@value #MAX_WORLD} en route par monde, un par liaison). Ils
 * marchent de jour et s'arrêtent la nuit (à l'auberge de la liaison s'il y en a une, {@link Inns}). On leur parle :
 * troc du peuple (rang Toléré dans leur village d'origine), rumeurs du monde, escorte (réputation à l'arrivée), lettre
 * à porter pour le messager. Une caravane peut tomber dans une embuscade à mi-chemin ({@link Ambushes}).
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#TRAVELLERS}) : {@code id = genre|départ|arrivée|blocs|marcheurs|embuscade|escorte|cargaison}.
 */
public final class Travellers {

    public static final int MAX_WORLD = 6;
    /** Chance qu'une liaison libre voie partir un voyageur chaque matin. */
    public static final double DEPARTURE_CHANCE = 0.35;
    public static final int ESCORT_REPUTATION = 25;
    public static final int ESCORT_RANGE = 24;
    /** L'escorte est perdue si le joueur reste plus de {@value #ESCORT_AWAY} s loin du voyageur (2 × ESCORT_RANGE). */
    public static final int ESCORT_AWAY = 60;
    /** Gain de relation à l'arrivée : caravane, autre voyageur. */
    public static final int CARAVAN_RELATION = 5;
    public static final int TRAVELLER_RELATION = 1;
    public static final int LETTER_REPUTATION = 20;
    public static final int LETTER_REACH = 12;
    public static final String LETTER = "Nakasar_Peuples_Letter";
    public static final String LETTER_FLAG = "World_Letter:";
    public static final String KEYS = WorldLife.KEYS + "traveller.";

    public enum Kind {
        MERCHANT("Monde_Marchand", 1),
        PILGRIM("Monde_Pelerin", 1),
        MESSENGER("Monde_Messager", 1),
        CARAVAN("Monde_Caravane", 3);

        final String dialogue;
        final int walkers;

        Kind(String dialogue, int walkers) {
            this.dialogue = dialogue;
            this.walkers = walkers;
        }

        public String key() {
            return name().toLowerCase();
        }
    }

    /** Un voyageur en route (état sauvé). */
    public static final class Traveller {
        final String id;
        Kind kind;
        String from;
        String to;
        double at;
        int walkers;
        /** 0 pas encore, 1 passé (ou évitée), 2 en cours. */
        int ambush;
        String escort = "-";
        int cargo;

        Traveller(String id) {
            this.id = id;
        }

        static Traveller parse(String id, String value) {
            String[] p = value.split("\\|", -1);
            if (p.length < 8) {
                return null;
            }
            try {
                Traveller t = new Traveller(id);
                t.kind = Kind.valueOf(p[0]);
                t.from = p[1];
                t.to = p[2];
                t.at = Double.parseDouble(p[3]);
                t.walkers = Integer.parseInt(p[4]);
                t.ambush = Integer.parseInt(p[5]);
                t.escort = p[6];
                t.cargo = Integer.parseInt(p[7]);
                return t;
            } catch (IllegalArgumentException e) {
                return null;
            }
        }

        String format() {
            return kind.name() + "|" + from + "|" + to + "|" + String.format(java.util.Locale.ROOT, "%.1f", at) + "|" + walkers
                    + "|" + ambush + "|" + escort + "|" + cargo;
        }

        public Kind kind() {
            return kind;
        }

        public String from() {
            return from;
        }

        public String to() {
            return to;
        }

        String walkKey() {
            return "T:" + id;
        }
    }

    private static final Map<Ref<EntityStore>, String> OWNER = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Secondes passées par l'escorteur loin de son voyageur (id du voyageur). */
    private static final Map<String, Float> ESCORT_AWAY_FOR = new java.util.concurrent.ConcurrentHashMap<>();

    private Travellers() {
    }

    // ---- Registre ----

    public static List<Traveller> all(World world) {
        List<Traveller> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.TRAVELLERS).entrySet()) {
            Traveller t = Traveller.parse(e.getKey(), e.getValue());
            if (t != null) {
                out.add(t);
            }
        }
        return out;
    }

    public static Traveller get(World world, String id) {
        String v = id == null ? null : WorldLife.registry(world).get(WorldLifeRegistry.Part.TRAVELLERS, id);
        return v == null ? null : Traveller.parse(id, v);
    }

    static void save(World world, Traveller t) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRAVELLERS, t.id, t.format());
    }

    static void drop(World world, Store<EntityStore> store, Traveller t) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRAVELLERS, t.id, null);
        Walk.end(store, t.walkKey());
        Ambushes.cancel(store, t.walkKey()); // la bande qui a tué tous les marcheurs repart
        ESCORT_AWAY_FOR.remove(t.id);
    }

    /** Le PNJ n'est plus (retiré ou mort). */
    static void forget(Ref<EntityStore> ref) {
        OWNER.remove(ref);
    }

    /** Le voyageur de ce PNJ (ou null). */
    public static Traveller of(World world, Ref<EntityStore> npc) {
        String id = npc == null ? null : OWNER.get(npc);
        return id == null ? null : get(world, id);
    }

    // ---- Départs ----

    /** Départs du matin (une fois par jour de jeu). */
    static void morning(World world, Store<EntityStore> store, Random random) {
        List<Traveller> current = all(world);
        int count = current.size();
        List<Links.Link> links = new ArrayList<>(Links.all(world));
        Collections.shuffle(links, random);
        for (Links.Link link : links) {
            if (count >= MAX_WORLD) {
                break;
            }
            if (busy(current, link)) {
                continue;
            }
            int relation = Relations.value(world, link.a(), link.b());
            boolean allied = relation >= Relations.ALLY;
            if (!allied && random.nextDouble() >= DEPARTURE_CHANCE) {
                continue;
            }
            Kind kind = allied ? Kind.CARAVAN : Kind.values()[random.nextInt(Kind.values().length)];
            if (relation <= Relations.RIVAL && kind != Kind.MESSENGER) {
                continue; // entre rivaux, seuls les messagers passent encore
            }
            boolean ab = random.nextBoolean();
            if (start(world, kind, ab ? link.a() : link.b(), ab ? link.b() : link.a()) != null) {
                count++;
            }
        }
    }

    private static boolean busy(List<Traveller> current, Links.Link link) {
        for (Traveller t : current) {
            if (link.key().equals(Links.key(t.from, t.to))) {
                return true;
            }
        }
        return false;
    }

    /** Fait partir un voyageur (commande, départs du matin) ; null si la liaison n'existe pas. */
    public static Traveller start(World world, Kind kind, Village from, Village to) {
        if (Links.of(world, from.id(), to.id()) == null) {
            return null;
        }
        Traveller t = new Traveller(Long.toString(System.currentTimeMillis(), 36) + Integer.toString(new Random().nextInt(1296), 36));
        t.kind = kind;
        t.from = from.id();
        t.to = to.id();
        t.walkers = kind.walkers;
        t.cargo = kind == Kind.CARAVAN ? 3 : 0;
        save(world, t);
        Links.trip(world, from.id(), to.id(), Links.TRIED);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (monde vivant) : %s de %s vers %s", kind, from.name(), to.name());
        return t;
    }

    // ---- Marche ----

    /** Le pas de tous les voyageurs. */
    static void step(World world, Store<EntityStore> store, List<Vector3d> players, float dt) {
        boolean night = GameClock.isNight(store);
        for (Traveller t : all(world)) {
            Village from = Villages.registry(world).byId(t.from);
            Village to = Villages.registry(world).byId(t.to);
            if (from == null || to == null || t.walkers <= 0) {
                drop(world, store, t);
                continue;
            }
            Routes.Path path = Links.path(world, from, to);
            if (t.at >= path.length() - Walk.ARRIVE) {
                arrive(world, store, t, from, to);
                continue;
            }
            boolean moving = !night || Inns.nightStopAhead(world, t, path);
            if (t.ambush == 2) {
                moving = false;
                if (Ambushes.over(world, store, t.walkKey())) {
                    t.ambush = 1;
                }
            }
            Walk walk = Walk.of(t.walkKey());
            boolean wasReal = walk.real();
            People people = from.people();
            t.at = walk.step(world, store, players, path, t.at, dt, t.walkers, moving, from.y(),
                    (i, at, yaw) -> spawnWalker(store, t, people, i, at, yaw));
            if (!wasReal && walk.real()) {
                for (Ref<EntityStore> ref : walk.alive()) {
                    OWNER.put(ref, t.id);
                }
                // Un joueur arrive : les chunks autour de lui sont chargés, on recalcule le trajet sur le terrain réel
                // (pont posé, lac comblé), et chaque voyageur de cette route reprend au point le plus proche.
                Routes.Path fresh = Links.refresh(world, from, to);
                if (fresh != path) {
                    for (Traveller o : all(world)) {
                        if (o.from.equals(t.from) && o.to.equals(t.to)) {
                            double[] was = path.point(o.at);
                            o.at = fresh.closest(was[0], was[1], 0, fresh.length());
                            Walk.of(o.walkKey()).reset(o.at);
                            if (o != t) {
                                save(world, o);
                            }
                        }
                    }
                    path = fresh;
                }
            }
            followEscort(world, store, t, path, dt);
            if (t.kind == Kind.CARAVAN && t.ambush == 0 && t.at >= path.length() / 2) {
                t.ambush = Ambushes.roll(world, store, t.walkKey(), path.point(t.at), path.dir(t.at), from.people(),
                        walk.alive(), players) ? 2 : 1;
                if (t.ambush == 1 && Ambushes.virtualLoss(players, path.point(t.at))) {
                    t.cargo = Math.max(0, t.cargo - 1);
                    dev.nakasar.hytale.peuples.village.Chantiers.announce(world, to, Message.translation(KEYS + "ambushedAway").param("from", from.name()), null, NotificationStyle.Warning);
                }
            }
            save(world, t);
        }
    }

    /** L'escorteur doit rester près du voyageur pendant le trajet, pas seulement l'attendre à l'arrivée. */
    private static void followEscort(World world, Store<EntityStore> store, Traveller t, Routes.Path path, float dt) {
        if ("-".equals(t.escort)) {
            return;
        }
        PlayerRef escort = null;
        for (PlayerRef p : world.getPlayerRefs()) {
            if (p.getUuid().toString().equals(t.escort)) {
                escort = p;
            }
        }
        double[] here = path.point(t.at);
        Vector3d at = escort == null ? null : Requests.position(store, escort.getReference());
        double range = 2.0 * ESCORT_RANGE;
        if (at != null && Math.hypot(at.x() - here[0], at.z() - here[1]) <= range) {
            ESCORT_AWAY_FOR.remove(t.id);
            return;
        }
        float away = ESCORT_AWAY_FOR.merge(t.id, dt, Float::sum);
        if (away < ESCORT_AWAY) {
            return;
        }
        ESCORT_AWAY_FOR.remove(t.id);
        t.escort = "-";
        if (escort != null) {
            Village to = Villages.registry(world).byId(t.to);
            Message m = Message.translation(KEYS + "escortLost").param("to", to == null ? "?" : to.name());
            escort.sendMessage(m);
            NotificationUtil.sendNotification(escort.getPacketHandler(), m, NotificationStyle.Warning);
        }
    }

    private static Ref<EntityStore> spawnWalker(Store<EntityStore> store, Traveller t, People people, int i, Vector3d at, float yaw) {
        String role = i == 0 && t.kind != Kind.PILGRIM && t.kind != Kind.MESSENGER ? peddlerRole(people) : travellerRole(people);
        Ref<EntityStore> ref = WorldLife.spawn(store, role, at, yaw);
        if (ref == null) {
            return null;
        }
        WorldLife.side(ref, "T:" + t.id, 0);
        WorldLife.talker(ref, Travellers::talk);
        WorldLife.mortal(ref, (world, npc, where, killer) -> died(world, t.id, npc));
        OWNER.put(ref, t.id);
        return ref;
    }

    public static String travellerRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Traveller";
    }

    public static String peddlerRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Peddler";
    }

    private static void died(World world, String id, Ref<EntityStore> npc) {
        OWNER.remove(npc);
        Traveller t = get(world, id);
        if (t == null) {
            return;
        }
        t.walkers--;
        if (t.kind == Kind.CARAVAN) {
            t.cargo = Math.max(0, t.cargo - 1);
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (t.walkers <= 0) {
            Links.trip(world, t.from, t.to, Links.FAILED);
            Village to = Villages.registry(world).byId(t.to);
            Village from = Villages.registry(world).byId(t.from);
            if (to != null && from != null) {
                dev.nakasar.hytale.peuples.village.Chantiers.announce(world, from, Message.translation(KEYS + "lost." + t.kind.key()).param("to", to.name()), null, NotificationStyle.Warning);
            }
            drop(world, store, t);
        } else {
            save(world, t);
        }
    }

    private static void arrive(World world, Store<EntityStore> store, Traveller t, Village from, Village to) {
        long day = GameClock.day(store);
        Links.trip(world, from.id(), to.id(), Links.SUCCEEDED);
        // Chaque marcheur arrivé compte pour un passage (une caravane : ses trois porteurs).
        Links.pass(world, Links.key(from.id(), to.id()), day, Math.max(1, t.walkers));
        if (t.kind == Kind.CARAVAN && t.cargo > 0) {
            Villages.addEssor(to, t.cargo);
            Relations.change(world, from, to, CARAVAN_RELATION);
        } else if (t.kind != Kind.CARAVAN) {
            Relations.change(world, from, to, TRAVELLER_RELATION);
        }
        // Escorte : le joueur qui l'a accompagnée est là à l'arrivée.
        if (!"-".equals(t.escort)) {
            for (PlayerRef p : world.getPlayerRefs()) {
                if (!p.getUuid().toString().equals(t.escort)) {
                    continue;
                }
                Vector3d at = Requests.position(store, p.getReference());
                if (at != null && to.horizontalDistanceSquared(at.x(), at.z()) <= (Villages.RADIUS + ESCORT_RANGE) * (double) (Villages.RADIUS + ESCORT_RANGE)) {
                    Reputations.change(world, store, p.getReference(), p, from, ESCORT_REPUTATION, KEYS + "escortReason");
                    Reputations.change(world, store, p.getReference(), p, to, ESCORT_REPUTATION / 2, KEYS + "escortReason");
                    Message m = Message.translation(KEYS + "escortDone").param("to", to.name());
                    p.sendMessage(m);
                    NotificationUtil.sendNotification(p.getPacketHandler(), m, NotificationStyle.Success);
                }
            }
        }
        drop(world, store, t);
    }

    // ---- Dialogue ----

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Traveller t = of(world, npc);
        Dialogue dialogue = t == null ? null : Dialogue.get(t.kind.dialogue);
        if (dialogue == null) {
            return;
        }
        Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
    }

    /** Troc du voyageur : celui de son peuple, ouvert au rang Toléré dans son village d'origine. */
    static boolean openShop(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Traveller t) {
        Village from = Villages.registry(world).byId(t.from);
        if (from == null) {
            return false;
        }
        if (!Reputations.rank(store, ref, from).atLeast(Rank.TOLERE)) {
            DialogueSpeech.say(player, Message.translation(KEYS + "shopRank").param("village", from.name()));
            return false;
        }
        return dev.nakasar.hytale.peuples.reputation.Shops.open(store, ref, player, from, shop(from.people()));
    }

    public static String shop(People people) {
        return "Nakasar_Peuples_Travel_" + people.id();
    }

    /** Le joueur escortera ce voyageur jusqu'à son arrivée. */
    static boolean escort(World world, PlayerRef player, Traveller t) {
        Village to = Villages.registry(world).byId(t.to);
        if (to == null) {
            return false;
        }
        t.escort = player.getUuid().toString();
        save(world, t);
        DialogueSpeech.say(player, Message.translation(KEYS + "escortStart").param("to", to.name()));
        return true;
    }

    /**
     * Le messager confie sa lettre au joueur et rentre chez lui. `parley` : lettre de paix entre villages rivaux (le
     * joueur doit être Ami des deux), qui apporte une trêve à sa livraison.
     */
    static boolean letter(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Traveller t, boolean parley) {
        Village to = Villages.registry(world).byId(t.to);
        Village from = Villages.registry(world).byId(t.from);
        if (to == null || from == null) {
            return false;
        }
        if (parley && !canParley(world, store, ref, from, to)) {
            DialogueSpeech.say(player, Message.translation(KEYS + "parleyRank").param("a", from.name()).param("b", to.name()));
            return false;
        }
        if (!giveLetter(world, store, ref, player, to, parley ? from : null)) {
            return false;
        }
        Links.trip(world, from.id(), to.id(), Links.SUCCEEDED); // la lettre poursuit sa route avec le joueur
        drop(world, store, t);
        return true;
    }

    /** Vrai si les deux villages sont rivaux et le joueur Ami de chacun. */
    static boolean canParley(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village a, Village b) {
        return Relations.value(world, a, b) <= Relations.RIVAL && Reputations.rank(store, ref, a).atLeast(Rank.AMI)
                && Reputations.rank(store, ref, b).atLeast(Rank.AMI);
    }

    /** Donne une lettre pour `to` (de paix si `parleyFrom` n'est pas null). */
    static boolean giveLetter(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village to, Village parleyFrom) {
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        boolean carried = WorldLife.count(store, ref, LETTER::equals) > 0;
        for (String f : new ArrayList<>(data.flags())) {
            if (f.startsWith(LETTER_FLAG)) {
                if (!carried) {
                    data.setFlag(f, false); // lettre perdue (mort, jetée, rangée) : elle ne compte plus
                    continue;
                }
                DialogueSpeech.say(player, Message.translation(KEYS + "letterAlready"));
                return false;
            }
        }
        CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        ItemStack stack = new ItemStack(LETTER, 1);
        if (!inventory.canAddItemStack(stack)) {
            DialogueSpeech.say(player, Message.translation("nakasar_peuples.dialogue.inventoryFull"));
            return false;
        }
        inventory.addItemStack(stack);
        data.setFlag(LETTER_FLAG + to.id() + (parleyFrom == null ? "" : ":" + parleyFrom.id()), true);
        DialogueSpeech.say(player, dev.nakasar.hytale.peuples.klops.Klops.describe(store, ref, to,
                KEYS + (parleyFrom == null ? "letterGiven" : "parleyGiven")));
        return true;
    }

    /** Livraison des lettres : le joueur arrive près du cœur du village destinataire. */
    static void letters(World world, Store<EntityStore> store) {
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            PeuplesPlayer data = ref == null || !ref.isValid() ? null : PeuplesPlayer.get(store, ref);
            if (data == null) {
                continue;
            }
            String flag = null;
            for (String f : data.flags()) {
                if (f.startsWith(LETTER_FLAG)) {
                    flag = f;
                }
            }
            if (flag == null) {
                continue;
            }
            String[] ids = flag.substring(LETTER_FLAG.length()).split(":");
            String id = ids[0];
            Village to = Villages.registry(world).byId(id);
            Village parleyFrom = ids.length > 1 ? Villages.registry(world).byId(ids[1]) : null;
            if (to == null) {
                data.setFlag(flag, false);
                continue;
            }
            Vector3d at = Requests.position(store, ref);
            if (at == null || to.horizontalDistanceSquared(at.x(), at.z()) > (double) LETTER_REACH * LETTER_REACH) {
                continue;
            }
            CombinedItemContainer inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
            if (!inventory.removeItemStack(new ItemStack(LETTER, 1), true, true).succeeded()) {
                continue;
            }
            data.setFlag(flag, false);
            if (parleyFrom != null) {
                Relations.parley(world, parleyFrom, to, GameClock.day(store));
            }
            Requests.give(store, ref, new ItemStack(to.people().favorItem(), 1));
            Message m = Message.translation(KEYS + "letterDelivered").param("village", to.name());
            player.sendMessage(m);
            NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Success);
            Reputations.change(world, store, ref, player, to, LETTER_REPUTATION, KEYS + "letterReason");
        }
    }

    /** Ligne de la commande /monde. */
    static Message describe(World world, Traveller t) {
        Village from = Villages.registry(world).byId(t.from);
        Village to = Villages.registry(world).byId(t.to);
        Links.Link link = Links.of(world, t.from, t.to);
        return Message.translation(KEYS + "line").param("kind", Message.translation(KEYS + "kind." + t.kind.key()))
                .param("from", from == null ? "?" : from.name()).param("to", to == null ? "?" : to.name())
                .param("at", (int) t.at).param("length", link == null ? 0 : (int) link.length()).param("walkers", t.walkers);
    }

    public static void clearAll() {
        OWNER.clear();
        ESCORT_AWAY_FOR.clear();
    }
}
