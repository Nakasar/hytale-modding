package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.builtin.triggervolumes.TriggerVolumesPlugin;
import com.hypixel.hytale.builtin.triggervolumes.manager.TriggerVolumeManager;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Combat du golem de cristal, dans la Salle des Transmutations ronde de la Tour de l'Alchimiste (Kevin, 19 octobre
 * 2026).
 *
 * <p>La salle a quatre quadrants élémentaires ({@link TowerLayout#TRANS_QUADRANTS} : terre, air, glace, feu), chacun un
 * volume ({@code Trans_<élément>}, tools/alchemist_traps.py, Traps.transmutation) dont ce système pose les étiquettes :
 * <ul>
 *   <li>dès que le golem est engagé, trois quadrants sont actifs ({@code State = Active} : flammes intenses, blizzard,
 *   vents forts, pics de pierre) et le quatrième calme ({@code State = Calm} : effet léger) ;</li>
 *   <li>toutes les {@value #CYCLE_SECONDS} s, le répit passe à un quadrant voisin : {@value #WARN_SECONDS} s avant, le
 *   voisin se calme et l'ancien quadrant calme s'annonce ({@code Fx = Warn} : zones rouges, son), puis il redevient
 *   actif. Les joueurs ont le temps de changer de quadrant ;</li>
 *   <li>chaque quadrant qui devient actif fait sortir un esprit de son élément ({@link TowerLayout#TRANS_SPIRITS}, au
 *   plus {@value #SPIRIT_MAX} à la fois) ;</li>
 *   <li>{@code Fx} est rejoué toutes les {@value #PULSE_SECONDS} s pour les particules ;</li>
 *   <li>plus aucun joueur dans la salle pendant {@value #RESET_SECONDS} s : le golem regagne toute sa vie, les esprits
 *   disparaissent, les quadrants s'éteignent ;</li>
 *   <li>mort du golem : les quadrants s'éteignent, les esprits disparaissent et le sceau du pied de l'hélice se dissout
 *   ({@code Trans_Seal Golem = On}).</li>
 * </ul>
 */
public final class TransmutationSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Crystal_Golem";
    static final float CYCLE_SECONDS = 16f;
    /** = alchemist_traps.TRANS_WARN (durée des zones rouges). */
    static final float WARN_SECONDS = 5f;
    /** = alchemist_traps.TRANS_PULSE (durée des particules). */
    static final float PULSE_SECONDS = 3f;
    static final int SPIRIT_MAX = 5;
    static final float RESET_SECONDS = 8f;
    private static final float INTERVAL = 0.25f;
    private static final double ARENA_MARGIN = 1;
    /** Hauteur de la salle au-dessus du sol, pour savoir qui est dedans. */
    private static final double ROOM_HEIGHT = 16;

    private static final String ACTIVE = "Active";
    private static final String CALM = "Calm";
    private static final String OFF = "Off";

    /** État du combat par golem (le monde de l'instance n'en a qu'un). */
    private static final class Fight {
        boolean started;
        /** Quadrant calme ; `next` se calme WARN_SECONDS avant le changement (-1 sinon). */
        int calm = -1;
        int next = -1;
        long switchAt;
        long nextPulse;
        float absent;
        boolean sealed;
        final List<Ref<EntityStore>> spirits = new ArrayList<>();
    }

    private static final Map<Ref<EntityStore>, Fight> FIGHTS = new ConcurrentHashMap<>();

    /** Système partagé par les mondes, chacun sur son thread : un compte à rebours par monde. */
    private final Map<World, Float> wait = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float left = wait.getOrDefault(world, 0f) - dt;
        if (left > 0f) {
            wait.put(world, left);
            return;
        }
        wait.put(world, INTERVAL);
        if (!TowerFallSystem.isTower(store)) {
            return;
        }
        // Le store est en plein traitement : on regarde et on agit juste après.
        world.execute(() -> step(world, INTERVAL));
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Ref<EntityStore>> golems = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())) {
                    golems.add(chunk.getReferenceTo(i));
                }
            }
        });
        // Golem disparu du monde (chunk déchargé) : on retire ses esprits.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            removeSpirits(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> golem : golems) {
            update(world, store, golem, FIGHTS.computeIfAbsent(golem, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> golem, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        if (volumes == null) {
            return;
        }
        if (!alive(golem, store)) {
            if (!fight.sealed) {
                fight.sealed = true;
                stop(volumes, fight, store);
                setTag(volumes, TowerLayout.TRANS_SEAL, "Golem", "On");
            }
            return;
        }
        EntityStatMap stats = store.getComponent(golem, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        boolean engaged = fight.started || isEngaged(golem, store, health);
        boolean present = playerInRoom(world, store);
        // Remise à zéro : groupe mort ou sorti de la salle.
        if (engaged && !present) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                stop(volumes, fight, store);
                if (stats != null) {
                    stats.maximizeStatValue(DefaultEntityStatTypes.getHealth());
                }
                FIGHTS.put(golem, new Fight());
            }
            return;
        }
        fight.absent = 0f;
        if (!engaged) {
            return;
        }
        int count = TowerLayout.TRANS_ZONES.length;
        if (!fight.started) {
            // Éveil : un quadrant calme au hasard, les trois autres actifs, chacun avec son esprit.
            fight.started = true;
            fight.calm = ThreadLocalRandom.current().nextInt(count);
            for (int i = 0; i < count; i++) {
                setTag(volumes, TowerLayout.TRANS_ZONES[i], "State", i == fight.calm ? CALM : ACTIVE);
                if (i != fight.calm) {
                    spawnSpirit(store, fight, i);
                }
            }
            fight.switchAt = now + seconds(CYCLE_SECONDS);
            fight.nextPulse = now;
        }
        fight.spirits.removeIf(spirit -> !alive(spirit, store));
        keepSpiritsInRoom(store, fight);

        // Annonce : un voisin se calme, le quadrant calme s'annonce avant de redevenir actif.
        if (fight.next < 0 && now >= fight.switchAt - seconds(WARN_SECONDS)) {
            fight.next = (fight.calm + (ThreadLocalRandom.current().nextBoolean() ? 1 : count - 1)) % count;
            setTag(volumes, TowerLayout.TRANS_ZONES[fight.next], "State", CALM);
            pulse(volumes, fight.next, CALM);
            pulse(volumes, fight.calm, "Warn");
        }
        if (now >= fight.switchAt) {
            int woken = fight.calm;
            fight.calm = fight.next;
            fight.next = -1;
            fight.switchAt = now + seconds(CYCLE_SECONDS);
            setTag(volumes, TowerLayout.TRANS_ZONES[woken], "State", ACTIVE);
            pulse(volumes, woken, ACTIVE);
            spawnSpirit(store, fight, woken);
        }
        if (now >= fight.nextPulse) {
            fight.nextPulse = now + seconds(PULSE_SECONDS);
            for (int i = 0; i < count; i++) {
                // Le quadrant qui s'annonce garde ses zones rouges jusqu'au bout.
                if (fight.next >= 0 && i == fight.calm) {
                    continue;
                }
                pulse(volumes, i, i == fight.calm || i == fight.next ? CALM : ACTIVE);
            }
        }
    }

    /** Rejoue l'effet visuel d'un quadrant : Fx repasse par None pour que le volume voie une nouvelle étiquette. */
    private static void pulse(TriggerVolumeManager volumes, int zone, String fx) {
        setTag(volumes, TowerLayout.TRANS_ZONES[zone], "Fx", "None");
        setTag(volumes, TowerLayout.TRANS_ZONES[zone], "Fx", fx);
    }

    /** Quadrants éteints, esprits retirés. */
    private static void stop(TriggerVolumeManager volumes, Fight fight, Store<EntityStore> store) {
        for (String zone : TowerLayout.TRANS_ZONES) {
            setTag(volumes, zone, "State", OFF);
            setTag(volumes, zone, "Fx", "None");
        }
        removeSpirits(fight, store);
    }

    private static void spawnSpirit(Store<EntityStore> store, Fight fight, int zone) {
        if (fight.spirits.size() >= SPIRIT_MAX) {
            return;
        }
        Vector3d[] spots = TowerLayout.TRANS_SPIRIT_SPOTS[zone];
        Vector3d at = new Vector3d(spots[ThreadLocalRandom.current().nextInt(spots.length)]);
        String role = TowerLayout.TRANS_SPIRITS[zone];
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f());
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Golem de cristal : impossible de faire apparaître '%s'", role);
            return;
        }
        Ref<EntityStore> spirit = spawned.first();
        // Jamais sauvegardé : le combat repose tout au rechargement de l'instance.
        store.ensureAndGetComponent(spirit, EntityStore.REGISTRY.getNonSerializedComponentType());
        NPCEntity npc = store.getComponent(spirit, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(at);
        }
        fight.spirits.add(spirit);
    }

    /** Un esprit qui est passé sous le sol de la salle (ou sorti par le haut de l'hélice) revient à son quadrant. */
    private static void keepSpiritsInRoom(Store<EntityStore> store, Fight fight) {
        Vector3d center = TowerLayout.TRANS_CENTER;
        for (Ref<EntityStore> spirit : fight.spirits) {
            TransformComponent transform = store.getComponent(spirit, TransformComponent.getComponentType());
            if (transform == null || store.getComponent(spirit, Teleport.getComponentType()) != null) {
                continue;
            }
            Vector3d position = transform.getPosition();
            if (position.y() >= center.y() - 0.5 && horizontal(position, center) <= TowerLayout.TRANS_ARENA_RADIUS + 1) {
                continue;
            }
            NPCEntity npc = store.getComponent(spirit, NPCEntity.getComponentType());
            Vector3d leash = npc == null ? null : npc.getLeashPoint();
            if (leash != null) {
                store.putComponent(spirit, Teleport.getComponentType(), new Teleport(new Vector3d(leash), new Rotation3f()));
            }
        }
    }

    private static void removeSpirits(Fight fight, Store<EntityStore> store) {
        for (Ref<EntityStore> spirit : fight.spirits) {
            if (spirit.isValid()) {
                store.removeEntity(spirit, RemoveReason.REMOVE);
            }
        }
        fight.spirits.clear();
    }

    private static void setTag(TriggerVolumeManager volumes, String volume, String key, String value) {
        volumes.setTag(volume, key, value, null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
    }

    private static boolean playerInRoom(World world, Store<EntityStore> store) {
        Vector3d center = TowerLayout.TRANS_CENTER;
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            Vector3d position = transform.getPosition();
            double dy = position.y() - center.y();
            if (horizontal(position, center) <= TowerLayout.TRANS_ARENA_RADIUS + ARENA_MARGIN && dy > -2 && dy < ROOM_HEIGHT) {
                return true;
            }
        }
        return false;
    }

    private static double horizontal(Vector3d a, Vector3d b) {
        double dx = a.x() - b.x();
        double dz = a.z() - b.z();
        return Math.sqrt(dx * dx + dz * dz);
    }

    private static boolean isEngaged(Ref<EntityStore> ref, Store<EntityStore> store, EntityStatValue health) {
        StateSupport state = StateSupport.get(ref, store);
        String name = state == null ? null : state.getStateName();
        if (name != null && name.startsWith("Combat")) {
            return true;
        }
        return health != null && health.get() < health.getMax() - 0.5f;
    }

    private static boolean alive(Ref<EntityStore> ref, Store<EntityStore> store) {
        if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return false;
        }
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        return health == null || health.get() > 0f;
    }

    private static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    /** Oublie les combats en cours (arrêt du plugin). Les esprits partent avec le monde. */
    public static void clearAll() {
        FIGHTS.clear();
    }
}
