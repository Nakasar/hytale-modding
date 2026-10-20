package dev.nakasar.hytale.fractals.stage;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.instability.Instabilities;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Morts des ennemis des fractales (groupe d'inspection, après les réductions) : un coup qui emporte toute la vie
 * restante d'un PNJ du camp ({@link Foes}) est annoncé une fois, sur le thread du monde, aux instabilités (Dernier
 * rire, Vengeance) et au déroulé de la fractale (barre d'événement des vagues).
 */
public final class FoeDeathSystem extends DamageEventSystem {

    /** PNJ déjà annoncés (deux coups mortels dans le même tick). */
    private static final Set<Ref<EntityStore>> REPORTED = Collections.synchronizedSet(Collections.newSetFromMap(new WeakHashMap<>()));

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || damage.getAmount() <= 0f) {
            return;
        }
        World world = store.getExternalData().getWorld();
        if (FractalCatalog.fractalOf(world) == null) {
            return;
        }
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        if (health == null || transform == null || npc == null || health.get() > damage.getAmount()
                || !Foes.inGroup(victim, buffer) || !REPORTED.add(victim)) {
            return;
        }
        String role = npc.getRoleName();
        Vector3d at = new Vector3d(transform.getPosition());
        world.execute(() -> {
            Store<EntityStore> s = world.getEntityStore().getStore();
            Instabilities.onFoeDeath(world, s, role, at);
            FractalStage stage = Stages.of(world);
            if (stage != null) {
                stage.onFoeDeath(world, s, role, at);
            }
        });
    }
}
