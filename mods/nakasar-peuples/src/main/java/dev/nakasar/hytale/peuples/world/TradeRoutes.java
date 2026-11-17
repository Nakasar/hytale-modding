package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.HamletRegistry;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * Les routes commerciales (proposition « routes commerciales et luxes », Kevin, 16 novembre 2026). Une route relie un
 * village à un autre village de sa liaison ({@value Links#MAX_LENGTH} blocs au plus, relation au-dessus de Rival) ou à
 * un lieu-dit posé (sans embargo). Un joueur Ami du village et Toléré du partenaire l'ouvre à l'onglet Commerce du
 * panneau contre {@value #OFFERING} faveurs ; un village l'ouvre aussi seul au conseil du matin (une chance sur
 * {@value #AUTO_ODDS}, {@value #AUTO_MAX} routes autonomes au plus par monde).
 *
 * <p>Places : palier 1, 2, 3 → 1, 2, 3 routes (plus la Halle marchande du fil des bâtiments) ; un lieu-dit en a 2
 * (3 animé). Niveaux I à III : autant de cases d'export de chaque côté, une caravane tous les 3, 2 puis 1 jours. Le
 * niveau II demande une route entièrement balisée, {@value #ARRIVALS_2} arrivées et le palier 2 des deux côtés ; le
 * niveau III, {@value #ARRIVALS_3} arrivées, le palier 3 d'un des deux et une auberge si la liaison dépasse
 * {@value Inns#MIN_LENGTH} blocs. Trois caravanes perdues d'affilée font perdre un niveau.
 *
 * <p>Équilibre : le poids des exportations d'un côté (commune 1, fine 2, luxe 3 par case) doit couvrir celui de ses
 * importations ; sinon le manque se paie en crédit ({@value #CREDIT_PER_FAVOUR} par faveur versée), faute de quoi la
 * case importée la plus lourde reste à quai.
 *
 * <p>Une relation qui tombe au rang de rival, ou un embargo, suspend la route ; au bout de {@value #BREAK_DAYS} jours
 * elle est rompue.
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#TRADE_ROUTES}) :
 * {@code a|b = niveau|arrivées|pertes d'affilée|prochain départ|suspendue depuis|auto|crédit a|crédit b|exports a|exports b},
 * exports en ids séparés par des virgules ; plus les boîtes {@code ~inbox:<village> = objet:n,...} (livraisons qui
 * attendent que le dépôt soit chargé ou ait de la place).
 */
public final class TradeRoutes {

    public static final int OFFERING = 5;
    public static final int RAISE_OFFERING = 5;
    public static final int AUTO_ODDS = 10;
    public static final int AUTO_MAX = 6;
    public static final int ARRIVALS_2 = 8;
    public static final int ARRIVALS_3 = 20;
    public static final int LOST_LIMIT = 3;
    public static final int BREAK_DAYS = 14;
    public static final int CREDIT_PER_FAVOUR = 3;
    public static final int MAX_LEVEL = 3;
    public static final String KEYS = WorldLife.KEYS + "trade.";
    private static final String INBOX = "~inbox:";

    /** Une route (état sauvé). `a` a l'id le plus petit. */
    public static final class Route {
        final String key;
        final String a;
        final String b;
        int level = 1;
        int arrivals;
        int lost;
        long next = Long.MIN_VALUE;
        long suspended = Long.MIN_VALUE;
        boolean auto;
        int creditA;
        int creditB;
        final List<String> exportsA = new ArrayList<>();
        final List<String> exportsB = new ArrayList<>();

        Route(String a, String b) {
            this.key = Links.key(a, b);
            this.a = a.compareTo(b) <= 0 ? a : b;
            this.b = a.compareTo(b) <= 0 ? b : a;
        }

        static Route parse(String key, String v) {
            int cut = key.indexOf('|');
            String[] p = v.split("\\|", -1);
            if (cut <= 0 || p.length < 10) {
                return null;
            }
            try {
                Route r = new Route(key.substring(0, cut), key.substring(cut + 1));
                r.level = Math.max(1, Math.min(MAX_LEVEL, Integer.parseInt(p[0])));
                r.arrivals = Integer.parseInt(p[1]);
                r.lost = Integer.parseInt(p[2]);
                r.next = Long.parseLong(p[3]);
                r.suspended = Long.parseLong(p[4]);
                r.auto = "1".equals(p[5]);
                r.creditA = Integer.parseInt(p[6]);
                r.creditB = Integer.parseInt(p[7]);
                list(r.exportsA, p[8]);
                list(r.exportsB, p[9]);
                return r;
            } catch (NumberFormatException e) {
                return null;
            }
        }

        private static void list(List<String> out, String s) {
            for (String item : s.split(",")) {
                if (!item.isBlank()) {
                    out.add(item);
                }
            }
        }

        String format() {
            return level + "|" + arrivals + "|" + lost + "|" + next + "|" + suspended + "|" + (auto ? 1 : 0) + "|" + creditA + "|"
                    + creditB + "|" + String.join(",", exportsA) + "|" + String.join(",", exportsB);
        }

        public String key() {
            return key;
        }

        public int level() {
            return level;
        }

        public int arrivals() {
            return arrivals;
        }

        public int lost() {
            return lost;
        }

        public boolean auto() {
            return auto;
        }

        public boolean suspended() {
            return suspended != Long.MIN_VALUE;
        }

        public long suspendedSince() {
            return suspended;
        }

        public long next() {
            return next;
        }

        public boolean has(String id) {
            return a.equals(id) || b.equals(id);
        }

        public String other(String id) {
            return a.equals(id) ? b : a;
        }

        /** Ce que `id` envoie à l'autre bout (modifiable). */
        public List<String> exportsOf(String id) {
            return a.equals(id) ? exportsA : exportsB;
        }

        /** Ce que `id` reçoit de l'autre bout. */
        public List<String> importsOf(String id) {
            return a.equals(id) ? exportsB : exportsA;
        }

        public int credit(String id) {
            return a.equals(id) ? creditA : creditB;
        }

        void addCredit(String id, int n) {
            if (a.equals(id)) {
                creditA = Math.max(0, creditA + n);
            } else {
                creditB = Math.max(0, creditB + n);
            }
        }

        /** Jours entre deux caravanes (3, 2 puis 1). */
        public int interval() {
            return 4 - level;
        }
    }

    private TradeRoutes() {
    }

    // ---- Registre ----

    public static List<Route> all(World world) {
        List<Route> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.TRADE_ROUTES).entrySet()) {
            if (e.getKey().startsWith("~")) {
                continue;
            }
            Route r = Route.parse(e.getKey(), e.getValue());
            if (r != null) {
                out.add(r);
            }
        }
        return out;
    }

    public static Route get(World world, String key) {
        String v = key == null ? null : WorldLife.registry(world).get(WorldLifeRegistry.Part.TRADE_ROUTES, key);
        return v == null ? null : Route.parse(key, v);
    }

    public static Route between(World world, Village x, Village y) {
        return get(world, Links.key(x.id(), y.id()));
    }

    static void save(World world, Route r) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRADE_ROUTES, r.key, r.format());
    }

    static void remove(World world, Route r) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRADE_ROUTES, r.key, null);
    }

    /** Les routes d'un village (ou d'un lieu-dit, id {@code H:<lieu-dit>}). */
    public static List<Route> of(World world, Village v) {
        List<Route> out = new ArrayList<>();
        for (Route r : all(world)) {
            if (r.has(v.id())) {
                out.add(r);
            }
        }
        return out;
    }

    /** Ce que le village importe par ses routes actives autres que `except` (réexportation). */
    static Set<String> importedElsewhere(World world, Village v, String except) {
        Set<String> out = new LinkedHashSet<>();
        for (Route r : of(world, v)) {
            if (!r.key.equals(except) && !r.suspended()) {
                out.addAll(r.importsOf(v.id()));
            }
        }
        return out;
    }

    // ---- Ends ----

    public static Village village(World world, String id) {
        return id == null ? null : Villages.registry(world).byId(id);
    }

    /** Le lieu-dit d'un bout de route, ou null (un village). */
    public static Hamlets.Place hamlet(World world, Village v) {
        return v != null && v.isHamlet() ? Hamlets.get(world, v.id().substring(HamletRegistry.PREFIX.length())) : null;
    }

    /** Nom affiché d'un bout de route. */
    public static Message name(World world, Village v) {
        Hamlets.Place h = hamlet(world, v);
        return h != null ? h.name() : Message.raw(v.name());
    }

    /** Places de routes du village : son palier (plus la Halle marchande) ; lieu-dit : 2, 3 s'il est animé. */
    public static int slots(World world, Village v, long day) {
        Hamlets.Place h = hamlet(world, v);
        if (h != null) {
            return Hamlets.lively(world, h, day) ? 3 : 2;
        }
        return Math.max(0, Math.min(3, v.tier())) + hallLevel(v);
    }

    /**
     * Niveau de la Halle marchande (fil « familles de bâtiments ») : une place de route de plus par niveau. Tant que ce
     * bâtiment n'existe pas dans le mod, 0.
     */
    static int hallLevel(Village v) {
        for (var ws : v.workshops()) {
            if (ws.id() != null && ws.id().endsWith("_Halle")) {
                return ws.level();
            }
        }
        return 0;
    }

    public static int used(World world, Village v) {
        return of(world, v).size();
    }

    /** Distance cœur à cœur (place du marché pour un lieu-dit). */
    static double distance(Village x, Village y) {
        return WorldLife.distance(x, y);
    }

    /**
     * Partenaires possibles du village (hors routes ouvertes) : villages de ses liaisons au-dessus de Rival, lieux-dits
     * posés à moins de {@value Links#MAX_LENGTH} blocs sans embargo. Du plus proche au plus loin.
     */
    public static List<Village> candidates(World world, Village v) {
        List<Village> out = new ArrayList<>();
        if (v.isHamlet()) {
            return out;
        }
        for (Links.Link l : Links.of(world, v)) {
            Village o = l.other(v.id());
            if (o != null && !o.isHamlet() && Relations.value(world, v, o) > Relations.RIVAL && between(world, v, o) == null) {
                out.add(o);
            }
        }
        for (Hamlets.Place h : Hamlets.all(world)) {
            Village hv = h.stage() == Hamlets.BUILT ? Hamlets.state(world, h) : null;
            if (hv != null && Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z())) <= Links.MAX_LENGTH
                    && !Allegiance.embargoed(world, h, v) && between(world, v, hv) == null) {
                out.add(hv);
            }
        }
        out.sort((x, y) -> Double.compare(distance(v, x), distance(v, y)));
        return out;
    }

    /** Pourquoi la route ne peut pas s'ouvrir entre `v` et `o` (raison, ou null). */
    public static Message blocked(World world, Village v, Village o, long day) {
        if (between(world, v, o) != null) {
            return Message.translation(KEYS + "why.exists");
        }
        if (used(world, v) >= slots(world, v, day)) {
            return Message.translation(KEYS + "why.slots").param("village", name(world, v)).param("slots", slots(world, v, day));
        }
        if (used(world, o) >= slots(world, o, day)) {
            return Message.translation(KEYS + "why.slots").param("village", name(world, o)).param("slots", slots(world, o, day));
        }
        if (!candidates(world, v).contains(o)) {
            return Message.translation(KEYS + "why.partner").param("village", name(world, o));
        }
        return null;
    }

    // ---- Joueur ----

    private static boolean pay(Store<EntityStore> store, Ref<EntityStore> ref, Village v, int n) {
        String favour = v.people().favorItem();
        if (WorldLife.count(store, ref, favour::equals) < n) {
            return false;
        }
        WorldLife.take(store, ref, favour::equals, n);
        return true;
    }

    /** Ouverture par un joueur (Ami de `v`, Toléré de `o`, {@value #OFFERING} faveurs). Rend la raison du refus, ou null. */
    public static Message open(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, Village o) {
        long day = GameClock.day(store);
        if (!Reputations.rank(store, ref, v).atLeast(Rank.AMI)) {
            return Message.translation(KEYS + "why.rankAmi").param("village", v.name());
        }
        if (!Reputations.rank(store, ref, o).atLeast(Rank.TOLERE)) {
            return Message.translation(KEYS + "why.rankTolere").param("village", name(world, o));
        }
        Message why = blocked(world, v, o, day);
        if (why != null) {
            return why;
        }
        if (!pay(store, ref, v, OFFERING)) {
            return Message.translation(KEYS + "why.offering").param("count", OFFERING);
        }
        create(world, v, o, false, day);
        return null;
    }

    static Route create(World world, Village v, Village o, boolean auto, long day) {
        Route r = new Route(v.id(), o.id());
        r.auto = auto;
        r.next = day + 1;
        save(world, r);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (commerce) : route %s ouverte%s", r.key, auto ? " (autonome)" : "");
        Message m = Message.translation(KEYS + "opened").param("a", name(world, v)).param("b", name(world, o));
        announce(world, v, m, NotificationStyle.Success);
        announce(world, o, m, NotificationStyle.Success);
        return r;
    }

    /** Ce qui manque pour passer la route au niveau suivant (raison, ou null). */
    public static Message raiseBlocked(World world, Route r) {
        Village x = village(world, r.a);
        Village y = village(world, r.b);
        if (x == null || y == null) {
            return Message.translation(KEYS + "why.partner").param("village", "?");
        }
        if (r.level >= MAX_LEVEL) {
            return Message.translation(KEYS + "why.maxLevel");
        }
        if (r.suspended()) {
            return Message.translation(KEYS + "why.suspended");
        }
        if (r.level == 1) {
            if (Routes.gap(world, x.x() + 0.5, x.z() + 0.5, y.x() + 0.5, y.z() + 0.5) > 0) {
                return Message.translation(KEYS + "why.beacons");
            }
            if (r.arrivals < ARRIVALS_2) {
                return Message.translation(KEYS + "why.arrivals").param("count", r.arrivals).param("need", ARRIVALS_2);
            }
            if (x.tier() < 2 || y.tier() < 2) {
                return Message.translation(KEYS + "why.tier2");
            }
            return null;
        }
        if (r.arrivals < ARRIVALS_3) {
            return Message.translation(KEYS + "why.arrivals").param("count", r.arrivals).param("need", ARRIVALS_3);
        }
        if (Math.max(x.tier(), y.tier()) < 3) {
            return Message.translation(KEYS + "why.tier3");
        }
        if (!x.isHamlet() && !y.isHamlet() && distance(x, y) >= Inns.MIN_LENGTH) {
            Inns.Inn inn = Inns.get(world, r.key);
            if (inn == null || !inn.open()) {
                return Message.translation(KEYS + "why.inn").param("length", Inns.MIN_LENGTH);
            }
        }
        return null;
    }

    /** Passage au niveau suivant par un joueur Ami du village (contre {@value #RAISE_OFFERING} faveurs). */
    public static Message raise(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, Route r) {
        if (!Reputations.rank(store, ref, v).atLeast(Rank.AMI)) {
            return Message.translation(KEYS + "why.rankAmi").param("village", v.name());
        }
        Message why = raiseBlocked(world, r);
        if (why != null) {
            return why;
        }
        if (!pay(store, ref, v, RAISE_OFFERING)) {
            return Message.translation(KEYS + "why.offering").param("count", RAISE_OFFERING);
        }
        r.level++;
        r.auto = false; // un joueur s'en occupe : les cases ne sont plus choisies par le conseil
        save(world, r);
        Message m = Message.translation(KEYS + "raised").param("a", name(world, village(world, r.a)))
                .param("b", name(world, village(world, r.b))).param("level", r.level);
        announce(world, village(world, r.a), m, NotificationStyle.Success);
        announce(world, village(world, r.b), m, NotificationStyle.Success);
        return null;
    }

    /**
     * Pose `item` dans la case `slot` des exportations de `sender` (null : vide la case). Le joueur doit être Ami du
     * village dont il ouvre le panneau (`board`).
     */
    public static Message setCase(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village board, Route r, Village sender,
                                  int slot, String item) {
        if (!Reputations.rank(store, ref, board).atLeast(Rank.AMI)) {
            return Message.translation(KEYS + "why.rankAmi").param("village", board.name());
        }
        List<String> list = r.exportsOf(sender.id());
        if (slot < 0 || slot >= r.level) {
            return Message.translation(KEYS + "why.slot");
        }
        if (item != null) {
            Village receiver = village(world, r.other(sender.id()));
            if (receiver != null && !TradeGoods.allowed(receiver.people(), item)) {
                return Message.translation(KEYS + "why.metal");
            }
            if (list.contains(item)) {
                return Message.translation(KEYS + "why.twice");
            }
        }
        if (item == null) {
            if (slot < list.size()) {
                list.remove(slot);
            }
        } else if (slot < list.size()) {
            list.set(slot, item);
        } else {
            list.add(item);
        }
        r.auto = false;
        save(world, r);
        return null;
    }

    /** Un joueur verse une faveur du village au crédit de la route (côté du village). */
    public static Message payCredit(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, Route r) {
        if (!pay(store, ref, v, 1)) {
            return Message.translation(KEYS + "why.offering").param("count", 1);
        }
        r.addCredit(v.id(), CREDIT_PER_FAVOUR);
        save(world, r);
        return null;
    }

    /** Fermeture de la route par un joueur Ami (ou la commande). */
    public static Message close(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, Route r) {
        if (ref != null && !Reputations.rank(store, ref, v).atLeast(Rank.AMI)) {
            return Message.translation(KEYS + "why.rankAmi").param("village", v.name());
        }
        drop(world, store, r, "closed");
        return null;
    }

    static void drop(World world, Store<EntityStore> store, Route r, String reason) {
        remove(world, r);
        TradeCaravans.dropRoute(world, store, r.key);
        Message m = Message.translation(KEYS + reason).param("a", name(world, village(world, r.a)))
                .param("b", name(world, village(world, r.b)));
        announce(world, village(world, r.a), m, NotificationStyle.Warning);
        announce(world, village(world, r.b), m, NotificationStyle.Warning);
    }

    // ---- Équilibre ----

    public static int weight(List<String> items) {
        int w = 0;
        for (String item : items) {
            w += TradeGoods.grade(item).weight();
        }
        return w;
    }

    /** Manque de poids de `id` sur la route (importations moins exportations ; 0 si équilibré). */
    public static int deficit(Route r, String id) {
        return Math.max(0, weight(r.importsOf(id)) - weight(r.exportsOf(id)));
    }

    /**
     * Les cases que la caravane vers `receiver` peut porter : celles que couvrent ses exportations plus son crédit, en
     * retirant d'abord la case la plus lourde. Le crédit n'est pas débité ici : {@link #spendCredit} le fait une fois la
     * cargaison chargée.
     */
    static List<String> cleared(Route r, String receiver) {
        List<String> cases = new ArrayList<>(r.importsOf(receiver));
        int budget = weight(r.exportsOf(receiver)) + r.credit(receiver);
        cases.sort((x, y) -> TradeGoods.grade(y).weight() - TradeGoods.grade(x).weight());
        while (!cases.isEmpty() && weight(cases) > budget) {
            cases.remove(0);
        }
        return cases;
    }

    /** Débite le crédit de `receiver` du manque de poids de ce que la caravane porte vraiment. */
    static void spendCredit(Route r, String receiver, List<String> loaded) {
        int used = weight(loaded) - weight(r.exportsOf(receiver));
        if (used > 0) {
            r.addCredit(receiver, -Math.min(used, r.credit(receiver)));
        }
    }

    // ---- Matin ----

    /** Une fois par jour : suspensions et ruptures, départs des caravanes, routes ouvertes par les villages. */
    static void morning(World world, Store<EntityStore> store, long day, Random random) {
        for (Route r : all(world)) {
            Village x = village(world, r.a);
            Village y = village(world, r.b);
            if (x == null || y == null) {
                remove(world, r);
                TradeCaravans.dropRoute(world, store, r.key);
                continue;
            }
            boolean broken = brokenTie(world, x, y);
            if (broken && !r.suspended()) {
                r.suspended = day;
                save(world, r);
                Message m = Message.translation(KEYS + "suspended").param("a", name(world, x)).param("b", name(world, y))
                        .param("days", BREAK_DAYS);
                announce(world, x, m, NotificationStyle.Warning);
                announce(world, y, m, NotificationStyle.Warning);
                continue;
            }
            if (broken) {
                if (day - r.suspended >= BREAK_DAYS) {
                    drop(world, store, r, "broken");
                }
                continue;
            }
            if (r.suspended()) {
                r.suspended = Long.MIN_VALUE;
            }
            if (r.auto) {
                autoCases(world, r, x, y, day);
                if (r.exportsA.isEmpty()) {
                    // Plus rien à échanger dans les deux sens : la route autonome libère ses places.
                    drop(world, store, r, "idle");
                    continue;
                }
            }
            if (day >= r.next) {
                TradeCaravans.dispatch(world, store, r, x, y);
                TradeCaravans.dispatch(world, store, r, y, x);
                r.next = day + r.interval();
            }
            save(world, r);
        }
        council(world, day, random);
    }

    /** Relation tombée au rang de rival (villages), ou embargo (lieu-dit). */
    static boolean brokenTie(World world, Village x, Village y) {
        Hamlets.Place hx = hamlet(world, x);
        Hamlets.Place hy = hamlet(world, y);
        if (hx == null && hy == null) {
            return Relations.value(world, x, y) <= Relations.RIVAL;
        }
        if (hx != null && hy == null) {
            return Allegiance.embargoed(world, hx, y);
        }
        if (hy != null && hx == null) {
            return Allegiance.embargoed(world, hy, x);
        }
        return false;
    }

    /** Conseil du matin : un village avec une place libre ouvre une route seul (une chance sur {@value #AUTO_ODDS}). */
    private static void council(World world, long day, Random random) {
        int autos = 0;
        for (Route r : all(world)) {
            if (r.auto) {
                autos++;
            }
        }
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        Collections.shuffle(villages, random);
        for (Village v : villages) {
            if (autos >= AUTO_MAX) {
                return;
            }
            if (v.isHamlet() || used(world, v) >= slots(world, v, day) || random.nextInt(AUTO_ODDS) != 0) {
                continue;
            }
            for (Village o : candidates(world, v)) {
                if (used(world, o) >= slots(world, o, day)) {
                    continue;
                }
                Route trial = new Route(v.id(), o.id());
                autoCases(world, trial, v, o, day);
                if (trial.exportsA.isEmpty()) {
                    continue; // rien à échanger : pas de route morte qui occuperait les places
                }
                Route r = create(world, v, o, true, day);
                r.exportsA.addAll(trial.exportsA);
                r.exportsB.addAll(trial.exportsB);
                save(world, r);
                autos++;
                break;
            }
        }
    }

    /**
     * Cases d'une route autonome : chaque bout exporte ce qu'il produit et dont l'autre manque, par paires de même classe
     * (luxe contre luxe, puis fine, puis commune) pour que l'équilibre tienne sans crédit ; au plus le niveau de la route.
     */
    static void autoCases(World world, Route r, Village x, Village y, long day) {
        List<String> fromX = new ArrayList<>(pickAuto(world, r, x, y, day));
        List<String> fromY = new ArrayList<>(pickAuto(world, r, y, x, day));
        List<String> outX = r.exportsOf(x.id());
        List<String> outY = r.exportsOf(y.id());
        outX.clear();
        outY.clear();
        for (TradeGoods.Grade g : new TradeGoods.Grade[] {TradeGoods.Grade.LUXURY, TradeGoods.Grade.FINE, TradeGoods.Grade.COMMON}) {
            while (outX.size() < r.level) {
                String a = first(fromX, g);
                String b = first(fromY, g);
                if (a == null || b == null) {
                    break;
                }
                outX.add(a);
                outY.add(b);
                fromX.remove(a);
                fromY.remove(b);
            }
        }
    }

    private static String first(List<String> items, TradeGoods.Grade g) {
        for (String item : items) {
            if (TradeGoods.grade(item) == g) {
                return item;
            }
        }
        return null;
    }

    private static List<String> pickAuto(World world, Route r, Village sender, Village receiver, long day) {
        Map<String, TradeCatalogue.Source> cat = TradeCatalogue.of(world, sender, r.key, day);
        // Ce qui manque au receveur d'abord (sans exclure ce qu'il a déjà : la route garde ses cases d'un jour à l'autre).
        List<String> lacking = new ArrayList<>();
        List<String> rest = new ArrayList<>();
        TradeGoods.Luxury own = TradeGoods.terroir(receiver.people());
        for (String item : cat.keySet()) {
            if (!TradeGoods.allowed(receiver.people(), item) || (own != null && own.item().equals(item))) {
                continue;
            }
            (TradeAccess.has(world, receiver, item, day) ? rest : lacking).add(item);
        }
        lacking.addAll(rest);
        return lacking;
    }

    // ---- Livraisons ----

    /** Livre au dépôt de `v` ; ce qui ne rentre pas (ou tout, dépôt non chargé) attend dans la boîte du village. */
    static void deliver(World world, Village v, List<ItemStack> goods) {
        ItemContainer chest = Villages.depositChest(world, v);
        Map<String, Integer> left = inbox(world, v);
        for (ItemStack s : goods) {
            ItemStack rest = chest == null ? s : chest.addItemStack(s).getRemainder();
            if (!ItemStack.isEmpty(rest)) {
                left.merge(rest.getItemId(), rest.getQuantity(), Integer::sum);
            }
        }
        saveInbox(world, v, left);
    }

    static Map<String, Integer> inbox(World world, Village v) {
        Map<String, Integer> out = new LinkedHashMap<>();
        String s = WorldLife.registry(world).get(WorldLifeRegistry.Part.TRADE_ROUTES, INBOX + v.id());
        if (s == null) {
            return out;
        }
        for (String part : s.split(",")) {
            int cut = part.lastIndexOf(':');
            if (cut > 0) {
                try {
                    out.merge(part.substring(0, cut), Integer.parseInt(part.substring(cut + 1)), Integer::sum);
                } catch (NumberFormatException ignored) {
                    // entrée abîmée
                }
            }
        }
        return out;
    }

    private static void saveInbox(World world, Village v, Map<String, Integer> items) {
        StringBuilder b = new StringBuilder();
        for (Map.Entry<String, Integer> e : items.entrySet()) {
            if (e.getValue() > 0) {
                b.append(b.length() == 0 ? "" : ",").append(e.getKey()).append(':').append(e.getValue());
            }
        }
        WorldLife.registry(world).put(WorldLifeRegistry.Part.TRADE_ROUTES, INBOX + v.id(), b.length() == 0 ? null : b.toString());
    }

    /** Vide les boîtes dans les dépôts chargés (pas lent du monde vivant). */
    static void flushInboxes(World world) {
        for (String key : new ArrayList<>(WorldLife.registry(world).part(WorldLifeRegistry.Part.TRADE_ROUTES).keySet())) {
            if (!key.startsWith(INBOX)) {
                continue;
            }
            Village v = village(world, key.substring(INBOX.length()));
            if (v == null) {
                WorldLife.registry(world).put(WorldLifeRegistry.Part.TRADE_ROUTES, key, null);
                continue;
            }
            ItemContainer chest = Villages.depositChest(world, v);
            if (chest == null) {
                continue;
            }
            Map<String, Integer> items = inbox(world, v);
            Map<String, Integer> left = new LinkedHashMap<>();
            for (Map.Entry<String, Integer> e : items.entrySet()) {
                ItemStack rest = chest.addItemStack(new ItemStack(e.getKey(), e.getValue())).getRemainder();
                if (!ItemStack.isEmpty(rest)) {
                    left.put(e.getKey(), rest.getQuantity());
                }
            }
            saveInbox(world, v, left);
        }
    }

    static void announce(World world, Village v, Message m, NotificationStyle style) {
        if (v != null && !v.isHamlet()) {
            Chantiers.announce(world, v, m, null, style);
        }
    }

    /** Lignes de la commande. */
    static Message describe(World world, Route r) {
        Village x = village(world, r.a);
        Village y = village(world, r.b);
        return Message.translation(KEYS + "cmd.line").param("a", x == null ? Message.raw(r.a) : name(world, x))
                .param("b", y == null ? Message.raw(r.b) : name(world, y)).param("level", r.level).param("arrivals", r.arrivals)
                .param("next", r.next).param("auto", r.auto ? "A" : "J").param("exportsA", String.join(", ", r.exportsA))
                .param("exportsB", String.join(", ", r.exportsB));
    }
}
