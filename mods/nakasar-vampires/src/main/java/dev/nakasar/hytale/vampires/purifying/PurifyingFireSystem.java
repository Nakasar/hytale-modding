package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.DelayedEntitySystem;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
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
import it.unimi.dsi.fastutil.doubles.DoubleArrayList;
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
 *   <li>les feux à moins de {@value #RADIUS} + {@value #APPROACH} blocs d'un mort-vivant sont relevés pour
 *       {@link PurifyingSteeringSystem}, qui le fait marcher à l'écart (aucune poussée) ;</li>
 *   <li>dans cette bande, il oublie à chaque passage les cibles qui se tiennent elles-mêmes près d'un feu : il ne
 *       cherche pas à les rejoindre ;</li>
 *   <li>s'il reste plus de {@value #BURN_DELAY} secondes dans le rayon (enfermé dans le camp, par exemple), le feu
 *       le brûle ({@value #BURN_DAMAGE} dégâts de feu par seconde) jusqu'à ce qu'il sorte ou meure.</li>
 * </ul>
 * Le porteur d'une aura de lumière (rune, {@link LightAuraInteraction}) compte comme un feu qui le suit.
 *
 * <p>Les rôles vanilla (squelettes, zombies...) n'ont pas de capteur « fuir un bloc » qu'on pourrait leur ajouter sans
 * les remplacer, d'où ces systèmes plutôt que du JSON.
 */
public final class PurifyingFireSystem extends DelayedEntitySystem<EntityStore> {

    public static final String UNDEAD_GROUP = "Nakasar_Undead";
    public static final String TORCH = "Nakasar_Purifying_Torch";
    public static final String LANTERN = "Nakasar_Purifying_Lantern";
    /** Distance horizontale (blocs) en deçà de laquelle un mort-vivant s'éloigne du feu (PURIFY_RADIUS des prefabs). */
    public static final int RADIUS = 7;
    /** Bande au-delà du rayon où le mort-vivant ne s'approche plus du feu et renonce aux cibles qu'il protège. */
    public static final int APPROACH = 4;
    /** Une cible à moins de cette distance d'un feu est protégée. */
    private static final int SHELTER = RADIUS + 2;
    /** Écart de hauteur pris en compte entre le PNJ et le feu (palissade, poteaux). */
    private static final int HEIGHT = 5;
    private static final float INTERVAL = 0.25f;
    private static final float BURN_DELAY = 5f;
    private static final float BURN_DAMAGE = 6f;
    private static final int BURN_EVERY = Math.round(1f / INTERVAL);

    private static final Query<EntityStore> QUERY =
            Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType());

    /** Nombre de passages consécutifs dans le rayon, par mort-vivant (système non parallèle). */
    private final Map<Ref<EntityStore>, Integer> exposure = new HashMap<>();
    private int torchId = -1;
    private int lanternId = -1;
    private IntList fireIds = IntList.of();

    private final PurifyingFires fires;

    public PurifyingFireSystem(PurifyingFires fires) {
        super(INTERVAL);
        this.fires = fires;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false; // lit les sections de blocs du monde et tient la table des feux et l'état d'exposition
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
        Fires found = scan(chunks, store, position, RADIUS + APPROACH);
        if (found.nearest == null) {
            fires.remove(ref);
            exposure.remove(ref);
            return;
        }
        fires.put(ref, found.positions.toDoubleArray());
        forgetSheltered(ref, chunks, store, buffer);
        if (found.nearestDistanceSq > (long) RADIUS * RADIUS) {
            exposure.remove(ref);
            return;
        }
        burn(ref, buffer);
    }

    /**
     * Vrai si un feu purificateur (bloc ou aura de lumière) brûle à moins de {@value #RADIUS} blocs de
     * {@code position} : la lumière qui blesse les joueurs vampires ({@code vampirism.VampireSystem}). L'aura que
     * porte {@code self} ne compte pas. À appeler depuis le fil du monde, comme ce système.
     */
    public boolean nearFire(ChunkStore chunks, Store<EntityStore> entities, Vector3d position, Ref<EntityStore> self) {
        resolveFireIds();
        return scan(chunks, entities, position, RADIUS, self).nearest != null;
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
    private void forgetSheltered(Ref<EntityStore> ref, ChunkStore chunks, Store<EntityStore> entities,
                                 CommandBuffer<EntityStore> buffer) {
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
            if (transform != null && scan(chunks, entities, transform.getPosition(), SHELTER).nearest != null) {
                marked.clearMarkedEntity(slot);
            }
        }
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

    /**
     * Feux chargés à moins de {@code radius} blocs (à l'horizontale) de {@code from} : blocs de feu purificateur et
     * porteurs d'une aura de lumière ({@link LightAuraSystem}) du même monde.
     */
    private Fires scan(ChunkStore chunks, Store<EntityStore> entities, Vector3d from, int radius) {
        return scan(chunks, entities, from, radius, null);
    }

    private Fires scan(ChunkStore chunks, Store<EntityStore> entities, Vector3d from, int radius,
                       Ref<EntityStore> exclude) {
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
                        fires.positions.add(x + 0.5);
                        fires.positions.add(z + 0.5);
                    });
                }
            }
        }
        fires.add(entities, this.fires, exclude, cx, cz, minY, maxY, radiusSq);
        return fires;
    }

    /** Résultat d'une recherche de feux : le plus proche et les positions (x, z) de tous. */
    private static final class Fires {
        Vector3d nearest;
        long nearestDistanceSq;
        final DoubleArrayList positions = new DoubleArrayList();

        /** Ajoute les auras de lumière du monde dans le rayon, comme des feux centrés sur leurs porteurs. */
        void add(Store<EntityStore> entities, PurifyingFires registry, Ref<EntityStore> exclude, int cx, int cz,
                 int minY, int maxY, long radiusSq) {
            registry.forEachAura(entities, exclude, aura -> {
                if (aura[1] < minY - 1 || aura[1] > maxY + 1) {
                    return;
                }
                double gx = aura[0] - (cx + 0.5);
                double gz = aura[2] - (cz + 0.5);
                double distanceSq = gx * gx + gz * gz;
                if (distanceSq > radiusSq) {
                    return;
                }
                if (distanceSq < nearestDistanceSq) {
                    nearestDistanceSq = (long) Math.floor(distanceSq);
                    nearest = new Vector3d(aura[0], aura[1], aura[2]);
                }
                positions.add(aura[0]);
                positions.add(aura[2]);
            });
        }
    }
}
