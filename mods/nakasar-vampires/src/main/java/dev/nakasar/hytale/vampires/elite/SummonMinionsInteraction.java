package dev.nakasar.hytale.vampires.elite;

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
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
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
 * {@code "Type": "Nakasar_SummonMinions"} : une élite fait apparaître ses serviteurs autour d'elle. Chaque serviteur
 * est un PNJ indépendant ({@code MinionRole}) qui a sa propre vie et ses propres attaques : vrilles combattantes de la
 * citrouille géante, rouages enchantés de l'armure enchantée, fantômes invoqués du Spectre.
 *
 * <p>Au plus {@code MaxAlive} serviteurs vivants par élite : un appel n'en fait apparaître que ce qui manque, dans
 * la limite de {@code Count}. Les serviteurs ne sont pas sauvegardés ({@code NonSerialized}) et disparaissent avec
 * leur élite (morte ou retirée du monde) ; on vérifie toutes les {@value #POLL_MS} ms. Un serviteur parti à plus
 * de {@value #LEASH} blocs de son élite (fantôme qui poursuit un joueur en fuite) est retiré : il ne la protège plus
 * de loin, et l'IA de l'élite (capteur {@code Count}, 40 blocs) peut rappeler une vague.
 *
 * <p>Les serviteurs apparaissent répartis autour de l'élite et jamais à moins de {@code MinSpacing} blocs d'un autre
 * (déjà là ou du même appel) : deux serviteurs ne se chevauchent pas. S'il ne reste pas de place, il en vient moins.
 *
 * <p>{@code HealSummonerPerSecond} : chaque serviteur vivant rend ce nombre de PV par seconde à son élite (rouages de
 * l'armure enchantée) ; le montant est celui de l'appel qui l'a fait venir. Tant qu'une élite protégée par {@link MinionShieldSystem} a des serviteurs vivants
 * ({@link #hasLivingMinions}), elle est invulnérable (composant {@link Invulnerable}, retiré quand la vague est
 * détruite) ; il peut aussi faire venir la première vague dès le premier
 * coup reçu ({@link #summonFirstWave}).
 *
 * <p>Clés JSON : {@code MinionRole} (string, obligatoire), {@code Count} (int, défaut 5), {@code MaxAlive} (int,
 * défaut 5), {@code MinDistance} et {@code MaxDistance} (float, défaut 3 et 7 blocs), {@code MinSpacing} (float,
 * défaut 2,5 blocs), {@code HealSummonerPerSecond} (float, défaut 0).
 */
public class SummonMinionsInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_SummonMinions";

    public static final BuilderCodec<SummonMinionsInteraction> CODEC = BuilderCodec
            .builder(SummonMinionsInteraction.class, SummonMinionsInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Fait apparaitre des serviteurs (PNJ) autour du lanceur.")
            .append(new KeyedCodec<>("MinionRole", Codec.STRING), (i, v) -> i.minionRole = v, i -> i.minionRole)
            .documentation("Role du PNJ serviteur.")
            .add()
            .append(new KeyedCodec<>("Count", Codec.INTEGER), (i, v) -> i.count = v, i -> i.count)
            .documentation("Nombre maximal de serviteurs qui apparaissent a chaque appel.")
            .add()
            .append(new KeyedCodec<>("MaxAlive", Codec.INTEGER), (i, v) -> i.maxAlive = v, i -> i.maxAlive)
            .documentation("Nombre maximal de serviteurs vivants par lanceur.")
            .add()
            .append(new KeyedCodec<>("MinDistance", Codec.FLOAT), (i, v) -> i.minDistance = v, i -> i.minDistance)
            .documentation("Distance minimale au lanceur, en blocs.")
            .add()
            .append(new KeyedCodec<>("MaxDistance", Codec.FLOAT), (i, v) -> i.maxDistance = v, i -> i.maxDistance)
            .documentation("Distance maximale au lanceur, en blocs.")
            .add()
            .append(new KeyedCodec<>("MinSpacing", Codec.FLOAT), (i, v) -> i.minSpacing = v, i -> i.minSpacing)
            .documentation("Distance minimale entre deux serviteurs, en blocs.")
            .add()
            .append(new KeyedCodec<>("HealSummonerPerSecond", Codec.FLOAT), (i, v) -> i.healPerSecond = v, i -> i.healPerSecond)
            .documentation("PV rendus au lanceur chaque seconde par serviteur vivant.")
            .add()
            .build();

    private static final long POLL_MS = 250;
    private static final int ATTEMPTS_PER_MINION = 6;
    /** Au-delà de cette distance horizontale à son élite, un serviteur est retiré. */
    private static final double LEASH = 36.0;

    /** Serviteurs vivants par élite. Lu et modifié sur le thread du monde. */
    private static final Map<Ref<EntityStore>, List<Ref<EntityStore>>> MINIONS = new ConcurrentHashMap<>();
    /** PV rendus chaque seconde à son élite, par serviteur soigneur (réglage de l'appel qui l'a fait venir). */
    private static final Map<Ref<EntityStore>, Float> HEAL = new ConcurrentHashMap<>();
    /** Dernier appel d'invocation par élite depuis son dernier retour au calme (System.nanoTime), réussi ou non. */
    private static final Map<Ref<EntityStore>, Long> LAST_CALL = new ConcurrentHashMap<>();

    protected String minionRole;
    protected int count = 5;
    protected int maxAlive = 5;
    protected float minDistance = 3f;
    protected float maxDistance = 7f;
    protected float minSpacing = 2.5f;
    protected float healPerSecond = 0f;

    public SummonMinionsInteraction() {
    }

    /** Vague fixée en Java (même réglage qu'une interaction JSON), pour {@link #summonFirstWave}. */
    public static SummonMinionsInteraction preset(String role, int count, int maxAlive, float minDistance,
                                                  float maxDistance, float minSpacing) {
        SummonMinionsInteraction wave = new SummonMinionsInteraction();
        wave.minionRole = role;
        wave.count = count;
        wave.maxAlive = maxAlive;
        wave.minDistance = minDistance;
        wave.maxDistance = maxDistance;
        wave.minSpacing = minSpacing;
        return wave;
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> summoner = owner != null && owner.isValid() ? owner : context.getEntity();
        if (minionRole == null || minionRole.isBlank()) {
            VampiresPlugin.get().getLogger().atWarning().log("%s : MinionRole manquant, aucun serviteur", TYPE_ID);
            return;
        }
        if (buffer == null || summoner == null || !summoner.isValid()) {
            return;
        }
        TransformComponent transform = buffer.getComponent(summoner, TransformComponent.getComponentType());
        if (transform == null) {
            return;
        }
        Vector3d center = new Vector3d(transform.getPosition());
        World world = buffer.getExternalData().getWorld();
        LAST_CALL.put(summoner, System.nanoTime());
        // Le store est en plein traitement : les serviteurs apparaissent juste après.
        world.execute(() -> summon(world, summoner, center));
    }

    /**
     * Fait venir la vague donnée autour de l'élite, hors de son IA, si aucune invocation n'a eu lieu depuis son
     * dernier retour au calme ({@link #forgetCalls}) : premier coup reçu avant qu'elle n'ait pu lancer la sienne.
     * Appelé pendant le traitement du store : la vague vient juste après.
     */
    public static void summonFirstWave(SummonMinionsInteraction wave, World world, Ref<EntityStore> summoner, Vector3d center) {
        if (LAST_CALL.putIfAbsent(summoner, System.nanoTime()) != null) {
            return;
        }
        Vector3d at = new Vector3d(center);
        world.execute(() -> wave.summon(world, summoner, at));
    }

    /** Oublie les invocations de l'élite (revenue au calme) : le prochain premier coup relancera une vague. */
    public static void forgetCalls(Ref<EntityStore> summoner) {
        LAST_CALL.remove(summoner);
    }

    /** Vrai si l'élite a au moins un serviteur vivant (sur le thread du monde). */
    public static boolean hasLivingMinions(Ref<EntityStore> summoner, Store<EntityStore> store) {
        List<Ref<EntityStore>> minions = MINIONS.get(summoner);
        if (minions == null) {
            return false;
        }
        for (Ref<EntityStore> minion : minions) {
            if (alive(minion, store)) {
                return true;
            }
        }
        return false;
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    private void summon(World world, Ref<EntityStore> summoner, Vector3d center) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (!alive(summoner, store)) {
            if (!MINIONS.containsKey(summoner)) {
                // Morte avant la vague : aucun suivi ne nettoiera son entrée.
                LAST_CALL.remove(summoner);
            }
            return;
        }
        boolean watched = MINIONS.containsKey(summoner);
        List<Ref<EntityStore>> minions = MINIONS.computeIfAbsent(summoner, k -> new ArrayList<>());
        minions.removeIf(minion -> !alive(minion, store));
        int wanted = Math.min(count, maxAlive - minions.size());
        // Positions (x, z) des serviteurs déjà là, puis de ceux qui arrivent : chacun garde ses distances.
        List<double[]> taken = new ArrayList<>();
        for (Ref<EntityStore> minion : minions) {
            TransformComponent transform = store.getComponent(minion, TransformComponent.getComponentType());
            if (transform != null) {
                taken.add(new double[]{transform.getPosition().x, transform.getPosition().z});
            }
        }
        double start = ThreadLocalRandom.current().nextDouble(Math.PI * 2);
        int spawned = 0;
        // Partagé par les serviteurs de l'appel : une sonde qui échoue partout n'est pas retentée.
        boolean[] probeUsable = {true};
        for (int i = 0; i < wanted; i++) {
            // Angles répartis sur le tour (avec un peu de hasard) : les serviteurs encerclent l'élite.
            Ref<EntityStore> minion = spawnOne(world, store, center, start + i * Math.PI * 2 / wanted, taken, probeUsable);
            if (minion != null) {
                // Jamais sauvegardé : il ne survit pas à son élite ni au déchargement du chunk.
                store.ensureAndGetComponent(minion, EntityStore.REGISTRY.getNonSerializedComponentType());
                minions.add(minion);
                if (healPerSecond > 0f) {
                    HEAL.put(minion, healPerSecond);
                }
                spawned++;
            }
        }
        if (spawned > 0) {
            VampiresPlugin.get().getLogger().atInfo().log("%s : %d '%s' apparu(s), %d vivant(s)", TYPE_ID, spawned, minionRole, minions.size());
        } else if (wanted > 0) {
            VampiresPlugin.get().getLogger().atWarning().log("%s : aucun serviteur '%s' n'a pu apparaître", TYPE_ID, minionRole);
        }
        if (!minions.isEmpty() && MinionShieldSystem.isShielded(summoner, store)) {
            // Barre de boss en mode invulnérable, comme les boss du donjon Deepworks ; retiré par watch().
            store.ensureComponent(summoner, Invulnerable.getComponentType());
        }
        if (!watched) {
            world.scheduleAfter(() -> watch(world, summoner), POLL_MS, TimeUnit.MILLISECONDS);
        }
    }

    /**
     * Fait apparaître un serviteur sur l'anneau, autour de l'angle donné, à distance des positions déjà prises (la
     * sienne y est ajoutée) ; null si aucune place. D'abord posé sur le sol par la sonde ; si la sonde ne trouve rien,
     * au niveau de l'élite et à {@code MinDistance}, là où le terrain est le plus proche de sa hauteur.
     */
    private Ref<EntityStore> spawnOne(World world, Store<EntityStore> store, Vector3d center, double baseAngle,
                                      List<double[]> taken, boolean[] probeUsable) {
        NPCPlugin npcs = NPCPlugin.get();
        for (int attempt = 0; attempt < ATTEMPTS_PER_MINION && probeUsable[0]; attempt++) {
            double[] spot = candidate(center, baseAngle, attempt, maxDistance, taken);
            if (spot == null) {
                continue;
            }
            Ref<EntityStore>[] result = newRefHolder();
            SpawnTestResult test = npcs.spawnNPCWithColumnProbe(store, minionRole, null, world,
                    MathUtil.floor(spot[0]), MathUtil.floor(spot[1]), center.y, facing(center, spot), (npc, ref, s) -> result[0] = ref);
            if (test == SpawnTestResult.TEST_OK && result[0] != null) {
                return keep(store, result[0], spot, taken);
            }
            if (test == SpawnTestResult.FAIL_NOT_SPAWNABLE || test == SpawnTestResult.FAIL_SPAWN) {
                // Échec qui ne dépend pas de l'endroit : inutile de sonder pour les serviteurs suivants.
                probeUsable[0] = false;
            }
        }
        for (int attempt = 0; attempt < ATTEMPTS_PER_MINION; attempt++) {
            double[] spot = candidate(center, baseAngle, attempt, minDistance, taken);
            if (spot == null) {
                continue;
            }
            Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = npcs.spawnNPC(store, minionRole, null,
                    new Vector3d(spot[0], center.y, spot[1]), facing(center, spot));
            if (spawned != null && spawned.first() != null) {
                return keep(store, spawned.first(), spot, taken);
            }
        }
        return null;
    }

    /**
     * Position (x, z) au centre d'une colonne de blocs, entre {@code MinDistance} et {@code ringMax} de l'élite
     * (vérifié après recentrage) et libre ; null sinon. Les premiers essais restent près de l'angle prévu.
     */
    private double[] candidate(Vector3d center, double baseAngle, int attempt, float ringMax, List<double[]> taken) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        double angle = attempt < 3 ? baseAngle + random.nextDouble(-0.35, 0.35) : random.nextDouble(Math.PI * 2);
        double distance = ringMax > minDistance ? random.nextDouble(minDistance, ringMax) : minDistance;
        double x = MathUtil.floor(center.x + Math.cos(angle) * distance) + 0.5;
        double z = MathUtil.floor(center.z + Math.sin(angle) * distance) + 0.5;
        double ring = Math.hypot(x - center.x, z - center.z);
        if (ring < minDistance || ring > Math.max(ringMax, minDistance + 1) || !free(x, z, taken)) {
            return null;
        }
        return new double[]{x, z};
    }

    /** Tourné vers l'élite, dos au combat qui l'entoure. */
    private static Rotation3f facing(Vector3d center, double[] spot) {
        return new Rotation3f(0f, (float) Math.atan2(center.x - spot[0], center.z - spot[1]), 0f);
    }

    private static Ref<EntityStore> keep(Store<EntityStore> store, Ref<EntityStore> minion, double[] spot, List<double[]> taken) {
        TransformComponent transform = store.getComponent(minion, TransformComponent.getComponentType());
        taken.add(transform != null ? new double[]{transform.getPosition().x, transform.getPosition().z} : spot);
        return minion;
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

    /**
     * Toutes les {@value #POLL_MS} ms : retire les serviteurs partis trop loin ({@value #LEASH} blocs), soigne l'élite
     * par ses serviteurs vivants ({@code HealSummonerPerSecond}) ; retire les serviteurs d'une élite morte ou
     * disparue. Tourne sur le thread du monde.
     */
    private static void watch(World world, Ref<EntityStore> summoner) {
        List<Ref<EntityStore>> minions = MINIONS.get(summoner);
        if (minions == null) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        minions.removeIf(minion -> {
            if (alive(minion, store)) {
                return false;
            }
            HEAL.remove(minion);
            return true;
        });
        if (alive(summoner, store)) {
            TransformComponent home = store.getComponent(summoner, TransformComponent.getComponentType());
            float healing = 0f;
            for (var it = minions.iterator(); it.hasNext(); ) {
                Ref<EntityStore> minion = it.next();
                TransformComponent at = store.getComponent(minion, TransformComponent.getComponentType());
                if (home != null && at != null && Math.hypot(at.getPosition().x - home.getPosition().x,
                        at.getPosition().z - home.getPosition().z) > LEASH) {
                    it.remove();
                    HEAL.remove(minion);
                    store.removeEntity(minion, RemoveReason.REMOVE);
                    continue;
                }
                healing += HEAL.getOrDefault(minion, 0f);
            }
            heal(store, summoner, healing * POLL_MS / 1000f);
            if (minions.isEmpty() && MinionShieldSystem.isShielded(summoner, store)) {
                store.tryRemoveComponent(summoner, Invulnerable.getComponentType());
            }
            world.scheduleAfter(() -> watch(world, summoner), POLL_MS, TimeUnit.MILLISECONDS);
            return;
        }
        MINIONS.remove(summoner);
        LAST_CALL.remove(summoner);
        for (Ref<EntityStore> minion : minions) {
            HEAL.remove(minion);
            if (minion.isValid()) {
                store.removeEntity(minion, RemoveReason.REMOVE);
            }
        }
    }

    /** Rend des PV à l'élite (plafonnés à son maximum par sa table de statistiques). */
    private static void heal(Store<EntityStore> store, Ref<EntityStore> summoner, float amount) {
        if (amount <= 0f) {
            return;
        }
        EntityStatMap stats = store.getComponent(summoner, EntityStatMap.getComponentType());
        if (stats != null) {
            stats.addStatValue(DefaultEntityStatTypes.getHealth(), amount);
        }
    }

    private static boolean alive(Ref<EntityStore> ref, Store<EntityStore> store) {
        return ref.isValid() && store.getComponent(ref, DeathComponent.getComponentType()) == null;
    }

    /** Oublie les serviteurs suivis (arrêt du plugin). Ils partent avec le monde. */
    public static void clearAll() {
        MINIONS.clear();
        HEAL.clear();
        LAST_CALL.clear();
    }
}
