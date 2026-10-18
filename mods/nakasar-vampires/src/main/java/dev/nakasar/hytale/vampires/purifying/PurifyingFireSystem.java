package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.DelayedEntitySystem;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.entity.knockback.KnockbackComponent;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;
import it.unimi.dsi.fastutil.ints.IntList;
import org.joml.Vector3d;

/**
 * Feu purificateur : les morts-vivants (groupe de PNJ {@value #UNDEAD_GROUP}) ne s'approchent pas à moins de
 * {@value #RADIUS} blocs d'une torche ou d'une lanterne de feu blanc (blocs {@value #TORCH} et {@value #LANTERN},
 * posés autour et dans le camp des chasseurs de vampires).
 *
 * <p>Quatre fois par seconde, un mort-vivant à portée d'un de ces blocs est repoussé (recul horizontal, à l'opposé
 * du feu le plus proche) et oublie les cibles qui se tiennent elles-mêmes près du feu : il ne revient pas aussitôt
 * les chercher. Les rôles du jeu n'ont pas de capteur « fuir un bloc », d'où ce système plutôt que du JSON.
 */
public final class PurifyingFireSystem extends DelayedEntitySystem<EntityStore> {

    public static final String UNDEAD_GROUP = "Nakasar_Undead";
    public static final String TORCH = "Nakasar_Purifying_Torch";
    public static final String LANTERN = "Nakasar_Purifying_Lantern";
    /** Distance horizontale (blocs) en deçà de laquelle un mort-vivant est repoussé. */
    public static final int RADIUS = 7;
    /** Écart de hauteur pris en compte entre le PNJ et le feu (palissade, poteaux). */
    private static final int HEIGHT = 5;
    private static final double PUSH_SPEED = 7.0;
    private static final double PUSH_LIFT = 2.5;

    private static final Query<EntityStore> QUERY =
            Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());

    public PurifyingFireSystem() {
        super(0.25f);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false; // lit les sections de blocs du monde et pose des composants
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        if (!Allegiances.inGroup(ref, UNDEAD_GROUP, buffer)) {
            return;
        }
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        ChunkStore chunks = buffer.getExternalData().getWorld().getChunkStore();
        Vector3d fire = nearestFire(chunks, position);
        if (fire == null) {
            return;
        }
        forgetTargetsNear(ref, fire, buffer);

        double dx = position.x - fire.x;
        double dz = position.z - fire.z;
        double length = Math.sqrt(dx * dx + dz * dz);
        if (length < 1.0e-3) {
            double angle = Math.random() * Math.PI * 2;
            dx = Math.cos(angle);
            dz = Math.sin(angle);
            length = 1;
        }
        KnockbackComponent knockback = buffer.ensureAndGetComponent(ref, KnockbackComponent.getComponentType());
        knockback.setVelocity(new Vector3d(dx / length * PUSH_SPEED, PUSH_LIFT, dz / length * PUSH_SPEED));
        knockback.setVelocityType(ChangeVelocityType.Set);
        knockback.setVelocityConfig(null);
        knockback.setDuration(0f);
        knockback.setTimer(0f);
    }

    /** Oublie les cibles marquées qui se tiennent à portée du feu : le mort-vivant cesse de les poursuivre. */
    private static void forgetTargetsNear(Ref<EntityStore> ref, Vector3d fire, CommandBuffer<EntityStore> buffer) {
        MarkedEntitySupport marked = buffer.getComponent(ref, MarkedEntitySupport.getComponentType());
        if (marked == null) {
            return;
        }
        for (int slot = 0; slot < marked.getMarkedEntitySlotCount(); slot++) {
            Ref<EntityStore> target = marked.getMarkedEntityRef(slot);
            if (target == null || !target.isValid()) {
                continue;
            }
            TransformComponent transform = buffer.getComponent(target, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            Vector3d at = transform.getPosition();
            double dx = at.x - fire.x;
            double dz = at.z - fire.z;
            if (dx * dx + dz * dz <= (RADIUS + 2) * (RADIUS + 2)) {
                marked.clearMarkedEntity(slot);
            }
        }
    }

    /** Centre du bloc de feu purificateur chargé le plus proche (à l'horizontale), ou null hors de portée. */
    private static Vector3d nearestFire(ChunkStore chunks, Vector3d from) {
        int torch = BlockType.getAssetMap().getIndexOrDefault(TORCH, -1);
        int lantern = BlockType.getAssetMap().getIndexOrDefault(LANTERN, -1);
        if (torch < 0 && lantern < 0) {
            return null;
        }
        IntList ids = torch < 0 ? IntList.of(lantern) : lantern < 0 ? IntList.of(torch) : IntList.of(torch, lantern);
        Store<ChunkStore> store = chunks.getStore();
        int cx = (int) Math.floor(from.x);
        int cy = (int) Math.floor(from.y);
        int cz = (int) Math.floor(from.z);
        int minY = Math.max(0, cy - HEIGHT);
        int maxY = cy + HEIGHT;
        long[] best = {(long) RADIUS * RADIUS + 1};
        Vector3d[] result = {null};
        for (int sx = (cx - RADIUS) >> ChunkUtil.BITS; sx <= (cx + RADIUS) >> ChunkUtil.BITS; sx++) {
            for (int sy = minY >> ChunkUtil.BITS; sy <= maxY >> ChunkUtil.BITS; sy++) {
                for (int sz = (cz - RADIUS) >> ChunkUtil.BITS; sz <= (cz + RADIUS) >> ChunkUtil.BITS; sz++) {
                    int baseX = sx << ChunkUtil.BITS;
                    int baseY = sy << ChunkUtil.BITS;
                    int baseZ = sz << ChunkUtil.BITS;
                    Ref<ChunkStore> sectionRef = chunks.getChunkSectionReferenceAtBlock(baseX, baseY, baseZ);
                    if (sectionRef == null || !sectionRef.isValid()) {
                        continue;
                    }
                    BlockSection section = store.getComponent(sectionRef, BlockSection.getComponentType());
                    if (section == null || !(torch >= 0 && section.contains(torch) || lantern >= 0 && section.contains(lantern))) {
                        continue;
                    }
                    section.find(ids, blockIndex -> {
                        int x = baseX + ChunkUtil.xFromIndex(blockIndex);
                        int y = baseY + ChunkUtil.yFromIndex(blockIndex);
                        int z = baseZ + ChunkUtil.zFromIndex(blockIndex);
                        long dx = x - cx;
                        long dz = z - cz;
                        long distance = dx * dx + dz * dz;
                        if (distance < best[0] && y >= minY && y <= maxY) {
                            best[0] = distance;
                            result[0] = new Vector3d(x + 0.5, y, z + 0.5);
                        }
                    });
                }
            }
        }
        return result[0];
    }
}
