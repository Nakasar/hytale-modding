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

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Les ambassades (GDD de la conquête, « Prendre un lieu-dit par la parole ») : deux négociateurs et un garde partent du
 * village, marchent de jour comme les marchands ({@link HamletTrips}, genre A) et parlementent {@value #PARLEY_HOURS}
 * heure de jeu sur la place. Chance de réussite : 50 % plus l'écart d'influence avec le propriétaire (entre 10 et
 * 95 %), +15 % si un joueur Ami du village escorte (à moins de {@value #ESCORT_RANGE} blocs à la fin), +15 % avec la
 * spécialité Diplomatie, +15 % avec une lettre de ralliement d'un habitant, −20 % par garde du propriétaire sur place ;
 * chassés d'office si le village est rival du propriétaire et que des gardes sont là. Réussite : +{@value #SUCCESS}
 * d'influence, le lieu-dit passe au village (s'il lui reste une place) et le garde de l'ambassade reste. Échec :
 * {@value #FAILURE}, et {@value #COOLDOWN_DAYS} jours avant de retenter.
 *
 * <p>Départs : chaque matin, un village du palier 2 ou plus qui a une place libre envoie une ambassade (une chance sur
 * cinq) vers un lieu-dit où son influence atteint {@value Allegiance#EMBASSY_MIN} et dépasse de
 * {@value Allegiance#EMBASSY_LEAD} celle du propriétaire ; {@value #MAX_WORLD} ambassades au plus dans le monde. Un
 * joueur Ami peut en demander une au tableau du village (onglet Domaine) contre {@value #OFFERING} faveurs du peuple.
 */
public final class Embassies {

    public static final int NEGOTIATORS = 2;
    public static final int PARLEY_HOURS = 1;
    public static final int ESCORT_RANGE = 32;
    public static final int SUCCESS = 10;
    public static final int FAILURE = -5;
    public static final int COOLDOWN_DAYS = 7;
    public static final double COUNCIL_CHANCE = 0.2;
    public static final int MAX_WORLD = 3;
    public static final int OFFERING = 3;
    public static final int KILLED_REPUTATION = -80;
    private static final String KEYS = Heraldry.KEYS + "embassy.";

    private Embassies() {
    }

    /** Le village peut-il envoyer une ambassade vers ce lieu-dit (sans compter le seuil d'influence) ? Rend la raison du refus, ou null. */
    static Message blocked(World world, Hamlets.Place h, Village v, long day) {
        Village owner = Allegiance.owner(world, h);
        if (owner != null && owner.id().equals(v.id())) {
            return Message.translation(KEYS + "already").param("hamlet", h.name());
        }
        if (Allegiance.cap(v) <= 0) {
            return Message.translation(KEYS + "tier");
        }
        if (!Allegiance.canHold(world, v)) {
            return Message.translation(KEYS + "full").param("village", v.name()).param("cap", Allegiance.cap(v));
        }
        if (Allegiance.cooling(world, h, v, day)) {
            return Message.translation(KEYS + "cooling").param("hamlet", h.name());
        }
        for (HamletTrips.Trip t : HamletTrips.ofKind(world, HamletTrips.EMBASSY)) {
            if (t.village().equals(v.id()) || t.hamlet().equals(h.id())) {
                return Message.translation(KEYS + "busy");
            }
        }
        if (Math.sqrt(v.horizontalDistanceSquared(h.x(), h.z())) > Allegiance.RANGE) {
            return Message.translation(KEYS + "far").param("range", Allegiance.RANGE);
        }
        return null;
    }

    /** Fait partir l'ambassade (commande, demande d'un joueur, conseil du matin). */
    static HamletTrips.Trip start(World world, Store<EntityStore> store, Hamlets.Place h, Village v) {
        HamletTrips.Trip t = HamletTrips.startKind(world, h, v, HamletTrips.EMBASSY, NEGOTIATORS + 1);
        if (t != null) {
            Chantiers.announce(world, v, Message.translation(KEYS + "left").param("hamlet", h.name()), null, NotificationStyle.Default);
            Village owner = Allegiance.owner(world, h);
            if (owner != null) {
                Chantiers.announce(world, owner, Message.translation(KEYS + "warned").param("village", v.name()).param("hamlet", h.name()), null,
                        NotificationStyle.Warning);
            }
        }
        return t;
    }

    /** Demande d'un joueur Ami au tableau du village, contre {@value #OFFERING} faveurs du peuple. Rend la raison du refus, ou null. */
    public static Message request(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v, Hamlets.Place h) {
        if (!Reputations.rank(store, ref, v).atLeast(Rank.AMI)) {
            return Message.translation(KEYS + "rank").param("village", v.name());
        }
        Message why = blocked(world, h, v, GameClock.day(store));
        if (why != null) {
            return why;
        }
        String favour = v.people().favorItem();
        if (WorldLife.count(store, ref, favour::equals) < OFFERING) {
            return Message.translation(KEYS + "offering").param("count", OFFERING);
        }
        WorldLife.take(store, ref, favour::equals, OFFERING);
        return start(world, store, h, v) == null ? Message.translation(KEYS + "busy") : null;
    }

    /** Conseil du matin. */
    static void morning(World world, Store<EntityStore> store, long day, Random random) {
        int ongoing = HamletTrips.ofKind(world, HamletTrips.EMBASSY).size();
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        Collections.shuffle(villages, random);
        for (Village v : villages) {
            if (ongoing >= MAX_WORLD) {
                return;
            }
            if (v.tier() < 2 || random.nextDouble() >= COUNCIL_CHANCE) {
                continue;
            }
            Hamlets.Place best = null;
            int bestLead = Integer.MIN_VALUE;
            for (Hamlets.Place h : Hamlets.all(world)) {
                if (h.stage() != Hamlets.BUILT || blocked(world, h, v, day) != null) {
                    continue;
                }
                int inf = Allegiance.influence(world, h, v);
                Village owner = Allegiance.owner(world, h);
                int lead = inf - (owner == null ? 0 : Allegiance.influence(world, h, owner));
                if (inf >= Allegiance.EMBASSY_MIN && lead >= Allegiance.EMBASSY_LEAD && lead > bestLead) {
                    best = h;
                    bestLead = lead;
                }
            }
            if (best != null && start(world, store, best, v) != null) {
                ongoing++;
            }
        }
    }

    /** Arrivée sur la place : chassés si rivaux du propriétaire et gardés, sinon parlement d'une heure. */
    static void arrive(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        Village owner = Allegiance.owner(world, h);
        int[] m = h.market();
        if (owner != null && owner.id().equals(v.id())) {
            // Le lieu-dit s'est rallié en chemin : rien à négocier, l'ambassade rentre.
            t.leg = HamletTrips.BACK;
            t.at = 0;
            Walk.of(t.walkKey()).reset(0);
            return;
        }
        if (owner != null && Garrisons.count(world, h) > 0 && Relations.value(world, owner, v) <= Relations.RIVAL) {
            Allegiance.change(world, h, v, FAILURE);
            Allegiance.cool(world, h, v, GameClock.day(store) + COOLDOWN_DAYS);
            Message msg = Message.translation(KEYS + "chased").param("village", v.name()).param("hamlet", h.name()).param("owner", owner.name());
            Chantiers.announce(world, v, msg, null, NotificationStyle.Warning);
            WorldLife.announce(world, store, m[0], m[1], 96, msg, NotificationStyle.Warning);
            t.leg = HamletTrips.BACK;
            t.at = 0;
            Walk.of(t.walkKey()).reset(0);
            return;
        }
        t.leg = HamletTrips.STAY;
        t.at = 0;
        t.until = GameClock.seconds(store) + PARLEY_HOURS * 3600L;
        WorldLife.announce(world, store, m[0], m[1], 96, Message.translation(KEYS + "parley").param("village", v.name()).param("hamlet", h.name()),
                NotificationStyle.Default);
    }

    /** Chance de réussite (0 à 1) de l'ambassade, avec les joueurs proches de la place. */
    static double chance(World world, Store<EntityStore> store, Hamlets.Place h, Village v) {
        Village owner = Allegiance.owner(world, h);
        int lead = Allegiance.influence(world, h, v) - (owner == null ? 0 : Allegiance.influence(world, h, owner));
        double p = Math.max(0.10, Math.min(0.95, 0.5 + lead / 100.0));
        int[] m = h.market();
        for (PlayerRef pr : WorldLife.playersNear(world, store, m[0], m[1], ESCORT_RANGE)) {
            Ref<EntityStore> ref = pr.getReference();
            if (ref != null && ref.isValid() && Reputations.rank(store, ref, v).atLeast(Rank.AMI)) {
                p += 0.15;
                break;
            }
        }
        if (Allegiance.councilSpecialty(v, Allegiance.DIPLOMACY)) {
            p += 0.15;
        }
        if (v.id().equals(Allegiance.letter(world, h))) {
            p += 0.15;
        }
        if (owner != null) {
            p -= 0.20 * Garrisons.count(world, h);
        }
        return Math.max(0.05, Math.min(0.95, p));
    }

    /**
     * Fin du parlement : la décision. Rend vrai si l'ambassade rentre au village (étape retour), faux si la tournée est
     * finie sur place.
     */
    static boolean resolve(World world, Store<EntityStore> store, HamletTrips.Trip t, Village v, Hamlets.Place h) {
        double p = chance(world, store, h, v);
        boolean success = new Random().nextDouble() < p;
        int[] m = h.market();
        if (v.id().equals(Allegiance.letter(world, h))) {
            Allegiance.setLetter(world, h, null); // la lettre sert une fois
        }
        if (!success) {
            Allegiance.change(world, h, v, FAILURE);
            Allegiance.cool(world, h, v, GameClock.day(store) + COOLDOWN_DAYS);
            Message msg = Message.translation(KEYS + "failed").param("village", v.name()).param("hamlet", h.name())
                    .param("chance", (int) Math.round(p * 100));
            Chantiers.announce(world, v, msg, null, NotificationStyle.Warning);
            WorldLife.announce(world, store, m[0], m[1], 96, msg, NotificationStyle.Warning);
            return true;
        }
        Allegiance.change(world, h, v, SUCCESS);
        Village now = Allegiance.owner(world, h);
        if (now != null && now.id().equals(v.id())) {
            return true; // rallié pendant le parlement : rien à prendre, l'ambassade rentre
        }
        if (!Allegiance.canHold(world, v)) {
            Chantiers.announce(world, v, Message.translation(KEYS + "noRoom").param("hamlet", h.name()), null, NotificationStyle.Default);
            return true;
        }
        Allegiance.setOwner(world, store, h, v, "embassy");
        // Le garde de l'ambassade reste sur place, s'il a survécu à la route : un marcheur de moins sur le retour.
        boolean guardAlive = t.walkers >= NEGOTIATORS + 1;
        if (!guardAlive) {
            return true; // le garde est tombé en route : les négociateurs rentrent, pas de garde offert
        }
        Garrisons.add(world, h, v, 1);
        Walk walk = Walk.of(t.walkKey());
        List<Ref<EntityStore>> live = walk.alive();
        if (!live.isEmpty()) {
            Ref<EntityStore> guard = live.remove(live.size() - 1);
            WorldLife.remove(store, guard);
        }
        t.walkers--;
        if (t.walkers <= 0) {
            HamletTrips.drop(world, store, t);
            return false;
        }
        return true;
    }
}
