package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.boss.Telegraphs;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.world.Allegiance;
import dev.nakasar.hytale.peuples.world.Relations;
import dev.nakasar.hytale.peuples.world.WorldLife;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

/**
 * La vie des ouvrages (Kevin, 2026-11-16) : siège, capture, reprise, raids, ruine et relève.
 * <ul>
 *   <li><b>Expédition</b> : un village rival du village qui tient l'ouvrage (relation au plus {@value #ATTACK_RELATION},
 *   hors trêve, palier 3) envoie {@value #SOLDIERS} soldats (un de plus avec la spécialité Garnison de sa Caserne). Il part
 *   de lui-même (une chance sur dix par semaine) ou à la demande d'un joueur Hôte au panneau du rival, contre
 *   {@value #OFFERING} faveurs. La troupe marche ({@value #MARCH_PER_BLOCK} s de jeu par bloc, une heure au moins) ;
 *   pendant ce temps l'ouvrage est assiégé et son effet suspendu ;</li>
 *   <li><b>Assaut</b> : un joueur à moins de {@value WorldLife#REAL_RANGE} blocs, c'est un vrai combat (soldats camp 1
 *   contre gardes camp 0) : l'attaquant (soldats et joueurs de son camp) doit tenir seul le disque de capture de {@value #CAPTURE_RADIUS} blocs autour du
 *   panneau pendant {@value #CAPTURE_SECONDS} s (disque rouge au sol, à sa taille exacte), {@value #ASSAULT_SECONDS} s au
 *   plus. Personne : réglé seul (soldats × palier contre gardes × palier + tours de garde proches, à 20 % près). Les
 *   combattants sont des rôles de défenseurs amicaux envers les joueurs : ils gardent la régénération vanilla hors
 *   combat (exception de la règle n° 1). Les gardes tombés restent comptés si l'assaut repasse sans témoin ;</li>
 *   <li><b>Capture</b> : l'ouvrage passe à l'attaquant, même au-delà de ses limites (Kevin) ; ses soldats restants le
 *   gardent. Le propriétaire peut le reprendre (bouton Reprendre au panneau, rang Ami, sans frais) ; au palier 3 il lance
 *   lui-même sa reprise après {@value #RETAKE_DAYS} jours ; au bout de {@value #LOST_DAYS} jours l'ouvrage est perdu
 *   pour de bon et ne compte plus dans sa limite ;</li>
 *   <li><b>Raid</b> : un raid sur quatre vise un ouvrage (Raids) ; perdu, l'ouvrage est rasé, le village garde son
 *   palier. Une ruine se relève pour la moitié de la fondation et {@value #REBUILD_HOURS} h de travaux.</li>
 * </ul>
 * État sauvé dans {@link AnnexState} (Occupant, Garrison, SiegeBy...) ; le combat réel est en mémoire.
 */
public final class Ouvrages {

    public static final String KEYS = Annexes.KEYS + "ouvrage.";
    public static final int SOLDIERS = 4;
    public static final int OFFERING = 5;
    public static final double WEEKLY_CHANCE = 0.10;
    public static final int ATTACK_RELATION = -40;
    public static final int CAPTURE_RADIUS = 6;
    public static final int CAPTURE_SECONDS = 15;
    public static final int ASSAULT_SECONDS = 300;
    public static final int COOLDOWN_DAYS = 14;
    public static final int RETAKE_DAYS = 3;
    public static final int LOST_DAYS = 14;
    public static final int MARCH_PER_BLOCK = 12;
    public static final int MIN_MARCH = 3600;
    public static final int REBUILD_HOURS = 12;
    public static final int RELATION_LOSS = -25;
    public static final int ANNOUNCE_RANGE = 600;
    /** Force des habitants de l'ouvrage dans l'assaut sans témoin. */
    private static final int SENTRY = 2;
    /** Le disque rouge dure 6 s (particule Nakasar_Peuples_Warning_60) : redessiné à ce rythme. */
    private static final long DISC_MILLIS = 6000L;
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    private static final class Fight {
        final long started = System.currentTimeMillis();
        final List<Ref<EntityStore>> attackers = new ArrayList<>();
        final List<Ref<EntityStore>> defenders = new ArrayList<>();
        long clearSince;
        long drawn;
        boolean spawned;
    }

    private static final Map<String, Fight> FIGHTS = new ConcurrentHashMap<>();
    /** Gardes du propriétaire tués pendant le siège en cours (l'ouvrage non pris n'a pas de garnison sauvée). */
    private static final Map<String, Integer> FALLEN = new ConcurrentHashMap<>();
    /** Recharge après une reprise ratée par le propriétaire : courte, pour qu'il puisse réessayer avant la perte. */
    public static final int RETAKE_COOLDOWN_DAYS = 2;

    private Ouvrages() {
    }

    static String key(Infrastructures.Work w) {
        return w.owner().id() + "/" + w.workshop().getId();
    }

    /** Clé de camp des combattants (WorldAttitudeSystem). */
    static String sideKey(Infrastructures.Work w) {
        return "OS:" + key(w);
    }

    /** L'ouvrage `workshopId` du village `ownerId`, ou null. */
    public static Infrastructures.Work find(World world, String ownerId, String workshopId) {
        Village owner = Villages.registry(world).byId(ownerId);
        Workshop w = Workshop.get(workshopId);
        AnnexState a = owner == null ? null : owner.annex(workshopId);
        if (owner == null || w == null || !w.isAnnex() || !w.annex().infrastructure() || a == null || a.granted()) {
            return null;
        }
        return new Infrastructures.Work(owner, w, a);
    }

    /** Gardes de l'ouvrage : la garnison de l'occupant, sinon les villageois du propriétaire arrivés à son niveau (+1 Garnison). */
    public static int defenders(Infrastructures.Work w) {
        if (w.state().occupied()) {
            return Math.max(0, w.state().garrison());
        }
        int n = 0;
        for (VillageLayout.Job job : w.workshop().annex().workers()) {
            if (job.tier() <= w.level()) {
                n++;
            }
        }
        return n + dev.nakasar.hytale.peuples.workshop.Projects.garrisonBonus(w.owner());
    }

    /** Gardes encore debout pour le siège en cours : {@link #defenders} moins ceux tombés dans un assaut réel. */
    static int standing(Infrastructures.Work w) {
        return w.state().occupied() ? defenders(w) : Math.max(0, defenders(w) - FALLEN.getOrDefault(key(w), 0));
    }

    // ---- Lancer une expédition ----

    /** Pourquoi `attacker` ne peut pas attaquer l'ouvrage (reprise comprise), ou null. */
    public static Message blocked(World world, Village attacker, Infrastructures.Work w, long day) {
        Village holder = Villages.registry(world).byId(w.holder());
        Message name = Message.translation(w.workshop().nameKey());
        if (holder == null || holder.id().equals(attacker.id())) {
            return Message.translation(KEYS + "own").param("building", name);
        }
        if (!w.state().built()) {
            return Message.translation(KEYS + "notStanding").param("building", name);
        }
        if (w.state().besieged()) {
            return Message.translation(KEYS + "busy").param("building", name);
        }
        if (Allegiance.expeditionCooling(world, attacker, day)) {
            return Message.translation(KEYS + "cooling").param("village", attacker.name());
        }
        boolean retake = w.owner().id().equals(attacker.id());
        if (retake) {
            return null; // le propriétaire reprend son bien : pas besoin d'être rival de l'occupant
        }
        if (attacker.tier() < 3) {
            return Message.translation(KEYS + "tier").param("village", attacker.name());
        }
        if (Relations.value(world, attacker, holder) > ATTACK_RELATION) {
            return Message.translation(KEYS + "notRival").param("village", attacker.name()).param("holder", holder.name())
                    .param("value", ATTACK_RELATION);
        }
        if (Relations.truce(world, attacker, holder, day)) {
            return Message.translation(KEYS + "truce").param("village", holder.name());
        }
        if (Math.sqrt(attacker.horizontalDistanceSquared(w.state().x(), w.state().z())) > Allegiance.RANGE) {
            return Message.translation(KEYS + "far").param("range", Allegiance.RANGE);
        }
        return null;
    }

    /** Ouvrages que `attacker` peut attaquer aujourd'hui (onglet Ouvrages de son panneau). */
    public static List<Infrastructures.Work> targets(World world, Village attacker, long day) {
        List<Infrastructures.Work> out = new ArrayList<>();
        for (Infrastructures.Work w : Infrastructures.all(world)) {
            if (!w.owner().id().equals(attacker.id()) && !w.holder().equals(attacker.id()) && w.state().built()
                    && blocked(world, attacker, w, day) == null) {
                out.add(w);
            }
        }
        out.sort((a, b) -> Double.compare(attacker.horizontalDistanceSquared(a.state().x(), a.state().z()),
                attacker.horizontalDistanceSquared(b.state().x(), b.state().z())));
        return out;
    }

    /** Demande d'un joueur Hôte au panneau de `attacker`, contre {@value #OFFERING} faveurs. Rend la raison du refus, ou null. */
    public static Message request(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village attacker, Infrastructures.Work w) {
        if (!Reputations.rank(store, ref, attacker).atLeast(Rank.HOTE)) {
            return Message.translation(KEYS + "rank").param("village", attacker.name()).param("rank", Message.translation(Rank.HOTE.nameKey()));
        }
        Message why = blocked(world, attacker, w, GameClock.day(store));
        if (why != null) {
            return why;
        }
        String favour = attacker.people().favorItem();
        if (WorldLife.count(store, ref, favour::equals) < OFFERING) {
            return Message.translation(KEYS + "offering").param("count", OFFERING);
        }
        WorldLife.take(store, ref, favour::equals, OFFERING);
        launch(world, store, attacker, w);
        return null;
    }

    /** Bouton Reprendre (rang Ami au panneau du propriétaire, sans frais). Rend la raison du refus, ou null. */
    public static Message retake(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village owner, Infrastructures.Work w) {
        if (!Reputations.rank(store, ref, owner).atLeast(Annexes.GRANT_RANK)) {
            return Message.translation(KEYS + "rank").param("village", owner.name()).param("rank", Message.translation(Annexes.GRANT_RANK.nameKey()));
        }
        if (!w.state().occupied() || w.state().lost()) {
            return Message.translation(KEYS + "notOccupied").param("building", Message.translation(w.workshop().nameKey()));
        }
        Message why = blocked(world, owner, w, GameClock.day(store));
        if (why != null) {
            return why;
        }
        launch(world, store, owner, w);
        return null;
    }

    static void launch(World world, Store<EntityStore> store, Village attacker, Infrastructures.Work w) {
        int soldiers = SOLDIERS + dev.nakasar.hytale.peuples.workshop.Projects.garrisonBonus(attacker);
        double distance = Math.sqrt(attacker.horizontalDistanceSquared(w.state().x(), w.state().z()));
        long arrive = GameClock.seconds(store) + Math.max(MIN_MARCH, (long) (distance * MARCH_PER_BLOCK));
        Village holder = Villages.registry(world).byId(w.holder());
        w.state().startSiege(attacker.id(), arrive, soldiers);
        Message m = Message.translation(KEYS + (w.owner().id().equals(attacker.id()) ? "retakeAnnounce" : "announce"))
                .param("village", attacker.name()).param("building", Message.translation(w.workshop().nameKey()))
                .param("owner", w.owner().name()).param("holder", holder == null ? "?" : holder.name())
                .param("x", w.state().x()).param("z", w.state().z());
        Chantiers.announce(world, attacker, m, null, NotificationStyle.Warning);
        if (holder != null && holder != attacker) {
            Chantiers.announce(world, holder, m, null, NotificationStyle.Danger);
        }
        if (w.owner() != holder && w.owner() != attacker) {
            Chantiers.announce(world, w.owner(), m, null, NotificationStyle.Warning);
        }
        WorldLife.announce(world, store, w.state().x(), w.state().z(), ANNOUNCE_RANGE, m, NotificationStyle.Danger);
        LOGGER.atInfo().log("Nakasar Peuples : %s envoie %d soldats contre l'ouvrage %s de %s (tenu par %s), arrivée %d",
                attacker.name(), soldiers, w.workshop().getId(), w.owner().name(), holder == null ? "?" : holder.name(), arrive);
    }

    // ---- Le matin : occupation qui dure, reprises, expéditions spontanées ----

    public static void morning(World world, Store<EntityStore> store, long day, Random random) {
        List<Infrastructures.Work> all = Infrastructures.all(world);
        for (Infrastructures.Work w : all) {
            AnnexState a = w.state();
            if (!a.occupied() || a.lost()) {
                continue;
            }
            if (day - a.occupiedDay() >= LOST_DAYS) {
                a.setLost(true);
                Village holder = Villages.registry(world).byId(a.occupant());
                Chantiers.announce(world, w.owner(), Message.translation(KEYS + "lost").param("building", Message.translation(w.workshop().nameKey()))
                        .param("village", holder == null ? "?" : holder.name()).param("days", LOST_DAYS), null, NotificationStyle.Warning);
                continue;
            }
            if (day - a.occupiedDay() >= RETAKE_DAYS && w.owner().tier() >= 3 && blocked(world, w.owner(), w, day) == null) {
                launch(world, store, w.owner(), w);
            }
        }
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        Collections.shuffle(villages, random);
        for (Village v : villages) {
            if (v.isHamlet() || v.tier() < 3 || random.nextDouble() >= WEEKLY_CHANCE / 7.0) {
                continue;
            }
            List<Infrastructures.Work> targets = targets(world, v, day);
            if (!targets.isEmpty()) {
                launch(world, store, v, targets.get(random.nextInt(targets.size())));
                return; // une expédition spontanée par matin au plus
            }
        }
    }

    // ---- Le pas : arrivée, assaut réel ou réglé seul ----

    public static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        long now = GameClock.seconds(store);
        for (Infrastructures.Work w : Infrastructures.all(world)) {
            AnnexState a = w.state();
            String key = key(w);
            if (!a.besieged()) {
                Fight f = FIGHTS.remove(key);
                if (f != null) {
                    release(store, f);
                }
                continue;
            }
            Village attacker = Villages.registry(world).byId(a.siegeBy());
            Village holder = Villages.registry(world).byId(w.holder());
            if (attacker == null || holder == null || attacker == holder || !a.built()) {
                end(store, w);
                continue;
            }
            if (now < a.siegeArrive()) {
                continue;
            }
            Fight f = FIGHTS.get(key);
            if (WorldLife.near(players, a.x(), a.z(), WorldLife.REAL_RANGE)) {
                if (f == null) {
                    f = new Fight();
                    FIGHTS.put(key, f);
                    WorldLife.announce(world, store, a.x(), a.z(), WorldLife.REAL_RANGE * 2, Message.translation(KEYS + "assault")
                            .param("village", attacker.name()).param("building", Message.translation(w.workshop().nameKey())), NotificationStyle.Danger);
                }
                fight(world, store, w, f, attacker, holder);
            } else {
                if (f != null) {
                    FIGHTS.remove(key);
                    release(store, f);
                }
                autoResolve(world, store, w, attacker, holder);
            }
        }
    }

    private static void fight(World world, Store<EntityStore> store, Infrastructures.Work w, Fight f, Village attacker, Village holder) {
        AnnexState a = w.state();
        Vector3d centre = WorldLife.ground(world, a.x(), a.z(), 6);
        if (centre == null) {
            return; // zone pas chargée : on attend
        }
        if (!f.spawned) {
            int soldiers = a.siegeSoldiers();
            int guards = standing(w);
            if (!WorldLife.budget(world, soldiers + guards)) {
                return;
            }
            f.spawned = true;
            double dx = attacker.x() - a.x();
            double dz = attacker.z() - a.z();
            double len = Math.max(1, Math.hypot(dx, dz));
            for (int i = 0; i < soldiers; i++) {
                Vector3d at = WorldLife.ground(world, (int) Math.floor(a.x() + dx / len * 14 + (i - soldiers / 2.0) * 2),
                        (int) Math.floor(a.z() + dz / len * 14), 6);
                Ref<EntityStore> ref = at == null ? null : WorldLife.spawn(store, Relations.fighterRole(attacker.people()), at,
                        (float) Math.atan2(dx, -dz));
                if (ref != null) {
                    WorldLife.side(ref, sideKey(w), 1);
                    String k = key(w);
                    WorldLife.mortal(ref, (wd, npc, where, killer) -> soldierDied(wd, k, npc));
                    f.attackers.add(ref);
                }
            }
            for (int i = 0; i < guards; i++) {
                double angle = i * Math.PI * 2 / Math.max(1, guards);
                Vector3d at = WorldLife.ground(world, (int) Math.floor(a.x() + Math.cos(angle) * 3), (int) Math.floor(a.z() + Math.sin(angle) * 3), 4);
                Ref<EntityStore> ref = at == null ? null : WorldLife.spawn(store, Relations.fighterRole(holder.people()), at, (float) -angle);
                if (ref != null) {
                    WorldLife.side(ref, sideKey(w), 0);
                    String k = key(w);
                    WorldLife.mortal(ref, (wd, npc, where, killer) -> guardDied(wd, k, npc));
                    f.defenders.add(ref);
                }
            }
        }
        f.attackers.removeIf(r -> !r.isValid());
        f.defenders.removeIf(r -> !r.isValid());
        long now = System.currentTimeMillis();
        if (now - f.drawn >= DISC_MILLIS) {
            // Disque de capture : rouge, exactement à sa taille (règle n° 3).
            f.drawn = now;
            Telegraphs.particle(store, "Nakasar_Peuples_Warning_60", new Vector3d(centre).add(0, 0.1, 0), (float) (Telegraphs.WARNING_SCALE * CAPTURE_RADIUS));
        }
        for (Ref<EntityStore> ref : f.attackers) {
            WorldLife.leash(store, ref, centre);
        }
        // Les joueurs comptent aussi (Kevin, 2026-11-17) : un joueur dans le disque est du camp du village où son rang est
        // le plus haut (Ami au moins) ; à rang égal, il ne compte pour personne.
        int[] players = playersWithin(world, store, centre, attacker, holder);
        if (f.attackers.isEmpty() && players[0] == 0) {
            defend(world, store, w, attacker, holder);
            return;
        }
        boolean held = f.defenders.isEmpty() && players[1] == 0 && (players[0] > 0 || anyWithin(store, f.attackers, centre));
        if (held) {
            if (f.clearSince == 0) {
                f.clearSince = now;
            } else if (now - f.clearSince >= CAPTURE_SECONDS * 1000L) {
                win(world, store, w, attacker, holder, f.attackers.size());
                return;
            }
        } else {
            f.clearSince = 0;
        }
        if (now - f.started >= ASSAULT_SECONDS * 1000L) {
            if (f.attackers.size() + players[0] > f.defenders.size() + players[1]) {
                win(world, store, w, attacker, holder, Math.max(1, f.attackers.size()));
            } else {
                defend(world, store, w, attacker, holder);
            }
        }
    }

    /** Joueurs dans le disque de prise : {camp attaquant, camp défenseur}. */
    private static int[] playersWithin(World world, Store<EntityStore> store, Vector3d centre, Village attacker, Village holder) {
        int[] out = new int[2];
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            Vector3d at = Requests.position(store, ref);
            if (at == null || !Telegraphs.inCircle(at, centre, CAPTURE_RADIUS)) {
                continue;
            }
            Rank forAttacker = Reputations.rank(store, ref, attacker);
            Rank forHolder = Reputations.rank(store, ref, holder);
            if (forAttacker.atLeast(Rank.AMI) && forAttacker != forHolder && forAttacker.atLeast(forHolder)) {
                out[0]++;
            } else if (forHolder.atLeast(Rank.AMI) && forHolder != forAttacker && forHolder.atLeast(forAttacker)) {
                out[1]++;
            }
        }
        return out;
    }

    private static boolean anyWithin(Store<EntityStore> store, List<Ref<EntityStore>> refs, Vector3d centre) {
        for (Ref<EntityStore> ref : refs) {
            Vector3d at = Requests.position(store, ref);
            if (at != null && Telegraphs.inCircle(at, centre, CAPTURE_RADIUS)) {
                return true;
            }
        }
        return false;
    }

    private static void soldierDied(World world, String key, Ref<EntityStore> npc) {
        Infrastructures.Work w = byKey(world, key);
        if (w != null) {
            w.state().setSiegeSoldiers(w.state().siegeSoldiers() - 1);
        }
    }

    private static void guardDied(World world, String key, Ref<EntityStore> npc) {
        Infrastructures.Work w = byKey(world, key);
        if (w == null) {
            return;
        }
        if (w.state().occupied()) {
            w.state().setGarrison(Math.max(0, w.state().garrison() - 1));
        } else {
            FALLEN.merge(key, 1, Integer::sum); // compté si l'assaut repasse en résolution sans témoin
        }
    }

    private static Infrastructures.Work byKey(World world, String key) {
        int slash = key.indexOf('/');
        return slash < 0 ? null : find(world, key.substring(0, slash), key.substring(slash + 1));
    }

    /** Assaut sans témoin : soldats × palier contre (gardes × palier + habitants + tours proches), chacun à 20 % près. */
    private static void autoResolve(World world, Store<EntityStore> store, Infrastructures.Work w, Village attacker, Village holder) {
        Random random = new Random();
        int soldiers = w.state().siegeSoldiers();
        int guards = standing(w);
        int towers = 0;
        for (Infrastructures.Work t : Infrastructures.held(world, holder, Infrastructures.TOWER)) {
            if (t != w && t.distanceSquared(w.state().x(), w.state().z()) <= 160.0 * 160.0) {
                towers++;
            }
        }
        double attack = soldiers * Math.max(1, attacker.tier()) * (0.8 + 0.4 * random.nextDouble());
        double defence = (guards * Math.max(1, holder.tier()) + SENTRY + towers) * (0.8 + 0.4 * random.nextDouble());
        if (attack > defence) {
            win(world, store, w, attacker, holder, Math.max(1, soldiers - guards / 2));
        } else {
            if (w.state().occupied() && guards > 0 && random.nextBoolean()) {
                w.state().setGarrison(guards - 1);
            }
            defend(world, store, w, attacker, holder);
        }
    }

    private static void win(World world, Store<EntityStore> store, Infrastructures.Work w, Village attacker, Village holder, int survivors) {
        AnnexState a = w.state();
        long day = GameClock.day(store);
        Message name = Message.translation(w.workshop().nameKey());
        boolean retake = w.owner().id().equals(attacker.id());
        end(store, w);
        if (retake) {
            a.occupy(null, day, 0);
        } else {
            // Un ouvrage déjà perdu pour son propriétaire le reste quand un tiers le prend.
            boolean wasLost = a.lost();
            a.occupy(attacker.id(), day, Math.max(1, survivors));
            a.setLost(wasLost);
            Villagers.dismiss(store, w.owner().id(), Villagers.ANNEX_PREFIX + w.workshop().getId() + "/");
        }
        Relations.change(world, attacker, holder, RELATION_LOSS);
        Message m = Message.translation(KEYS + (retake ? "retaken" : "taken")).param("village", attacker.name()).param("building", name)
                .param("owner", w.owner().name()).param("holder", holder.name());
        Chantiers.announce(world, attacker, m, null, NotificationStyle.Success);
        Chantiers.announce(world, holder, m, null, NotificationStyle.Danger);
        if (w.owner() != attacker && w.owner() != holder) {
            Chantiers.announce(world, w.owner(), m, null, NotificationStyle.Warning);
        }
        WorldLife.announce(world, store, a.x(), a.z(), ANNOUNCE_RANGE, m, NotificationStyle.Warning);
        AnnexMarkers.clearAll();
        LOGGER.atInfo().log("Nakasar Peuples : ouvrage %s de %s %s par %s (%d soldats restants)", w.workshop().getId(), w.owner().name(),
                retake ? "repris" : "pris", attacker.name(), survivors);
    }

    private static void defend(World world, Store<EntityStore> store, Infrastructures.Work w, Village attacker, Village holder) {
        end(store, w);
        boolean retake = w.owner().id().equals(attacker.id());
        Allegiance.expeditionCool(world, attacker, GameClock.day(store) + (retake ? RETAKE_COOLDOWN_DAYS : COOLDOWN_DAYS));
        Message m = Message.translation(KEYS + "repelled").param("village", attacker.name())
                .param("building", Message.translation(w.workshop().nameKey())).param("holder", holder.name());
        Chantiers.announce(world, holder, m, null, NotificationStyle.Success);
        Chantiers.announce(world, attacker, m, null, NotificationStyle.Warning);
        WorldLife.announce(world, store, w.state().x(), w.state().z(), WorldLife.REAL_RANGE * 2, m, NotificationStyle.Success);
    }

    private static void end(Store<EntityStore> store, Infrastructures.Work w) {
        w.state().clearSiege();
        FALLEN.remove(key(w));
        Fight f = FIGHTS.remove(key(w));
        if (f != null) {
            release(store, f);
        }
    }

    private static void release(Store<EntityStore> store, Fight f) {
        f.attackers.forEach(r -> WorldLife.remove(store, r));
        f.defenders.forEach(r -> WorldLife.remove(store, r));
    }

    // ---- Ruine et relève ----

    /**
     * Rase l'ouvrage `workshopId` du village (raid perdu) : villageois renvoyés, état « ruine » (place gardée), blocs
     * retirés tout de suite si la zone est chargée, sinon au passage d'un joueur ({@link Annexes#step}). Faux si l'ouvrage
     * n'est pas debout.
     */
    public static boolean raze(World world, Store<EntityStore> store, Village owner, String workshopId, PlayerRef by) {
        Infrastructures.Work w = find(world, owner.id(), workshopId);
        if (w == null || !w.state().built()) {
            return false;
        }
        end(store, w);
        Villagers.dismiss(store, owner.id(), Villagers.ANNEX_PREFIX + workshopId + "/");
        w.state().markRuin();
        if (Annexes.demolish(world, owner, w.workshop(), w.state())) {
            w.state().setCleared(true);
        }
        Message m = Message.translation(KEYS + "razed").param("building", Message.translation(w.workshop().nameKey()))
                .param("x", w.state().x()).param("z", w.state().z());
        Chantiers.announce(world, owner, m, null, NotificationStyle.Danger);
        LOGGER.atInfo().log("Nakasar Peuples : ouvrage %s de %s rasé en %d %d", workshopId, owner.name(), w.state().x(), w.state().z());
        return true;
    }

    /** Matériaux pour relever une ruine : la moitié de la fondation. */
    public static Map<String, Integer> rebuildCost(Workshop w) {
        Map<String, Integer> out = new LinkedHashMap<>();
        for (VillageLayout.Material m : w.annex().materials()) {
            out.merge(m.itemId(), Math.max(1, m.quantity() / 2), Integer::sum);
        }
        return out;
    }

    /** Relève la ruine de l'ouvrage `w` (rang Ami) : moitié de la fondation au dépôt, {@value #REBUILD_HOURS} h de travaux. */
    public static boolean rebuild(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, Workshop w) {
        Message block = Annexes.block(store, ref, village, 0);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        AnnexState a = village.annex(w.getId());
        if (a == null || !a.ruined()) {
            return false;
        }
        if (!a.cleared()) {
            player.sendMessage(Message.translation(KEYS + "notCleared"));
            return false;
        }
        Map<String, Integer> cost = rebuildCost(w);
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        if (deposit == null) {
            player.sendMessage(Message.translation("nakasar_peuples.board.depositMissing"));
            return false;
        }
        Map<String, Integer> missing = new LinkedHashMap<>();
        cost.forEach((item, q) -> {
            int have = deposit.getOrDefault(item, 0);
            if (have < q) {
                missing.put(item, q - have);
            }
        });
        if (!missing.isEmpty()) {
            player.sendMessage(Message.translation(Annexes.KEYS + "missing").param("list", Annexes.materialList(missing)));
            return false;
        }
        ItemContainer chest = Villages.depositChest(world, village);
        cost.forEach((item, q) -> Requests.take(chest, item, q));
        long now = GameClock.seconds(store);
        a.startWorks(a.x(), a.y(), a.z(), a.rotation(), a.ground(), now, now + REBUILD_HOURS * 3600L);
        world.execute(() -> {
            Annexes.prepare(world, village, w, a);
            Annexes.site(world, village, w, a, 1);
        });
        Chantiers.announce(world, village, Message.translation(KEYS + "rebuilding").param("player", player.getUsername())
                .param("building", Message.translation(w.nameKey())).param("hours", REBUILD_HOURS), null, NotificationStyle.Success);
        return true;
    }

    public static void clearAll() {
        FIGHTS.clear();
    }
}
