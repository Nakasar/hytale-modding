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
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.VillageBoard;
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
    /** Une chasse compte les morts des rôles du modèle tuées par le joueur jusqu'à cette distance du village. */
    public static final int HUNT_RADIUS = 220;

    private static final class State {
        float elapsed;
        /** Joueurs déjà vus cette session (suivi renvoyé à la connexion). */
        final Set<UUID> seen = new HashSet<>();
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
            dev.nakasar.hytale.peuples.workshop.Workshops.refresh(world, store, village);
        }
        Set<UUID> here = new HashSet<>();
        List<Vector3d> positions = new ArrayList<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> pr = p.getReference();
            Vector3d pos = pr == null || !pr.isValid() ? null : Requests.position(store, pr);
            if (pos != null) {
                positions.add(pos);
            }
        }
        RequestSpawns.stepLingering(store, positions);
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
            case DEFENSE -> stepDefense(store, village);
            case PLANT -> stepPlant(world, store, ref, player, data, r, t, at);
            case CARAVAN, HARVEST, DESTROY, BOSS -> Expeditions.step(world, store, ref, player, data, r, t, village, at, key);
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
     * Défense (étape 6) : la demande a attiré un raid sur le village (raid/Raids), qui la remplit ou la fait échouer au
     * bilan. Si plus aucun raid n'est attendu (annulé par une commande), elle en attire un nouveau.
     */
    private static void stepDefense(Store<EntityStore> store, Village village) {
        if (!Raids.pending(village)) {
            Raids.schedule(village, Raids.nextNight(store, village), "Request");
        }
    }

    /** Rayon du bosquet brûlé d'une plantation. */
    public static final int GROVE_RADIUS = 6;
    private static final String BURNT_SOIL = "Soil_Grass_Burnt";
    private static final String BURNT_STUMP = "Wood_Burnt_Trunk";
    /** Un tronc qui a poussé de la pousse compte aussi. */
    private static final String GROWN_TRUNK = "Wood_Oak_Trunk";

    /**
     * Plantation (étape 6) : à l'approche, le lieu devient un bosquet brûlé (sol calciné, souches) ; chaque pousse
     * ({@code ItemId}) plantée dans le bosquet compte, et l'avancement ne redescend pas si on en arrache une.
     */
    private static void stepPlant(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, PeuplesPlayer data,
                                  PlayerRequest r, RequestTemplate t, Vector3d at) {
        if (!near(at, r.site(), SITE_RANGE) || !knowSiteHeight(world, r)) {
            return;
        }
        int[] s = r.site();
        ChunkStore chunks = world.getChunkStore();
        Terrain terrain = new Terrain(world);
        if (!r.prepared()) {
            ThreadLocalRandom random = ThreadLocalRandom.current();
            for (int dx = -GROVE_RADIUS; dx <= GROVE_RADIUS; dx++) {
                for (int dz = -GROVE_RADIUS; dz <= GROVE_RADIUS; dz++) {
                    if (dx * dx + dz * dz > GROVE_RADIUS * GROVE_RADIUS) {
                        continue;
                    }
                    int x = s[0] + dx, z = s[2] + dz;
                    int y = terrain.surface(x, z);
                    if (y == Terrain.NONE || Math.abs(y - (s[1] - 1)) > 4) {
                        continue;
                    }
                    String top = Blocks.name(chunks, x, y, z);
                    if (top != null && top.startsWith("Soil_Grass")) {
                        Blocks.set(chunks, x, y, z, BURNT_SOIL, 0);
                    }
                    // Les herbes et fleurs brûlées disparaissent ; quelques souches calcinées restent debout.
                    String above = Blocks.name(chunks, x, y + 1, z);
                    if (above != null && above.startsWith("Plant_")) {
                        Blocks.set(chunks, x, y + 1, z, null, 0);
                    }
                    if (dx * dx + dz * dz >= 9 && random.nextInt(9) == 0 && Blocks.isEmpty(chunks, x, y + 1, z)) {
                        int h = 1 + random.nextInt(2);
                        for (int i = 1; i <= h; i++) {
                            Blocks.set(chunks, x, y + i, z, BURNT_STUMP, 0);
                        }
                    }
                }
            }
            r.setPrepared(true);
            player.sendMessage(Message.translation(Requests.KEYS + "plant.found").param("item", VillageBoard.itemName(t.itemId())));
        }
        int planted = 0;
        for (int dx = -GROVE_RADIUS - 1; dx <= GROVE_RADIUS + 1; dx++) {
            for (int dz = -GROVE_RADIUS - 1; dz <= GROVE_RADIUS + 1; dz++) {
                for (int y = s[1] - 4; y <= s[1] + 3; y++) {
                    String name = Blocks.name(chunks, s[0] + dx, y, s[2] + dz);
                    if (t.itemId().equals(name) || GROWN_TRUNK.equals(name)) {
                        planted++;
                        break;
                    }
                }
            }
        }
        if (planted > r.progress()) {
            Requests.advance(world, store, ref, player, data, r, planted - r.progress());
        }
    }

    /** Demandes dont le lieu a été vérifié sûr pendant cette session. */
    private static final java.util.Set<PlayerRequest> CHECKED =
            java.util.Collections.newSetFromMap(java.util.Collections.synchronizedMap(new java.util.WeakHashMap<>()));

    /** Rayon de recherche d'un lieu sûr autour du lieu tiré d'une demande (lac, rivière, falaise). */
    static final int SITE_SAFE_RADIUS = 24;

    /**
     * Fait apparaître `role` sur un point sûr ({@link Terrain#safeSpot}) à moins de `spread` blocs de (x, z), sinon
     * sur le lieu lui-même (déjà sûr, voir {@link #knowSiteHeight}) ; attaché à `leash` s'il est donné.
     */
    static Ref<EntityStore> spawnOnGround(World world, Store<EntityStore> store, String key, RequestSpawns.Kind kind, String role,
                                          int x, int z, int spread, Vector3d leash) {
        Terrain terrain = new Terrain(world);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int[] spot = terrain.safeSpot(x + random.nextInt(-spread, spread + 1), z + random.nextInt(-spread, spread + 1), 2);
        if (spot == null) {
            spot = terrain.safeSpot(x, z, spread);
        }
        if (spot == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : pas de point sûr pour '%s' autour de %d, %d", role, x, z);
            return null;
        }
        Ref<EntityStore> spawned = RequestSpawns.spawn(store, key, kind, role, new Vector3d(spot[0] + 0.5, spot[1], spot[2] + 0.5),
                (float) random.nextDouble(-Math.PI, Math.PI));
        if (spawned != null && leash != null) {
            NPCEntity npc = store.getComponent(spawned, NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(new Vector3d(leash));
            }
        }
        return spawned;
    }

    /**
     * Fixe la hauteur du lieu quand sa colonne est chargée, en le déplaçant au point sûr le plus proche (pas sous l'eau,
     * dans la lave, dans un bloc ou sur une pente) ; vrai si le lieu est connu. Le guetteur, le captif et le bosquet s'y
     * posent, et la bande ou les gardiens s'y replient.
     */
    static boolean knowSiteHeight(World world, PlayerRequest r) {
        int[] s = r.site();
        Terrain terrain = new Terrain(world);
        if (r.siteHeightKnown()) {
            // Un lieu fixé avant la recherche de point sûr (sauvegarde ancienne) est revu une fois par session.
            if (!CHECKED.add(r) || terrain.surface(s[0], s[2]) == Terrain.NONE || terrain.safeFeet(s[0], s[2]) != Terrain.NONE) {
                return true;
            }
        } else if (terrain.surface(s[0], s[2]) == Terrain.NONE) {
            return false;
        }
        CHECKED.add(r);
        int[] spot = terrain.safeSpot(s[0], s[2], SITE_SAFE_RADIUS);
        if (spot == null) {
            spot = terrain.safeSpot(s[0], s[2], SITE_SAFE_RADIUS * 2);
        }
        if (spot == null) {
            // Rien de sûr à 48 blocs (pleine mer) : le lieu reste sur le sol, comme avant.
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : aucun point sûr à %d blocs du lieu %d, %d de la demande %s",
                    SITE_SAFE_RADIUS * 2, s[0], s[2], r.templateId());
            r.setSite(s[0], terrain.surface(s[0], s[2]) + 1, s[2]);
            return true;
        }
        r.setSite(spot[0], spot[1], spot[2]);
        return true;
    }

    static boolean near(Vector3d at, int[] site, int range) {
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
            state.guards.remove(key);
        }
    }
}
