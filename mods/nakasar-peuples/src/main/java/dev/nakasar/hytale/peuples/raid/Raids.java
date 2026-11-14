package dev.nakasar.hytale.peuples.raid;

import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventRecord;
import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventsWorldConfig;
import com.hypixel.hytale.builtin.adventure.worldevents.action.EventStartAction;
import com.hypixel.hytale.builtin.adventure.worldevents.action.EventStopAction;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.PlayerRequest;
import dev.nakasar.hytale.peuples.request.RequestTemplate;
import dev.nakasar.hytale.peuples.request.RequestType;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.RaidRecord;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les raids sur les villages (étape 6 ; GDD, Raids) : « un raid est un événement de monde (même moteur que la brèche
 * des chasseurs) : annonce 1 min avant (tambours, fumée, marqueur de carte), vague de 5 à 12 ennemis du peuple hostile
 * voisin selon le palier, 5 min, puis bilan. Les gardes du village se battent avec le joueur. Un raid perdu enflamme
 * un bâtiment et fait redescendre le palier d'un cran. »
 *
 * <p>Le Java tient la vérité (qui est en vie, qui a tué, issue) ; l'évènement de monde vanilla {@value #EVENT} affiche le
 * compte à rebours dans la liste des évènements de la carte, puis joue le titre et le cri de guerre à l'arrivée de la
 * vague, au camp trork ({@link RaidLocationCondition}). Sans évènements de monde dans ce monde, le Java joue ce titre
 * lui-même.
 *
 * <p>Déroulé :
 * <ol>
 *   <li><b>Attendu</b> : un raid est prévu pour la nuit d'un jour de jeu ({@link RaidRecord}) quand le village gagne un
 *       palier, au hasard chaque matin (selon le palier, deux nuits au moins entre deux raids), quand un joueur prend la
 *       demande de défense ou la veillée de la chaîne, ou par la commande. Les gardes en parlent le jour.</li>
 *   <li><b>Annonce</b> ({@value #WARN_SECONDS} s) : la nuit, dès qu'un joueur est à moins de {@value #START_RADIUS}
 *       blocs du cœur (un village ne brûle jamais sans témoin : sinon le raid attend la nuit suivante). Cor de guerre,
 *       titre, direction du camp ; les gardes du village (un par palier, {@link #DEFENDERS}) se postent autour du
 *       cœur.</li>
 *   <li><b>Assaut</b> (au plus {@value #FIGHT_SECONDS} s) : la vague ({@link #wave}) sort du camp, à
 *       {@value #CAMP_DISTANCE} blocs, et marche sur le cœur.</li>
 *   <li><b>Bilan</b> : victoire si tous les assaillants tombent ; défaite au bout du temps, si tous les gardes sont tombés
 *       avec un assaillant à moins de {@value #HEART_REACH} blocs du cœur, ou si plus aucun joueur n'est à moins de
 *       {@value #WATCH_RADIUS} blocs pendant {@value #ABANDON_SECONDS} s.</li>
 * </ol>
 *
 * <p>Règles permanentes (AGENTS.md) : assaillants et gardes sont des rôles du mod sur les modèles et les attaques des
 * Trorks et des Razorleaf vanilla ; aucun ne se régénère (VillageNoRegenSystem : moins de 96 blocs d'un village) ; aucune
 * zone d'alerte (pas d'attaque spéciale). Les PNJ du raid ne sont pas sauvegardés.
 */
public final class Raids {

    public static final String KEYS = "nakasar_peuples.raid.";
    public static final String EVENT = "Nakasar_Peuples_Raid";

    public static final int WARN_SECONDS = 60;
    public static final int FIGHT_SECONDS = 300;
    /** Les PNJ restants partent (sont retirés) ce temps après le bilan. */
    public static final int CLEANUP_SECONDS = 8;
    /** Distance du camp trork au cœur du village. */
    public static final int CAMP_DISTANCE = 42;
    /** Un joueur à moins de cette distance du cœur déclenche un raid attendu. */
    public static final int START_RADIUS = 80;
    /** Un joueur à moins de cette distance du cœur pendant le raid y participe (bilan, récompenses). */
    public static final int WATCH_RADIUS = 160;
    public static final int ABANDON_SECONDS = 90;
    /** Défaite si les gardes sont tous tombés et qu'un assaillant est à moins de cette distance du cœur. */
    public static final int HEART_REACH = 16;
    /** Nuits minimales entre deux raids tirés au hasard. */
    public static final int MIN_GAP = 2;
    /** Chance d'un raid tiré au hasard chaque matin, par palier. */
    static final double[] CHANCE = {0.10, 0.20, 0.30, 0.40};
    /** Gardes du village par palier (GDD, Villages vivants : 1, 2, 4, 6). */
    public static final int[] DEFENDERS = {1, 2, 4, 6};
    /** Pas de début de raid dans les deux dernières heures de la nuit (le bilan tomberait après l'aube). */
    static final int LAST_START_HOUR = 4;

    public static final int REP_WIN = 50;
    public static final int ESSOR_WIN = 30;
    public static final int FAVORS_WIN = 4;

    public static final String RAIDER_PREFIX = "Nakasar_Peuples_Raider_";
    public static final String WARRIOR = RAIDER_PREFIX + "Trork_Warrior";
    public static final String MAULER = RAIDER_PREFIX + "Trork_Mauler";
    public static final String BRAWLER = RAIDER_PREFIX + "Trork_Brawler";
    public static final String WARLORD = RAIDER_PREFIX + "Trork_Warlord";
    /** Trophée du raid gagné (crânes vanilla), donné à chaque joueur qui a abattu un assaillant. */
    public static final String TROPHY = "Nakasar_Peuples_Trophy_Trork";

    static final String HORN = "SFX_Gobliterator_Arena_Horn";
    static final String VICTORY_SOUND = "SFX_Coffer_Goblin_Reward";

    /** Ce que représente un PNJ du raid. */
    public enum Kind { RAIDER, DEFENDER }

    public enum Phase { WARN, FIGHT, DONE }

    /** Un raid en cours (mémoire de session). */
    static final class Active {
        final String villageId;
        final long night;
        final UUID eventId;
        final List<Vector3i> camps = new ArrayList<>();
        final List<Ref<EntityStore>> raiders = new ArrayList<>();
        final List<Ref<EntityStore>> defenders = new ArrayList<>();
        final Set<UUID> participants = new HashSet<>();
        final Set<UUID> killers = new HashSet<>();
        Phase phase = Phase.WARN;
        float elapsed;
        float unwatched;
        int total;
        int byPlayers;
        int byGuards;
        int fallen;
        boolean eventRunning;

        Active(String villageId, long night, UUID eventId) {
            this.villageId = villageId;
            this.night = night;
            this.eventId = eventId;
        }
    }

    private record Owner(String villageId, Kind kind) {
    }

    private static final Map<String, Active> ACTIVE = new HashMap<>();
    private static final Map<Ref<EntityStore>, Owner> OWNERS = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Lieu (camp) de chaque évènement de raid, lu par {@link RaidLocationCondition}. */
    private static final Map<UUID, Vector3i> LOCATIONS = new ConcurrentHashMap<>();
    /** Dernier jour de jeu où le tirage du matin a été fait, par village. */
    private static final Map<String, Long> ROLLED = new HashMap<>();

    private Raids() {
    }

    // ---- Lecture ----

    static Vector3i location(UUID event) {
        return event == null ? null : LOCATIONS.get(event);
    }

    /** Vrai si un raid est en cours au village (cette session). */
    public static synchronized boolean isActive(Village village) {
        return village != null && ACTIVE.containsKey(village.id());
    }

    /** Vrai si un raid est attendu au village pour cette nuit (ou une nuit déjà passée sans témoin). */
    public static boolean tonight(Store<EntityStore> store, Village village) {
        RaidRecord r = village.raid();
        return r.scheduled() && r.night() <= GameClock.day(store);
    }

    /** Vrai si un raid est attendu (plus tard) ou en cours. */
    public static boolean pending(Village village) {
        return village.raid().scheduled() || isActive(village);
    }

    /** Ce que représente ce PNJ pour un raid, ou null. */
    public static Kind kind(Ref<EntityStore> ref) {
        Owner o = ref == null ? null : OWNERS.get(ref);
        return o == null ? null : o.kind();
    }

    /** Étape 7 : un camp trork n'est jamais pillé (ce sont les Trorks qui pillent les Kweebecs). */
    public static boolean raided(People people) {
        return people != People.TRORK;
    }

    /** Vrai si le rôle est un assaillant de raid. */
    public static boolean isRaiderRole(String role) {
        return role != null && role.startsWith(RAIDER_PREFIX);
    }

    /** Rôle du garde de raid du peuple. */
    public static String defenderRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Defender";
    }

    /**
     * Évènement de monde du raid sur ce peuple : {@value #EVENT} pour les Kweebecs, {@code Nakasar_Peuples_Raid_<Peuple>}
     * pour les autres (étape 8 : titre, compte à rebours et cri propres aux Scaraks et au culte).
     */
    public static String event(People people) {
        return people == People.KWEEBEC ? EVENT : EVENT + "_" + people.id();
    }

    /** Trophée du raid gagné sur ce peuple (crânes trorks, carapace scarak, masque du culte). */
    public static String trophy(People people) {
        return "Nakasar_Peuples_Trophy_" + people.raidEnemy();
    }

    /**
     * Clé de texte du raid qui nomme l'ennemi : la clé Kweebec (Trorks) telle quelle, suffixée du peuple pour les autres
     * ({@code raid.title.wave.Feran}…).
     */
    public static String key(People people, String suffix) {
        return people == People.KWEEBEC ? KEYS + suffix : KEYS + suffix + "." + people.id();
    }

    /** Rôles des quatre rangs d'assaillants (guerrier, cogneur, brute, chef) contre ce peuple. */
    static String[] raiders(People people) {
        return switch (people) {
            case FERAN -> new String[] {RAIDER_PREFIX + "Scarak_Fighter", RAIDER_PREFIX + "Scarak_Louse",
                    RAIDER_PREFIX + "Scarak_Defender", RAIDER_PREFIX + "Scarak_Broodmother"};
            case RENONCE -> new String[] {RAIDER_PREFIX + "Cult_Cultist", RAIDER_PREFIX + "Cult_Berserker",
                    RAIDER_PREFIX + "Cult_Brute", RAIDER_PREFIX + "Cult_Marauder"};
            // Étape 9 : la montée du Vide sur les Slothians (larves, rampants, squelettes brûlés vanilla).
            case SLOTHIAN -> new String[] {RAIDER_PREFIX + "Void_Larva", RAIDER_PREFIX + "Void_Crawler",
                    RAIDER_PREFIX + "Void_Skeleton_Soldier", RAIDER_PREFIX + "Void_Skeleton_Knight"};
            default -> new String[] {WARRIOR, MAULER, BRAWLER, WARLORD};
        };
    }

    /**
     * Vrai si l'assaillant `raider` s'en prend au PNJ `role` : Trorks contre Kweebecs, Scaraks contre Feran, culte contre
     * Renoncés (étape 8).
     */
    public static boolean preys(String raider, String role) {
        if (raider == null || role == null || !isRaiderRole(raider)) {
            return false;
        }
        String rest = raider.substring(RAIDER_PREFIX.length());
        if (rest.startsWith("Scarak_")) {
            return role.contains("Feran");
        }
        if (rest.startsWith("Cult_")) {
            return role.contains("Renonce");
        }
        if (rest.startsWith("Void_")) {
            return role.contains("Slothian");
        }
        return role.contains("Kweebec");
    }

    /** La vague d'un raid sur un village de ce peuple et de ce palier (5, 7, 9 ou 12 assaillants). */
    public static List<String> wave(People people, int tier) {
        return wave(people, tier, 0);
    }

    /** Idem, avec `extra` guerriers de plus (étape 8 : niveau de la ruche scarak sur les Feran). */
    public static List<String> wave(People people, int tier, int extra) {
        List<String> out = new ArrayList<>();
        int[][] counts = {
                // guerriers, cogneurs, brutes, chef de guerre
                {4, 1, 0, 0},
                {4, 2, 1, 0},
                {4, 2, 2, 1},
                {5, 3, 3, 1},
        };
        int[] c = counts[Math.max(0, Math.min(3, tier))];
        String[] roles = raiders(people);
        for (int n = 0; n < extra; n++) {
            out.add(roles[0]);
        }
        for (int i = 0; i < roles.length; i++) {
            for (int n = 0; n < c[i]; n++) {
                out.add(roles[i]);
            }
        }
        return out;
    }

    /** État du raid au village, en une ligne (tableau, commande, dialogues). */
    public static Message status(Store<EntityStore> store, Village village) {
        Active a;
        synchronized (Raids.class) {
            a = ACTIVE.get(village.id());
        }
        if (a != null) {
            int alive = alive(a.raiders);
            return a.phase == Phase.WARN
                    ? Message.translation(key(village.people(), "status.warn")).param("seconds", Math.max(0, WARN_SECONDS - (int) a.elapsed))
                    : Message.translation(KEYS + "status.fight").param("alive", alive).param("total", a.total)
                    .param("seconds", Math.max(0, FIGHT_SECONDS - (int) a.elapsed));
        }
        RaidRecord r = village.raid();
        if (r.scheduled()) {
            return Message.translation(r.night() <= GameClock.day(store) ? KEYS + "status.tonight" : KEYS + "status.later")
                    .param("cause", Message.translation(r.cause() == null || r.cause().equals("Random")
                            ? key(village.people(), "cause.Random") : KEYS + "cause." + r.cause()));
        }
        return Message.translation(KEYS + "status.none");
    }

    /** Bilan du dernier raid, ou null s'il n'y en a pas eu. */
    public static Message lastReport(Village village) {
        RaidRecord r = village.raid();
        if (r.lastResult() == null) {
            return null;
        }
        boolean won = "Won".equals(r.lastResult());
        Message m = Message.translation(won ? KEYS + "last.won" : KEYS + "last.lost")
                .param("killed", r.lastKilled()).param("raiders", r.lastRaiders()).param("fallen", r.lastFallen())
                .param("won", r.won()).param("lost", r.lost());
        if (!won) {
            m = m.param("building", r.lastBurnt() == null ? Message.translation(KEYS + "noBuilding")
                    : Message.translation(Chantiers.buildingKey(r.lastBurnt())));
        }
        return m;
    }

    // ---- Prévision ----

    /**
     * Prévoit un raid au village pour la nuit du jour `night` (cause : Tier, Random, Request, Chain, Command). Un raid
     * déjà attendu garde sa nuit si elle est plus proche. Rend vrai si un raid est attendu au retour.
     */
    public static boolean schedule(Village village, long night, String cause) {
        RaidRecord r = village.raid();
        if (r.scheduled() && r.night() <= night) {
            return true;
        }
        r.schedule(night, cause);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : raid prévu au village %s pour la nuit %d (%s)", village.name(), night, cause);
        return true;
    }

    /**
     * Nuit du prochain raid qu'un joueur peut demander (défense, veillée) : cette nuit, sauf si un raid y a déjà eu lieu
     * (alors la suivante).
     */
    public static long nextNight(Store<EntityStore> store, Village village) {
        long day = GameClock.day(store);
        return village.raid().lastNight() >= day ? day + 1 : day;
    }

    // ---- Pas du système ----

    /** Le pas des raids d'un monde, une fois par seconde, sur le thread du monde. */
    static synchronized void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        long day = GameClock.day(store);
        boolean night = GameClock.isNight(store);
        int hour = GameClock.hour(store);
        List<Vector3d> players = new ArrayList<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, p.getReference());
            if (at != null) {
                players.add(at);
            }
        }
        for (Village village : new ArrayList<>(Villages.registry(world).all())) {
            if (!raided(village.people())) {
                continue;
            }
            Active a = ACTIVE.get(village.id());
            if (a != null) {
                stepActive(world, store, village, a, dt);
                continue;
            }
            RaidRecord r = village.raid();
            if (r.active()) {
                // Raid interrompu par un redémarrage : il reprendra depuis l'annonce, sans pénalité.
                r.setActive(false);
            }
            morning(store, village, day, night);
            if (r.scheduled() && r.night() < day) {
                // Personne n'est venu la nuit prévue : le raid attend la prochaine nuit avec un témoin.
                r.schedule(day, r.cause());
            }
            if (r.scheduled() && r.night() <= day && night && hour >= 0 && !(hour >= LAST_START_HOUR && hour < GameClock.MORNING)
                    && near(village, players, START_RADIUS) && Villages.heartPresent(world, village)) {
                begin(world, store, village);
            }
        }
        // Raids d'un village effacé.
        ACTIVE.keySet().removeIf(id -> {
            if (Villages.registry(world).byId(id) == null) {
                Active gone = ACTIVE.get(id);
                removeAll(store, gone);
                stopEvent(store, gone);
                return true;
            }
            return false;
        });
    }

    /** Tirage du matin et raid du palier gagné. */
    private static void morning(Store<EntityStore> store, Village village, long day, boolean night) {
        RaidRecord r = village.raid();
        if (r.tierSeen() < 0) {
            r.setTierSeen(village.tier());
        } else if (village.tier() > r.tierSeen()) {
            r.setTierSeen(village.tier());
            schedule(village, nextNight(store, village), "Tier");
        } else if (village.tier() < r.tierSeen()) {
            r.setTierSeen(village.tier());
        }
        Long rolled = ROLLED.get(village.id());
        if (night || (rolled != null && rolled == day)) {
            return;
        }
        ROLLED.put(village.id(), day);
        if (r.scheduled() || (r.lastNight() != RaidRecord.NONE && day - r.lastNight() < MIN_GAP)) {
            return;
        }
        Random random = new Random(village.id().hashCode() * 7919L + day);
        double chance = CHANCE[Math.max(0, Math.min(3, village.tier()))]
                + dev.nakasar.hytale.peuples.zone.Hive.extraChance(store.getExternalData().getWorld(), village);
        if (random.nextDouble() < chance) {
            schedule(village, day, "Random");
        }
    }

    /** Ouvre le raid : annonce, gardes, évènement de monde. Rend faux si aucun camp n'a pu être placé. */
    static boolean begin(World world, Store<EntityStore> store, Village village) {
        Terrain terrain = new Terrain(world);
        Random random = ThreadLocalRandom.current();
        int campCount = village.tier() >= 2 ? 2 : 1;
        double base = random.nextDouble(0, Math.PI * 2);
        List<Vector3i> camps = new ArrayList<>();
        for (int c = 0; c < campCount; c++) {
            for (int attempt = 0; attempt < 8 && camps.size() == c; attempt++) {
                double angle = base + c * (Math.PI * 0.8) + attempt * (Math.PI / 4);
                int x = village.x() + (int) Math.round(Math.cos(angle) * CAMP_DISTANCE);
                int z = village.z() + (int) Math.round(Math.sin(angle) * CAMP_DISTANCE);
                int[] spot = terrain.safeSpot(x, z, 8);
                if (spot != null) {
                    camps.add(new Vector3i(spot[0], spot[1], spot[2]));
                }
            }
        }
        if (camps.isEmpty()) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : pas de camp de raid possible autour de %s (terrain pas chargé ?)", village.name());
            return false;
        }
        long night = GameClock.day(store);
        Active a = new Active(village.id(), night, UUID.randomUUID());
        a.camps.addAll(camps);
        ACTIVE.put(village.id(), a);
        village.raid().setActive(true);
        LOCATIONS.put(a.eventId, new Vector3i(camps.get(0)));
        if (WorldEventsWorldConfig.isEnabled(world)) {
            try {
                EventStartAction.startEvent(store, new WorldEventRecord(a.eventId, event(village.people()), true));
                a.eventRunning = true;
            } catch (RuntimeException e) {
                PeuplesPlugin.get().getLogger().atWarning().log("Peuples : évènement de raid %s non lancé (%s)", event(village.people()), e.getMessage());
            }
        }
        // Les gardes se postent autour du cœur.
        int guards = DEFENDERS[Math.max(0, Math.min(3, village.tier()))];
        String role = defenderRole(village.people());
        for (int i = 0; i < guards; i++) {
            double angle = base + i * (Math.PI * 2 / guards);
            int x = village.x() + (int) Math.round(Math.cos(angle) * 4);
            int z = village.z() + (int) Math.round(Math.sin(angle) * 4);
            int[] safe = terrain.safeSpot(x, z, 3);
            if (safe == null) {
                continue;
            }
            Vector3d spot = new Vector3d(safe[0] + 0.5, safe[1], safe[2] + 0.5);
            Ref<EntityStore> ref = spawn(store, village, Kind.DEFENDER, role, spot, (float) -angle);
            if (ref != null) {
                a.defenders.add(ref);
                leash(store, ref, spot);
            }
        }
        Vector3i camp = camps.get(0);
        Message direction = Message.translation(Villages.MESSAGES + "dir." + Requests.direction(camp.x() - village.x(), camp.z() - village.z()));
        Message warn = Message.translation(KEYS + "warning").param("village", village.name()).param("direction", direction)
                .param("seconds", WARN_SECONDS).param("enemy", Message.translation(KEYS + "enemy." + village.people().id()));
        announce(world, store, village, a, warn, Message.translation(KEYS + "title.warning"),
                Message.translation(key(village.people(), "title.warningSub")).param("direction", direction), NotificationStyle.Danger);
        sound(store, HORN, new Vector3d(village.x() + 0.5, village.y() + 1, village.z() + 0.5));
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : raid sur %s (palier %d, %d camp(s), %d garde(s), évènement %s)",
                village.name(), village.tier(), camps.size(), a.defenders.size(), a.eventRunning ? a.eventId : "aucun");
        return true;
    }

    private static void stepActive(World world, Store<EntityStore> store, Village village, Active a, float dt) {
        a.elapsed += dt;
        prune(a.raiders);
        prune(a.defenders);
        List<PlayerRef> watching = watchers(world, store, village);
        for (PlayerRef p : watching) {
            a.participants.add(p.getUuid());
        }
        switch (a.phase) {
            case WARN -> {
                if (a.elapsed >= WARN_SECONDS) {
                    spawnWave(world, store, village, a);
                    a.phase = Phase.FIGHT;
                    a.elapsed = 0f;
                }
            }
            case FIGHT -> {
                a.unwatched = watching.isEmpty() ? a.unwatched + dt : 0f;
                if (a.raiders.isEmpty()) {
                    resolve(world, store, village, a, true, "cleared");
                } else if (a.elapsed >= FIGHT_SECONDS) {
                    resolve(world, store, village, a, false, "timeout");
                } else if (a.unwatched >= ABANDON_SECONDS) {
                    resolve(world, store, village, a, false, "abandon");
                } else if (a.fallen > 0 && a.defenders.isEmpty() && raiderNearHeart(store, village, a)) {
                    // Tous les gardes sont tombés et un assaillant atteint le cœur du village.
                    resolve(world, store, village, a, false, "guards");
                }
            }
            case DONE -> {
                if (a.elapsed >= CLEANUP_SECONDS) {
                    removeAll(store, a);
                    ACTIVE.remove(village.id());
                }
            }
        }
    }

    private static void spawnWave(World world, Store<EntityStore> store, Village village, Active a) {
        Terrain terrain = new Terrain(world);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        List<String> wave = wave(village.people(), village.tier(),
                dev.nakasar.hytale.peuples.zone.Hive.extraRaiders(world, village));
        Vector3d heart = new Vector3d(village.x() + 0.5, village.y(), village.z() + 0.5);
        for (int i = 0; i < wave.size(); i++) {
            Vector3i camp = a.camps.get(i % a.camps.size());
            // Point sûr près du camp (le camp lui-même l'est) : jamais sous l'eau, dans un bloc ou sur une pente.
            int[] spot = terrain.safeSpot(camp.x() + random.nextInt(-4, 5), camp.z() + random.nextInt(-4, 5), 2);
            int x = spot == null ? camp.x() : spot[0];
            int z = spot == null ? camp.z() : spot[2];
            int feet = spot == null ? camp.y() : spot[1];
            float yaw = (float) Math.atan2(-(village.x() - x), -(village.z() - z));
            Ref<EntityStore> ref = spawn(store, village, Kind.RAIDER, wave.get(i), new Vector3d(x + 0.5, feet, z + 0.5), yaw);
            if (ref != null) {
                a.raiders.add(ref);
                leash(store, ref, heart);
            }
        }
        a.total = a.raiders.size();
        Message arrived = Message.translation(KEYS + "arrived").param("village", village.name()).param("count", a.total)
                .param("enemy", Message.translation(KEYS + "enemy." + village.people().id()));
        // Avec l'évènement de monde, son étape d'arrivée joue le titre et le cri de guerre au camp.
        announce(world, store, village, a, arrived, a.eventRunning ? null : Message.translation(key(village.people(), "title.wave")),
                Message.translation(KEYS + "title.waveSub").param("count", a.total), NotificationStyle.Danger);
    }

    /** Fin du raid : bilan, récompenses ou incendie, demandes de défense. */
    static void resolve(World world, Store<EntityStore> store, Village village, Active a, boolean victory, String why) {
        a.phase = Phase.DONE;
        a.elapsed = 0f;
        stopEvent(store, a);
        int killed = a.byPlayers + a.byGuards;
        String burnt = null;
        if (victory) {
            Villages.addEssor(village, ESSOR_WIN);
        } else {
            VillageLayout.Building b = Chantiers.burn(world, village, null, true);
            burnt = b == null ? null : b.id();
            if (b == null) {
                // Village sans plan (fondé à la main) : rien à brûler, la jauge d'essor se vide.
                Villages.addEssor(village, -village.essor());
            }
        }
        village.raid().record(a.night, victory, a.total, killed, a.fallen, burnt);
        Message enemy = Message.translation(KEYS + "enemy." + village.people().id());
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            boolean took = a.participants.contains(p.getUuid());
            if (took) {
                Message report = Message.translation(victory ? KEYS + "report.won" : key(village.people(), "report.lost." + why))
                        .param("village", village.name()).param("killed", killed).param("raiders", a.total)
                        .param("byPlayers", a.byPlayers).param("byGuards", a.byGuards).param("fallen", a.fallen)
                        .param("enemy", enemy).param("rep", REP_WIN).param("essor", ESSOR_WIN).param("favors", FAVORS_WIN)
                        .param("favor", VillageBoard.itemName(village.people().favorItem()))
                        .param("building", burnt == null ? Message.translation(KEYS + "noBuilding") : Message.translation(Chantiers.buildingKey(burnt)));
                p.sendMessage(report);
                EventTitleUtil.showEventTitleToPlayer(p, Message.translation(victory ? KEYS + "title.won" : KEYS + "title.lost"),
                        Message.raw(village.name()), EventTitleStyle.Default, null, 4f, 0.5f, 1f);
                if (victory) {
                    Reputations.change(world, store, ref, p, village, REP_WIN, KEYS + "reputationReason");
                    Requests.give(store, ref, new ItemStack(village.people().favorItem(), FAVORS_WIN));
                    if (a.killers.contains(p.getUuid())) {
                        Requests.give(store, ref, new ItemStack(trophy(village.people()), 1));
                        p.sendMessage(Message.translation(KEYS + "trophy").param("item", VillageBoard.itemName(trophy(village.people()))));
                    }
                }
            }
            settleRequests(world, store, ref, p, village, victory, took);
        }
        if (victory) {
            sound(store, VICTORY_SOUND, new Vector3d(village.x() + 0.5, village.y() + 1, village.z() + 0.5));
        }
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : raid sur %s %s (%s) : %d/%d abattus (%d joueurs, %d gardes), %d garde(s) tombé(s), brûlé : %s",
                village.name(), victory ? "gagné" : "perdu", why, killed, a.total, a.byPlayers, a.byGuards, a.fallen, burnt);
    }

    /**
     * Demandes de défense (tableau) et veillée (chaîne) du joueur pour ce village : remplies si le raid est gagné et qu'il
     * y était, échouées si le raid est perdu.
     */
    private static void settleRequests(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                       boolean victory, boolean took) {
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        if (data == null) {
            return;
        }
        for (PlayerRequest r : new ArrayList<>(data.requests())) {
            RequestTemplate t = r.template();
            if (t == null || t.type() != RequestType.DEFENSE || !r.villageId().equals(village.id()) || data.request(r.id()) == null) {
                continue;
            }
            if (victory && took) {
                Requests.advance(world, store, ref, player, data, r, r.needed() - r.progress());
            } else if (!victory) {
                Requests.fail(world, store, ref, player, data, r, KEYS + "requestLost");
            }
        }
    }

    /** Annule le raid en cours (commande, village effacé) : PNJ retirés, raid attendu oublié. */
    public static synchronized boolean cancel(World world, Village village) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Active a = ACTIVE.remove(village.id());
        village.raid().setActive(false);
        village.raid().unschedule();
        if (a == null) {
            return false;
        }
        removeAll(store, a);
        stopEvent(store, a);
        return true;
    }

    /** Lance tout de suite un raid au village (commande d'essai) ; rend faux si un raid est déjà en cours. */
    public static synchronized boolean startNow(World world, Village village) {
        if (ACTIVE.containsKey(village.id())) {
            return false;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        village.raid().schedule(GameClock.day(store), "Command");
        return begin(world, store, village);
    }

    /** Fait finir le raid en cours (commande d'essai) : victoire ou défaite. */
    public static synchronized boolean finishNow(World world, Village village, boolean victory) {
        Active a = ACTIVE.get(village.id());
        if (a == null || a.phase == Phase.DONE) {
            return false;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (victory) {
            for (Ref<EntityStore> r : new ArrayList<>(a.raiders)) {
                OWNERS.remove(r);
                if (r.isValid()) {
                    store.removeEntity(r, RemoveReason.REMOVE);
                }
            }
            a.byGuards += a.raiders.size();
            a.raiders.clear();
        }
        resolve(world, store, village, a, victory, victory ? "cleared" : "timeout");
        return true;
    }

    // ---- Morts (RaidDeathSystem) ----

    /** Un PNJ du raid est mort ; `playerKiller` est le joueur qui l'a abattu, ou null (garde, chute, feu...). */
    static synchronized void died(Ref<EntityStore> ref, UUID playerKiller) {
        Owner o = OWNERS.remove(ref);
        if (o == null) {
            return;
        }
        Active a = ACTIVE.get(o.villageId());
        if (a == null) {
            return;
        }
        if (o.kind() == Kind.RAIDER) {
            a.raiders.remove(ref);
            if (playerKiller != null) {
                a.byPlayers++;
                a.killers.add(playerKiller);
                a.participants.add(playerKiller);
            } else {
                a.byGuards++;
            }
        } else {
            a.defenders.remove(ref);
            a.fallen++;
        }
    }

    // ---- Outils ----

    private static Ref<EntityStore> spawn(Store<EntityStore> store, Village village, Kind kind, String role, Vector3d at, float yaw) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, yaw, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de faire apparaître '%s' pour le raid de %s", role, village.name());
            return null;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        OWNERS.put(ref, new Owner(village.id(), kind));
        return ref;
    }

    private static void leash(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d at) {
        NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(new Vector3d(at));
        }
    }

    private static void removeAll(Store<EntityStore> store, Active a) {
        if (a == null) {
            return;
        }
        List<Ref<EntityStore>> all = new ArrayList<>(a.raiders);
        all.addAll(a.defenders);
        for (Ref<EntityStore> r : all) {
            OWNERS.remove(r);
            if (r.isValid()) {
                store.removeEntity(r, RemoveReason.REMOVE);
            }
        }
        a.raiders.clear();
        a.defenders.clear();
        LOCATIONS.remove(a.eventId);
    }

    private static void stopEvent(Store<EntityStore> store, Active a) {
        if (a == null || !a.eventRunning) {
            return;
        }
        a.eventRunning = false;
        try {
            EventStopAction.stopEvent(store, a.eventId, (event, id) -> id.equals(event.uuid));
        } catch (RuntimeException e) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : évènement de raid non arrêté (%s)", e.getMessage());
        }
    }

    private static void prune(List<Ref<EntityStore>> refs) {
        refs.removeIf(r -> {
            if (!r.isValid()) {
                OWNERS.remove(r);
                return true;
            }
            return false;
        });
    }

    private static int alive(List<Ref<EntityStore>> refs) {
        int n = 0;
        for (Ref<EntityStore> r : refs) {
            if (r.isValid()) {
                n++;
            }
        }
        return n;
    }

    private static boolean raiderNearHeart(Store<EntityStore> store, Village village, Active a) {
        for (Ref<EntityStore> r : a.raiders) {
            Vector3d at = Requests.position(store, r);
            if (at != null && village.horizontalDistanceSquared(at.x(), at.z()) <= (double) HEART_REACH * HEART_REACH) {
                return true;
            }
        }
        return false;
    }

    private static boolean near(Village village, List<Vector3d> players, int radius) {
        for (Vector3d p : players) {
            if (village.horizontalDistanceSquared(p.x(), p.z()) <= (double) radius * radius) {
                return true;
            }
        }
        return false;
    }

    private static List<PlayerRef> watchers(World world, Store<EntityStore> store, Village village) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, p.getReference());
            if (at != null && village.horizontalDistanceSquared(at.x(), at.z()) <= (double) WATCH_RADIUS * WATCH_RADIUS) {
                out.add(p);
            }
        }
        return out;
    }

    /** Message, notification et titre aux joueurs à moins de {@value #WATCH_RADIUS} blocs (ils participent). */
    private static void announce(World world, Store<EntityStore> store, Village village, Active a, Message message, Message title,
                                 Message subtitle, NotificationStyle style) {
        for (PlayerRef p : watchers(world, store, village)) {
            a.participants.add(p.getUuid());
            p.sendMessage(message);
            NotificationUtil.sendNotification(p.getPacketHandler(), message, style);
            if (title != null) {
                EventTitleUtil.showEventTitleToPlayer(p, title, subtitle, EventTitleStyle.Default, null, 3.5f, 0.4f, 0.8f);
            }
        }
    }

    private static void sound(Store<EntityStore> store, String id, Vector3d at) {
        int index = SoundEvent.getAssetMap().getIndexOrDefault(id, -1);
        if (index >= 0) {
            SoundUtil.playSoundEvent3d(index, SoundCategory.SFX, at.x(), at.y(), at.z(), store);
        }
    }

    public static synchronized void clearAll() {
        ACTIVE.clear();
        OWNERS.clear();
        LOCATIONS.clear();
        ROLLED.clear();
    }
}
