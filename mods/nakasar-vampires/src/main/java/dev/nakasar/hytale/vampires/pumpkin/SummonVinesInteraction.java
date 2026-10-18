package dev.nakasar.hytale.vampires.pumpkin;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.util.MathUtil;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.spawning.SpawnTestResult;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;

/**
 * {@code "Type": "Nakasar_SummonVines"} : la citrouille géante fait sortir de terre des vrilles combattantes autour
 * d'elle. Chaque vrille est un PNJ indépendant ({@code VineRole}) qui a sa propre vie et ses propres attaques
 * (épines, balayage annoncé).
 *
 * <p>Au plus {@code MaxAlive} vrilles vivantes par citrouille : un appel n'en fait sortir que ce qui manque, dans
 * la limite de {@code Count}. Les vrilles ne sont pas sauvegardées ({@code NonSerialized}) et disparaissent avec
 * leur citrouille (morte ou retirée du monde) ; on vérifie toutes les {@value #POLL_MS} ms.
 *
 * <p>Les vrilles sortent réparties autour de la citrouille et jamais à moins de {@code MinSpacing} blocs d'une autre
 * vrille (déjà sortie ou du même appel) : deux vrilles ne se chevauchent pas. S'il ne reste pas de place, il en sort
 * moins.
 *
 * <p>Clés JSON : {@code VineRole} (string, défaut {@code Nakasar_Pumpkin_Vine}), {@code Count} (int, défaut 5),
 * {@code MaxAlive} (int, défaut 6), {@code MinDistance} et {@code MaxDistance} (float, défaut 3 et 7 blocs),
 * {@code MinSpacing} (float, défaut 2,5 blocs).
 */
public class SummonVinesInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_SummonVines";

    public static final BuilderCodec<SummonVinesInteraction> CODEC = BuilderCodec
            .builder(SummonVinesInteraction.class, SummonVinesInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Fait sortir de terre des vrilles combattantes (PNJ) autour du lanceur.")
            .append(new KeyedCodec<>("VineRole", Codec.STRING), (i, v) -> i.vineRole = v, i -> i.vineRole)
            .documentation("Role du PNJ vrille.")
            .add()
            .append(new KeyedCodec<>("Count", Codec.INTEGER), (i, v) -> i.count = v, i -> i.count)
            .documentation("Nombre maximal de vrilles qui sortent a chaque appel.")
            .add()
            .append(new KeyedCodec<>("MaxAlive", Codec.INTEGER), (i, v) -> i.maxAlive = v, i -> i.maxAlive)
            .documentation("Nombre maximal de vrilles vivantes par lanceur.")
            .add()
            .append(new KeyedCodec<>("MinDistance", Codec.FLOAT), (i, v) -> i.minDistance = v, i -> i.minDistance)
            .documentation("Distance minimale au lanceur, en blocs.")
            .add()
            .append(new KeyedCodec<>("MaxDistance", Codec.FLOAT), (i, v) -> i.maxDistance = v, i -> i.maxDistance)
            .documentation("Distance maximale au lanceur, en blocs.")
            .add()
            .append(new KeyedCodec<>("MinSpacing", Codec.FLOAT), (i, v) -> i.minSpacing = v, i -> i.minSpacing)
            .documentation("Distance minimale entre deux vrilles, en blocs.")
            .add()
            .build();

    private static final long POLL_MS = 1000;
    private static final int ATTEMPTS_PER_VINE = 8;

    /** Vrilles vivantes par citrouille. Lu et modifié sur le thread du monde. */
    private static final Map<Ref<EntityStore>, List<Ref<EntityStore>>> VINES = new ConcurrentHashMap<>();

    protected String vineRole = "Nakasar_Pumpkin_Vine";
    protected int count = 5;
    protected int maxAlive = 6;
    protected float minDistance = 3f;
    protected float maxDistance = 7f;
    protected float minSpacing = 2.5f;

    public SummonVinesInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> summoner = owner != null && owner.isValid() ? owner : context.getEntity();
        if (buffer == null || summoner == null || !summoner.isValid()) {
            return;
        }
        TransformComponent transform = buffer.getComponent(summoner, TransformComponent.getComponentType());
        if (transform == null) {
            return;
        }
        Vector3d center = new Vector3d(transform.getPosition());
        World world = buffer.getExternalData().getWorld();
        // Le store est en plein traitement : on fait sortir les vrilles juste après.
        world.execute(() -> summon(world, summoner, center));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    private void summon(World world, Ref<EntityStore> summoner, Vector3d center) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (!alive(summoner, store)) {
            return;
        }
        boolean watched = VINES.containsKey(summoner);
        List<Ref<EntityStore>> vines = VINES.computeIfAbsent(summoner, k -> new ArrayList<>());
        vines.removeIf(vine -> !alive(vine, store));
        int wanted = Math.min(count, maxAlive - vines.size());
        // Positions (x, z) des vrilles déjà là, puis de celles qui sortent : chacune garde ses distances.
        List<double[]> taken = new ArrayList<>();
        for (Ref<EntityStore> vine : vines) {
            TransformComponent transform = store.getComponent(vine, TransformComponent.getComponentType());
            if (transform != null) {
                taken.add(new double[]{transform.getPosition().x, transform.getPosition().z});
            }
        }
        double start = ThreadLocalRandom.current().nextDouble(Math.PI * 2);
        int spawned = 0;
        for (int i = 0; i < wanted; i++) {
            // Angles répartis sur le tour (avec un peu de hasard) : les vrilles encerclent la citrouille.
            Ref<EntityStore> vine = spawnOne(world, store, center, start + i * Math.PI * 2 / wanted, taken);
            if (vine != null) {
                // Jamais sauvegardée : elle ne survit pas à sa citrouille ni au déchargement du chunk.
                store.ensureAndGetComponent(vine, EntityStore.REGISTRY.getNonSerializedComponentType());
                vines.add(vine);
                spawned++;
            }
        }
        if (spawned > 0) {
            VampiresPlugin.get().getLogger().atInfo().log("%s : %d vrille(s) sortie(s) de terre, %d vivante(s)", TYPE_ID, spawned, vines.size());
        } else if (wanted > 0) {
            VampiresPlugin.get().getLogger().atWarning().log("%s : aucune vrille '%s' n'a pu sortir de terre", TYPE_ID, vineRole);
        }
        if (!watched) {
            world.scheduleAfter(() -> watch(world, summoner), POLL_MS, TimeUnit.MILLISECONDS);
        }
    }

    /**
     * Fait sortir une vrille sur l'anneau, autour de l'angle donné, posée sur le sol et à distance des positions
     * déjà prises (la sienne y est ajoutée) ; null si aucune place.
     */
    private Ref<EntityStore> spawnOne(World world, Store<EntityStore> store, Vector3d center, double baseAngle, List<double[]> taken) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        NPCPlugin npcs = NPCPlugin.get();
        boolean probe = true;
        // Deux passes : avec la sonde de sol, puis (si elle n'a rien trouvé) au niveau de la citrouille.
        for (int attempt = 0; attempt < ATTEMPTS_PER_VINE * 2; attempt++) {
            if (attempt == ATTEMPTS_PER_VINE) {
                probe = false;
            }
            // D'abord près de l'angle prévu, puis n'importe où sur l'anneau.
            double angle = attempt % ATTEMPTS_PER_VINE < 3 ? baseAngle + random.nextDouble(-0.35, 0.35) : random.nextDouble(Math.PI * 2);
            double distance = maxDistance > minDistance ? random.nextDouble(minDistance, maxDistance) : minDistance;
            // La sonde pose la vrille au centre de la colonne de blocs : on vérifie l'espacement à cet endroit.
            int bx = MathUtil.floor(center.x + Math.cos(angle) * distance);
            int bz = MathUtil.floor(center.z + Math.sin(angle) * distance);
            double x = bx + 0.5;
            double z = bz + 0.5;
            if (!free(x, z, taken)) {
                continue;
            }
            // Tournée vers la citrouille, dos au combat qui l'entoure.
            Rotation3f rotation = new Rotation3f(0f, (float) Math.atan2(center.x - x, center.z - z), 0f);
            Ref<EntityStore> vine = null;
            if (probe) {
                Ref<EntityStore>[] result = newRefHolder();
                SpawnTestResult test = npcs.spawnNPCWithColumnProbe(store, vineRole, null, world, bx, bz, center.y, rotation,
                        (npc, ref, s) -> result[0] = ref);
                if (test == SpawnTestResult.TEST_OK) {
                    vine = result[0];
                } else if (test == SpawnTestResult.FAIL_NOT_SPAWNABLE || test == SpawnTestResult.FAIL_SPAWN) {
                    probe = false;
                }
            }
            if (vine == null && !probe) {
                // La sonde ne trouve pas de place : on la pose au niveau de la citrouille.
                Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = npcs.spawnNPC(store, vineRole, null, new Vector3d(x, center.y, z), rotation);
                vine = spawned == null ? null : spawned.first();
            }
            if (vine != null) {
                TransformComponent transform = store.getComponent(vine, TransformComponent.getComponentType());
                taken.add(transform != null ? new double[]{transform.getPosition().x, transform.getPosition().z} : new double[]{x, z});
                return vine;
            }
        }
        return null;
    }

    private boolean free(double x, double z, List<double[]> taken) {
        for (double[] other : taken) {
            double dx = other[0] - x;
            double dz = other[1] - z;
            if (dx * dx + dz * dz < minSpacing * minSpacing) {
                return false;
            }
        }
        return true;
    }

    @SuppressWarnings("unchecked")
    private static Ref<EntityStore>[] newRefHolder() {
        return (Ref<EntityStore>[]) new Ref[1];
    }

    /** Retire les vrilles d'une citrouille morte ou disparue ; sinon repasse plus tard. Tourne sur le thread du monde. */
    private static void watch(World world, Ref<EntityStore> summoner) {
        List<Ref<EntityStore>> vines = VINES.get(summoner);
        if (vines == null) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        vines.removeIf(vine -> !alive(vine, store));
        if (alive(summoner, store)) {
            world.scheduleAfter(() -> watch(world, summoner), POLL_MS, TimeUnit.MILLISECONDS);
            return;
        }
        VINES.remove(summoner);
        for (Ref<EntityStore> vine : vines) {
            if (vine.isValid()) {
                store.removeEntity(vine, RemoveReason.REMOVE);
            }
        }
    }

    private static boolean alive(Ref<EntityStore> ref, Store<EntityStore> store) {
        return ref.isValid() && store.getComponent(ref, DeathComponent.getComponentType()) == null;
    }

    /** Oublie les vrilles suivies (arrêt du plugin). Elles partent avec le monde. */
    public static void clearAll() {
        VINES.clear();
    }
}
