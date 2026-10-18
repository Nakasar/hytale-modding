package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Fait vivre les auras de lumière ({@link LightAura}) : publie à chaque tick la position du porteur pour
 * {@link PurifyingFireSystem}, puis éteint l'aura à la fin de sa durée en rendant au porteur sa lumière d'origine.
 */
public final class LightAuraSystem extends EntityTickingSystem<EntityStore> {

    private final PurifyingFires fires;

    public LightAuraSystem(PurifyingFires fires) {
        this.fires = fires;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Query.and(LightAura.getComponentType(), TransformComponent.getComponentType());
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        LightAura aura = chunk.getComponent(index, LightAura.getComponentType());
        aura.remaining -= dt;
        if (aura.remaining <= 0) {
            fires.removeAura(ref);
            if (aura.lightByUs) {
                if (aura.previousLight != null) {
                    buffer.putComponent(ref, DynamicLight.getComponentType(), new DynamicLight(aura.previousLight));
                } else {
                    buffer.tryRemoveComponent(ref, DynamicLight.getComponentType());
                }
            }
            buffer.removeComponent(ref, LightAura.getComponentType());
            return;
        }
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        fires.putAura(ref, position.x, position.y, position.z);
    }

    /** Porteur déchargé ou supprimé en pleine aura : on lui rend sa lumière avant la sauvegarde. */
    public static final class Unload extends HolderSystem<EntityStore> {

        @Override
        public Query<EntityStore> getQuery() {
            return LightAura.getComponentType();
        }

        @Override
        public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
        }

        @Override
        public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {
            LightAura aura = holder.getComponent(LightAura.getComponentType());
            if (aura != null && aura.lightByUs) {
                if (aura.previousLight != null) {
                    holder.putComponent(DynamicLight.getComponentType(), new DynamicLight(aura.previousLight));
                } else {
                    holder.tryRemoveComponent(DynamicLight.getComponentType());
                }
            }
            holder.tryRemoveComponent(LightAura.getComponentType());
        }
    }
}
