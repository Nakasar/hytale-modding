package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.builtin.triggervolumes.TriggerVolumesPlugin;
import com.hypixel.hytale.builtin.triggervolumes.manager.TriggerVolumeManager;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Portes de la Tour de l'Alchimiste : les gardiens d'airain ({@value #ROLE}) de la cour les gardent. Quand
 * {@link TowerLayout#COURT_GUARDIANS} d'entre eux sont morts, le volume des portes ({@link TowerLayout#COURT_DOOR},
 * tools/alchemist_traps.py, Traps.court) reçoit {@code Guardians = On} et les portes tombent.
 *
 * <p>Les gardiens naissent de leurs blocs d'apparition quand la cour se charge : on compte les morts (gardiens vus avec
 * un {@link DeathComponent}), pas les vivants.
 */
public final class CourtGuardSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Brass_Guardian";
    private static final float INTERVAL = 0.25f;

    /** Gardiens morts, par monde (chaque instance de la tour a les siens) ; un monde ouvert n'est plus suivi. */
    private final Map<World, Set<Ref<EntityStore>>> dead = Collections.synchronizedMap(new WeakHashMap<>());
    private final Set<World> opened = Collections.synchronizedSet(Collections.newSetFromMap(new WeakHashMap<>()));
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
        if (opened.contains(world) || !TowerFallSystem.isTower(store)) {
            return;
        }
        // Le store est en plein traitement : on regarde juste après.
        world.execute(() -> step(world));
    }

    private void step(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Set<Ref<EntityStore>> fallen = dead.computeIfAbsent(world, w -> new HashSet<>());
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())
                        && chunk.getComponent(i, DeathComponent.getComponentType()) != null) {
                    fallen.add(chunk.getReferenceTo(i));
                }
            }
        });
        if (fallen.size() < TowerLayout.COURT_GUARDIANS) {
            return;
        }
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        if (volumes != null) {
            volumes.setTag(TowerLayout.COURT_DOOR, "Guardians", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
        }
        opened.add(world);
        dead.remove(world);
    }
}
