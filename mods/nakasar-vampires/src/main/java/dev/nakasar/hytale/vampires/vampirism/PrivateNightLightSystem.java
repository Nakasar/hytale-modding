package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.protocol.ComponentUpdateType;
import com.hypixel.hytale.protocol.DynamicLightUpdate;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.modules.entity.tracker.EntityTrackerSystems;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Vision nocturne du vampire, vue de lui seul. La nuit, une faible lumière l'entoure, mais elle n'est envoyée qu'à son
 * propre client : les autres joueurs ne voient rien, un vampire n'est pas reconnaissable à sa lumière.
 *
 * <p>Une lumière d'entité ({@link DynamicLight}) serait envoyée à tous ceux qui voient le joueur
 * ({@code EntitySystems.DynamicLightTracker}). Ce système, dans le même groupe, envoie la mise à jour de lumière au
 * seul spectateur qu'est le vampire lui-même, sans poser de composant. Quand le joueur porte une vraie lumière d'entité
 * (aura de lumière), elle passe avant et ce système se tait ; à sa fin, la lumière privée revient.
 */
public final class PrivateNightLightSystem extends EntityTickingSystem<EntityStore> {

    /** Faible et froide : elle aide à voir sans colorer la nuit. */
    static final ColorLight NIGHT_LIGHT = new ColorLight((byte) 6, (byte) 3, (byte) 3, (byte) 4);

    private static final Query<EntityStore> QUERY = Query.and(Vampire.getComponentType(), Player.getComponentType(),
            EntityTrackerSystems.EntityViewer.getComponentType(), EntityTrackerSystems.Visible.getComponentType());

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return EntityTrackerSystems.QUEUE_UPDATE_GROUP;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        Vampire vampire = chunk.getComponent(index, Vampire.getComponentType());
        EntityTrackerSystems.EntityViewer self = chunk.getComponent(index,
                EntityTrackerSystems.EntityViewer.getComponentType());
        EntityTrackerSystems.Visible visible = chunk.getComponent(index, EntityTrackerSystems.Visible.getComponentType());
        if (!visible.visibleTo.containsKey(ref)) {
            vampire.privateLightSent = false; // le client ne suit pas (encore) sa propre entité
            return;
        }
        if (chunk.getComponent(index, DynamicLight.getComponentType()) != null) {
            vampire.privateLightSent = false; // une vraie lumière d'entité (aura) est envoyée à tous, elle passe avant
            return;
        }
        boolean wanted = !SunExposure.isDay(store);
        if (wanted && (!vampire.privateLightSent || visible.newlyVisibleTo.containsKey(ref))) {
            self.queueUpdate(ref, new DynamicLightUpdate(new ColorLight(NIGHT_LIGHT)));
            vampire.privateLightSent = true;
        } else if (!wanted && vampire.privateLightSent) {
            self.queueRemove(ref, ComponentUpdateType.DynamicLight);
            vampire.privateLightSent = false;
        }
    }

    /** Éteint la lumière privée chez le joueur (guérison : le système ne le suit plus après). */
    static void clear(Ref<EntityStore> ref, Vampire vampire, ComponentAccessor<EntityStore> accessor) {
        if (vampire == null || !vampire.privateLightSent) {
            return;
        }
        vampire.privateLightSent = false;
        EntityTrackerSystems.EntityViewer self = accessor.getComponent(ref,
                EntityTrackerSystems.EntityViewer.getComponentType());
        if (self != null && self.visible.contains(ref) && accessor.getComponent(ref, DynamicLight.getComponentType()) == null) {
            self.queueRemove(ref, ComponentUpdateType.DynamicLight);
        }
    }
}
