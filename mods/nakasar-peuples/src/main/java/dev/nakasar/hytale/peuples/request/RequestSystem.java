package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Le pas des demandes, une fois par seconde et par monde (sur le thread du monde, juste après le tick) :
 * <ul>
 *   <li>tirage du matin au tableau de chaque village ;</li>
 *   <li>pour chaque joueur et chacune de ses demandes : fin à son terme, dépôt lu quand il est près du coffre, bande de
 *       la chasse et guetteur de la livraison posés quand il approche du lieu, captif de l'escorte et ses gardiens,
 *       arrivée du captif au village, attaque de nuit de la défense ;</li>
 *   <li>suivi à l'écran mis à jour (seulement ce qui change) et renvoyé à la connexion ;</li>
 *   <li>crieur de chaque village posé près du tableau quand un joueur approche ({@link Criers}).</li>
 * </ul>
 */
public final class RequestSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 1f;
    /** Le lieu d'une demande s'anime quand le joueur passe à moins de cette distance (blocs, à plat). */
    public static final int SITE_RANGE = 72;
    /** L'attaque d'une défense part de cette distance du cœur. */
    public static final int DEFENSE_SPAWN_DISTANCE = 30;
    /** Une chasse compte les morts des rôles du modèle tuées par le joueur jusqu'à cette distance du village. */
    public static final int HUNT_RADIUS = 220;

    private static final class State {
        float elapsed;
        /** Joueurs déjà vus cette session (suivi renvoyé à la connexion). */
        final Set<UUID> seen = new HashSet<>();
        /** Demandes dont l'attaque de nuit est partie (clé RequestSpawns). */
        final Set<String> waves = new HashSet<>();
        /** Escortes dont les gardiens sont apparus cette session. */
        final Set<String> guards = new HashSet<>();
    }

    private static final Map<World, State> STATES = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        State state = STATES.computeIfAbsent(world, w -> new State());
        state.elapsed += dt;
        if (state.elapsed < INTERVAL) {
            return;
        }
        state.elapsed = 0f;
        if (Villages.registry(world).all().isEmpty()) {
            return;
        }
        world.execute(() -> step(world, state));
    }

    private static void step(World world, State state) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Village> villages = Villages.registry(world).all();
        for (Village village : villages) {
            Requests.refresh(store, village);
        }
        Set<UUID> here = new HashSet<>();
        boolean night = GameClock.isNight(store);
        long now = GameClock.seconds(store);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            here.add(player.getUuid());
            boolean firstSeen = state.seen.add(player.getUuid());
            if (firstSeen) {
                RequestHud.forget(player.getUuid());
            }
            Vector3d at = Requests.position(store, ref);
            if (at == null) {
                continue;
            }
            Criers.ensureNear(world, store, at);
            PeuplesPlayer data = PeuplesPlayer.get(store, ref);
            if (data == null || data.requests().isEmpty()) {
                continue;
            }
            for (PlayerRequest r : new ArrayList<>(data.requests())) {
                if (data.request(r.id()) == null) {
                    continue;
                }
                stepRequest(world, store, ref, player, data, r, at, night, now, state);
                if (data.request(r.id()) != null) {
                    Requests.showHud(world, store, ref, player, r, firstSeen);
                }
            }
        }
        state.seen.retainAll(here);
    }

    private static void stepRequest(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                    PlayerRequest r, Vector3d at, boolean night, long now, State state) {
        RequestTemplate t = r.template();
        Village village = Villages.registry(world).byId(r.villageId());
        String key = RequestSpawns.key(player.getUuid(), r.id());
        if (t == null || village == null) {
            Requests.end(world, store, ref, player, data, r);
            player.sendMessage(Message.translation(Requests.KEYS + "vanished"));
            return;
        }
        if (now >= r.expires()) {
            state.waves.remove(key);
            state.guards.remove(key);
            Requests.fail(world, store, ref, player, data, r, Requests.KEYS + "expired");
            return;
        }
        switch (t.type()) {
            case GATHER, CRAFT -> {
                if (Requests.nearDeposit(store, ref, village)) {
                    Requests.pullDeposit(world, store, ref, player, village, r);
                }
            }
            case HUNT -> stepHunt(world, store, r, t, at, key);
            case DELIVERY -> {
                if (near(at, r.site(), SITE_RANGE) && knowSiteHeight(world, r)
                        && RequestSpawns.first(key, RequestSpawns.Kind.LOOKOUT) == null) {
                    int[] s = r.site();
                    RequestSpawns.spawn(store, key, RequestSpawns.Kind.LOOKOUT, village.people().lookoutRole(),
                            new Vector3d(s[0] + 0.5, s[1], s[2] + 0.5), yawToward(s, village));
                }
            }
            case ESCORT -> stepEscort(world, store, ref, player, data, r, t, village, at, key, state);
            case DEFENSE -> stepDefense(world, store, ref, player, data, r, t, village, at, key, night, state);
        }
    }

    /** Chasse : la bande (ce qui manque encore) apparaît à son repaire quand le joueur approche. */
    private static void stepHunt(World world, Store<EntityStore> store, PlayerRequest r, RequestTemplate t, Vector3d at, String key) {
        if (!near(at, r.site(), SITE_RANGE) || !knowSiteHeight(world, r)) {
            return;
        }
        int alive = RequestSpawns.of(key, RequestSpawns.Kind.FOE).size();
        int missing = r.needed() - r.progress() - alive;
        if (alive > 0 || missing <= 0) {
            return;
        }
        String[] spawns = t.spawns();
        int[] s = r.site();
        for (int i = 0; i < missing; i++) {
            String role = spawns[(r.progress() + i) % spawns.length];
            spawnOnGround(world, store, key, RequestSpawns.Kind.FOE, role, s[0], s[2], 4, null);
        }
    }

    /**
     * Escorte : le captif et ses gardiens apparaissent quand le joueur approche ; le captif suit le joueur le plus proche
     * (son rôle) et la demande est remplie quand il arrive près du cœur du village.
     */
    private static void stepEscort(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                   PlayerRequest r, RequestTemplate t, Village village, Vector3d at, String key, State state) {
        Ref<EntityStore> captive = RequestSpawns.first(key, RequestSpawns.Kind.CAPTIVE);
        if (captive == null) {
            if (!near(at, r.site(), SITE_RANGE) || !knowSiteHeight(world, r)) {
                return;
            }
            int[] s = r.site();
            RequestSpawns.spawn(store, key, RequestSpawns.Kind.CAPTIVE, village.people().captiveRole(),
                    new Vector3d(s[0] + 0.5, s[1], s[2] + 0.5), yawToward(s, village));
            if (state.guards.add(key)) {
                for (String role : t.spawns()) {
                    spawnOnGround(world, store, key, RequestSpawns.Kind.GUARD, role, s[0], s[2], 5, null);
                }
            }
            return;
        }
        Vector3d c = Requests.position(store, captive);
        if (c != null && village.horizontalDistanceSquared(c.x(), c.z()) <= (double) Requests.ESCORT_HOME * Requests.ESCORT_HOME) {
            state.guards.remove(key);
            Requests.advance(world, store, ref, player, data, r, 1);
        }
    }

    /**
     * Défense : la nuit venue, si le joueur est au village, l'attaque part à {@value #DEFENSE_SPAWN_DISTANCE} blocs du
     * cœur, avec le cœur pour point d'attache (les Trorks marchent sur le village). Chaque mort compte ; au matin, une
     * attaque encore debout fait échouer la demande et les assaillants se retirent.
     */
    private static void stepDefense(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                    PlayerRequest r, RequestTemplate t, Village village, Vector3d at, String key, boolean night, State state) {
        if (!night) {
            if (state.waves.remove(key)) {
                Requests.fail(world, store, ref, player, data, r, Requests.KEYS + "defense.lost");
            }
            return;
        }
        boolean inVillage = village.horizontalDistanceSquared(at.x(), at.z()) <= (double) Villages.RADIUS * Villages.RADIUS;
        int alive = RequestSpawns.of(key, RequestSpawns.Kind.FOE).size();
        int missing = r.needed() - r.progress() - alive;
        if (!inVillage || alive > 0 || missing <= 0) {
            return;
        }
        boolean first = state.waves.add(key);
        double angle = ThreadLocalRandom.current().nextDouble(0, Math.PI * 2);
        int cx = village.x() + (int) Math.round(Math.cos(angle) * DEFENSE_SPAWN_DISTANCE);
        int cz = village.z() + (int) Math.round(Math.sin(angle) * DEFENSE_SPAWN_DISTANCE);
        Vector3d heart = new Vector3d(village.x() + 0.5, village.y(), village.z() + 0.5);
        String[] spawns = t.spawns();
        for (int i = 0; i < missing; i++) {
            spawnOnGround(world, store, key, RequestSpawns.Kind.FOE, spawns[(r.progress() + i) % spawns.length], cx, cz, 4, heart);
        }
        if (first) {
            Message warn = Message.translation(Requests.KEYS + "defense.attack").param("village", village.name())
                    .param("direction", Message.translation(Villages.MESSAGES + "dir." + Requests.direction(cx - village.x(), cz - village.z())));
            player.sendMessage(warn);
            com.hypixel.hytale.server.core.util.NotificationUtil.sendNotification(player.getPacketHandler(), warn,
                    com.hypixel.hytale.protocol.packets.interface_.NotificationStyle.Danger);
        }
    }

    /** Fait apparaître `role` sur le sol, à moins de `spread` blocs de (x, z) ; attaché à `leash` s'il est donné. */
    private static void spawnOnGround(World world, Store<EntityStore> store, String key, RequestSpawns.Kind kind, String role,
                                      int x, int z, int spread, Vector3d leash) {
        Terrain terrain = new Terrain(world);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int px = x + random.nextInt(-spread, spread + 1);
        int pz = z + random.nextInt(-spread, spread + 1);
        int y = terrain.surface(px, pz);
        if (y == Terrain.NONE) {
            px = x;
            pz = z;
            y = terrain.surface(px, pz);
        }
        if (y == Terrain.NONE) {
            return;
        }
        Ref<EntityStore> spawned = RequestSpawns.spawn(store, key, kind, role, new Vector3d(px + 0.5, y + 1, pz + 0.5),
                (float) random.nextDouble(-Math.PI, Math.PI));
        if (spawned != null && leash != null) {
            NPCEntity npc = store.getComponent(spawned, NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(new Vector3d(leash));
            }
        }
    }

    /** Calcule la hauteur du lieu si sa colonne est chargée ; vrai si elle est connue. */
    private static boolean knowSiteHeight(World world, PlayerRequest r) {
        if (r.siteHeightKnown()) {
            return true;
        }
        int[] s = r.site();
        int y = new Terrain(world).surface(s[0], s[2]);
        if (y == Terrain.NONE) {
            return false;
        }
        r.setSite(s[0], y + 1, s[2]);
        return true;
    }

    private static boolean near(Vector3d at, int[] site, int range) {
        double dx = site[0] + 0.5 - at.x();
        double dz = site[2] + 0.5 - at.z();
        return dx * dx + dz * dz <= (double) range * range;
    }

    /** Lacet (radians) pour regarder de `from` vers le cœur du village. */
    private static float yawToward(int[] from, Village village) {
        double dx = village.x() - from[0];
        double dz = village.z() - from[2];
        return (float) Math.atan2(-dx, -dz);
    }

    /** Oublie l'état d'une demande (fin par une autre voie : mort du captif, livraison). */
    static void forget(World world, String key) {
        State state = STATES.get(world);
        if (state != null) {
            state.waves.remove(key);
            state.guards.remove(key);
        }
    }
}
