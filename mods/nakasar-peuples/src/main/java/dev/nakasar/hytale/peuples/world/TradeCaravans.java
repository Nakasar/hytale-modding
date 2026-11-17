package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.reputation.Shops;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Deposits;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les caravanes des routes commerciales (Kevin, 16 novembre 2026) : au jour du départ, une caravane part de chaque bout
 * avec les exportations de son village (prises au dépôt s'il est chargé, sinon chargement plein de sa production ; le
 * luxe du terroir ne se prend jamais au dépôt). Elle marche comme les voyageurs ({@link Walk}) par la route de la
 * liaison et dépose sa cargaison au dépôt d'arrivée : chaque marchandise livrée ouvre l'accès du village
 * ({@link TradeAccess}) pour {@value TradeAccess#DELIVERY_DAYS} jours.
 *
 * <p>À mi-chemin, une chance sur {@value #AMBUSH_ODDS} d'embuscade (deux fois moins sur une route entièrement
 * balisée, et deux fois moins en territoire gardé) : sous les yeux d'un joueur, une bande attaque
 * ({@link Ambushes}) ; sinon la caravane perd un tiers de sa cargaison. Tous les porteurs tués : la cargaison tombe
 * au sol et la route compte une perte ({@value TradeRoutes#LOST_LIMIT} d'affilée font perdre un niveau).
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#TRADE_CARAVANS}) :
 * {@code id = route|de|vers|blocs|porteurs|embuscade (0 à venir, 1 passée, 2 en cours)|objet:n,objet:n}.
 */
public final class TradeCaravans {

    public static final int AMBUSH_ODDS = 6;
    public static final String DIALOGUE = "Monde_Commerce";

    /** Une caravane (état sauvé). */
    public static final class Caravan {
        final String id;
        String route;
        String from;
        String to;
        double at;
        int walkers;
        int ambush;
        final Map<String, Integer> cargo = new LinkedHashMap<>();

        Caravan(String id) {
            this.id = id;
        }

        static Caravan parse(String id, String v) {
            String[] p = v.split("\\|", -1);
            if (p.length < 7) {
                return null;
            }
            try {
                Caravan c = new Caravan(id);
                c.route = p[0];
                c.from = p[1];
                c.to = p[2];
                c.at = Double.parseDouble(p[3]);
                c.walkers = Integer.parseInt(p[4]);
                c.ambush = Integer.parseInt(p[5]);
                for (String s : p[6].split(",")) {
                    int cut = s.lastIndexOf(':');
                    if (cut > 0) {
                        c.cargo.merge(s.substring(0, cut), Integer.parseInt(s.substring(cut + 1)), Integer::sum);
                    }
                }
                return c;
            } catch (NumberFormatException e) {
                return null;
            }
        }

        String format() {
            StringBuilder b = new StringBuilder();
            for (Map.Entry<String, Integer> e : cargo.entrySet()) {
                if (e.getValue() > 0) {
                    b.append(b.length() == 0 ? "" : ",").append(e.getKey()).append(':').append(e.getValue());
                }
            }
            return route + "|" + from + "|" + to + "|" + String.format(Locale.ROOT, "%.1f", at) + "|" + walkers + "|" + ambush + "|" + b;
        }

        String walkKey() {
            return "TC:" + id;
        }

        public String from() {
            return from;
        }

        public String to() {
            return to;
        }

        public double at() {
            return at;
        }

        public Map<String, Integer> cargo() {
            return cargo;
        }
    }

    private static final Map<Ref<EntityStore>, String> OWNER = Collections.synchronizedMap(new IdentityHashMap<>());

    private TradeCaravans() {
    }

    // ---- Registre ----

    public static List<Caravan> all(World world) {
        List<Caravan> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.TRADE_CARAVANS).entrySet()) {
            Caravan c = Caravan.parse(e.getKey(), e.getValue());
            if (c != null) {
                out.add(c);
            }
        }
        return out;
    }

    public static Caravan get(World world, String id) {
        String v = id == null ? null : WorldLife.registry(world).get(WorldLifeRegistry.Part.TRADE_CARAVANS, id);
        return v == null ? null : Caravan.parse(id, v);
    }

    static void save(World world, Caravan c) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRADE_CARAVANS, c.id, c.format());
    }

    static void drop(World world, Store<EntityStore> store, Caravan c) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRADE_CARAVANS, c.id, null);
        Walk.end(store, c.walkKey());
        Ambushes.cancel(store, c.walkKey());
    }

    /** La route est fermée : ses caravanes rentrent (retirées, cargaison perdue pour personne). */
    static void dropRoute(World world, Store<EntityStore> store, String route) {
        for (Caravan c : all(world)) {
            if (c.route.equals(route)) {
                drop(world, store, c);
            }
        }
    }

    public static Caravan of(World world, Ref<EntityStore> npc) {
        String id = npc == null ? null : OWNER.get(npc);
        return id == null ? null : get(world, id);
    }

    static void forget(Ref<EntityStore> ref) {
        OWNER.remove(ref);
    }

    // ---- Départ ----

    /** Fait partir la caravane de `from` vers `to` (si une caravane de ce sens n'est pas déjà en route). */
    static Caravan dispatch(World world, Store<EntityStore> store, TradeRoutes.Route r, Village from, Village to) {
        for (Caravan o : all(world)) {
            if (o.route.equals(r.key()) && o.from.equals(from.id())) {
                return null;
            }
        }
        List<String> cases = TradeRoutes.cleared(r, to.id());
        if (cases.isEmpty()) {
            return null;
        }
        long day = GameClock.day(store);
        Map<String, TradeCatalogue.Source> catalogue = TradeCatalogue.of(world, from, r.key(), day);
        ItemContainer chest = Villages.depositChest(world, from);
        Caravan c = new Caravan(Long.toString(System.currentTimeMillis(), 36) + Integer.toString(new Random().nextInt(1296), 36));
        c.route = r.key();
        c.from = from.id();
        c.to = to.id();
        c.walkers = r.level() >= 2 ? 3 : 2;
        for (String item : cases) {
            TradeCatalogue.Source source = catalogue.get(item);
            if (source == null) {
                continue; // plus produit, plus importé : la case part vide
            }
            int load = TradeGoods.grade(item).load(r.level());
            int n;
            if (source == TradeCatalogue.Source.TERROIR) {
                n = load;
            } else if (chest != null) {
                n = Requests.take(chest, item, load);
            } else {
                n = source.produced() ? load : 0;
            }
            if (n > 0) {
                c.cargo.merge(item, n, Integer::sum);
            }
        }
        if (c.cargo.isEmpty()) {
            TradeRoutes.announce(world, from, Message.translation(TradeRoutes.KEYS + "empty").param("to", TradeRoutes.name(world, to)), NotificationStyle.Warning);
            return null;
        }
        save(world, c);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (commerce) : caravane %s → %s (%s)", from.id(), to.id(), c.format());
        return c;
    }

    // ---- Marche ----

    /** Le pas de toutes les caravanes. */
    static void step(World world, Store<EntityStore> store, List<Vector3d> players, float dt) {
        boolean night = GameClock.isNight(store);
        for (Caravan c : all(world)) {
            Village from = TradeRoutes.village(world, c.from);
            Village to = TradeRoutes.village(world, c.to);
            if (from == null || to == null || c.walkers <= 0 || TradeRoutes.get(world, c.route) == null) {
                drop(world, store, c);
                continue;
            }
            Routes.Path path = Links.path(world, from, to);
            if (c.at >= path.length() - Walk.ARRIVE) {
                arrive(world, store, c, from, to);
                continue;
            }
            boolean moving = !night;
            if (c.ambush == 2) {
                moving = false;
                if (Ambushes.over(world, store, c.walkKey())) {
                    c.ambush = 1;
                }
            }
            Walk walk = Walk.of(c.walkKey());
            boolean wasReal = walk.real();
            People people = from.people();
            c.at = walk.step(world, store, players, path, c.at, dt, c.walkers, moving, from.y(),
                    (i, at, yaw) -> spawnWalker(store, c, people, i, at, yaw));
            if (!wasReal && walk.real()) {
                for (Ref<EntityStore> ref : walk.alive()) {
                    OWNER.put(ref, c.id);
                }
                Routes.Path fresh = Links.refresh(world, from, to);
                if (fresh != path) {
                    double[] was = path.point(c.at);
                    c.at = fresh.closest(was[0], was[1], 0, fresh.length());
                    walk.reset(c.at);
                    path = fresh;
                }
            }
            if (c.ambush == 0 && c.at >= path.length() / 2) {
                c.ambush = 1;
                ambush(world, store, players, c, path, from, to, walk);
            }
            save(world, c);
        }
    }

    /** Tirage à mi-chemin : une chance sur six, une sur douze sur route balisée, une sur deux évitée en territoire gardé. */
    private static void ambush(World world, Store<EntityStore> store, List<Vector3d> players, Caravan c, Routes.Path path, Village from,
                               Village to, Walk walk) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        double[] here = path.point(c.at);
        int odds = Routes.gap(world, from.x() + 0.5, from.z() + 0.5, to.x() + 0.5, to.z() + 0.5) <= 0 ? AMBUSH_ODDS * 2 : AMBUSH_ODDS;
        if (random.nextInt(odds) != 0 || Territories.spared(world, here)) {
            return;
        }
        if (WorldLife.near(players, here[0], here[1], Ambushes.WITNESS)) {
            if (Ambushes.roll(world, store, c.walkKey(), here, path.dir(c.at), from.people(), walk.alive(), players, true)) {
                c.ambush = 2;
            }
            return;
        }
        // Sans témoin : un tiers de chaque marchandise perdu.
        c.cargo.replaceAll((item, n) -> n - Math.max(1, n / 3));
        c.cargo.values().removeIf(n -> n <= 0);
        TradeRoutes.announce(world, to, Message.translation(TradeRoutes.KEYS + "ambushedAway").param("from", TradeRoutes.name(world, from)),
                NotificationStyle.Warning);
    }

    /** Arrivée : cargaison au dépôt, accès ouvert, arrivée comptée, passage sur la liaison. */
    private static void arrive(World world, Store<EntityStore> store, Caravan c, Village from, Village to) {
        long day = GameClock.day(store);
        List<ItemStack> goods = new ArrayList<>();
        for (Map.Entry<String, Integer> e : c.cargo.entrySet()) {
            goods.add(new ItemStack(e.getKey(), e.getValue()));
            TradeAccess.grant(world, to, e.getKey(), day + TradeAccess.DELIVERY_DAYS, day);
        }
        TradeRoutes.deliver(world, to, goods);
        TradeRoutes.Route r = TradeRoutes.get(world, c.route);
        if (r != null) {
            r.arrivals++;
            r.lost = 0;
            TradeRoutes.save(world, r);
        }
        Hamlets.Place hTo = TradeRoutes.hamlet(world, to);
        Hamlets.Place hFrom = TradeRoutes.hamlet(world, from);
        if (hTo != null) {
            Links.pass(world, to.id(), day, Math.max(1, c.walkers));
            if (hFrom == null) {
                Allegiance.merchantArrived(world, store, hTo, from, true);
            }
        } else if (hFrom != null) {
            Links.pass(world, from.id(), day, Math.max(1, c.walkers));
        } else {
            Links.pass(world, Links.key(from.id(), to.id()), day, Math.max(1, c.walkers));
        }
        Villages.addEssor(to, 1);
        TradeRoutes.announce(world, to, Message.translation(TradeRoutes.KEYS + "arrived").param("from", TradeRoutes.name(world, from))
                .param("goods", goodsLine(c.cargo)), NotificationStyle.Success);
        drop(world, store, c);
    }

    /** « 6 x Planches, 2 x Épices » (noms des objets). */
    static Message goodsLine(Map<String, Integer> cargo) {
        Message line = null;
        for (Map.Entry<String, Integer> e : cargo.entrySet()) {
            Message one = Message.translation(TradeRoutes.KEYS + "goods").param("count", e.getValue())
                    .param("item", Message.translation(TradeGoods.itemKey(e.getKey())));
            line = line == null ? one : Message.translation(TradeRoutes.KEYS + "goodsMore").param("a", line).param("b", one);
        }
        return line == null ? Message.translation(TradeRoutes.KEYS + "goodsNone") : line;
    }

    static Ref<EntityStore> spawnWalker(Store<EntityStore> store, Caravan c, People people, int i, Vector3d at, float yaw) {
        Ref<EntityStore> ref = WorldLife.spawn(store, i == 0 ? Travellers.peddlerRole(people) : Travellers.travellerRole(people), at, yaw);
        if (ref == null) {
            return null;
        }
        WorldLife.side(ref, c.walkKey(), 0);
        WorldLife.talker(ref, TradeCaravans::talk);
        WorldLife.mortal(ref, (world, npc, where, killer) -> died(world, c.id, npc, where, killer));
        OWNER.put(ref, c.id);
        return ref;
    }

    private static void died(World world, String id, Ref<EntityStore> npc, Vector3d where, PlayerRef killer) {
        OWNER.remove(npc);
        Caravan c = get(world, id);
        if (c == null) {
            return;
        }
        c.walkers--;
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (c.walkers > 0) {
            save(world, c);
            return;
        }
        // Plus de porteurs : la cargaison tombe au sol, la route compte une perte.
        if (where != null && !c.cargo.isEmpty()) {
            List<ItemStack> goods = new ArrayList<>();
            c.cargo.forEach((item, n) -> goods.add(new ItemStack(item, n)));
            Deposits.drop(world, new int[] {(int) Math.floor(where.x()), (int) Math.floor(where.y()) + 1, (int) Math.floor(where.z())}, goods);
        }
        Village from = TradeRoutes.village(world, c.from);
        Village to = TradeRoutes.village(world, c.to);
        TradeRoutes.Route r = TradeRoutes.get(world, c.route);
        if (r != null) {
            r.lost++;
            boolean down = r.lost >= TradeRoutes.LOST_LIMIT && r.level > 1;
            if (r.lost >= TradeRoutes.LOST_LIMIT) {
                r.lost = 0;
                if (down) {
                    r.level--;
                    r.exportsA.subList(Math.min(r.level, r.exportsA.size()), r.exportsA.size()).clear();
                    r.exportsB.subList(Math.min(r.level, r.exportsB.size()), r.exportsB.size()).clear();
                }
            }
            TradeRoutes.save(world, r);
            if (down && from != null && to != null) {
                Message m = Message.translation(TradeRoutes.KEYS + "downgraded").param("a", TradeRoutes.name(world, from))
                        .param("b", TradeRoutes.name(world, to)).param("level", r.level);
                TradeRoutes.announce(world, from, m, NotificationStyle.Warning);
                TradeRoutes.announce(world, to, m, NotificationStyle.Warning);
            }
        }
        if (from != null && to != null) {
            Message m = Message.translation(TradeRoutes.KEYS + "lost").param("from", TradeRoutes.name(world, from)).param("to", TradeRoutes.name(world, to));
            TradeRoutes.announce(world, from, m, NotificationStyle.Warning);
            TradeRoutes.announce(world, to, m, NotificationStyle.Warning);
        }
        drop(world, store, c);
    }

    // ---- Dialogue ----

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Dialogue dialogue = of(world, npc) == null ? null : Dialogue.get(DIALOGUE);
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    /** Troc du caravanier : celui des voyageurs de son peuple, au rang Toléré dans son village. */
    static boolean openShop(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Caravan c) {
        Village v = TradeRoutes.village(world, c.from);
        if (v == null) {
            return false;
        }
        if (!Reputations.rank(store, ref, v).atLeast(Rank.TOLERE)) {
            DialogueSpeech.say(player, Message.translation(TradeRoutes.KEYS + "shopRank").param("village", TradeRoutes.name(world, v)));
            return false;
        }
        return Shops.open(store, ref, player, v, Travellers.shop(v.people()));
    }

    /** « Que portes-tu ? » */
    static boolean where(World world, Store<EntityStore> store, PlayerRef player, Caravan c) {
        Village from = TradeRoutes.village(world, c.from);
        Village to = TradeRoutes.village(world, c.to);
        if (from == null || to == null) {
            return false;
        }
        DialogueSpeech.say(player, Message.translation(TradeRoutes.KEYS + "where").param("from", TradeRoutes.name(world, from))
                .param("to", TradeRoutes.name(world, to)).param("goods", goodsLine(c.cargo)));
        return true;
    }

    /** Rumeurs : les caravanes en route. */
    static List<Message> rumours(World world) {
        List<Message> out = new ArrayList<>();
        for (Caravan c : all(world)) {
            Village from = TradeRoutes.village(world, c.from);
            Village to = TradeRoutes.village(world, c.to);
            if (from != null && to != null) {
                out.add(Message.translation(TradeRoutes.KEYS + "rumour").param("from", TradeRoutes.name(world, from)).param("to", TradeRoutes.name(world, to)));
            }
        }
        return out;
    }

    static Message describe(World world, Caravan c) {
        Village from = TradeRoutes.village(world, c.from);
        Village to = TradeRoutes.village(world, c.to);
        int length = from == null || to == null ? 0 : (int) Links.path(world, from, to).length();
        return Message.translation(TradeRoutes.KEYS + "cmd.caravan").param("from", from == null ? Message.raw(c.from) : TradeRoutes.name(world, from))
                .param("to", to == null ? Message.raw(c.to) : TradeRoutes.name(world, to)).param("at", (int) c.at).param("length", length)
                .param("walkers", c.walkers).param("goods", goodsLine(c.cargo));
    }

    public static void clearAll() {
        OWNER.clear();
    }
}
