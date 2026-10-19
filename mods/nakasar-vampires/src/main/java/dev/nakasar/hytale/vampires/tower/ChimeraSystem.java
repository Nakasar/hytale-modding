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
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
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
 * Combat de la Chimère du laboratoire, second mini-boss de la Tour de l'Alchimiste.
 *
 * <p>Ses coups (morsure, poing de golem, fauchage de la queue) sont dans son rôle ; ce système mène le reste :
 * <ul>
 *   <li><b>Étagères de réactifs</b> : {@value #SHELF_ROLE}, PNJ fragiles et immobiles (gelés), posés à leur place
 *   ({@link TowerLayout#CHIMERA_SHELVES}) quand la Chimère est là et remis à la remise à zéro.</li>
 *   <li><b>Régénération</b> : toutes les {@value #DIVE_INTERVAL} s de combat, et une fois quand elle passe sous la moitié
 *   de sa vie, elle plonge dans la cuve centrale : gelée et invulnérable ({@link Invulnerable}, barre de boss en mode
 *   invulnérable), elle regagne {@value #REGEN_PER_SECOND} de sa vie par seconde pendant {@value #REGEN_BASE} s plus
 *   {@value #REGEN_PER_SHELF} s par étagère encore debout. Chaque étagère debout envoie un homoncule porteur
 *   ({@value #FEEDER_ROLE}) toutes les {@value #FEEDER_INTERVAL} s ; arrivé à la cuve, il y verse ses réactifs
 *   (+{@value #FEEDER_HEAL} de sa vie). Casser une étagère raccourcit donc la régénération en cours et les suivantes ;
 *   tuer les porteurs la prive de leurs réactifs. Elle ressort ensuite sur la case libre la plus proche d'un joueur.</li>
 *   <li><b>Acide</b> : pendant le combat, la cuve crache de l'acide ({@code Chimera_Acid Cast = On}, zones annoncées
 *   au sol) toutes les {@value #ACID_INTERVAL} s, {@value #ACID_INTERVAL_REGEN} s pendant la régénération.</li>
 *   <li><b>Remise à zéro</b> : plus aucun joueur dans le laboratoire pendant {@value #RESET_SECONDS} s alors qu'elle
 *   est engagée : elle sort de la cuve, regagne toute sa vie, les porteurs disparaissent et les étagères reviennent.</li>
 *   <li><b>Mort</b> : le sceau de la porte nord se dissout ({@code Chimera_Seal Chimera = On}) ; porteurs et étagères
 *   disparaissent.</li>
 * </ul>
 */
public final class ChimeraSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Lab_Chimera";
    static final String SHELF_ROLE = "Nakasar_Chimera_Reagent_Shelf";
    static final String FEEDER_ROLE = "Nakasar_Chimera_Feeder";
    static final float DIVE_INTERVAL = 60f;
    static final float REGEN_BASE = 6f;
    static final float REGEN_PER_SHELF = 4f;
    static final float REGEN_PER_SECOND = 0.015f;
    static final float FEEDER_HEAL = 0.04f;
    static final float FEEDER_INTERVAL = 4f;
    static final float ACID_INTERVAL = 10f;
    static final float ACID_INTERVAL_REGEN = 5f;
    static final float RESET_SECONDS = 8f;
    private static final float INTERVAL = 0.25f;
    /** Un porteur verse ses réactifs quand il touche la margelle de la cuve. */
    private static final double FEED_REACH = 3.2;
    private static final double ARENA_MARGIN = 2;
    private static final double ARENA_HEIGHT = 20;

    private static final String SOUND_SPLASH = "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts";
    private static final String PARTICLE_SPLASH = "Dungeon_Goblin_Toxic_Water";
    private static final String PARTICLE_FEED = "Impact_Poison";

    /** État du combat par Chimère (le monde de l'instance n'en a qu'une). */
    private static final class Fight {
        /** Étagère de chaque place de {@link TowerLayout#CHIMERA_SHELVES} (null : détruite) ; null tant que pas posées. */
        Ref<EntityStore>[] shelves;
        final List<Ref<EntityStore>> feeders = new ArrayList<>();
        long nextDive;
        boolean halfDone;
        boolean regenerating;
        long regenStart;
        long[] nextFeeder;
        long nextAcid;
        float absent;
        boolean sealed;
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
        List<Ref<EntityStore>> chimeras = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())) {
                    chimeras.add(chunk.getReferenceTo(i));
                }
            }
        });
        // Chimère disparue du monde (chunk déchargé) : on retire ses porteurs et ses étagères.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            clearHelpers(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> chimera : chimeras) {
            update(world, store, chimera, FIGHTS.computeIfAbsent(chimera, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        ArenaGate gate = ArenaGate.of(world, TowerLayout.CHIMERA_GATE, RESET_SECONDS, volumes);
        if (!alive(chimera, store)) {
            clearHelpers(fight, store);
            gate.finish(volumes);
            if (!fight.sealed && volumes != null) {
                fight.sealed = true;
                volumes.setTag(TowerLayout.CHIMERA_SEAL, "Chimera", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
            }
            return;
        }
        if (fight.shelves == null) {
            placeShelves(store, fight);
        }

        EntityStatMap stats = store.getComponent(chimera, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        boolean engaged = fight.regenerating || isEngaged(chimera, store, health);

        boolean present = playerInArena(world, store);
        gate.update(volumes, present, dt);
        // Remise à zéro : groupe mort ou sorti du laboratoire.
        if (engaged && !present) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                reset(world, store, chimera, fight, stats);
            }
            return;
        }
        fight.absent = 0f;
        if (!engaged) {
            return;
        }

        if (fight.regenerating) {
            regenerate(world, store, chimera, fight, stats, health, now, dt);
        } else {
            if (fight.nextDive == 0) {
                fight.nextDive = now + seconds(DIVE_INTERVAL);
            }
            boolean half = health != null && health.get() < health.getMax() * 0.5f;
            if (now >= fight.nextDive || (half && !fight.halfDone)) {
                fight.halfDone |= half;
                dive(store, chimera, fight, now);
            }
        }

        // Acide de la cuve.
        if (volumes != null) {
            if (fight.nextAcid == 0) {
                fight.nextAcid = now + seconds(ACID_INTERVAL * 0.5f);
            }
            if (now >= fight.nextAcid) {
                volumes.setTag(TowerLayout.CHIMERA_ACID, "Cast", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
                fight.nextAcid = now + seconds(fight.regenerating ? ACID_INTERVAL_REGEN : ACID_INTERVAL);
            }
        }
    }

    /** Plongeon dans la cuve : gelée, invulnérable, au centre. */
    private static void dive(Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight, long now) {
        fight.regenerating = true;
        fight.regenStart = now;
        fight.nextFeeder = new long[TowerLayout.CHIMERA_SHELVES.length];
        for (int i = 0; i < fight.nextFeeder.length; i++) {
            fight.nextFeeder[i] = now + seconds(1f + 0.5f * i);
        }
        store.ensureAndGetComponent(chimera, Frozen.getComponentType());
        store.ensureAndGetComponent(chimera, Invulnerable.getComponentType());
        Vector3d vat = new Vector3d(TowerLayout.CHIMERA_VAT);
        store.putComponent(chimera, Teleport.getComponentType(), new Teleport(vat, new Rotation3f()));
        splash(store, vat);
    }

    private static void regenerate(World world, Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight,
                                   EntityStatMap stats, EntityStatValue health, long now, float dt) {
        if (stats != null && health != null) {
            heal(stats, health, health.getMax() * REGEN_PER_SECOND * dt);
        }
        // Porteurs : chaque étagère debout en envoie un à intervalles ; ceux qui touchent la cuve la nourrissent.
        Vector3d vat = TowerLayout.CHIMERA_VAT;
        for (int i = 0; i < fight.shelves.length; i++) {
            if (fight.shelves[i] != null && !alive(fight.shelves[i], store)) {
                fight.shelves[i] = null;
            }
            if (fight.shelves[i] != null && now >= fight.nextFeeder[i]) {
                fight.nextFeeder[i] = now + seconds(FEEDER_INTERVAL);
                spawnFeeder(store, fight, i);
            }
        }
        double reach = TowerLayout.CHIMERA_VAT_RADIUS + FEED_REACH;
        fight.feeders.removeIf(feeder -> {
            if (!alive(feeder, store)) {
                return true;
            }
            TransformComponent transform = store.getComponent(feeder, TransformComponent.getComponentType());
            NPCEntity npc = store.getComponent(feeder, NPCEntity.getComponentType());
            if (transform == null) {
                return false;
            }
            Vector3d position = transform.getPosition();
            if (horizontal(position, vat) <= reach) {
                if (stats != null && health != null) {
                    heal(stats, health, health.getMax() * FEEDER_HEAL);
                }
                ParticleUtil.spawnParticleEffect(PARTICLE_FEED, new Vector3d(position).add(0, 0.8, 0), 0f, 0f, 0f, 1.5f, 1f, store);
                sound(SOUND_SPLASH, position, store);
                store.removeEntity(feeder, RemoveReason.REMOVE);
                return true;
            }
            if (npc != null) {
                // Le rôle du porteur va vers son point d'attache : la margelle, du côté de son étagère.
                npc.setLeashPoint(rim(position));
            }
            return false;
        });
        long end = fight.regenStart + seconds(REGEN_BASE + REGEN_PER_SHELF * livingShelves(fight));
        if (now >= end) {
            emerge(world, store, chimera, fight);
            fight.nextDive = now + seconds(DIVE_INTERVAL);
        }
    }

    /** Fin de la régénération : les porteurs restants repartent en fumée, elle ressort près d'un joueur. */
    private static void emerge(World world, Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight) {
        fight.regenerating = false;
        removeFeeders(fight, store);
        store.tryRemoveComponent(chimera, Frozen.getComponentType());
        store.tryRemoveComponent(chimera, Invulnerable.getComponentType());
        Vector3d exit = nearestExit(world, store);
        store.putComponent(chimera, Teleport.getComponentType(), new Teleport(exit, new Rotation3f()));
        splash(store, TowerLayout.CHIMERA_VAT);
        splash(store, exit);
    }

    private static void reset(World world, Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight, EntityStatMap stats) {
        if (fight.regenerating) {
            emerge(world, store, chimera, fight);
        }
        removeFeeders(fight, store);
        if (stats != null) {
            stats.maximizeStatValue(DefaultEntityStatTypes.getHealth());
        }
        Fight fresh = new Fight();
        fresh.sealed = fight.sealed;
        fresh.shelves = fight.shelves;
        placeShelves(store, fresh);
        FIGHTS.put(chimera, fresh);
    }

    /** Pose les étagères manquantes (toutes au premier passage). */
    @SuppressWarnings("unchecked")
    private static void placeShelves(Store<EntityStore> store, Fight fight) {
        if (fight.shelves == null) {
            fight.shelves = new Ref[TowerLayout.CHIMERA_SHELVES.length];
        }
        for (int i = 0; i < fight.shelves.length; i++) {
            if (fight.shelves[i] != null && alive(fight.shelves[i], store)) {
                continue;
            }
            Vector3d at = new Vector3d(TowerLayout.CHIMERA_SHELVES[i]);
            Ref<EntityStore> shelf = spawn(store, SHELF_ROLE, at, facing(at, TowerLayout.CHIMERA_VAT));
            if (shelf != null) {
                // Immobile : l'IA gelée ne la fait ni bouger ni tourner.
                store.ensureAndGetComponent(shelf, Frozen.getComponentType());
            }
            fight.shelves[i] = shelf;
        }
    }

    private static void spawnFeeder(Store<EntityStore> store, Fight fight, int shelf) {
        Vector3d at = new Vector3d(TowerLayout.CHIMERA_SHELVES[shelf]);
        Vector3d toward = new Vector3d(TowerLayout.CHIMERA_VAT).sub(at);
        toward.y = 0;
        if (toward.lengthSquared() > 1e-6) {
            at.add(toward.normalize().mul(1.2));
        }
        Ref<EntityStore> feeder = spawn(store, FEEDER_ROLE, at, facing(at, TowerLayout.CHIMERA_VAT));
        if (feeder == null) {
            return;
        }
        NPCEntity npc = store.getComponent(feeder, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(rim(at));
        }
        fight.feeders.add(feeder);
    }

    private static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at, Rotation3f rotation) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, rotation);
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Chimère : impossible de faire apparaître '%s'", role);
            return null;
        }
        // Jamais sauvegardé : le combat repose tout au rechargement de l'instance.
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        return spawned.first();
    }

    private static int livingShelves(Fight fight) {
        int count = 0;
        for (Ref<EntityStore> shelf : fight.shelves) {
            if (shelf != null) {
                count++;
            }
        }
        return count;
    }

    private static void heal(EntityStatMap stats, EntityStatValue health, float amount) {
        stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.min(health.getMax(), health.get() + amount));
    }

    /** Point de la margelle de la cuve du côté de `from`. */
    private static Vector3d rim(Vector3d from) {
        Vector3d vat = TowerLayout.CHIMERA_VAT;
        Vector3d out = new Vector3d(from).sub(vat);
        out.y = 0;
        if (out.lengthSquared() < 1e-6) {
            out.set(1, 0, 0);
        }
        out.normalize().mul(TowerLayout.CHIMERA_VAT_RADIUS + 2.5).add(vat);
        return out;
    }

    private static Vector3d nearestExit(World world, Store<EntityStore> store) {
        Vector3d[] exits = TowerLayout.CHIMERA_EXITS;
        Vector3d best = exits[ThreadLocalRandom.current().nextInt(exits.length)];
        double bestDistance = Double.MAX_VALUE;
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null || !inArena(transform.getPosition())) {
                continue;
            }
            for (Vector3d exit : exits) {
                double d = horizontal(exit, transform.getPosition());
                if (d < bestDistance) {
                    bestDistance = d;
                    best = exit;
                }
            }
        }
        return new Vector3d(best);
    }

    private static Rotation3f facing(Vector3d from, Vector3d to) {
        // Même convention que SummonMinionsInteraction.facing (tourné vers `to`).
        return new Rotation3f(0f, (float) Math.atan2(to.x() - from.x(), to.z() - from.z()), 0f);
    }

    private static void splash(Store<EntityStore> store, Vector3d at) {
        ParticleUtil.spawnParticleEffect(PARTICLE_SPLASH, new Vector3d(at).add(0, 0.3, 0), 0f, 0f, 0f, 2f, 2f, store);
        sound(SOUND_SPLASH, at, store);
    }

    private static void removeFeeders(Fight fight, Store<EntityStore> store) {
        for (Ref<EntityStore> feeder : fight.feeders) {
            if (feeder.isValid()) {
                store.removeEntity(feeder, RemoveReason.REMOVE);
            }
        }
        fight.feeders.clear();
    }

    private static void clearHelpers(Fight fight, Store<EntityStore> store) {
        removeFeeders(fight, store);
        if (fight.shelves != null) {
            for (int i = 0; i < fight.shelves.length; i++) {
                Ref<EntityStore> shelf = fight.shelves[i];
                if (shelf != null && shelf.isValid()) {
                    store.removeEntity(shelf, RemoveReason.REMOVE);
                }
                fight.shelves[i] = null;
            }
        }
    }

    private static boolean playerInArena(World world, Store<EntityStore> store) {
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform != null && inArena(transform.getPosition())) {
                return true;
            }
        }
        return false;
    }

    private static boolean inArena(Vector3d position) {
        Vector3d vat = TowerLayout.CHIMERA_VAT;
        double radius = TowerLayout.CHIMERA_ARENA_RADIUS + ARENA_MARGIN;
        double dy = position.y() - vat.y();
        return horizontal(position, vat) <= radius && dy > -2 && dy < ARENA_HEIGHT;
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

    private static void sound(String id, Vector3d position, Store<EntityStore> store) {
        int index = SoundEvent.getAssetMap().getIndexOrDefault(id, -1);
        if (index >= 0) {
            SoundUtil.playSoundEvent3d(index, SoundCategory.SFX, position.x(), position.y(), position.z(), store);
        }
    }

    private static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    /** Oublie les combats en cours (arrêt du plugin). Porteurs et étagères partent avec le monde. */
    public static void clearAll() {
        FIGHTS.clear();
    }
}
