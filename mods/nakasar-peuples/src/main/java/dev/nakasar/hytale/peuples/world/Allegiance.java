package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Deposits;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import dev.nakasar.hytale.peuples.workshop.Workshops;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * L'allégeance des lieux-dits (GDD « Villages et lieux-dits : allégeance et conquête », Kevin, 16 novembre 2026).
 *
 * <p><b>Influence.</b> Chaque village à moins de {@value #RANGE} blocs a une influence de {@value #MIN} à {@value #MAX}
 * sur chaque lieu-dit (le village d'origine part à +{@value #ORIGIN_START}). Le commerce la fait monter (marchand
 * +{@value #MERCHANT}, caravane +{@value #CARAVAN}, commande d'un joueur aux couleurs du village +{@value #ORDER},
 * tribut +{@value #TRIBUTE}, gardes qui repoussent une attaque +{@value #DEFENDED}), le tort la fait baisser (marchand
 * tué par quelqu'un aux couleurs du village {@value #MERCHANT_KILLED}, habitant tué {@value #RESIDENT_KILLED},
 * expédition contre le lieu-dit {@value #EXPEDITION_TARGET}, contre un lieu-dit voisin {@value #EXPEDITION_NEAR},
 * propriétaire qui laisse prendre le lieu-dit sans garde {@value #ABANDONED}). Tous les {@value #DRIFT_DAYS} jours,
 * chaque influence revient d'un point vers 0.
 *
 * <p><b>Propriétaire.</b> Un lieu-dit change de main par une ambassade réussie ({@link Embassies}), par ralliement
 * spontané (influence ≥ {@value #RALLY} pendant {@value #RALLY_DAYS} jours et {@value #RALLY_LEAD} points devant le
 * propriétaire, s'il reste une place au village), par conquête ({@link Sieges}) ; il se libère par sécession (influence
 * du propriétaire sous {@value #SECESSION} {@value #SECESSION_DAYS} jours de suite, sauf pendant l'occupation). Un
 * village tient au plus 1 lieu-dit au palier 2, 3 au palier 3, plus un par niveau de sa Maison du conseil.
 *
 * <p><b>Administration.</b> Le propriétaire garde le lieu-dit ({@link Garrisons}), en reçoit +{@value #ESSOR_PER_DAY}
 * d'essor par jour et un tribut chaque semaine (deux porteurs), y commerce deux fois plus souvent ; ses rivaux n'y
 * envoient plus de marchands et les joueurs Étrangers ou pires chez lui n'y troquent plus (embargo). Ses bannières et
 * son fanion flottent sur le lieu-dit ({@link Banners}).
 *
 * <p>États sauvés : {@link WorldLifeRegistry.Part#ALLEGIANCE}
 * {@code lieu-dit = propriétaire|depuis|occupé jusqu'au jour|jours bas|village du ralliement|jours du ralliement|dernier tribut},
 * plus les marques {@code ~letter:<lieu-dit>}, {@code ~cool:<lieu-dit>|<village>}, {@code ~expcool:<village>},
 * {@code ~drift}, {@code ~news} ; {@link WorldLifeRegistry.Part#INFLUENCE} {@code lieu-dit|village = valeur}.
 */
public final class Allegiance {

    public static final String KEYS = Heraldry.KEYS;
    public static final int RANGE = HamletTrips.RANGE;
    public static final int MIN = -100;
    public static final int MAX = 100;
    public static final int ORIGIN_START = 10;
    public static final int DRIFT_DAYS = 3;
    public static final int MERCHANT = 3;
    public static final int CARAVAN = 6;
    public static final int ORDER = 2;
    public static final int TRIBUTE = 1;
    public static final int DEFENDED = 10;
    public static final int MERCHANT_KILLED = -10;
    public static final int RESIDENT_KILLED = -15;
    public static final int EXPEDITION_TARGET = -40;
    public static final int EXPEDITION_NEAR = -10;
    public static final int NEAR_RANGE = 400;
    public static final int ABANDONED = -20;
    public static final int OCCUPIED_INFLUENCE = -15; // au-dessus de SECESSION : la rancœur sans sécession assurée à la fin de l'occupation
    public static final int FAVOURITE = 30;
    public static final int FAVOURITE_LEAD = 10;
    public static final int EMBASSY_MIN = 40;
    public static final int EMBASSY_LEAD = 20;
    public static final int RALLY = 80;
    public static final int RALLY_DIPLOMACY = 70;
    public static final int RALLY_LEAD = 30;
    public static final int RALLY_DAYS = 7;
    public static final int SECESSION = -20;
    public static final int SECESSION_DAYS = 3;
    public static final int OCCUPATION_DAYS = 7;
    public static final int ESSOR_PER_DAY = 1;
    public static final int TRIBUTE_DAYS = 7;
    public static final int TRIBUTE_PORTERS = 2;
    public static final int TRIBUTE_ESSOR = 2;
    /** Le propriétaire commerce deux fois plus souvent avec son lieu-dit. */
    public static final double OWNER_TRADE = 2.0;
    /** Réputation perdue auprès du lieu-dit par le joueur qui tue un de ses habitants. */
    public static final int RESIDENT_REPUTATION = -100;
    /** Bâtiment de métier de la Maison du conseil (tools/plots.py, projet « Conseil »). */
    public static final String COUNCIL = "Conseil";
    public static final String DIPLOMACY = "Diplomatie";
    public static final String GARRISON = "Garnison";
    /** Lots du tribut par genre de lieu-dit (un quart de la production ; un tiers avec la Maison du conseil III). */
    private static final Map<String, Object[]> TRIBUTE_LOTS = Map.of(
            "Mine", new Object[] {"Ore_Iron", 4},
            "Ferme", new Object[] {"Plant_Crop_Wheat_Item", 8},
            "Moulin", new Object[] {"Ingredient_Flour", 6},
            "Caserne", new Object[] {"Weapon_Arrow_Crude", 12},
            "Forge", new Object[] {"Ingredient_Bar_Iron", 3},
            "Scierie", new Object[] {"Wood_Oak_Trunk", 12},
            "Chasse", new Object[] {"Ingredient_Hide_Light", 4},
            "Bosquet", new Object[] {"Plant_Crop_Health1", 4});

    private static final String LETTER = "~letter:";
    private static final String COOL = "~cool:";
    private static final String EXPCOOL = "~expcool:";
    private static final String DRIFT = "~drift";
    private static final String NEWS = "~news";

    /** L'état d'un lieu-dit (sauvé). */
    static final class State {
        String owner = "";
        long since;
        long occupiedUntil = Long.MIN_VALUE;
        int lowDays;
        String rally = "";
        int rallyDays;
        long tribute = Long.MIN_VALUE;

        static State parse(String v) {
            State s = new State();
            if (v == null) {
                return s;
            }
            String[] p = v.split("\\|", -1);
            try {
                s.owner = p[0];
                s.since = p.length > 1 ? Long.parseLong(p[1]) : 0;
                s.occupiedUntil = p.length > 2 ? Long.parseLong(p[2]) : Long.MIN_VALUE;
                s.lowDays = p.length > 3 ? Integer.parseInt(p[3]) : 0;
                s.rally = p.length > 4 ? p[4] : "";
                s.rallyDays = p.length > 5 ? Integer.parseInt(p[5]) : 0;
                s.tribute = p.length > 6 ? Long.parseLong(p[6]) : Long.MIN_VALUE;
            } catch (NumberFormatException e) {
                // champ abîmé : valeurs par défaut pour la suite
            }
            return s;
        }

        String format() {
            return owner + "|" + since + "|" + occupiedUntil + "|" + lowDays + "|" + rally + "|" + rallyDays + "|" + tribute;
        }
    }

    private Allegiance() {
    }

    // ---- Lecture ----

    static State state(World world, String hamlet) {
        return State.parse(WorldLife.registry(world).get(WorldLifeRegistry.Part.ALLEGIANCE, hamlet));
    }

    static void save(World world, String hamlet, State s) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.ALLEGIANCE, hamlet, s.format());
    }

    /** Le village propriétaire du lieu-dit, ou null s'il est libre. */
    public static Village owner(World world, Hamlets.Place h) {
        if (h == null) {
            return null;
        }
        String id = state(world, h.id()).owner;
        return id == null || id.isEmpty() ? null : Villages.registry(world).byId(id);
    }

    /** Le propriétaire du lieu-dit dont `hamletState` est l'état propre (id {@code H:<lieu-dit>}), ou null. */
    public static Village holder(World world, Village hamletState) {
        if (hamletState == null || !hamletState.isHamlet()) {
            return null;
        }
        return owner(world, Hamlets.get(world, hamletState.id().substring(dev.nakasar.hytale.peuples.village.HamletRegistry.PREFIX.length())));
    }

    /** Vrai pendant l'occupation qui suit une conquête (pas de troc animé, pas de sécession). */
    public static boolean occupied(World world, Hamlets.Place h, long day) {
        return h != null && state(world, h.id()).occupiedUntil >= day;
    }

    public static long occupiedUntil(World world, Hamlets.Place h) {
        return state(world, h.id()).occupiedUntil;
    }

    public static int influence(World world, String hamlet, String village) {
        String v = WorldLife.registry(world).get(WorldLifeRegistry.Part.INFLUENCE, hamlet + "|" + village);
        if (v == null) {
            return 0;
        }
        try {
            return Integer.parseInt(v);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    public static int influence(World world, Hamlets.Place h, Village v) {
        return h == null || v == null ? 0 : influence(world, h.id(), v.id());
    }

    private static void setInfluence(World world, String hamlet, String village, int value) {
        int clamped = Math.max(MIN, Math.min(MAX, value));
        WorldLife.registry(world).put(WorldLifeRegistry.Part.INFLUENCE, hamlet + "|" + village, clamped == 0 ? null : Integer.toString(clamped));
    }

    /** Ajoute `delta` à l'influence du village sur le lieu-dit ; rend la nouvelle valeur. */
    public static int change(World world, Hamlets.Place h, Village v, int delta) {
        if (h == null || v == null || delta == 0) {
            return influence(world, h, v);
        }
        int now = Math.max(MIN, Math.min(MAX, influence(world, h, v) + delta));
        setInfluence(world, h.id(), v.id(), now);
        return now;
    }

    /** Pose l'influence (commande, occupation). */
    public static void set(World world, Hamlets.Place h, Village v, int value) {
        setInfluence(world, h.id(), v.id(), value);
    }

    /** Les villages qui comptent pour le lieu-dit (à moins de {@value #RANGE} blocs), du plus influent au moins. */
    public static List<Village> candidates(World world, Hamlets.Place h) {
        List<Village> out = new ArrayList<>();
        for (Village v : Villages.registry(world).all()) {
            if (Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z())) <= RANGE) {
                out.add(v);
            }
        }
        out.sort(Comparator.comparingInt((Village v) -> -influence(world, h, v)));
        return out;
    }

    /** Le village préféré du lieu-dit (au-dessus de +{@value #FAVOURITE}, {@value #FAVOURITE_LEAD} points devant le second), ou null. */
    public static Village favourite(World world, Hamlets.Place h) {
        List<Village> c = candidates(world, h);
        if (c.isEmpty()) {
            return null;
        }
        int first = influence(world, h, c.get(0));
        int second = c.size() > 1 ? influence(world, h, c.get(1)) : MIN;
        return first > FAVOURITE && first - second >= FAVOURITE_LEAD ? c.get(0) : null;
    }

    /** Les lieux-dits tenus par le village. */
    public static List<Hamlets.Place> holdings(World world, Village v) {
        List<Hamlets.Place> out = new ArrayList<>();
        for (Map.Entry<String, String> e : WorldLife.registry(world).part(WorldLifeRegistry.Part.ALLEGIANCE).entrySet()) {
            if (e.getKey().startsWith("~") || !v.id().equals(State.parse(e.getValue()).owner)) {
                continue;
            }
            Hamlets.Place h = Hamlets.get(world, e.getKey());
            if (h != null && h.stage() == Hamlets.BUILT) {
                out.add(h);
            }
        }
        return out;
    }

    // ---- Maison du conseil ----

    /** L'état de la Maison du conseil du village (le plus haut niveau de ses deux terrains), ou null. */
    static WorkshopState council(Village v) {
        WorkshopState best = null;
        for (String plot : new String[] {"E1", "E2"}) {
            String id = v.people().id() + "_" + plot + "_" + COUNCIL;
            if (Workshops.known(v, id) && v.isBuilt(plot + "_" + COUNCIL)) {
                WorkshopState s = v.workshop(id);
                if (s != null && (best == null || s.level() > best.level())) {
                    best = s;
                }
            }
        }
        return best;
    }

    /** Niveau de la Maison du conseil (0 : pas de Maison du conseil). */
    public static int councilLevel(Village v) {
        WorkshopState s = v == null ? null : council(v);
        return s == null ? 0 : s.level();
    }

    /** Vrai si la Maison du conseil du village a cette spécialité ({@value #DIPLOMACY} ou {@value #GARRISON}). */
    public static boolean councilSpecialty(Village v, String specialty) {
        WorkshopState s = v == null ? null : council(v);
        return s != null && specialty.equals(s.specialty());
    }

    /** Lieux-dits que le village peut tenir : 1 au palier 2, 3 au palier 3, plus un par niveau de sa Maison du conseil. */
    public static int cap(Village v) {
        if (v == null || v.isHamlet() || v.tier() < 2) {
            return 0;
        }
        return (v.tier() >= 3 ? 3 : 1) + councilLevel(v) + dev.nakasar.hytale.peuples.annex.Infrastructures.ownFortress(v);
    }

    public static boolean canHold(World world, Village v) {
        return holdings(world, v).size() < cap(v);
    }

    // ---- Embargo ----

    /** Vrai si les marchands de `v` ne viennent plus au lieu-dit (rival de son propriétaire). */
    public static boolean embargoed(World world, Hamlets.Place h, Village v) {
        Village owner = owner(world, h);
        if (owner == null || v == null || owner.id().equals(v.id())) {
            return false;
        }
        return Relations.value(world, owner, v) <= Relations.RIVAL;
    }

    /**
     * Embargo des joueurs : le lieu-dit tenu ne troque plus et ne passe plus de commande avec un joueur Étranger (ou
     * pire) chez son propriétaire. Dit pourquoi au joueur et rend vrai si le joueur est refusé.
     */
    public static boolean refuses(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Hamlets.Place h) {
        Village owner = owner(world, h);
        if (owner == null || ref == null || Reputations.rank(store, ref, owner).atLeast(Rank.TOLERE)) {
            return false;
        }
        if (player != null) {
            DialogueSpeech.say(player, Message.translation(KEYS + "embargo").param("village", owner.name()));
        }
        return true;
    }

    /** Embargo des commandes : `hamletState` est l'état propre du lieu-dit (id {@code H:<lieu-dit>}). */
    public static boolean refusesOrders(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village hamletState) {
        Hamlets.Place h = Hamlets.get(world, hamletState.id().substring(dev.nakasar.hytale.peuples.village.HamletRegistry.PREFIX.length()));
        if (h == null || owner(world, h) == null || Reputations.rank(store, ref, owner(world, h)).atLeast(Rank.TOLERE)) {
            return false;
        }
        player.sendMessage(Message.translation(KEYS + "embargo").param("village", owner(world, h).name()));
        return true;
    }

    // ---- Événements ----

    /** Un marchand ou une caravane est arrivé au lieu-dit. */
    static void merchantArrived(World world, Store<EntityStore> store, Hamlets.Place h, Village v, boolean caravan) {
        change(world, h, v, caravan ? CARAVAN : MERCHANT);
    }

    /** Un joueur a rendu une commande d'un lieu-dit : +{@value #ORDER} au village dont il porte les couleurs. */
    public static void playerOrder(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village hamletState) {
        if (hamletState == null || !hamletState.isHamlet()) {
            return;
        }
        Hamlets.Place h = Hamlets.get(world, hamletState.id().substring(dev.nakasar.hytale.peuples.village.HamletRegistry.PREFIX.length()));
        Village colours = Colours.of(world, store, ref);
        if (h != null && colours != null && Math.sqrt(colours.horizontalDistanceSquared(h.x(), h.z())) <= RANGE) {
            change(world, h, colours, ORDER);
        }
    }

    /** Un marcheur d'une tournée est mort : un joueur aux couleurs d'un village le fait payer à ce village. */
    static void walkerKilled(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h, PlayerRef killer) {
        if (killer == null) {
            return;
        }
        Ref<EntityStore> ref = killer.getReference();
        if (t.kind() == HamletTrips.EMBASSY) {
            Reputations.change(world, store, ref, killer, v, Embassies.KILLED_REPUTATION, KEYS + "reason.embassy");
        }
        Village colours = Colours.of(world, store, ref);
        if (colours != null && t.trade()) {
            change(world, h, colours, MERCHANT_KILLED);
        }
    }

    /** Un habitant du lieu-dit est mort de la main d'un joueur. */
    static void residentKilled(World world, Store<EntityStore> store, Hamlets.Place h, PlayerRef killer) {
        if (killer == null) {
            return;
        }
        Ref<EntityStore> ref = killer.getReference();
        Village colours = Colours.of(world, store, ref);
        if (colours != null) {
            change(world, h, colours, RESIDENT_KILLED);
        }
        Village state = Hamlets.state(world, h);
        if (state != null) {
            Reputations.change(world, store, ref, killer, state, RESIDENT_REPUTATION, KEYS + "reason.resident");
        }
    }

    // ---- Changement de propriétaire ----

    /**
     * Le lieu-dit passe à `to` (null : il redevient libre). `cause` : embassy, rally, conquest, secession, command.
     * Annonce aux villages concernés et aux joueurs proches, bannières repeintes, gardes congédiés.
     */
    public static void setOwner(World world, Store<EntityStore> store, Hamlets.Place h, Village to, String cause) {
        State s = state(world, h.id());
        Village from = s.owner.isEmpty() ? null : Villages.registry(world).byId(s.owner);
        if (to == null ? s.owner.isEmpty() : to.id().equals(s.owner)) {
            return; // déjà à lui (ou déjà libre)
        }
        long day = GameClock.day(store);
        s.owner = to == null ? "" : to.id();
        s.since = day;
        s.lowDays = 0;
        s.rally = "";
        s.rallyDays = 0;
        s.tribute = day;
        if (!"conquest".equals(cause)) {
            s.occupiedUntil = Long.MIN_VALUE;
        }
        save(world, h.id(), s);
        Garrisons.reset(world, store, h);
        Banners.repaint(world, h);
        Message m = to == null ? Message.translation(KEYS + "owner.free").param("hamlet", h.name()).param("village", from == null ? "?" : from.name())
                : Message.translation(KEYS + "owner." + cause).param("hamlet", h.name()).param("village", to.name())
                .param("from", from == null ? Message.translation(KEYS + "nobody") : Message.raw(from.name()));
        if (to != null) {
            Chantiers.announce(world, to, m, null, "conquest".equals(cause) ? NotificationStyle.Warning : NotificationStyle.Success);
        }
        if (from != null) {
            Chantiers.announce(world, from, m, null, NotificationStyle.Warning);
        }
        int[] market = h.market();
        WorldLife.announce(world, store, market[0], market[1], 160, m, NotificationStyle.Default);
        news(world, h, to == null ? from : to, to == null ? "secession" : cause, day);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples (conquête) : lieu-dit %s → %s (%s)", h.id(), to == null ? "libre" : to.name(), cause);
    }

    /** Occupation après une conquête : influence du vainqueur à {@value #OCCUPIED_INFLUENCE}, pas de sécession pendant {@value #OCCUPATION_DAYS} jours. */
    static void occupy(World world, Store<EntityStore> store, Hamlets.Place h, Village winner) {
        long day = GameClock.day(store);
        State s = state(world, h.id());
        s.occupiedUntil = day + OCCUPATION_DAYS;
        save(world, h.id(), s);
        setOwner(world, store, h, winner, "conquest");
        s = state(world, h.id());
        s.occupiedUntil = day + OCCUPATION_DAYS;
        save(world, h.id(), s);
        set(world, h, winner, OCCUPIED_INFLUENCE);
    }

    // ---- Lettre de ralliement ----

    /** La lettre de ralliement du lieu-dit (village qu'elle soutient), ou null. */
    static String letter(World world, Hamlets.Place h) {
        return WorldLife.registry(world).get(WorldLifeRegistry.Part.ALLEGIANCE, LETTER + h.id());
    }

    static void setLetter(World world, Hamlets.Place h, Village v) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.ALLEGIANCE, LETTER + h.id(), v == null ? null : v.id());
    }

    /** Peut-on demander une lettre de ralliement à l'habitant ? Couleurs d'un village qui ne tient pas le lieu-dit, rang Ami au lieu-dit. */
    static boolean canRally(World world, Store<EntityStore> store, Ref<EntityStore> ref, Hamlets.Place h) {
        Village colours = Colours.of(world, store, ref);
        Village owner = owner(world, h);
        Village state = Hamlets.state(world, h);
        return colours != null && state != null && (owner == null || !owner.id().equals(colours.id()))
                && !colours.id().equals(letter(world, h)) && Reputations.rank(store, ref, state).atLeast(Rank.AMI);
    }

    /** L'habitant écrit la lettre : la prochaine ambassade de ce village ici aura +15 %. */
    static boolean rally(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Hamlets.Place h) {
        Village colours = Colours.of(world, store, ref);
        if (colours == null || !canRally(world, store, ref, h)) {
            DialogueSpeech.say(player, Message.translation(KEYS + "letter.no"));
            return false;
        }
        setLetter(world, h, colours);
        DialogueSpeech.say(player, Message.translation(KEYS + "letter.yes").param("village", colours.name()));
        return true;
    }

    // ---- Délais ----

    static boolean cooling(World world, Hamlets.Place h, Village v, long day) {
        return running(world, COOL + h.id() + "|" + v.id(), day);
    }

    /** Vrai tant que le délai de la marque court ; une marque échue est effacée (la partie ne grossit pas). */
    private static boolean running(World world, String key, long day) {
        WorldLifeRegistry r = WorldLife.registry(world);
        long until = r.getLong(WorldLifeRegistry.Part.ALLEGIANCE, key, Long.MIN_VALUE);
        if (until == Long.MIN_VALUE) {
            return false;
        }
        if (until <= day) {
            r.put(WorldLifeRegistry.Part.ALLEGIANCE, key, null);
            return false;
        }
        return true;
    }

    static void cool(World world, Hamlets.Place h, Village v, long until) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.ALLEGIANCE, COOL + h.id() + "|" + v.id(), Long.toString(until));
    }

    static boolean expeditionCooling(World world, Village v, long day) {
        return running(world, EXPCOOL + v.id(), day);
    }

    static void expeditionCool(World world, Village v, long until) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.ALLEGIANCE, EXPCOOL + v.id(), Long.toString(until));
    }

    // ---- Tribut ----

    /** Les porteurs du tribut sont arrivés au lieu-dit : une heure sur la place, puis retour avec les lots. */
    static void tributeArrived(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        t.leg = HamletTrips.STAY;
        t.at = 0;
        t.until = GameClock.seconds(store) + 3600L;
        change(world, h, v, TRIBUTE);
    }

    /** Retour du tribut : essor et lots de la production du lieu-dit, au dépôt du propriétaire. */
    static void tributeHome(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        boolean third = councilLevel(v) >= 3;
        int essor = TRIBUTE_ESSOR + (third ? 1 : 0);
        Villages.addEssor(v, essor);
        Hamlet type = h.type();
        Object[] lot = type == null ? null : TRIBUTE_LOTS.get(type.type());
        Message what = Message.translation(KEYS + "tribute.essor");
        if (lot != null && t.walkers() > 0) {
            int qty = (int) lot[1];
            qty = third ? (qty * 4 + 2) / 3 : qty;
            qty = qty * t.walkers() / TRIBUTE_PORTERS;
            if (qty > 0) {
                int[] d = v.deposit();
                Deposits.drop(world, new int[] {d[0], d[1] + 1, d[2]}, List.of(new ItemStack((String) lot[0], qty)));
                what = Message.translation(KEYS + "tribute.lot").param("count", qty).param("item", Message.translation("server.items." + lot[0] + ".name"));
            }
        }
        Chantiers.announce(world, v, Message.translation(KEYS + "tribute.home").param("hamlet", h.name()).param("essor", essor).param("what", what),
                null, NotificationStyle.Success);
    }

    // ---- Matin ----

    /** Une fois par jour de jeu : dérive, sécession, ralliement, essor, tribut, gardes, ambassades et expéditions. */
    static void morning(World world, Store<EntityStore> store, long day, Random random) {
        WorldLifeRegistry r = WorldLife.registry(world);
        boolean drift = r.getLong(WorldLifeRegistry.Part.ALLEGIANCE, DRIFT, Long.MIN_VALUE) + DRIFT_DAYS <= day;
        if (drift) {
            r.put(WorldLifeRegistry.Part.ALLEGIANCE, DRIFT, Long.toString(day));
            // Délais échus : effacés (sinon chaque échec d'ambassade resterait sauvé pour toujours).
            for (String key : new ArrayList<>(r.part(WorldLifeRegistry.Part.ALLEGIANCE).keySet())) {
                if (key.startsWith(COOL) || key.startsWith(EXPCOOL)) {
                    running(world, key, day);
                }
            }
            for (Map.Entry<String, String> e : new ArrayList<>(r.part(WorldLifeRegistry.Part.INFLUENCE).entrySet())) {
                try {
                    int v = Integer.parseInt(e.getValue());
                    int next = v > 0 ? v - 1 : v < 0 ? v + 1 : 0;
                    r.put(WorldLifeRegistry.Part.INFLUENCE, e.getKey(), next == 0 ? null : Integer.toString(next));
                } catch (NumberFormatException ex) {
                    r.put(WorldLifeRegistry.Part.INFLUENCE, e.getKey(), null);
                }
            }
        }
        for (Hamlets.Place h : Hamlets.all(world)) {
            if (h.stage() != Hamlets.BUILT) {
                continue;
            }
            seed(world, h);
            State s = state(world, h.id());
            Village owner = s.owner.isEmpty() ? null : Villages.registry(world).byId(s.owner);
            if (!s.owner.isEmpty() && owner == null) {
                setOwner(world, store, h, null, "secession");
                continue;
            }
            if (owner != null) {
                Villages.addEssor(owner, ESSOR_PER_DAY);
                if (s.occupiedUntil != Long.MIN_VALUE && s.occupiedUntil == day - 1) {
                    Chantiers.announce(world, owner, Message.translation(KEYS + "occupation.end").param("hamlet", h.name()), null,
                            NotificationStyle.Default);
                }
                if (s.occupiedUntil < day && influence(world, h, owner) < SECESSION) {
                    s.lowDays++;
                    if (s.lowDays >= SECESSION_DAYS) {
                        save(world, h.id(), s);
                        setOwner(world, store, h, null, "secession");
                        continue;
                    }
                } else {
                    s.lowDays = 0;
                }
                if (s.tribute == Long.MIN_VALUE || day - s.tribute >= TRIBUTE_DAYS) {
                    if (HamletTrips.startKind(world, h, owner, HamletTrips.TRIBUTE, TRIBUTE_PORTERS) != null) {
                        s.tribute = day;
                    }
                }
            }
            // Ralliement spontané.
            Village best = null;
            for (Village v : candidates(world, h)) {
                best = v;
                break;
            }
            int threshold = best != null && councilSpecialty(best, DIPLOMACY) ? RALLY_DIPLOMACY : RALLY;
            boolean rallying = best != null && (owner == null || !owner.id().equals(best.id()))
                    && influence(world, h, best) >= threshold
                    && influence(world, h, best) - (owner == null ? 0 : influence(world, h, owner)) >= RALLY_LEAD
                    && canHold(world, best) && s.occupiedUntil < day;
            if (rallying) {
                s.rallyDays = best.id().equals(s.rally) ? s.rallyDays + 1 : 1;
                s.rally = best.id();
            } else {
                s.rally = "";
                s.rallyDays = 0;
            }
            save(world, h.id(), s);
            if (rallying && s.rallyDays >= RALLY_DAYS) {
                setOwner(world, store, h, best, "rally");
            }
        }
        Garrisons.morning(world, store, day);
        Embassies.morning(world, store, day, random);
        Sieges.morning(world, store, day, random);
    }

    /** Influence de départ : le village d'origine à +{@value #ORIGIN_START} (une fois). */
    static void seed(World world, Hamlets.Place h) {
        WorldLifeRegistry r = WorldLife.registry(world);
        if (r.get(WorldLifeRegistry.Part.ALLEGIANCE, h.id()) != null) {
            return;
        }
        save(world, h.id(), new State());
        Village origin = Hamlets.origin(world, h);
        if (origin != null) {
            change(world, h, origin, ORIGIN_START);
        }
    }

    // ---- Nouvelles (rumeurs) ----

    private static void news(World world, Hamlets.Place h, Village v, String cause, long day) {
        if (v == null) {
            return;
        }
        WorldLife.registry(world).put(WorldLifeRegistry.Part.ALLEGIANCE, NEWS, h.id() + "|" + v.id() + "|" + cause + "|" + day);
    }

    /** Rumeurs : le dernier changement de main (7 jours), les lieux-dits tenus, une expédition en marche. */
    static List<Message> rumours(World world, long day) {
        List<Message> out = new ArrayList<>();
        String n = WorldLife.registry(world).get(WorldLifeRegistry.Part.ALLEGIANCE, NEWS);
        if (n != null) {
            String[] p = n.split("\\|", -1);
            try {
                Hamlets.Place h = Hamlets.get(world, p[0]);
                Village v = Villages.registry(world).byId(p[1]);
                if (h != null && v != null && day - Long.parseLong(p[3]) <= 7) {
                    out.add(Message.translation(KEYS + "rumour." + p[2]).param("hamlet", h.name()).param("village", v.name()));
                }
            } catch (RuntimeException ignored) {
                // nouvelle abîmée : ignorée
            }
        }
        for (HamletTrips.Trip t : HamletTrips.ofKind(world, HamletTrips.EXPEDITION)) {
            Village v = Villages.registry(world).byId(t.village());
            Hamlets.Place h = Hamlets.get(world, t.hamlet());
            if (v != null && h != null) {
                out.add(Message.translation(KEYS + "rumour.expedition").param("village", v.name()).param("hamlet", h.name()));
            }
        }
        return out;
    }

    // ---- Descriptions ----

    /** « À qui appartient ce lieu ? » (dialogue de l'habitant). */
    static boolean sayOwner(World world, Store<EntityStore> store, PlayerRef player, Hamlets.Place h) {
        Village owner = owner(world, h);
        long day = GameClock.day(store);
        Message m;
        if (owner == null) {
            Village fav = favourite(world, h);
            m = fav == null ? Message.translation(KEYS + "say.free") : Message.translation(KEYS + "say.freeFavourite").param("village", fav.name());
        } else if (occupied(world, h, day)) {
            m = Message.translation(KEYS + "say.occupied").param("village", owner.name()).param("days", occupiedUntil(world, h) - day + 1);
        } else {
            int inf = influence(world, h, owner);
            String mood = inf >= FAVOURITE ? "glad" : inf >= 0 ? "fine" : "grumble";
            m = Message.translation(KEYS + "say.owned." + mood).param("village", owner.name()).param("guards", Garrisons.count(world, h));
        }
        DialogueSpeech.say(player, m);
        return true;
    }

    /** Ligne de la commande /monde allegeance. */
    static List<Message> describe(World world, Store<EntityStore> store, Hamlets.Place h) {
        List<Message> out = new ArrayList<>();
        long day = GameClock.day(store);
        Village owner = owner(world, h);
        State s = state(world, h.id());
        out.add(Message.translation(KEYS + "cmd.header").param("hamlet", h.name())
                .param("owner", owner == null ? Message.translation(KEYS + "nobody") : Message.raw(owner.name()))
                .param("guards", Garrisons.count(world, h)).param("target", owner == null ? 0 : Garrisons.target(world, h, owner))
                .param("occupied", occupied(world, h, day) ? 1 : 0).param("low", s.lowDays).param("rally", s.rallyDays));
        int shown = 0;
        for (Village v : candidates(world, h)) {
            if (shown++ >= 6) {
                break;
            }
            out.add(Message.translation(KEYS + "cmd.line").param("village", v.name()).param("value", influence(world, h, v))
                    .param("relation", owner == null || owner == v ? 0 : Relations.value(world, owner, v))
                    .param("holds", holdings(world, v).size()).param("cap", cap(v)));
        }
        return out;
    }
}
