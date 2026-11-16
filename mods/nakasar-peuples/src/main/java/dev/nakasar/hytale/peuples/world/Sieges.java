package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

/**
 * La conquête militaire (GDD de la conquête, « Prendre un lieu-dit par les armes ») : un village du palier 3, rival
 * du propriétaire d'un lieu-dit (hors trêve), y envoie {@value #SOLDIERS} soldats (un de plus avec la spécialité
 * Garnison). Une chance sur dix par semaine, une expédition au plus dans le monde ; un joueur Hôte peut la demander au
 * tableau (onglet Domaine) contre {@value #OFFERING} faveurs. Elle est annoncée à {@value #ANNOUNCE_RANGE} blocs, marche
 * de jour comme un marchand ({@link HamletTrips}, genre E), coûte {@value Allegiance#EXPEDITION_TARGET} d'influence au
 * lieu-dit visé et {@value Allegiance#EXPEDITION_NEAR} aux lieux-dits voisins.
 *
 * <p>L'assaut : un joueur à moins de {@value WorldLife#REAL_RANGE} blocs, c'est un vrai combat (soldats camp 1 contre
 * gardes camp 0, clé {@code HG:<lieu-dit>}) de {@value #ASSAULT_SECONDS} s au plus ; personne, il se règle seul
 * (soldats × palier contre gardes × palier + la sentinelle, à 20 % près). Victoire : le lieu-dit change de main, est
 * occupé {@value Allegiance#OCCUPATION_DAYS} jours (influence du vainqueur à {@value Allegiance#OCCUPIED_INFLUENCE}, pas
 * de troc animé), les soldats restants deviennent sa garde, la relation des deux villages perd {@value #RELATION_LOSS}.
 * Défense : +{@value Allegiance#DEFENDED} d'influence au propriétaire, l'attaquant attend {@value #COOLDOWN_DAYS} jours.
 * Pas d'incendie ni de perte de niveau (Kevin).
 */
public final class Sieges {

    public static final int SOLDIERS = 4;
    public static final double WEEKLY_CHANCE = 0.10;
    public static final int ANNOUNCE_RANGE = 600;
    public static final int ASSAULT_SECONDS = 300;
    /** Plus de gardes depuis ceci (s) : la place est prise. */
    public static final int CLEAR_SECONDS = 15;
    public static final int COOLDOWN_DAYS = 14;
    public static final int RELATION_LOSS = -25;
    public static final int OFFERING = 5;
    public static final int DEFEND_REPUTATION = 50;
    public static final int ATTACK_REPUTATION = 30;
    public static final int ATTACK_HAMLET_REPUTATION = -100;
    /** Force de la sentinelle (habitants) dans l'assaut sans témoin. */
    private static final int SENTRY = 2;
    private static final String KEYS = Heraldry.KEYS + "siege.";

    private static final class Siege {
        final long started;
        final int guards;
        long clearSince;

        Siege(long started, int guards) {
            this.started = started;
            this.guards = guards;
        }
    }

    private static final Map<String, Siege> SIEGES = new ConcurrentHashMap<>();

    private Sieges() {
    }

    public static boolean besieged(String hamlet) {
        return SIEGES.containsKey(hamlet);
    }

    /** Le village peut-il attaquer ce lieu-dit ? Rend la raison du refus, ou null. */
    static Message blocked(World world, Hamlets.Place h, Village v, long day) {
        Village owner = Allegiance.owner(world, h);
        if (v.tier() < 3) {
            return Message.translation(KEYS + "tier");
        }
        if (owner == null) {
            return Message.translation(KEYS + "free").param("hamlet", h.name());
        }
        if (owner.id().equals(v.id())) {
            return Message.translation(Heraldry.KEYS + "embassy.already").param("hamlet", h.name());
        }
        if (Relations.value(world, owner, v) > Relations.RIVAL) {
            return Message.translation(KEYS + "notRival").param("village", owner.name());
        }
        if (Relations.truce(world, owner, v, day)) {
            return Message.translation(KEYS + "truce").param("village", owner.name());
        }
        if (!Allegiance.canHold(world, v)) {
            return Message.translation(Heraldry.KEYS + "embassy.full").param("village", v.name()).param("cap", Allegiance.cap(v));
        }
        if (Allegiance.expeditionCooling(world, v, day)) {
            return Message.translation(KEYS + "cooling");
        }
        if (!HamletTrips.ofKind(world, HamletTrips.EXPEDITION).isEmpty()) {
            return Message.translation(KEYS + "busy");
        }
        if (Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z())) > Allegiance.RANGE) {
            return Message.translation(Heraldry.KEYS + "embassy.far").param("range", Allegiance.RANGE);
        }
        return null;
    }

    /** Fait partir l'expédition : annonces et influence perdue tout de suite. */
    static HamletTrips.Trip start(World world, Store<EntityStore> store, Hamlets.Place h, Village v) {
        int soldiers = SOLDIERS + (Allegiance.councilSpecialty(v, Allegiance.GARRISON) ? 1 : 0);
        HamletTrips.Trip t = HamletTrips.startKind(world, h, v, HamletTrips.EXPEDITION, soldiers);
        if (t == null) {
            return null;
        }
        Allegiance.change(world, h, v, Allegiance.EXPEDITION_TARGET);
        for (Hamlets.Place o : Hamlets.all(world)) {
            if (!o.id().equals(h.id()) && o.stage() == Hamlets.BUILT
                    && (long) (o.x() - h.x()) * (o.x() - h.x()) + (long) (o.z() - h.z()) * (o.z() - h.z()) <= (long) Allegiance.NEAR_RANGE * Allegiance.NEAR_RANGE) {
                Allegiance.change(world, o, v, Allegiance.EXPEDITION_NEAR);
            }
        }
        Village owner = Allegiance.owner(world, h);
        Message m = Message.translation(KEYS + "announce").param("village", v.name()).param("hamlet", h.name())
                .param("owner", owner == null ? Message.translation(Heraldry.KEYS + "nobody") : Message.raw(owner.name()));
        Chantiers.announce(world, v, m, null, NotificationStyle.Warning);
        if (owner != null) {
            Chantiers.announce(world, owner, m, null, NotificationStyle.Danger);
        }
        int[] market = h.market();
        WorldLife.announce(world, store, market[0], market[1], ANNOUNCE_RANGE, m, NotificationStyle.Danger);
        return t;
    }

    /** Demande d'un joueur Hôte au tableau, contre {@value #OFFERING} faveurs. Rend la raison du refus, ou null. */
    public static Message request(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, Hamlets.Place h) {
        if (!Reputations.rank(store, ref, v).atLeast(Rank.HOTE)) {
            return Message.translation(KEYS + "rank").param("village", v.name());
        }
        Message why = blocked(world, h, v, GameClock.day(store));
        if (why != null) {
            return why;
        }
        String favour = v.people().favorItem();
        if (WorldLife.count(store, ref, favour::equals) < OFFERING) {
            return Message.translation(Heraldry.KEYS + "embassy.offering").param("count", OFFERING);
        }
        WorldLife.take(store, ref, favour::equals, OFFERING);
        return start(world, store, h, v) == null ? Message.translation(KEYS + "busy") : null;
    }

    /** Tirage du matin : une chance sur dix par semaine pour chaque village du palier 3 qui a un lieu-dit rival à prendre. */
    static void morning(World world, Store<EntityStore> store, long day, Random random) {
        if (!HamletTrips.ofKind(world, HamletTrips.EXPEDITION).isEmpty()) {
            return;
        }
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        Collections.shuffle(villages, random);
        for (Village v : villages) {
            if (v.tier() < 3 || random.nextDouble() >= WEEKLY_CHANCE / 7.0) {
                continue;
            }
            List<Hamlets.Place> targets = new ArrayList<>();
            for (Hamlets.Place h : Hamlets.all(world)) {
                if (h.stage() == Hamlets.BUILT && blocked(world, h, v, day) == null) {
                    targets.add(h);
                }
            }
            if (!targets.isEmpty() && start(world, store, targets.get(random.nextInt(targets.size())), v) != null) {
                return;
            }
        }
    }

    /** Arrivée devant le lieu-dit : assaut réel si un joueur est là, sinon réglé aussitôt. */
    static void arrive(World world, Store<EntityStore> store, List<Vector3d> players, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        Village owner = Allegiance.owner(world, h);
        if (owner == null) {
            // Le lieu-dit s'est libéré en chemin : il est pris sans combat.
            if (!Allegiance.canHold(world, v)) {
                retreat(world, store, t, v, h); // plus de place au village : la troupe rentre
                return;
            }
            Allegiance.occupy(world, store, h, v);
            Garrisons.add(world, h, v, t.walkers);
            HamletTrips.drop(world, store, t);
            return;
        }
        if (owner.id().equals(v.id())) {
            Garrisons.add(world, h, v, t.walkers);
            HamletTrips.drop(world, store, t);
            return;
        }
        int[] m = h.market();
        t.leg = HamletTrips.STAY;
        t.at = 0;
        if (WorldLife.near(players, m[0], m[1], WorldLife.REAL_RANGE)) {
            SIEGES.put(h.id(), new Siege(System.currentTimeMillis(), Garrisons.count(world, h)));
            WorldLife.announce(world, store, m[0], m[1], WorldLife.REAL_RANGE * 2,
                    Message.translation(KEYS + "assault").param("village", v.name()).param("hamlet", h.name()), NotificationStyle.Danger);
        } else {
            autoResolve(world, store, t, v, h, owner);
        }
    }

    /** Le pas de l'assaut ; rend vrai si la tournée existe encore. */
    static boolean step(World world, Store<EntityStore> store, List<Vector3d> players, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        Village owner = Allegiance.owner(world, h);
        Siege s = SIEGES.get(h.id());
        int[] m = h.market();
        if (owner == null || owner.id().equals(v.id())) {
            SIEGES.remove(h.id());
            arrive(world, store, players, t, v, h);
            return HamletTrips.get(world, t.id()) != null;
        }
        if (Relations.value(world, owner, v) > Relations.RIVAL || Relations.truce(world, owner, v, GameClock.day(store))) {
            retreat(world, store, t, v, h); // le lieu-dit a changé de main en chemin : plus un rival, on rentre
            return HamletTrips.get(world, t.id()) != null;
        }
        if (s == null || !WorldLife.near(players, m[0], m[1], WorldLife.REAL_RANGE)) {
            autoResolve(world, store, t, v, h, owner);
            return HamletTrips.get(world, t.id()) != null;
        }
        Walk walk = Walk.of(t.walkKey());
        List<Ref<EntityStore>> live = walk.alive();
        if (live.isEmpty() && t.walkers > 0 && WorldLife.budget(world, t.walkers)) {
            // Les soldats arrivent du côté de leur village, à une douzaine de blocs de la place.
            double dx = v.x() - m[0], dz = v.z() - m[1];
            double len = Math.max(1, Math.hypot(dx, dz));
            for (int i = 0; i < t.walkers; i++) {
                Vector3d at = WorldLife.ground(world, (int) Math.floor(m[0] + dx / len * 12 + (i - t.walkers / 2.0) * 2),
                        (int) Math.floor(m[1] + dz / len * 12), 6);
                if (at == null) {
                    continue;
                }
                Ref<EntityStore> ref = HamletTrips.spawnWalker(store, t, v.people(), i, at, (float) Math.atan2(dx, -dz));
                if (ref != null) {
                    walk.refs.add(ref);
                }
            }
            live = walk.alive();
        }
        Vector3d centre = WorldLife.ground(world, m[0], m[1], 6);
        if (centre != null) {
            for (Ref<EntityStore> ref : live) {
                WorldLife.leash(store, ref, centre);
            }
        }
        long now = System.currentTimeMillis();
        int guards = Garrisons.count(world, h);
        if (guards <= 0) {
            if (s.clearSince == 0) {
                s.clearSince = now;
            } else if (now - s.clearSince >= CLEAR_SECONDS * 1000L) {
                win(world, store, t, v, h, owner, s.guards);
                return HamletTrips.get(world, t.id()) != null; // la troupe peut rentrer (plus de place)
            }
        } else {
            s.clearSince = 0;
        }
        if (now - s.started >= ASSAULT_SECONDS * 1000L) {
            if (t.walkers > guards) {
                win(world, store, t, v, h, owner, s.guards);
                return HamletTrips.get(world, t.id()) != null; // la troupe peut rentrer (plus de place)
            }
            defend(world, store, t, v, h, owner);
            return HamletTrips.get(world, t.id()) != null;
        }
        return true;
    }

    /** Assaut sans témoin : soldats × palier contre gardes × palier + sentinelle, chacun à 20 % près. */
    private static void autoResolve(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h, Village owner) {
        Random random = new Random();
        int guards = Garrisons.count(world, h);
        double attack = t.walkers * Math.max(1, v.tier()) * (0.8 + 0.4 * random.nextDouble());
        double defence = (guards * Math.max(1, owner.tier()) + SENTRY) * (0.8 + 0.4 * random.nextDouble());
        if (attack > defence) {
            t.walkers = Math.max(1, t.walkers - guards);
            Garrisons.setCount(world, h, 0);
            win(world, store, t, v, h, owner, guards);
        } else {
            t.walkers = t.walkers / 2;
            if (guards > 0 && random.nextBoolean()) {
                Garrisons.setCount(world, h, guards - 1);
            }
            defend(world, store, t, v, h, owner);
        }
    }

    private static void win(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h, Village owner, int guardsAtStart) {
        SIEGES.remove(h.id());
        if (!Allegiance.canHold(world, v)) {
            retreat(world, store, t, v, h); // le village a gagné un autre lieu-dit pendant la marche : pas de place
            return;
        }
        if (guardsAtStart <= 0) {
            Allegiance.change(world, h, owner, Allegiance.ABANDONED);
        }
        Relations.change(world, v, owner, RELATION_LOSS);
        int[] m = h.market();
        Message msg = Message.translation(KEYS + "won").param("village", v.name()).param("hamlet", h.name()).param("owner", owner.name());
        Village state = Hamlets.state(world, h);
        for (PlayerRef p : WorldLife.playersNear(world, store, m[0], m[1], WorldLife.REAL_RANGE)) {
            Ref<EntityStore> ref = p.getReference();
            if (Colours.wears(store, ref, v)) {
                Reputations.change(world, store, ref, p, v, ATTACK_REPUTATION, Heraldry.KEYS + "reason.conquest");
                if (state != null) {
                    Reputations.change(world, store, ref, p, state, ATTACK_HAMLET_REPUTATION, Heraldry.KEYS + "reason.conquered");
                }
            }
        }
        int survivors = Math.max(1, t.walkers);
        HamletTrips.drop(world, store, t);
        Allegiance.occupy(world, store, h, v);
        Garrisons.add(world, h, v, survivors);
        Chantiers.announce(world, owner, msg, null, NotificationStyle.Danger);
        WorldLife.announce(world, store, m[0], m[1], ANNOUNCE_RANGE, msg, NotificationStyle.Warning);
    }

    private static void defend(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h, Village owner) {
        SIEGES.remove(h.id());
        Allegiance.change(world, h, owner, Allegiance.DEFENDED);
        Allegiance.expeditionCool(world, v, GameClock.day(store) + COOLDOWN_DAYS);
        int[] m = h.market();
        for (PlayerRef p : WorldLife.playersNear(world, store, m[0], m[1], WorldLife.REAL_RANGE)) {
            Ref<EntityStore> ref = p.getReference();
            if (Colours.wears(store, ref, owner)) {
                Reputations.change(world, store, ref, p, owner, DEFEND_REPUTATION, Heraldry.KEYS + "reason.defence");
            }
        }
        Message msg = Message.translation(KEYS + "repelled").param("village", v.name()).param("hamlet", h.name()).param("owner", owner.name());
        Chantiers.announce(world, owner, msg, null, NotificationStyle.Success);
        Chantiers.announce(world, v, msg, null, NotificationStyle.Warning);
        WorldLife.announce(world, store, m[0], m[1], WorldLife.REAL_RANGE * 2, msg, NotificationStyle.Success);
        if (t.walkers <= 0) {
            HamletTrips.drop(world, store, t);
            return;
        }
        t.leg = HamletTrips.BACK;
        t.at = 0;
        Walk.of(t.walkKey()).reset(0);
    }

    /** Tous les soldats sont morts (sur la route ou à l'assaut). */
    static void wiped(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        Village owner = Allegiance.owner(world, h);
        if (t.leg() == HamletTrips.STAY && owner != null && !owner.id().equals(v.id())) {
            defend(world, store, t, v, h, owner);
            return;
        }
        SIEGES.remove(h.id());
        Allegiance.expeditionCool(world, v, GameClock.day(store) + COOLDOWN_DAYS);
        Chantiers.announce(world, v, Message.translation(KEYS + "lost").param("hamlet", h.name()), null, NotificationStyle.Warning);
    }

    /** La troupe renonce et rentre (plus de place au village, ou plus de rival à combattre) ; délai avant la suivante. */
    private static void retreat(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        SIEGES.remove(h.id());
        Allegiance.expeditionCool(world, v, GameClock.day(store) + COOLDOWN_DAYS);
        Chantiers.announce(world, v, Message.translation(KEYS + "retreat").param("hamlet", h.name()), null, NotificationStyle.Default);
        if (t.walkers <= 0) {
            HamletTrips.drop(world, store, t);
            return;
        }
        t.leg = HamletTrips.BACK;
        t.at = 0;
        Walk.of(t.walkKey()).reset(0);
    }

    /** La tournée d'expédition est finie, quelle qu'en soit la raison : plus de siège en cours. */
    static void forget(String hamlet) {
        SIEGES.remove(hamlet);
    }

    public static void clearAll() {
        SIEGES.clear();
    }
}
