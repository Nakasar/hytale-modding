package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Les villageois à métier (étape 5 ; GDD, Villageois et métiers) : chaque métier du plan ({@link VillageLayout.Job})
 * a son PNJ du mod (apparence vanilla qui dit le métier : chapeau de chantier du bâtisseur, feuilles du garde...) dès
 * que le village atteint son palier et que son bâtiment de travail est debout.
 *
 * <p>Routine : le jour il travaille à son poste (le rôle y joue son animation de travail), la nuit il rentre à son
 * logis ; le Java déplace son point d'attache, et s'il n'arrive pas à rejoindre sa cible il y est téléporté quand
 * aucun joueur ne regarde (GDD : « par téléportation discrète si l'IA n'y arrive pas »). Le bâtisseur part sur le
 * chantier en cours, avec des aides (un par bâtiment, {@value #MAX_HELPERS} au plus) qui repartent à la fin.
 *
 * <p>Non sauvegardés, posés quand un joueur approche ; tué, un villageois revient au matin suivant. Ils se
 * régénèrent hors combat (régénération vanilla des PNJ amicaux, {@link VillageNoRegenSystem}).
 */
public final class Villagers {

    /** Les villageois apparaissent quand un joueur passe à moins de cette distance du cœur. */
    public static final int RANGE = 72;
    /** Aides du bâtisseur sur un chantier. */
    public static final int MAX_HELPERS = 3;
    /** Un villageois à plus de cette distance de sa cible depuis {@value #STUCK_SECONDS} s est téléporté. */
    private static final int STUCK_DISTANCE = 18;
    private static final float STUCK_SECONDS = 40f;
    /** Pas de téléportation sous les yeux d'un joueur à moins de cette distance. */
    private static final int WATCHED = 20;
    private static final String HELPER = "chantier:";

    private record Key(String village, String slot) {
    }

    /** Un villageois posé : son village, son poste (id du métier, ou chantier:bâtiment), son dialogue. */
    public record Posted(String village, String slot, String dialogue) {
    }

    /** Ce qu'un poste veut : rôle, dialogue, cible du moment. */
    private record Want(String role, String dialogue, Vector3d target) {
    }

    private static final Map<Key, Ref<EntityStore>> BY_SLOT = new HashMap<>();
    private static final Map<Ref<EntityStore>, Posted> POSTED = Collections.synchronizedMap(new IdentityHashMap<>());
    private static final Map<Key, Long> DEATHS = new HashMap<>();
    /** Dialogue du dernier villageois mort à chaque poste (son nom et son métier, pour le tableau et les autres PNJ). */
    private static final Map<Key, String> DEAD_DIALOGUE = new HashMap<>();
    private static final Map<Ref<EntityStore>, Float> STUCK = new IdentityHashMap<>();
    /** Hauteur du sol des postes (x, z) déjà sondée. */
    private static final Map<Long, Integer> GROUND = new HashMap<>();
    /** Postes déplacés vers un point sûr voisin : (x, z) du poste -> (x, z) du point. */
    private static final Map<Long, int[]> SHIFTED = new HashMap<>();

    private Villagers() {
    }

    /**
     * Pas des villageois (thread du monde) : pose et retire les PNJ selon le palier, les bâtiments debout et le
     * chantier, puis déplace leur point d'attache selon l'heure.
     */
    public static synchronized void step(World world, Store<EntityStore> store, List<Vector3d> players, float dt) {
        boolean night = GameClock.isNight(store);
        long day = GameClock.day(store);
        for (Village village : Villages.registry(world).all()) {
            VillageLayout layout = Chantiers.layout(village);
            if (layout == null) {
                continue;
            }
            // Avant-postes de métier (annex/) : leurs villageois apparaissent quand un joueur approche de l'avant-poste.
            for (AnnexState annex : village.annexes()) {
                if (!annex.granted() && nearSpot(annex.x(), annex.z(), players, RANGE)) {
                    place(world, store, village, annexWanted(world, village, annex, night), ANNEX_PREFIX + annex.id() + "/", players, day, dt);
                }
            }
            if (!near(village, players, RANGE)) {
                continue;
            }
            place(world, store, village, wanted(world, village, layout, night), null, players, day, dt);
        }
    }

    /** Retire tout de suite les villageois des postes `group` (préfixe) du village : avant-poste détruit. */
    public static synchronized void dismiss(Store<EntityStore> store, String villageId, String group) {
        for (Key key : new ArrayList<>(BY_SLOT.keySet())) {
            if (key.village().equals(villageId) && key.slot().startsWith(group)) {
                despawn(store, key);
            }
        }
    }

    /** Slots des villageois d'avant-poste : {@code AP_<bâtiment>/<métier>}. */
    public static final String ANNEX_PREFIX = "AP_";

    /**
     * Pose, retire et guide les villageois voulus d'un groupe de postes : ceux du village (`group` null : tous les postes
     * hors avant-postes) ou ceux d'un avant-poste (`group` : préfixe de ses postes).
     */
    private static void place(World world, Store<EntityStore> store, Village village, Map<String, Want> wanted, String group,
                              List<Vector3d> players, long day, float dt) {
        {
            for (Map.Entry<Key, Ref<EntityStore>> e : new ArrayList<>(BY_SLOT.entrySet())) {
                String slot = e.getKey().slot();
                boolean mine = group == null ? !slot.startsWith(ANNEX_PREFIX) : slot.startsWith(group);
                if (e.getKey().village().equals(village.id()) && mine && !wanted.containsKey(slot)) {
                    despawn(store, e.getKey());
                }
            }
            for (Map.Entry<String, Want> e : wanted.entrySet()) {
                Key key = new Key(village.id(), e.getKey());
                Ref<EntityStore> ref = BY_SLOT.get(key);
                if (ref != null && !ref.isValid()) {
                    BY_SLOT.remove(key);
                    POSTED.remove(ref);
                    STUCK.remove(ref);
                    ref = null;
                }
                Want want = e.getValue();
                if (ref == null) {
                    Long death = DEATHS.get(key);
                    if (death != null && death >= day) {
                        continue;
                    }
                    spawn(store, village, key, want);
                    continue;
                }
                follow(store, ref, want.target(), players, dt);
            }
        }
    }

    /** Postes voulus dans le village : métiers ouverts et aides du chantier, avec leur cible du moment. */
    private static Map<String, Want> wanted(World world, Village village, VillageLayout layout, boolean night) {
        Map<String, Want> out = new LinkedHashMap<>();
        ChantierState chantier = village.chantier();
        List<VillageLayout.Building> works = new ArrayList<>();
        if (chantier != null) {
            for (String id : chantier.buildings()) {
                VillageLayout.Building b = layout.building(id);
                if (b != null && !b.small()) {
                    works.add(b);
                }
            }
        }
        VillageLayout.Job builder = null;
        for (VillageLayout.Job job : layout.jobs()) {
            if (job.tier() > village.tier() || (!job.building().isEmpty() && !village.isStanding(job.building()))) {
                continue;
            }
            if (job.builder()) {
                builder = job;
            }
            int[] spot = night ? job.homeSpot() : job.work();
            if (job.builder() && !night && !works.isEmpty()) {
                spot = front(works.get(0));
            }
            if (!night || village.isStanding(job.home()) || job.home().isEmpty()) {
                out.put(job.id(), new Want(job.role(), job.dialogue(), ground(world, village, spot)));
            } else {
                // Logis brûlé : il dort près du feu de la place.
                out.put(job.id(), new Want(job.role(), job.dialogue(), ground(world, village, job.work())));
            }
        }
        if (builder != null && !night) {
            for (int i = 1; i < works.size() && i <= MAX_HELPERS; i++) {
                VillageLayout.Building b = works.get(i);
                out.put(HELPER + b.id(), new Want(builder.role(), builder.dialogue(), ground(world, village, front(b))));
            }
        }
        return out;
    }

    /**
     * Postes voulus d'un avant-poste : pendant les travaux, ses deux premiers villageois s'affairent devant le chantier ;
     * debout, chaque villageois arrivé au niveau de l'avant-poste travaille à son poste le jour et rentre la nuit.
     */
    private static Map<String, Want> annexWanted(World world, Village village, AnnexState annex, boolean night) {
        Map<String, Want> out = new LinkedHashMap<>();
        dev.nakasar.hytale.peuples.workshop.Workshop w = dev.nakasar.hytale.peuples.workshop.Workshop.get(annex.id());
        if (w == null || !w.isAnnex() || annex.occupied() || annex.ruined()) {
            return out; // ouvrage pris par un rival (sa garnison le tient) ou rasé : personne du village
        }
        int level = village.workshop(w.getId()).level();
        VillageLayout.Job[] workers = w.annex().workers();
        for (int i = 0; i < workers.length; i++) {
            VillageLayout.Job job = workers[i];
            if (annex.working() ? i >= 2 || night : job.tier() > level) {
                continue;
            }
            int[] local = night && annex.built() ? job.homeSpot() : job.work();
            int[] at = dev.nakasar.hytale.peuples.annex.Annexes.toWorld(annex, local[0], local[1]);
            out.put(ANNEX_PREFIX + annex.id() + "/" + job.id(), new Want(job.role(), job.dialogue(), groundAt(world, at[0], at[1], annex.y())));
        }
        return out;
    }

    private static boolean nearSpot(int x, int z, List<Vector3d> players, int range) {
        for (Vector3d p : players) {
            double dx = p.x() - x;
            double dz = p.z() - z;
            if (dx * dx + dz * dz <= (double) range * range) {
                return true;
            }
        }
        return false;
    }

    /** Vrai si le villageois de l'avant-poste `workshopId`, métier `jobId`, est là (apparu, vivant). */
    public static synchronized boolean presentAt(Village village, String workshopId, String jobId) {
        return present(village, ANNEX_PREFIX + workshopId + "/" + jobId);
    }

    /** Poste devant un bâtiment (2 blocs hors de l'emprise, côté place), comme tools/generate_village_layouts.py. */
    static int[] front(VillageLayout.Building b) {
        int[] r = b.rect();
        int cx = Math.floorDiv(r[0] + r[1], 2);
        int cz = Math.floorDiv(r[2] + r[3], 2);
        if (Math.abs(cx) >= Math.abs(cz)) {
            return cx > 0 ? new int[] {r[0] - 2, cz} : new int[] {r[1] + 2, cz};
        }
        return cz > 0 ? new int[] {cx, r[2] - 2} : new int[] {cx, r[3] + 2};
    }

    /** Point au sol du poste (x, z) relatif au cœur. */
    private static Vector3d ground(World world, Village village, int[] spot) {
        return groundAt(world, village.x() + spot[0], village.z() + spot[1], village.y());
    }

    /** Point au sol de la colonne (x, z) du monde ; `fallbackY` si elle n'est pas chargée. */
    public static Vector3d groundAt(World world, int x, int z, int fallbackY) {
        long key = ((long) x << 32) ^ (z & 0xffffffffL);
        Integer y = GROUND.get(key);
        if (y == null) {
            Terrain terrain = new Terrain(world);
            int s = terrain.surface(x, z);
            if (s == Terrain.NONE) {
                return new Vector3d(x + 0.5, fallbackY, z + 0.5);
            }
            // Poste sous l'eau ou dans la lave : le point sûr le plus proche, à 3 blocs au plus (sinon le poste). Un
            // poste dans un bâtiment (plancher au-dessus du sol naturel) reste où il est.
            boolean drowned = terrain.hasFluid(x, s + 1, z) || terrain.hasFluid(x, s + 2, z);
            int[] safe = drowned ? terrain.safeSpot(x, z, 3) : null;
            if (safe != null) {
                SHIFTED.put(key, new int[] {safe[0], safe[2]});
                y = safe[1];
            } else {
                y = s + 1;
            }
            GROUND.put(key, y);
        }
        int[] shift = SHIFTED.get(key);
        return shift == null ? new Vector3d(x + 0.5, y, z + 0.5) : new Vector3d(shift[0] + 0.5, y, shift[1] + 0.5);
    }

    private static void spawn(Store<EntityStore> store, Village village, Key key, Want want) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, want.role(), null, want.target(),
                new Rotation3f(0f, 0f, 0f));
        if (spawned == null || spawned.first() == null) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : impossible de poser '%s' au village %s", want.role(), village.name());
            DEATHS.put(key, Long.MAX_VALUE - 1);
            return;
        }
        Ref<EntityStore> ref = spawned.first();
        store.ensureAndGetComponent(ref, EntityStore.REGISTRY.getNonSerializedComponentType());
        NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(new Vector3d(want.target()));
        }
        BY_SLOT.put(key, ref);
        POSTED.put(ref, new Posted(key.village(), key.slot(), want.dialogue()));
    }

    /** Déplace le point d'attache vers la cible ; téléporte un villageois coincé loin d'elle quand personne ne regarde. */
    private static void follow(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d target, List<Vector3d> players, float dt) {
        NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
        if (npc == null) {
            return;
        }
        Vector3d leash = npc.getLeashPoint();
        if (leash == null || leash.distanceSquared(target) > 0.25) {
            npc.setLeashPoint(new Vector3d(target));
        }
        Vector3d at = Requests.position(store, ref);
        if (at == null || at.distanceSquared(target) <= (double) STUCK_DISTANCE * STUCK_DISTANCE) {
            STUCK.remove(ref);
            return;
        }
        float stuck = STUCK.getOrDefault(ref, 0f) + dt;
        if (stuck < STUCK_SECONDS || watched(players, at) || watched(players, target)) {
            STUCK.put(ref, stuck);
            return;
        }
        STUCK.remove(ref);
        store.putComponent(ref, Teleport.getComponentType(), new Teleport(new Vector3d(target), new Rotation3f(0f, 0f, 0f)));
    }

    private static boolean watched(List<Vector3d> players, Vector3d at) {
        for (Vector3d p : players) {
            if (p.distanceSquared(at) <= (double) WATCHED * WATCHED) {
                return true;
            }
        }
        return false;
    }

    private static boolean near(Village village, List<Vector3d> players, int range) {
        for (Vector3d p : players) {
            if (village.horizontalDistanceSquared(p.x(), p.z()) <= (double) range * range) {
                return true;
            }
        }
        return false;
    }

    private static void despawn(Store<EntityStore> store, Key key) {
        Ref<EntityStore> ref = BY_SLOT.remove(key);
        if (ref != null) {
            POSTED.remove(ref);
            STUCK.remove(ref);
            if (ref.isValid()) {
                store.removeEntity(ref, RemoveReason.REMOVE);
            }
        }
    }

    /**
     * Inscrit un PNJ posé ailleurs (porteur d'un convoi d'avant-poste) comme villageois de `village` : pas de
     * régénération, attitude et dialogue du village. Il n'a pas de poste à tenir ({@link #place} ne le touche pas).
     */
    public static void enlist(Ref<EntityStore> ref, String village, String slot, String dialogue) {
        POSTED.put(ref, new Posted(village, slot, dialogue));
    }

    /** Oublie un PNJ inscrit par {@link #enlist}. */
    public static void discharge(Ref<EntityStore> ref) {
        POSTED.remove(ref);
    }

    /** Poste du villageois `ref`, ou null. */
    public static Posted posted(Ref<EntityStore> ref) {
        return ref == null ? null : POSTED.get(ref);
    }

    /** Le villageois `ref` est mort : il reviendra au matin (les aides du chantier, au prochain chantier). */
    public static synchronized void died(Store<EntityStore> store, Ref<EntityStore> ref) {
        Posted p = POSTED.remove(ref);
        if (p != null) {
            Key key = new Key(p.village(), p.slot());
            BY_SLOT.remove(key);
            STUCK.remove(ref);
            DEATHS.put(key, GameClock.day(store));
            DEAD_DIALOGUE.put(key, p.dialogue());
        }
    }

    /**
     * Dialogues des villageois du village tués aujourd'hui dont le métier est toujours ouvert : ils reviendront au matin.
     * Les aides du chantier ne reviennent qu'au prochain chantier : ils n'y sont pas.
     */
    public static synchronized List<String> absent(Store<EntityStore> store, Village village) {
        List<String> out = new ArrayList<>();
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return out;
        }
        long day = GameClock.day(store);
        for (VillageLayout.Job job : layout.jobs()) {
            if (job.tier() > village.tier() || (!job.building().isEmpty() && !village.isStanding(job.building()))) {
                continue;
            }
            Key key = new Key(village.id(), job.id());
            Long death = DEATHS.get(key);
            String dialogue = DEAD_DIALOGUE.get(key);
            Ref<EntityStore> ref = BY_SLOT.get(key);
            if (death != null && death >= day && death != Long.MAX_VALUE - 1 && dialogue != null && (ref == null || !ref.isValid())) {
                out.add(dialogue);
            }
        }
        return out;
    }

    /** Villageois présents et métiers ouverts du village : {présents, ouverts}. */
    public static synchronized int[] count(Village village) {
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return new int[] {0, 0};
        }
        int open = 0;
        int here = 0;
        for (VillageLayout.Job job : layout.jobs()) {
            if (job.tier() > village.tier() || (!job.building().isEmpty() && !village.isStanding(job.building()))) {
                continue;
            }
            open++;
            Ref<EntityStore> ref = BY_SLOT.get(new Key(village.id(), job.id()));
            if (ref != null && ref.isValid()) {
                here++;
            }
        }
        return new int[] {here, open};
    }

    /** Vrai si le villageois du métier `jobId` du village est là (apparu, vivant). */
    public static synchronized boolean present(Village village, String jobId) {
        Ref<EntityStore> ref = BY_SLOT.get(new Key(village.id(), jobId));
        return ref != null && ref.isValid();
    }

    /** Les métiers du village et leur état, pour {@code /village metiers} : id -> villageois présent ? */
    public static synchronized Map<String, Boolean> jobs(Village village) {
        Map<String, Boolean> out = new LinkedHashMap<>();
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return out;
        }
        Set<String> seen = new HashSet<>();
        for (Map.Entry<Key, Ref<EntityStore>> e : BY_SLOT.entrySet()) {
            if (e.getKey().village().equals(village.id()) && e.getValue().isValid()) {
                seen.add(e.getKey().slot());
            }
        }
        for (VillageLayout.Job job : layout.jobs()) {
            out.put(job.id(), seen.contains(job.id()));
        }
        for (String slot : seen) {
            if (slot.startsWith(HELPER)) {
                out.put(slot, true);
            }
        }
        return out;
    }

    /** Retire les villageois du village (village effacé). */
    public static synchronized void remove(Store<EntityStore> store, String villageId) {
        for (Key key : new ArrayList<>(BY_SLOT.keySet())) {
            if (key.village().equals(villageId)) {
                despawn(store, key);
            }
        }
        GROUND.clear();
        SHIFTED.clear();
    }

    /** Oublie les hauteurs sondées (le terrain a changé : chantier, incendie). */
    public static synchronized void forgetGround() {
        GROUND.clear();
        SHIFTED.clear();
    }

    public static synchronized void clearAll() {
        BY_SLOT.clear();
        POSTED.clear();
        DEATHS.clear();
        DEAD_DIALOGUE.clear();
        STUCK.clear();
        GROUND.clear();
        SHIFTED.clear();
    }
}
