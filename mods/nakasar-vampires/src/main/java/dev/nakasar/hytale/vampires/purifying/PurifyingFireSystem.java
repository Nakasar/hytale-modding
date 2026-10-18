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
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;
import it.unimi.dsi.fastutil.ints.IntList;
import java.util.HashMap;
import java.util.Map;
import org.joml.Vector3d;

/**
 * Feu purificateur : les morts-vivants (groupe de PNJ {@value #UNDEAD_GROUP}) ne s'approchent pas à moins de
 * {@value #RADIUS} blocs d'une torche ou d'une lanterne de feu blanc (blocs {@value #TORCH} et {@value #LANTERN},
 * posés autour et dans le camp des chasseurs de vampires).
 *
 * <p>Quatre fois par seconde :
 * <ul>
 *   <li>un mort-vivant à moins de {@value #RADIUS} + {@value #APPROACH} blocs d'un feu oublie les cibles qui se
 *       tiennent elles-mêmes près d'un feu ; tant qu'il reste dans cette bande, il les oublie à chaque passage et
 *       s'arrête donc avant d'entrer dans le rayon ;</li>
 *   <li>dans le rayon, il est repoussé hors des feux (somme des répulsions de tous les feux proches, ce qui le
 *       pousse vers le bord le plus proche d'un groupe de feux) ;</li>
 *   <li>s'il y reste plus de {@value #BURN_DELAY} secondes (enfermé dans le camp, par exemple), le feu le brûle
 *       ({@value #BURN_DAMAGE} dégâts de feu par seconde) jusqu'à ce qu'il sorte ou meure.</li>
 * </ul>
 * Les rôles du jeu n'ont pas de capteur « fuir un bloc », d'où ce système plutôt que du JSON.
 */
public final class PurifyingFireSystem extends DelayedEntitySystem<EntityStore> {

    public static final String UNDEAD_GROUP = "Nakasar_Undead";
    public static final String TORCH = "Nakasar_Purifying_Torch";
    public static final String LANTERN = "Nakasar_Purifying_Lantern";
    /** Distance horizontale (blocs) en deçà de laquelle un mort-vivant est repoussé (PURIFY_RADIUS des prefabs). */
    public static final int RADIUS = 7;
    /** Bande au-delà du rayon où le mort-vivant renonce déjà aux cibles protégées par le feu. */
    private static final int APPROACH = 4;
    /** Une cible à moins de cette distance d'un feu est protégée. */
    private static final int SHELTER = RADIUS + 2;
    /** Écart de hauteur pris en compte entre le PNJ et le feu (palissade, poteaux). */
    private static final int HEIGHT = 5;
    private static final float INTERVAL = 0.25f;
    private static final double PUSH_SPEED = 7.0;
    /** Petite levée pour décoller du sol, seulement si le PNJ n'est pas déjà au-dessus du feu (fantômes). */
    private static final double PUSH_LIFT = 1.5;
    private static final float BURN_DELAY = 2f;
    private static final float BURN_DAMAGE = 6f;
    private static final int BURN_EVERY = Math.round(1f / INTERVAL);

    private static final Query<EntityStore> QUERY =
            Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());

    /** Nombre de passages consécutifs dans le rayon, par mort-vivant (système non parallèle). */
    private final Map<Ref<EntityStore>, Integer> exposure = new HashMap<>();
    private int torchId = -1;
    private int lanternId = -1;
    private IntList fireIds = IntList.of();

    public PurifyingFireSystem() {
        super(INTERVAL);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false; // lit les sections de blocs du monde, pose des composants et tient l'état d'exposition
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        if (!resolveFireIds()) {
            return;
        }
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        if (!Allegiances.inGroup(ref, UNDEAD_GROUP, buffer)) {
            return;
        }
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        ChunkStore chunks = buffer.getExternalData().getWorld().getChunkStore();
        Fires fires = scan(chunks, position, RADIUS + APPROACH);
        if (fires.nearest == null) {
            exposure.remove(ref);
            return;
        }
        forgetSheltered(ref, chunks, buffer);
        if (fires.nearestDistanceSq > (long) RADIUS * RADIUS) {
            exposure.remove(ref);
            return;
        }
        push(ref, position, fires, buffer);
        burn(ref, buffer);
    }

    /** Ids des deux blocs, résolus une fois les assets chargés ; faux tant qu'aucun n'existe. */
    private boolean resolveFireIds() {
        if (torchId < 0 || lanternId < 0) {
            torchId = BlockType.getAssetMap().getIndexOrDefault(TORCH, -1);
            lanternId = BlockType.getAssetMap().getIndexOrDefault(LANTERN, -1);
            fireIds = torchId < 0 ? (lanternId < 0 ? IntList.of() : IntList.of(lanternId))
                    : lanternId < 0 ? IntList.of(torchId) : IntList.of(torchId, lanternId);
        }
        return !fireIds.isEmpty();
    }

    /** Oublie les cibles marquées qui se tiennent près d'un feu : le mort-vivant cesse de les poursuivre. */
    private void forgetSheltered(Ref<EntityStore> ref, ChunkStore chunks, CommandBuffer<EntityStore> buffer) {
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
            if (transform != null && scan(chunks, transform.getPosition(), SHELTER).nearest != null) {
                marked.clearMarkedEntity(slot);
            }
        }
    }

    /**
     * Repousse le mort-vivant hors des feux, sauf si un autre recul (coup reçu) est déjà en attente : on ne
     * l'écrase pas, le feu repoussera au passage suivant.
     */
    private static void push(Ref<EntityStore> ref, Vector3d position, Fires fires, CommandBuffer<EntityStore> buffer) {
        if (buffer.getComponent(ref, KnockbackComponent.getComponentType()) != null) {
            return;
        }
        double dx = fires.awayX;
        double dz = fires.awayZ;
        double length = Math.sqrt(dx * dx + dz * dz);
        if (length < 1.0e-3) {
            double angle = Math.random() * Math.PI * 2;
            dx = Math.cos(angle);
            dz = Math.sin(angle);
            length = 1;
        }
        double lift = position.y <= fires.nearest.y + 1 ? PUSH_LIFT : 0;
        KnockbackComponent knockback = buffer.ensureAndGetComponent(ref, KnockbackComponent.getComponentType());
        knockback.setVelocity(new Vector3d(dx / length * PUSH_SPEED, lift, dz / length * PUSH_SPEED));
        knockback.setVelocityType(ChangeVelocityType.Set);
        knockback.setVelocityConfig(null);
        knockback.setDuration(0f);
        knockback.setTimer(0f);
    }

    /** Brûle le mort-vivant resté trop longtemps dans le rayon (enfermé dans le camp, par exemple). */
    private void burn(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer) {
        if (exposure.size() > 256) {
            exposure.keySet().removeIf(r -> !r.isValid());
        }
        int ticks = exposure.merge(ref, 1, Integer::sum);
        int delay = Math.round(BURN_DELAY / INTERVAL);
        if (ticks < delay || (ticks - delay) % BURN_EVERY != 0) {
            return;
        }
        DamageCause fire = DamageCause.getAssetMap().getAsset("Fire");
        if (fire != null) {
            DamageSystems.executeDamage(ref, buffer,
                    new Damage(new Damage.EnvironmentSource("Nakasar_Purifying_Fire"), fire, BURN_DAMAGE));
        }
    }

    /** Feux chargés à moins de {@code radius} blocs (à l'horizontale) de {@code from}. */
    private Fires scan(ChunkStore chunks, Vector3d from, int radius) {
        Fires fires = new Fires();
        Store<ChunkStore> store = chunks.getStore();
        int cx = (int) Math.floor(from.x);
        int cy = (int) Math.floor(from.y);
        int cz = (int) Math.floor(from.z);
        int minY = Math.max(0, cy - HEIGHT);
        int maxY = cy + HEIGHT;
        long radiusSq = (long) radius * radius;
        fires.nearestDistanceSq = radiusSq + 1;
        for (int sx = (cx - radius) >> ChunkUtil.BITS; sx <= (cx + radius) >> ChunkUtil.BITS; sx++) {
            for (int sy = minY >> ChunkUtil.BITS; sy <= maxY >> ChunkUtil.BITS; sy++) {
                for (int sz = (cz - radius) >> ChunkUtil.BITS; sz <= (cz + radius) >> ChunkUtil.BITS; sz++) {
                    int baseX = sx << ChunkUtil.BITS;
                    int baseY = sy << ChunkUtil.BITS;
                    int baseZ = sz << ChunkUtil.BITS;
                    Ref<ChunkStore> sectionRef = chunks.getChunkSectionReferenceAtBlock(baseX, baseY, baseZ);
                    if (sectionRef == null || !sectionRef.isValid()) {
                        continue;
                    }
                    BlockSection section = store.getComponent(sectionRef, BlockSection.getComponentType());
                    if (section == null || !(torchId >= 0 && section.contains(torchId)
                            || lanternId >= 0 && section.contains(lanternId))) {
                        continue;
                    }
                    section.find(fireIds, blockIndex -> {
                        int x = baseX + ChunkUtil.xFromIndex(blockIndex);
                        int y = baseY + ChunkUtil.yFromIndex(blockIndex);
                        int z = baseZ + ChunkUtil.zFromIndex(blockIndex);
                        if (y < minY || y > maxY) {
                            return;
                        }
                        double dx = from.x - (x + 0.5);
                        double dz = from.z - (z + 0.5);
                        long gx = x - cx;
                        long gz = z - cz;
                        long distanceSq = gx * gx + gz * gz;
                        if (distanceSq > radiusSq) {
                            return;
                        }
                        if (distanceSq < fires.nearestDistanceSq) {
                            fires.nearestDistanceSq = distanceSq;
                            fires.nearest = new Vector3d(x + 0.5, y, z + 0.5);
                        }
                        // répulsion plus forte près du feu, nulle au bord du rayon de poussée
                        double d = Math.max(0.5, Math.sqrt(dx * dx + dz * dz));
                        double weight = Math.max(0, RADIUS - d) / d;
                        fires.awayX += dx * weight;
                        fires.awayZ += dz * weight;
                    });
                }
            }
        }
        return fires;
    }

    /** Résultat d'une recherche de feux : le plus proche et la direction de fuite. */
    private static final class Fires {
        Vector3d nearest;
        long nearestDistanceSq;
        double awayX;
        double awayZ;
    }
}
