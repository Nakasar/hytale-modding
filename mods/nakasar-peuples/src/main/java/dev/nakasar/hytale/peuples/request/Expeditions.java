package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.entitystats.modifier.Modifier;
import com.hypixel.hytale.server.core.modules.entitystats.modifier.StaticModifier;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.boss.QuestBosses;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les quatre demandes ajoutées le 15 novembre 2026 (Kevin : « de nouveaux types de quêtes »), menées une fois par
 * seconde par {@link RequestSystem} pour chaque joueur qui en a une :
 * <ul>
 *   <li><b>Caravane</b> ({@link RequestType#CARAVAN}) : des caravaniers du village ({@code Members}) partent du cœur
 *   avec le joueur vers le village le plus proche qui n'est pas rival, entre {@code MinDistance} et {@code MaxDistance}
 *   blocs. Ils suivent le joueur le plus proche ; {@code Waves} embuscades ({@code Spawns}) leur barrent la route, à
 *   intervalles réguliers du trajet. Remplie quand un caravanier arrive au cœur du village de destination (qui donne
 *   aussi un peu de réputation) ; échoue si tous tombent.</li>
 *   <li><b>Récolte escortée</b> ({@link RequestType#HARVEST}) : des cueilleurs partent du cœur vers un lieu proche
 *   (une attaque à mi-chemin), y récoltent {@code Duration} secondes, figés, tant que le joueur reste près d'eux
 *   ({@code Waves} attaques pendant la récolte), puis reviennent au village. Le joueur reçoit sa part de la récolte
 *   ({@code ItemId} × {@code Quantity}).</li>
 *   <li><b>Destruction</b> ({@link RequestType#DESTROY}) : à l'approche du lieu, {@code Quantity} blocs vanilla
 *   ({@code TargetBlock}) y sont posés sur des points sûrs, gardés par une bande ({@code Spawns}) ; chaque bloc brisé
 *   compte.</li>
 *   <li><b>Boss</b> ({@link RequestType#BOSS}) : à l'approche du repaire, le chef ({@code Boss}) apparaît ; ses coups
 *   annoncés, ses renforts ({@code Spawns}) et sa barre de vie sont ceux des fractales ({@link QuestBosses}). Sa vie est
 *   gardée avec la demande : s'il disparaît (chunk déchargé, redémarrage), il revient comme il était.</li>
 * </ul>
 * Règles retenues des essais précédents : tout PNJ apparaît sur un point sûr ({@link Terrain#safeSpot}) ; les PNJ du
 * village et les assaillants ne disparaissent pas sous les yeux du joueur à la fin de la demande, ils partent quand
 * plus personne ne les voit ({@link RequestSpawns#release}).
 */
public final class Expeditions {

    /** Un PNJ escorté est rendu quand il arrive à cette distance du cœur du village (comme le captif). */
    public static final int HOME = Requests.ESCORT_HOME;
    /** Les cueilleurs se mettent au travail à cette distance du lieu de récolte. */
    public static final int HARVEST_REACH = 7;
    /** La récolte n'avance que si le joueur est à moins de cette distance du lieu. */
    public static final int HARVEST_WATCH = 28;
    /** Les assaillants d'une embuscade apparaissent à cette distance du groupe. */
    public static final int AMBUSH_DISTANCE = 22;
    /** Au-delà de cette distance du groupe, la tâche montre où il attend. */
    public static final int BEHIND = 24;
    /** Rayon du lieu d'une destruction (blocs posés et comptés). */
    public static final int DESTROY_RADIUS = 6;
    /** Vie du chef par palier du village : +25 % par palier. */
    public static final float BOSS_HEALTH_PER_TIER = 0.25f;

    /** Bandes de destruction déjà posées cette session (une fois par session, comme les gardiens d'une escorte). */
    private static final Set<String> GUARDED = Collections.synchronizedSet(new HashSet<>());
    /** Renforts du chef de chaque demande de boss (clé de la demande → rôles), pour {@link QuestBosses}. */
    private static final Map<String, String[]> ADDS = new ConcurrentHashMap<>();

    private Expeditions() {
    }

    /** Caravanier du peuple (suit le joueur, ne se bat pas). */
    public static String caravaneerRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Caravaneer";
    }

    /** Cueilleur du peuple (suit le joueur, récolte figé sur place). */
    public static String gathererRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Gatherer";
    }

    // ---- Tirage et prise ----

    /** Vrai si le modèle peut être tiré pour ce village (une caravane a besoin d'un autre village où aller). */
    public static boolean available(World world, Village village, RequestTemplate t) {
        return t.type() != RequestType.CARAVAN || destination(world, village, t) != null;
    }

    /** Village où mener la caravane : le plus proche, ni lui-même ni d'un peuple rival, à la bonne distance ; ou null. */
    public static Village destination(World world, Village from, RequestTemplate t) {
        Village best = null;
        double bestDistance = Double.MAX_VALUE;
        double min = (double) t.minDistance() * t.minDistance();
        double max = (double) t.maxDistance() * t.maxDistance();
        People rival = from.people().rival();
        for (Village v : Villages.registry(world).all()) {
            if (v.id().equals(from.id()) || v.people() == rival) {
                continue;
            }
            double d = from.horizontalDistanceSquared(v.x(), v.z());
            if (d >= min && d <= max && d < bestDistance) {
                best = v;
                bestDistance = d;
            }
        }
        return best;
    }

    /** Prépare la demande prise (destination de la caravane, départ du cœur) ; faux si elle ne peut pas commencer. */
    static boolean prepare(World world, PlayerRef player, Village village, RequestTemplate t, PlayerRequest r) {
        if (t.type() == RequestType.CARAVAN) {
            Village dest = destination(world, village, t);
            if (dest == null) {
                player.sendMessage(Message.translation(Requests.KEYS + "caravan.noDestination"));
                return false;
            }
            r.setTarget(dest.id());
        }
        if (t.type().escorted()) {
            r.setPosition(village.x(), village.y(), village.z());
        }
        return true;
    }

    // ---- Pas d'une seconde ----

    static void step(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                     PlayerRequest r, RequestTemplate t, Village village, Vector3d at, String key) {
        switch (t.type()) {
            case CARAVAN -> stepCaravan(world, store, ref, player, data, r, t, village, at, key);
            case HARVEST -> stepHarvest(world, store, ref, player, data, r, t, village, at, key);
            case DESTROY -> stepDestroy(world, store, ref, player, data, r, t, at, key);
            case BOSS -> stepBoss(world, store, player, r, t, village, at, key);
            default -> {
            }
        }
    }

    /**
     * Le groupe escorté : apparaît (ou réapparaît, après un chunk déchargé ou un redémarrage) à sa dernière position
     * quand le joueur en approche ; rend sa position du moment, ou null s'il n'est pas là.
     */
    private static Vector3d group(World world, Store<EntityStore> store, PlayerRef player, PlayerRequest r, RequestTemplate t,
                                  Village village, Vector3d at, String key) {
        List<Ref<EntityStore>> members = RequestSpawns.of(key, RequestSpawns.Kind.ESCORTED);
        if (members.isEmpty()) {
            int alive = r.count() < 0 ? t.members() : r.count();
            int[] pos = r.position();
            if (pos == null) {
                pos = new int[] {village.x(), village.y(), village.z()};
            }
            if (alive <= 0 || !RequestSystem.near(at, pos, RequestSystem.SITE_RANGE)) {
                return null;
            }
            Terrain terrain = new Terrain(world);
            if (terrain.surface(pos[0], pos[2]) == Terrain.NONE) {
                return null;
            }
            String role = t.type() == RequestType.CARAVAN ? caravaneerRole(village.people()) : gathererRole(village.people());
            int spawned = 0;
            for (int i = 0; i < alive; i++) {
                Ref<EntityStore> m = RequestSystem.spawnOnGround(world, store, key, RequestSpawns.Kind.ESCORTED, role, pos[0], pos[2], 3, null);
                if (m != null) {
                    spawned++;
                    if (t.type() == RequestType.HARVEST && r.stage() == 1) {
                        store.ensureAndGetComponent(m, Frozen.getComponentType());
                    }
                }
            }
            if (spawned == 0) {
                return null;
            }
            boolean first = r.count() < 0;
            r.setCount(spawned);
            if (first) {
                Message m = Message.translation(Requests.KEYS + (t.type() == RequestType.CARAVAN ? "caravan.start" : "harvest.start"))
                        .param("count", spawned);
                Village dest = r.target() == null ? null : Villages.registry(world).byId(r.target());
                if (dest != null) {
                    m = m.param("village", dest.name());
                }
                player.sendMessage(m);
            }
            members = RequestSpawns.of(key, RequestSpawns.Kind.ESCORTED);
        }
        double x = 0;
        double y = 0;
        double z = 0;
        int n = 0;
        for (Ref<EntityStore> m : members) {
            Vector3d p = Requests.position(store, m);
            if (p != null) {
                x += p.x();
                y += p.y();
                z += p.z();
                n++;
            }
        }
        if (n == 0) {
            return null;
        }
        Vector3d lead = new Vector3d(x / n, y / n, z / n);
        r.setPosition((int) Math.floor(lead.x()), (int) Math.floor(lead.y()), (int) Math.floor(lead.z()));
        // Les assaillants marchent sur le groupe (point d'attache des pillards, comme le cœur du village dans un raid).
        for (Ref<EntityStore> a : RequestSpawns.of(key, RequestSpawns.Kind.AMBUSH)) {
            NPCEntity npc = store.getComponent(a, NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(new Vector3d(lead));
            }
        }
        return lead;
    }

    /** Vrai si un PNJ escorté est à moins de {@value #HOME} blocs du cœur de `village`. */
    private static boolean arrived(Store<EntityStore> store, String key, Village village) {
        for (Ref<EntityStore> m : RequestSpawns.of(key, RequestSpawns.Kind.ESCORTED)) {
            Vector3d p = Requests.position(store, m);
            if (p != null && village.horizontalDistanceSquared(p.x(), p.z()) <= (double) HOME * HOME) {
                return true;
            }
        }
        return false;
    }

    /** Une embuscade : les assaillants apparaissent à {@value #AMBUSH_DISTANCE} blocs de `around`, du côté de `toward`. */
    private static void ambush(World world, Store<EntityStore> store, PlayerRef player, String key, RequestTemplate t, Vector3d around,
                               double toward) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        double angle = toward + random.nextDouble(-0.9, 0.9);
        int cx = (int) Math.round(around.x() + Math.cos(angle) * AMBUSH_DISTANCE);
        int cz = (int) Math.round(around.z() + Math.sin(angle) * AMBUSH_DISTANCE);
        int spawned = 0;
        for (String role : t.spawns()) {
            if (RequestSystem.spawnOnGround(world, store, key, RequestSpawns.Kind.AMBUSH, role, cx, cz, 4, around) != null) {
                spawned++;
            }
        }
        if (spawned > 0) {
            Message m = Message.translation(Requests.KEYS + "ambush").param("count", spawned);
            player.sendMessage(m);
            NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Warning);
        }
    }

    private static void stepCaravan(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                    PlayerRequest r, RequestTemplate t, Village village, Vector3d at, String key) {
        Village dest = r.target() == null ? null : Villages.registry(world).byId(r.target());
        if (dest == null) {
            Requests.fail(world, store, ref, player, data, r, Requests.KEYS + "caravan.noDestination");
            return;
        }
        Vector3d lead = group(world, store, player, r, t, village, at, key);
        if (lead == null) {
            return;
        }
        if (arrived(store, key, dest)) {
            // Le village d'arrivée sait qui a mené la caravane.
            Reputations.change(world, store, ref, player, dest, Math.max(1, t.reputation() / 2), Requests.KEYS + "caravan.destReason");
            Requests.advance(world, store, ref, player, data, r, 1);
            return;
        }
        double total = Math.sqrt(village.horizontalDistanceSquared(dest.x(), dest.z()));
        double left = Math.sqrt(dest.horizontalDistanceSquared(lead.x(), lead.z()));
        double travelled = total <= 0 ? 1 : 1 - left / total;
        int waves = t.waves();
        if (r.wavesDone() < waves && travelled >= (r.wavesDone() + 1.0) / (waves + 1.0)
                && RequestSpawns.of(key, RequestSpawns.Kind.AMBUSH).isEmpty()) {
            r.setWavesDone(r.wavesDone() + 1);
            ambush(world, store, player, key, t, lead, Math.atan2(dest.z() - lead.z(), dest.x() - lead.x()));
        }
    }

    private static void stepHarvest(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                    PlayerRequest r, RequestTemplate t, Village village, Vector3d at, String key) {
        Vector3d lead = group(world, store, player, r, t, village, at, key);
        if (lead == null) {
            return;
        }
        int[] s = r.site();
        double toSite = Math.hypot(s[0] + 0.5 - lead.x(), s[2] + 0.5 - lead.z());
        switch (r.stage()) {
            case 0 -> {
                double total = Math.sqrt(village.horizontalDistanceSquared(s[0] + 0.5, s[2] + 0.5));
                // Une attaque à mi-chemin.
                if (!r.prepared() && total > 0 && toSite <= total / 2) {
                    r.setPrepared(true);
                    ambush(world, store, player, key, t, lead, Math.atan2(s[2] - lead.z(), s[0] - lead.x()));
                }
                if (toSite <= HARVEST_REACH && RequestSystem.knowSiteHeight(world, r)) {
                    r.setStage(1);
                    r.setTimer(0);
                    for (Ref<EntityStore> m : RequestSpawns.of(key, RequestSpawns.Kind.ESCORTED)) {
                        store.ensureAndGetComponent(m, Frozen.getComponentType());
                    }
                    player.sendMessage(Message.translation(Requests.KEYS + "harvest.begin").param("seconds", t.duration()));
                }
            }
            case 1 -> {
                if (!RequestSystem.near(at, s, HARVEST_WATCH)) {
                    return;
                }
                r.setTimer(r.timer() + 1);
                int waves = t.waves();
                if (r.wavesDone() < waves && r.timer() >= t.duration() * (r.wavesDone() + 1) / (waves + 1)) {
                    r.setWavesDone(r.wavesDone() + 1);
                    ambush(world, store, player, key, t, new Vector3d(s[0] + 0.5, s[1], s[2] + 0.5),
                            ThreadLocalRandom.current().nextDouble(-Math.PI, Math.PI));
                }
                if (r.timer() >= t.duration()) {
                    r.setStage(2);
                    for (Ref<EntityStore> m : RequestSpawns.of(key, RequestSpawns.Kind.ESCORTED)) {
                        store.tryRemoveComponent(m, Frozen.getComponentType());
                    }
                    Message m = Message.translation(Requests.KEYS + "harvest.full");
                    player.sendMessage(m);
                    NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Default);
                }
            }
            default -> {
                if (arrived(store, key, village)) {
                    if (t.itemId() != null && t.quantity() > 0) {
                        // La part du joueur dans la récolte.
                        Requests.give(store, ref, new ItemStack(t.itemId(), t.quantity()));
                    }
                    Requests.advance(world, store, ref, player, data, r, 1);
                }
            }
        }
    }

    private static void stepDestroy(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                    PlayerRequest r, RequestTemplate t, Vector3d at, String key) {
        if (!RequestSystem.near(at, r.site(), RequestSystem.SITE_RANGE) || !RequestSystem.knowSiteHeight(world, r)) {
            return;
        }
        int[] s = r.site();
        ChunkStore chunks = world.getChunkStore();
        if (!r.prepared()) {
            Terrain terrain = new Terrain(world);
            ThreadLocalRandom random = ThreadLocalRandom.current();
            int wanted = t.needed();
            int placed = 0;
            double offset = random.nextDouble(0, Math.PI * 2);
            for (int i = 0; i < wanted; i++) {
                double angle = offset + i * Math.PI * 2 / wanted + random.nextDouble(-0.25, 0.25);
                double radius = 2.5 + random.nextDouble(0, DESTROY_RADIUS - 3);
                int[] spot = terrain.safeSpot(s[0] + (int) Math.round(Math.cos(angle) * radius),
                        s[2] + (int) Math.round(Math.sin(angle) * radius), 2);
                if (spot != null && Math.abs(spot[0] - s[0]) <= DESTROY_RADIUS && Math.abs(spot[2] - s[2]) <= DESTROY_RADIUS
                        && Blocks.isEmpty(chunks, spot[0], spot[1], spot[2])
                        && Blocks.set(chunks, spot[0], spot[1], spot[2], t.targetBlock(), random.nextInt(4))) {
                    placed++;
                    r.addMark(spot[0], spot[1], spot[2]);
                }
            }
            if (placed == 0) {
                PeuplesPlugin.get().getLogger().atWarning().log("Peuples : aucun %s posé au lieu %d, %d de la demande %s",
                        t.targetBlock(), s[0], s[2], t.getId());
                return;
            }
            r.setStage(placed);
            r.setPrepared(true);
            player.sendMessage(Message.translation(Requests.KEYS + "destroy.found").param("count", placed)
                    .param("item", VillageBoard.itemName(t.targetBlock())));
        }
        if (GUARDED.add(key)) {
            for (String role : t.spawns()) {
                RequestSystem.spawnOnGround(world, store, key, RequestSpawns.Kind.GUARD, role, s[0], s[2], 5,
                        new Vector3d(s[0] + 0.5, s[1], s[2] + 0.5));
            }
        }
        // Seuls les blocs posés comptent (un bloc à plusieurs cases a des cases de remplissage du même nom).
        int remaining = 0;
        for (int[] b : r.marks()) {
            // Section pas chargée : le bloc est encore là.
            if (Blocks.id(chunks, b[0], b[1], b[2]) == Blocks.UNLOADED || Blocks.is(Blocks.name(chunks, b[0], b[1], b[2]), t.targetBlock())) {
                remaining++;
            }
        }
        // Les blocs qui n'ont pas pu être posés comptent comme brisés.
        int destroyed = t.needed() - Math.min(r.stage(), remaining);
        if (destroyed > r.progress()) {
            Requests.advance(world, store, ref, player, data, r, destroyed - r.progress());
        }
    }

    private static void stepBoss(World world, Store<EntityStore> store, PlayerRef player, PlayerRequest r, RequestTemplate t,
                                 Village village, Vector3d at, String key) {
        Ref<EntityStore> boss = RequestSpawns.first(key, RequestSpawns.Kind.BOSS);
        if (boss != null) {
            // La vie du chef suit la demande : il revient comme il était s'il disparaît.
            r.setCount(Math.max(1, Math.round(QuestBosses.healthFraction(store, boss) * 1000f)));
            return;
        }
        if (!RequestSystem.near(at, r.site(), RequestSystem.SITE_RANGE) || !RequestSystem.knowSiteHeight(world, r)) {
            return;
        }
        int[] s = r.site();
        Vector3d lair = new Vector3d(s[0] + 0.5, s[1], s[2] + 0.5);
        boss = RequestSystem.spawnOnGround(world, store, key, RequestSpawns.Kind.BOSS, t.boss(), s[0], s[2], 2, lair);
        if (boss == null) {
            return;
        }
        ADDS.put(key, t.spawns());
        EntityStatMap stats = store.getComponent(boss, EntityStatMap.getComponentType());
        if (stats != null) {
            int health = DefaultEntityStatTypes.getHealth();
            stats.putModifier(health, "Nakasar_Peuples_BossTier", new StaticModifier(Modifier.ModifierTarget.MAX,
                    StaticModifier.CalculationType.MULTIPLICATIVE, 1f + BOSS_HEALTH_PER_TIER * village.tier()));
            stats.maximizeStatValue(health);
        }
        if (r.count() > 0) {
            QuestBosses.setHealthFraction(store, boss, r.count() / 1000f);
        }
        if (!r.prepared()) {
            r.setPrepared(true);
            Message m = Message.translation(Requests.KEYS + "boss.found").param("title", Requests.title(t));
            player.sendMessage(m);
            NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Warning);
        }
    }

    /** Renforts du chef (appelé par {@link QuestBosses} aux seuils de vie) : autour de lui, attachés au repaire. */
    public static void summonAdds(Store<EntityStore> store, String key, Ref<EntityStore> boss, Vector3d at) {
        String[] roles = ADDS.get(key);
        if (roles == null || roles.length == 0) {
            return;
        }
        World world = store.getExternalData().getWorld();
        NPCEntity npc = store.getComponent(boss, NPCEntity.getComponentType());
        Vector3d leash = npc == null || npc.getLeashPoint() == null ? at : new Vector3d(npc.getLeashPoint());
        for (String role : roles) {
            RequestSystem.spawnOnGround(world, store, key, RequestSpawns.Kind.ADD, role, (int) Math.floor(at.x()),
                    (int) Math.floor(at.z()), 5, leash);
        }
    }

    // ---- Morts ----

    /** Un PNJ escorté est tombé : un de moins ; la demande échoue s'il n'en reste aucun. */
    static void memberDied(World world, Store<EntityStore> store, PlayerRef player, PeuplesPlayer data, PlayerRequest r) {
        RequestTemplate t = r.template();
        int left = Math.max(0, (r.count() < 0 ? (t == null ? 1 : t.members()) : r.count()) - 1);
        r.setCount(left);
        boolean caravan = t != null && t.type() == RequestType.CARAVAN;
        if (left <= 0) {
            Requests.fail(world, store, player.getReference(), player, data, r,
                    Requests.KEYS + (caravan ? "caravan.lost" : "harvest.lost"));
            return;
        }
        Message m = Message.translation(Requests.KEYS + (caravan ? "caravan.memberLost" : "harvest.memberLost")).param("count", left);
        player.sendMessage(m);
        NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Warning);
    }

    // ---- Fin ----

    /**
     * Fin d'une de ces demandes (remplie, échouée, abandonnée, échue) : les PNJ escortés reprennent leurs pieds et, comme
     * les assaillants, les gardes et les renforts, ne partent que hors de vue des joueurs ; le chef aussi.
     */
    static void end(Store<EntityStore> store, String key) {
        for (Ref<EntityStore> m : RequestSpawns.of(key, RequestSpawns.Kind.ESCORTED)) {
            store.tryRemoveComponent(m, Frozen.getComponentType());
        }
        for (RequestSpawns.Kind kind : new RequestSpawns.Kind[] {RequestSpawns.Kind.ESCORTED, RequestSpawns.Kind.AMBUSH,
                RequestSpawns.Kind.GUARD, RequestSpawns.Kind.ADD, RequestSpawns.Kind.BOSS}) {
            RequestSpawns.release(key, kind);
        }
        GUARDED.remove(key);
        ADDS.remove(key);
    }

    // ---- Suivi à l'écran ----

    /** Ligne de tâche de ces demandes, vue depuis `from` : le but du moment (groupe resté en arrière, lieu, village). */
    static Message task(World world, Store<EntityStore> store, PlayerRef player, PlayerRequest r, RequestTemplate t, Village village,
                        Vector3d from) {
        String key = t.taskKey();
        int[] target = r.site();
        int count = Math.min(r.progress(), r.needed());
        int needed = r.needed();
        Village dest = r.target() == null ? null : Villages.registry(world).byId(r.target());
        int[] group = r.position();
        boolean behind = t.type().escorted() && r.count() >= 0 && group != null && from != null
                && Math.hypot(group[0] + 0.5 - from.x(), group[2] + 0.5 - from.z()) > BEHIND;
        switch (t.type()) {
            case CARAVAN -> {
                target = dest == null ? new int[] {village.x(), village.y(), village.z()} : new int[] {dest.x(), dest.y(), dest.z()};
                count = Math.max(0, r.count() < 0 ? t.members() : r.count());
                needed = t.members();
            }
            case HARVEST -> {
                count = Math.max(0, r.count() < 0 ? t.members() : r.count());
                needed = t.members();
                if (r.stage() == 1) {
                    key = Requests.KEYS + "harvest.working";
                    count = Math.min(r.timer(), t.duration());
                    needed = t.duration();
                } else if (r.stage() >= 2) {
                    key = Requests.KEYS + "harvest.home";
                    target = new int[] {village.x(), village.y(), village.z()};
                }
            }
            default -> {
            }
        }
        if (behind) {
            key = Requests.KEYS + "group.behind";
            target = group;
        }
        Message m = Message.translation(key).param("count", count).param("needed", needed)
                .param("village", dest == null ? Message.raw(village.name()) : Message.raw(dest.name()));
        if (t.itemId() != null) {
            m = m.param("item", VillageBoard.itemName(t.itemId()));
        }
        if (t.targetBlock() != null) {
            m = m.param("block", VillageBoard.itemName(t.targetBlock()));
        }
        if (from != null) {
            double dx = target[0] + 0.5 - from.x();
            double dz = target[2] + 0.5 - from.z();
            m = m.param("distance", (int) Math.round(Math.sqrt(dx * dx + dz * dz)))
                    .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(dx, dz)));
        } else {
            m = m.param("distance", "?").param("direction", "?");
        }
        return m;
    }

    public static void clearAll() {
        GUARDED.clear();
        ADDS.clear();
    }
}
