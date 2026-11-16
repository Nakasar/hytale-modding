package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les bêtes des enclos (GDD des bâtiments de métier, étape 3 : « L'élevage, peuple par peuple »). Chaque bâtiment de
 * métier qui est un enclos ({@link Workshop#isPen()}) a 3, 5 puis 7 bêtes selon son niveau : celles de base (lapins,
 * sangliers, poules du désert, mouflons, porcs sauvages), puis celles de sa spécialité au niveau II. Ce sont des rôles
 * vanilla {@code Tamed_*}, ou du mod sur un modèle vanilla quand le jeu n'en a pas d'apprivoisé.
 *
 * <p>Comme les villageois ({@link Villagers}) : posées seulement quand un joueur est à moins de {@value Villagers#RANGE}
 * blocs du cœur, non sauvegardées, sur un point sûr de l'intérieur de l'enclos ({@link Terrain#safeSpot}), attachées
 * à son centre. Elles se régénèrent hors combat (régénération vanilla, rôles amicaux) et ne laissent
 * aucun butin (Kevin : les produits passent par la boutique) : leur rôle est marqué « butin déjà lâché » dès leur
 * apparition. Une bête tuée ne revient qu'au matin suivant ({@value GameClock#MORNING} h) ; tuée par un joueur, elle
 * lui coûte {@value #KILL_REPUTATION} de réputation de village ({@link LivestockDeathSystem}).
 */
public final class Livestock {

    /** Réputation de village perdue par le joueur qui tue une bête d'enclos (GDD). */
    public static final int KILL_REPUTATION = -5;
    /** Bêtes posées par enclos et par pas (2 s) : pas de vague d'apparitions d'un coup. */
    private static final int SPAWNS_PER_STEP = 1;
    /** Essais de point sûr dans l'enclos avant d'attendre le pas suivant. */
    private static final int TRIES = 8;

    /** Un enclos : village et bâtiment de métier. */
    public record Key(String village, String workshop) {
    }

    private static final Map<Key, List<Ref<EntityStore>>> BY_PEN = new HashMap<>();
    private static final Map<Ref<EntityStore>, Key> OWNERS = Collections.synchronizedMap(new IdentityHashMap<>());
    /** Jour de jeu de chaque mort, par enclos : une bête morte manque jusqu'au matin suivant. */
    private static final Map<Key, List<Long>> DEATHS = new HashMap<>();

    private Livestock() {
    }

    /** Pas des enclos (thread du monde, VillageLifeSystem) : pose, change et retire les bêtes. */
    public static synchronized void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        long day = GameClock.day(store);
        for (Village village : Villages.registry(world).all()) {
            if (!near(village, players)) {
                continue;
            }
            for (Workshop w : Workshops.all(village)) {
                if (!w.isPen()) {
                    continue;
                }
                Key key = new Key(village.id(), w.getId());
                if (!Workshops.open(village, w)) {
                    despawn(store, key);
                    continue;
                }
                WorkshopState state = village.workshop(w.getId());
                List<String> roles = Arrays.asList(w.animals(state.level(), state.specialty()));
                List<Ref<EntityStore>> refs = alive(key);
                // Spécialité changée (ou rôle d'une ancienne version) : la bête part, une bonne viendra.
                for (Ref<EntityStore> r : new ArrayList<>(refs)) {
                    NPCEntity npc = store.getComponent(r, NPCEntity.getComponentType());
                    if (npc == null || !roles.contains(npc.getRoleName())) {
                        remove(store, r);
                        refs.remove(r);
                    }
                }
                List<Long> deaths = DEATHS.computeIfAbsent(key, k -> new ArrayList<>());
                deaths.removeIf(d -> d < day);
                int want = Math.max(0, w.livestockCount(state.level()) - deaths.size());
                while (refs.size() > want) {
                    Ref<EntityStore> last = refs.remove(refs.size() - 1);
                    remove(store, last);
                }
                for (int n = 0; n < SPAWNS_PER_STEP && refs.size() < want && !roles.isEmpty(); n++) {
                    Ref<EntityStore> spawned = spawn(world, store, village, w, key, nextRole(store, refs, roles));
                    if (spawned == null) {
                        break;
                    }
                    refs.add(spawned);
                }
            }
        }
    }

    /** Le rôle le moins présent dans l'enclos (les petits vanilla font partie du troupeau). */
    private static String nextRole(Store<EntityStore> store, List<Ref<EntityStore>> refs, List<String> roles) {
        Map<String, Integer> count = new HashMap<>();
        for (Ref<EntityStore> r : refs) {
            NPCEntity npc = store.getComponent(r, NPCEntity.getComponentType());
            if (npc != null) {
                count.merge(npc.getRoleName(), 1, Integer::sum);
            }
        }
        String best = roles.get(0);
        for (String role : roles) {
            if (count.getOrDefault(role, 0) < count.getOrDefault(best, 0)) {
                best = role;
            }
        }
        return best;
    }

    private static Ref<EntityStore> spawn(World world, Store<EntityStore> store, Village village, Workshop w, Key key, String role) {
        int[] pen = w.pen();
        int x0 = village.x() + pen[0];
        int x1 = village.x() + pen[1];
        int z0 = village.z() + pen[2];
        int z1 = village.z() + pen[3];
        Terrain terrain = new Terrain(world);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int[] spot = null;
        for (int i = 0; i < TRIES && spot == null; i++) {
            int[] s = terrain.safeSpot(random.nextInt(x0, x1 + 1), random.nextInt(z0, z1 + 1), 1);
            if (s != null && s[0] >= x0 && s[0] <= x1 && s[2] >= z0 && s[2] <= z1) {
                spot = s;
            }
        }
        if (spot == null) {
            return null;
        }
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null,
                new Vector3d(spot[0] + 0.5, spot[1], spot[2] + 0.5), new Rotation3f(0f, (float) random.nextDouble(-Math.PI, Math.PI), 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de poser la bête '%s' dans l'enclos %s (%s)",
                    role, w.getId(), village.name());
            return null;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null) {
            int cx = Math.floorDiv(x0 + x1, 2);
            int cz = Math.floorDiv(z0 + z1, 2);
            int cy = terrain.surface(cx, cz);
            npc.setLeashPoint(new Vector3d(cx + 0.5, cy == Terrain.NONE ? spot[1] : cy + 1, cz + 0.5));
            noLoot(npc);
        }
        BY_PEN.computeIfAbsent(key, k -> new ArrayList<>()).add(ref);
        OWNERS.put(ref, key);
        return ref;
    }

    /** Pas de butin : le système vanilla DropDeathItems saute un rôle dont le butin est déjà lâché. */
    static void noLoot(NPCEntity npc) {
        if (npc.getRole() != null && !npc.getRole().hasDroppedDeathItems()) {
            npc.getRole().setDeathItemsDropped();
        }
    }

    private static List<Ref<EntityStore>> alive(Key key) {
        List<Ref<EntityStore>> refs = BY_PEN.computeIfAbsent(key, k -> new ArrayList<>());
        refs.removeIf(r -> {
            if (!r.isValid()) {
                OWNERS.remove(r);
                return true;
            }
            return false;
        });
        return refs;
    }

    private static boolean near(Village village, List<Vector3d> players) {
        for (Vector3d p : players) {
            if (village.horizontalDistanceSquared(p.x(), p.z()) <= (double) Villagers.RANGE * Villagers.RANGE) {
                return true;
            }
        }
        return false;
    }

    private static void remove(Store<EntityStore> store, Ref<EntityStore> ref) {
        OWNERS.remove(ref);
        List<Ref<EntityStore>> refs = BY_PEN.values().stream().filter(l -> l.contains(ref)).findFirst().orElse(null);
        if (refs != null) {
            refs.remove(ref);
        }
        if (ref.isValid()) {
            store.removeEntity(ref, RemoveReason.REMOVE);
        }
    }

    private static void despawn(Store<EntityStore> store, Key key) {
        List<Ref<EntityStore>> refs = BY_PEN.remove(key);
        if (refs == null) {
            return;
        }
        for (Ref<EntityStore> r : refs) {
            OWNERS.remove(r);
            if (r.isValid()) {
                store.removeEntity(r, RemoveReason.REMOVE);
            }
        }
    }

    /** La spécialité du bâtiment a changé : ses bêtes partent, les nouvelles arrivent aux pas suivants. */
    public static synchronized void changed(Store<EntityStore> store, Village village, Workshop w) {
        despawn(store, new Key(village.id(), w.getId()));
    }

    /** Enclos de la bête `ref`, ou null si ce n'en est pas une. */
    public static Key owner(Ref<EntityStore> ref) {
        return ref == null ? null : OWNERS.get(ref);
    }

    /** La bête `ref` est morte : elle manque à son enclos jusqu'au matin suivant. Rend son enclos, ou null. */
    public static synchronized Key died(Store<EntityStore> store, Ref<EntityStore> ref) {
        Key key = OWNERS.remove(ref);
        if (key == null) {
            return null;
        }
        List<Ref<EntityStore>> refs = BY_PEN.get(key);
        if (refs != null) {
            refs.remove(ref);
        }
        DEATHS.computeIfAbsent(key, k -> new ArrayList<>()).add(GameClock.day(store));
        return key;
    }

    /** Bêtes présentes dans l'enclos du bâtiment (pour la page). */
    public static synchronized int count(Village village, Workshop w) {
        return alive(new Key(village.id(), w.getId())).size();
    }

    /** Retire les bêtes du village (village effacé). */
    public static synchronized void remove(Store<EntityStore> store, String villageId) {
        for (Key key : new ArrayList<>(BY_PEN.keySet())) {
            if (key.village().equals(villageId)) {
                despawn(store, key);
            }
        }
        DEATHS.keySet().removeIf(k -> k.village().equals(villageId));
    }

    public static synchronized void clearAll() {
        BY_PEN.clear();
        OWNERS.clear();
        DEATHS.clear();
    }
}
