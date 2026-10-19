package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.BlockMaterial;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Les esprits volants de la tour (élémentaires, tourbillons de pages du Codex) passaient à travers le sol (Kevin,
 * 19 octobre 2026). Dans la Tour de l'Alchimiste, toutes les {@value #INTERVAL} s, un volant dont le corps est dans un
 * bloc plein remonte au premier espace libre de deux blocs au-dessus (au plus {@value #SEARCH} blocs), sinon à son point
 * d'attache.
 */
public final class FlyerGuardSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.5f;
    private static final int SEARCH = 8;
    private static final String[] ROLE_PREFIXES = {"Nakasar_Elemental_", "Nakasar_Codex_Page_Vortex"};

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
        world.execute(() -> step(world));
    }

    private static void step(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Ref<EntityStore>> flyers = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && isFlyer(npc.getRoleName())) {
                    flyers.add(chunk.getReferenceTo(i));
                }
            }
        });
        ChunkStore chunks = world.getChunkStore();
        for (Ref<EntityStore> ref : flyers) {
            if (!ref.isValid() || store.getComponent(ref, Teleport.getComponentType()) != null) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            Vector3d position = transform.getPosition();
            int x = (int) Math.floor(position.x());
            int y = (int) Math.floor(position.y() + 0.3);
            int z = (int) Math.floor(position.z());
            if (!solid(chunks, x, y, z)) {
                continue;
            }
            Vector3d target = null;
            for (int up = 1; up <= SEARCH; up++) {
                if (!solid(chunks, x, y + up, z) && !solid(chunks, x, y + up + 1, z)) {
                    target = new Vector3d(position.x(), y + up + 0.1, position.z());
                    break;
                }
            }
            if (target == null) {
                NPCEntity npc = store.getComponent(ref, NPCEntity.getComponentType());
                Vector3d leash = npc == null ? null : npc.getLeashPoint();
                if (leash == null) {
                    continue;
                }
                target = new Vector3d(leash).add(0, 1, 0);
            }
            store.putComponent(ref, Teleport.getComponentType(), new Teleport(target, new Rotation3f()));
        }
    }

    static boolean isFlyer(String role) {
        if (role == null) {
            return false;
        }
        for (String prefix : ROLE_PREFIXES) {
            if (role.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private static boolean solid(ChunkStore chunks, int x, int y, int z) {
        Ref<ChunkStore> sectionRef = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (sectionRef == null || !sectionRef.isValid()) {
            return false;
        }
        BlockSection section = chunks.getStore().getComponent(sectionRef, BlockSection.getComponentType());
        if (section == null) {
            return false;
        }
        int id = section.get(x, y, z);
        if (id == BlockType.EMPTY_ID) {
            return false;
        }
        BlockType block = BlockType.getAssetMap().getAsset(id);
        return block != null && block.getMaterial() == BlockMaterial.Solid;
    }
}
