package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * PNJ de l'Observatoire, posés quand un joueur est là et qu'ils manquent, jamais sauvegardés (l'instance les repose à
 * chaque chargement) :
 * <ul>
 *   <li>le golem d'essai ({@value #ROLE}) à {@link ObservatoryLayout#GOLEM} : il ne riposte pas, ses PV remontent au
 *       maximum toutes les deux secondes ; les dégâts reçus sont annoncés au joueur par {@link TrialHitSystem} ;</li>
 *   <li>l'Archiviste ({@value #ARCHIVIST}) à {@link ObservatoryLayout#ARCHIVIST}, derrière son comptoir :
 *       invulnérable, il ouvre sa boutique de troc quand on lui parle.</li>
 * </ul>
 */
public final class ObservatoryNpcSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Fractal_Trial_Golem";
    public static final String ARCHIVIST = "Nakasar_Fractal_Archivist";
    private static final float INTERVAL = 2f;
    /** Temps écoulé depuis le dernier passage, par monde. */
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        if (!FractalCatalog.isObservatory(world)) {
            return;
        }
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        elapsed[0] = 0f;
        world.execute(() -> step(world));
    }

    private static void step(World world) {
        if (world.getPlayerRefs().isEmpty()) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (find(store, ARCHIVIST) == null) {
            Ref<EntityStore> archivist = spawn(store, ARCHIVIST, ObservatoryLayout.ARCHIVIST);
            if (archivist != null) {
                store.ensureAndGetComponent(archivist, Invulnerable.getComponentType());
            }
        }
        Ref<EntityStore> golem = find(store);
        if (golem == null) {
            spawn(store, ROLE, ObservatoryLayout.GOLEM);
            return;
        }
        EntityStatMap stats = store.getComponent(golem, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null && health.get() < health.getMax()) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), health.getMax());
        }
    }

    /** Golem d'essai du monde, ou null. */
    public static Ref<EntityStore> find(Store<EntityStore> store) {
        return find(store, ROLE);
    }

    /** PNJ de rôle `role` du monde, ou null. */
    static Ref<EntityStore> find(Store<EntityStore> store, String role) {
        Ref<EntityStore>[] found = new Ref[1];
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size() && found[0] == null; i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && role.equals(npc.getRoleName())) {
                    found[0] = chunk.getReferenceTo(i);
                }
            }
        });
        return found[0];
    }

    private static Ref<EntityStore> spawn(Store<EntityStore> store, String role, double[] at) {
        Vector3d position = new Vector3d(at[0], at[1], at[2]);
        // Face à l'Astrolabe : le golem vers l'est (son pupitre), l'Archiviste vers l'ouest (son comptoir).
        Rotation3f rotation = new Rotation3f(0f, Telegraphs.yawToward(position, new Vector3d(0.5, at[1], at[2])), 0f);
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, position, rotation);
        if (spawned == null || spawned.first() == null) {
            FractalsPlugin.get().getLogger().atWarning().log("Observatoire : impossible de faire apparaître '%s'", role);
            return null;
        }
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        return spawned.first();
    }
}
