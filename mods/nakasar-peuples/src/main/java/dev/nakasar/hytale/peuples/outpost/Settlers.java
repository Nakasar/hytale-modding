package dev.nakasar.hytale.peuples.outpost;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageNames;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.zone.SiteRules;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Le colon : fonder un village sans être Champion (demande de Kevin, 2026-11-15).
 * <ul>
 *   <li>un village au palier max ({@link Tiers#MAX}) fait venir un colon au plus une fois tous les
 *   {@value #COOLDOWN_DAYS} jours de jeu ; il attend près du cœur ;</li>
 *   <li>lui parler : il propose d'aider à fonder un nouveau village ; accepter, et il suit le joueur
 *   ({@code Nakasar_Peuples_<Peuple>_Settler_Follow}, ramené près de lui s'il est distancé) ;</li>
 *   <li>lui parler ailleurs : il examine l'endroit avec les règles de la génération naturelle ({@link SiteRules} :
 *   écarts, zone du peuple, sol, eau, relief). S'il convient, il propose de fonder ici ; sinon il dit pourquoi ;</li>
 *   <li>fonder : le village est bâti tout de suite à cet endroit ({@code VillageBuilder}) ; un joueur pris dans les blocs
 *   posés est déplacé au point libre le plus proche. Si la fondation échoue, le colon rentre à son village.</li>
 * </ul>
 * Les colons ne sont pas sauvegardés avec le monde : l'état vit dans le village ({@code SettlerDay}, {@code SettlerActive},
 * {@code SettlerOwner}) et le PNJ réapparaît au besoin. Tout se passe sur le thread du monde.
 */
public final class Settlers {

    public static final String KEYS = "nakasar_peuples.settler.";
    public static final String DIALOGUE = "Colon";
    public static final int COOLDOWN_DAYS = 7;
    /** Le colon qui attend n'apparaît qu'à l'approche d'un joueur, et s'en va quand plus personne n'est près. */
    public static final int RANGE = 48;
    private static final int DEPART_RANGE = 72;
    /** Au-delà, le colon qui suit est ramené près de son joueur (monture, téléportation, course). */
    public static final int CATCH_UP = 32;
    /** Poste du colon, relatif au cœur (à l'est, hors du tableau, du dépôt et du crieur). */
    private static final int SPOT_X = 4;
    private static final int SPOT_Z = -4;

    private record Spawned(String villageId, boolean following) {
    }

    private static final Map<Ref<EntityStore>, Spawned> REFS = new IdentityHashMap<>();
    private static final Map<String, Ref<EntityStore>> BY_VILLAGE = new HashMap<>();
    /** Dernier examen de site par joueur (lu par la condition SettlerSite pendant le dialogue). */
    private static final Map<UUID, SiteRules.Check> CHECKS = new HashMap<>();
    /** Village du colon à qui parle le joueur. */
    private static final Map<UUID, String> TALKING = new HashMap<>();

    private Settlers() {
    }

    public static String role(People people, boolean following) {
        return "Nakasar_Peuples_" + people.id() + "_Settler" + (following ? "_Follow" : "");
    }

    /** Village du colon `ref`, ou null si ce n'est pas un colon. */
    public static synchronized String villageOf(Ref<EntityStore> ref) {
        Spawned s = ref == null ? null : REFS.get(ref);
        return s == null ? null : s.villageId();
    }

    public static synchronized void clearAll() {
        REFS.clear();
        BY_VILLAGE.clear();
        CHECKS.clear();
        TALKING.clear();
    }

    // ---- Vie des colons (VillageLifeSystem, toutes les 2 s) ----

    public static synchronized void step(World world, Store<EntityStore> store) {
        long day = GameClock.day(store);
        for (Village village : new ArrayList<>(Villages.registry(world).all())) {
            if (!village.settlerActive() && village.tier() >= Tiers.MAX
                    && dev.nakasar.hytale.peuples.world.TradeAccess.missingForSettler(world, village, day) == 0
                    && (village.settlerDay() == Long.MIN_VALUE || day - village.settlerDay() >= COOLDOWN_DAYS)) {
                village.startSettler(day);
                PeuplesPlugin.get().getLogger().atInfo().log("Peuples : un colon arrive au village %s", village.name());
            }
            Ref<EntityStore> ref = BY_VILLAGE.get(village.id());
            if (ref != null && !ref.isValid()) {
                forget(ref);
                ref = null;
                if (village.settlerActive() && village.settlerOwner() != null) {
                    // Tué ou perdu en route : il rentre au village, où il attendra de nouveau.
                    PlayerRef owner = online(world, village.settlerOwner());
                    village.setSettlerOwner(null);
                    if (owner != null) {
                        owner.sendMessage(Message.translation(KEYS + "lost").param("village", village.name()));
                    }
                }
            }
            if (!village.settlerActive()) {
                despawn(store, ref);
                continue;
            }
            if (village.settlerOwner() == null) {
                waitAtVillage(world, store, village, ref);
            } else {
                follow(world, store, village, ref);
            }
        }
    }

    private static void waitAtVillage(World world, Store<EntityStore> store, Village village, Ref<EntityStore> ref) {
        Spawned s = ref == null ? null : REFS.get(ref);
        if (s != null && s.following()) {
            despawn(store, ref);
            ref = null;
        }
        double nearest = nearestPlayer(world, store, village.x(), village.z());
        if (ref == null && nearest <= RANGE) {
            Terrain terrain = new Terrain(world);
            int x = village.x() + SPOT_X;
            int z = village.z() + SPOT_Z;
            int[] safe = terrain.safeSpot(x, z, 6);
            if (safe != null) {
                spawn(store, village, false, new Vector3d(safe[0] + 0.5, safe[1], safe[2] + 0.5));
            }
        } else if (ref != null && nearest > DEPART_RANGE) {
            despawn(store, ref);
        }
    }

    private static void follow(World world, Store<EntityStore> store, Village village, Ref<EntityStore> ref) {
        Spawned s = ref == null ? null : REFS.get(ref);
        if (s != null && !s.following()) {
            despawn(store, ref);
            ref = null;
        }
        PlayerRef owner = online(world, village.settlerOwner());
        Ref<EntityStore> ownerRef = owner == null ? null : owner.getReference();
        Vector3d at = ownerRef == null || !ownerRef.isValid() ? null : Requests.position(store, ownerRef);
        if (at == null) {
            despawn(store, ref); // le joueur est parti : le colon reviendra avec lui
            return;
        }
        Vector3d pos = ref == null ? null : Requests.position(store, ref);
        if (ref != null && pos != null && pos.distanceSquared(at) <= (double) CATCH_UP * CATCH_UP) {
            return;
        }
        int[] safe = new Terrain(world).safeSpot((int) Math.floor(at.x()) + 2, (int) Math.floor(at.z()) + 2, 5);
        if (safe == null) {
            return;
        }
        Vector3d spot = new Vector3d(safe[0] + 0.5, safe[1], safe[2] + 0.5);
        if (ref == null) {
            spawn(store, village, true, spot);
        } else {
            store.putComponent(ref, Teleport.getComponentType(), new Teleport(spot, new Rotation3f(0f, 0f, 0f)));
        }
    }

    private static Ref<EntityStore> spawn(Store<EntityStore> store, Village village, boolean following, Vector3d at) {
        String role = role(village.people(), following);
        var spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, 0f, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de faire apparaître le colon '%s'", role);
            return null;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        if (!following) {
            NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
            if (npc != null) {
                npc.setLeashPoint(new Vector3d(at));
            }
        }
        REFS.put(ref, new Spawned(village.id(), following));
        BY_VILLAGE.put(village.id(), ref);
        return ref;
    }

    private static void despawn(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref == null) {
            return;
        }
        forget(ref);
        if (ref.isValid()) {
            store.removeEntity(ref, RemoveReason.REMOVE);
        }
    }

    private static void forget(Ref<EntityStore> ref) {
        Spawned s = REFS.remove(ref);
        if (s != null && BY_VILLAGE.get(s.villageId()) == ref) {
            BY_VILLAGE.remove(s.villageId());
        }
    }

    private static double nearestPlayer(World world, Store<EntityStore> store, double x, double z) {
        double best = Double.MAX_VALUE;
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> r = p.getReference();
            Vector3d at = r == null || !r.isValid() ? null : Requests.position(store, r);
            if (at != null) {
                best = Math.min(best, Math.hypot(at.x() - x, at.z() - z));
            }
        }
        return best;
    }

    private static PlayerRef online(World world, String uuid) {
        if (uuid == null) {
            return null;
        }
        for (PlayerRef p : world.getPlayerRefs()) {
            if (uuid.equals(p.getUuid().toString())) {
                return p;
            }
        }
        return null;
    }

    // ---- Dialogue ----

    /** Le joueur parle au colon `npc` : examen du site s'il le suit, puis dialogue {@value #DIALOGUE}. */
    public static synchronized void talk(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Ref<EntityStore> npc) {
        String villageId = villageOf(npc);
        Village village = villageId == null ? null : Villages.registry(world).byId(villageId);
        Dialogue dialogue = Dialogue.get(DIALOGUE);
        if (village == null || dialogue == null) {
            return;
        }
        String me = player.getUuid().toString();
        if (village.settlerOwner() != null && !village.settlerOwner().equals(me)) {
            player.sendMessage(Message.translation(KEYS + "busy"));
            return;
        }
        TALKING.put(player.getUuid(), villageId);
        CHECKS.remove(player.getUuid());
        List<Message> said = new ArrayList<>();
        if (me.equals(village.settlerOwner())) {
            SiteRules.Check check = examine(world, store, ref, village.people());
            CHECKS.put(player.getUuid(), check);
            if (!check.ok()) {
                // La raison détaillée s'affiche sous la réplique du colon, dans la fenêtre de dialogue.
                said.add(Message.translation(KEYS + "why").param("reason", check.message()));
            }
        }
        Dialogues.openPage(world, store, ref, player, dialogue, npc, null, said);
    }

    private static SiteRules.Check examine(World world, Store<EntityStore> store, Ref<EntityStore> ref, People people) {
        Vector3d at = Requests.position(store, ref);
        if (at == null) {
            return new SiteRules.Check(SiteRules.Reason.UNLOADED, Message.translation(SiteRules.KEYS + "unloaded"));
        }
        return SiteRules.check(world, people, (int) Math.floor(at.x()), (int) Math.floor(at.z()));
    }

    /** Raison du dernier examen du joueur, ou null s'il n'y en a pas (le colon ne le suit pas). */
    static synchronized SiteRules.Reason lastReason(UUID player) {
        SiteRules.Check c = CHECKS.get(player);
        return c == null ? null : c.reason();
    }

    private static Village talkingTo(World world, PlayerRef player) {
        String id = TALKING.get(player.getUuid());
        return id == null ? null : Villages.registry(world).byId(id);
    }

    /** « Je t'aide » : le colon suit le joueur. */
    static synchronized boolean accept(World world, Store<EntityStore> store, PlayerRef player) {
        Village village = talkingTo(world, player);
        if (village == null || !village.settlerActive()) {
            return false;
        }
        String me = player.getUuid().toString();
        for (Village other : Villages.registry(world).all()) {
            if (other != village && me.equals(other.settlerOwner())) {
                DialogueSpeech.say(player, Message.translation(KEYS + "already").param("village", other.name()));
                return false;
            }
        }
        // Le PNJ qui attend est remplacé par celui qui suit au prochain pas (step), hors de la fenêtre de dialogue.
        village.setSettlerOwner(me);
        Message m = Message.translation(KEYS + "follows").param("village", village.name());
        player.sendMessage(m);
        NotificationUtil.sendNotification(player.getPacketHandler(), m, NotificationStyle.Success);
        return true;
    }

    /** « Fondons le village ici » : nouvel examen, puis fondation au matin. */
    static synchronized boolean found(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player) {
        Village village = talkingTo(world, player);
        if (village == null || !player.getUuid().toString().equals(village.settlerOwner())) {
            return false;
        }
        Vector3d at = Requests.position(store, ref);
        SiteRules.Check check = examine(world, store, ref, village.people());
        if (!check.ok() || at == null) {
            DialogueSpeech.say(player, Message.translation(KEYS + "why").param("reason", check.message()));
            return false;
        }
        int x = (int) Math.floor(at.x());
        int z = (int) Math.floor(at.z());
        VillageLayout layout = VillageLayout.get(village.people().layout());
        if (layout == null) {
            return false;
        }
        // Fondation immédiate (Kevin) : le PNJ s'en va au prochain pas (step), le village est bâti dès les chunks chargés.
        String homeId = village.id();
        People people = village.people();
        village.endSettler();
        CHECKS.remove(player.getUuid());
        DialogueSpeech.say(player, Message.translation(KEYS + "founding").param("people", Message.translation(people.nameKey())));
        String name = VillageNames.pick(world, people);
        VillageBuilder.generate(world, layout, name, x, z, false, result -> {
            PlayerRef owner = online(world, player.getUuid().toString());
            if (result.village() == null) {
                returnHome(world, homeId);
                if (owner != null) {
                    Message back = Message.translation(KEYS + "failed").param("reason",
                            result.error() == null ? Message.raw("") : result.error());
                    owner.sendMessage(back);
                    NotificationUtil.sendNotification(owner.getPacketHandler(), back, NotificationStyle.Warning);
                }
                return;
            }
            Village founded = result.village();
            unstick(world, layout, founded);
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples : colon de %s : village %s fondé en %d %d par %s",
                    homeId, founded.name(), founded.x(), founded.z(), player.getUsername());
            if (owner != null) {
                Message m = Message.translation(KEYS + "founded").param("name", founded.name())
                        .param("people", Message.translation(people.nameKey()));
                owner.sendMessage(m);
                NotificationUtil.sendNotification(owner.getPacketHandler(), m, NotificationStyle.Success);
            }
        });
        return true;
    }

    /** Rayon de recherche d'une place libre pour un joueur pris dans les blocs posés. */
    private static final int UNSTICK_RADIUS = 16;

    /**
     * Les joueurs que les bâtiments posés ont enfermés (pieds ou tête dans un bloc solide) sont déplacés au point sûr le
     * plus proche, à une hauteur proche de la leur (pas sur un toit), sinon au point sûr le plus proche.
     */
    static void unstick(World world, VillageLayout layout, Village village) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Terrain terrain = new Terrain(world);
        double reach = layout.radius() + 8;
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> r = p.getReference();
            Vector3d at = r == null || !r.isValid() ? null : Requests.position(store, r);
            if (at == null || village.horizontalDistanceSquared(at.x(), at.z()) > reach * reach) {
                continue;
            }
            int bx = (int) Math.floor(at.x());
            int by = (int) Math.floor(at.y());
            int bz = (int) Math.floor(at.z());
            if (terrain.bodyFree(bx, by, bz)) {
                continue;
            }
            int[] spot = nearFeet(terrain, bx, by, bz);
            if (spot == null) {
                spot = terrain.safeSpot(bx, bz, UNSTICK_RADIUS);
            }
            if (spot != null) {
                store.putComponent(r, Teleport.getComponentType(),
                        new Teleport(new Vector3d(spot[0] + 0.5, spot[1], spot[2] + 0.5), new Rotation3f(0f, 0f, 0f)));
                p.sendMessage(Message.translation(KEYS + "unstuck"));
            }
        }
    }

    /** Point sûr le plus proche dont les pieds sont à 4 blocs au plus de `y`, ou null. */
    private static int[] nearFeet(Terrain terrain, int x, int y, int z) {
        for (int r = 1; r <= UNSTICK_RADIUS; r++) {
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    if (Math.max(Math.abs(dx), Math.abs(dz)) != r) {
                        continue;
                    }
                    int feet = terrain.safeFeet(x + dx, z + dz);
                    if (feet != Terrain.NONE && Math.abs(feet - y) <= 4) {
                        return new int[] {x + dx, feet, z + dz};
                    }
                }
            }
        }
        return null;
    }

    /** « Rentre au village » : le colon retourne attendre près du cœur. */
    static synchronized boolean sendHome(World world, Store<EntityStore> store, PlayerRef player) {
        Village village = talkingTo(world, player);
        if (village == null || !player.getUuid().toString().equals(village.settlerOwner())) {
            return false;
        }
        village.setSettlerOwner(null); // le PNJ qui suit s'en va au prochain pas (step)
        CHECKS.remove(player.getUuid());
        DialogueSpeech.say(player, Message.translation(KEYS + "home").param("village", village.name()));
        return true;
    }

    /** Fondation d'un colon échouée : il rentre attendre à son village. */
    static synchronized void returnHome(World world, String villageId) {
        Village village = Villages.registry(world).byId(villageId);
        if (village != null) {
            village.startSettler(village.settlerDay() == Long.MIN_VALUE ? 0 : village.settlerDay());
        }
    }

    /** Pour la commande d'essai : un colon tout de suite au village `village` (palier max ou non). */
    public static synchronized void summon(World world, Village village, long day) {
        despawn(world.getEntityStore().getStore(), BY_VILLAGE.get(village.id()));
        village.startSettler(day);
    }
}
