package dev.nakasar.hytale.peuples.boss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.RequestSpawns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Les coups annoncés des chefs des demandes de boss (Kevin, 15 novembre 2026 : « réutilise des mécaniques du mod des
 * fractales »). Le chef se bat au corps à corps avec ses attaques vanilla (son rôle) ; le Java y ajoute, toutes les
 * {@value #COOLDOWN} s quand un joueur est à moins de {@value #ENGAGE_RANGE} blocs, l'un des trois coups des boss de
 * fractales, chacun annoncé par sa zone rouge et figé le temps de l'annonce (comme {@code combat.ChargeInteraction}) :
 * <ul>
 *   <li>{@link #SLAM_RADIUS} : cercle autour de lui (onde de choc) ;</li>
 *   <li>cône de {@link #CONE_DEGREES}° et {@link #CONE_RADIUS} blocs vers le joueur le plus proche (balayage) ;</li>
 *   <li>ligne de {@link #LINE_LENGTH} sur {@link #LINE_WIDTH} blocs vers le joueur le plus proche (déferlante) ; pour le
 *       chef trork des Kweebecs ({@link #CHARGERS}), c'est une vraie charge le long de la ligne ({@link Charge}).</li>
 * </ul>
 * Aux deux tiers puis au tiers de sa vie, il appelle ses renforts (les {@code Spawns} du modèle) et porte le composant
 * vanilla {@link Invulnerable} tant qu'ils vivent, comme les élites protégées des fractales ({@code minions.MinionShieldSystem}).
 * Sous le tiers, il frappe plus souvent. Il ne se soigne jamais (règle n° 1 : VillageNoRegenSystem coupe la régénération
 * vanilla de tout rôle {@code Nakasar_Peuples_*}, et rien ici ne rend de vie, ni sous bouclier ni hors combat).
 *
 * <p>Les tailles des zones et des tests de touche viennent des mêmes constantes ({@link Telegraphs}, règle n° 3).
 */
public final class QuestBosses extends TickingSystem<EntityStore> {

    public static final String ROLE_PREFIX = "Nakasar_Peuples_Boss_";
    public static final String KEYS = "nakasar_peuples.request.boss.";

    private static final float INTERVAL = 0.1f;
    public static final int ENGAGE_RANGE = 24;
    public static final float COOLDOWN = 7f;
    public static final float ENRAGED_COOLDOWN = 4.5f;

    public static final double SLAM_RADIUS = 4.5;
    public static final float SLAM_SECONDS = 1.8f;
    public static final float SLAM_DAMAGE = 30f;

    public static final double CONE_RADIUS = 8;
    public static final int CONE_DEGREES = 90;
    public static final float CONE_SECONDS = 1.5f;
    public static final float CONE_DAMAGE = 26f;

    public static final double LINE_LENGTH = 14;
    public static final double LINE_WIDTH = 3;
    public static final float LINE_SECONDS = 1.6f;
    public static final float LINE_DAMAGE = 34f;

    /**
     * Les chefs dont la ligne est une vraie charge ({@link Charge}, Kevin 2026-11-15) : le chef trork des Kweebecs. Après
     * l'annonce, il fonce le long de la ligne ; un mur l'arrête et l'étourdit {@value #CHARGE_STUN_SECONDS} s.
     */
    private static final Set<String> CHARGERS = Set.of(ROLE_PREFIX + "Kweebec");
    public static final double CHARGE_SPEED = 16;
    public static final double CHARGE_KNOCKBACK = 9;
    public static final float CHARGE_STUN_SECONDS = 3f;

    /** Seuils de vie des renforts. */
    private static final float[] PHASES = {2f / 3f, 1f / 3f};
    private static final String HIT_SOUND = "SFX_Gobliterator_Club_Slam_Impact";
    private static final String SUMMON_SOUND = "SFX_Trork_Chieftain_Alerted";

    /** Combat en cours d'un chef (thread du monde). */
    private static final class Fight {
        long next;
        Telegraphs.Shape shape;
        float damage;
        int phases;
        int ability = ThreadLocalRandom.current().nextInt(3);
        boolean shielded;
        /** Course en cours (chefs de {@link #CHARGERS}). */
        Charge charge;
        /** Fin de l'étourdissement après un mur (0 : pas étourdi). */
        long stunnedUntil;
    }

    private static final Map<Ref<EntityStore>, Fight> FIGHTS = Collections.synchronizedMap(new IdentityHashMap<>());
    private final Map<World, Float> wait = Collections.synchronizedMap(new WeakHashMap<>());

    /** Appelé par une demande quand ses renforts doivent apparaître : (store, clé de la demande, chef). */
    @FunctionalInterface
    public interface Summoner {
        void summon(Store<EntityStore> store, String key, Ref<EntityStore> boss, Vector3d at);
    }

    private static volatile Summoner summoner;

    public static void setSummoner(Summoner value) {
        summoner = value;
    }

    /** Vrai si le rôle est un chef de demande de boss. */
    public static boolean isBossRole(String role) {
        return role != null && role.startsWith(ROLE_PREFIX);
    }

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float left = wait.getOrDefault(world, 0f) - dt;
        if (left > 0f && !charging()) { // une course avance à chaque image
            wait.put(world, left);
            return;
        }
        wait.put(world, INTERVAL);
        Map<Ref<EntityStore>, String> bosses = RequestSpawns.all(RequestSpawns.Kind.BOSS);
        if (bosses.isEmpty() && FIGHTS.isEmpty()) {
            return;
        }
        world.execute(() -> step(world, bosses));
    }

    private static void step(World world, Map<Ref<EntityStore>, String> bosses) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        synchronized (FIGHTS) {
            FIGHTS.keySet().removeIf(r -> !r.isValid());
            // Chef rendu à la nature (demande finie) : plus d'annonce, ni figé ni protégé.
            for (Ref<EntityStore> r : new ArrayList<>(FIGHTS.keySet())) {
                if (r.getStore() == store && !bosses.containsKey(r)) {
                    store.tryRemoveComponent(r, Frozen.getComponentType());
                    store.tryRemoveComponent(r, Invulnerable.getComponentType());
                    FIGHTS.remove(r);
                }
            }
        }
        long now = System.nanoTime();
        for (Map.Entry<Ref<EntityStore>, String> e : bosses.entrySet()) {
            Ref<EntityStore> boss = e.getKey();
            if (!boss.isValid() || boss.getStore() != store) {
                continue;
            }
            try {
                stepBoss(world, store, boss, e.getValue(), now);
            } catch (RuntimeException ex) {
                PeuplesPlugin.get().getLogger().atWarning().withCause(ex).log("Peuples : coup de chef interrompu");
                store.tryRemoveComponent(boss, Frozen.getComponentType());
                FIGHTS.remove(boss);
            }
        }
    }

    private static void stepBoss(World world, Store<EntityStore> store, Ref<EntityStore> boss, String key, long now) {
        if (store.getComponent(boss, DeathComponent.getComponentType()) != null) {
            FIGHTS.remove(boss);
            return;
        }
        TransformComponent transform = store.getComponent(boss, TransformComponent.getComponentType());
        if (transform == null) {
            return;
        }
        Vector3d at = new Vector3d(transform.getPosition());
        float health = healthFraction(store, boss);
        Fight fight = FIGHTS.computeIfAbsent(boss, r -> {
            Fight f = new Fight();
            // Un chef réapparu (redémarrage, chunk rechargé) garde sa vie : ses renforts déjà passés ne reviennent pas.
            for (float p : PHASES) {
                if (health < p) {
                    f.phases++;
                }
            }
            f.next = now + Telegraphs.nanos(3f);
            return f;
        });

        // Bouclier : tant que des renforts vivent, le chef ne prend aucun dégât (et ne se soigne pas pour autant).
        boolean adds = !RequestSpawns.of(key, RequestSpawns.Kind.ADD).isEmpty();
        if (adds != fight.shielded) {
            fight.shielded = adds;
            if (adds) {
                store.ensureAndGetComponent(boss, Invulnerable.getComponentType());
            } else {
                store.tryRemoveComponent(boss, Invulnerable.getComponentType());
                notifyNear(world, store, at, Message.translation(KEYS + "unshielded"), NotificationStyle.Default);
            }
        }

        // Course en cours : le chef fonce le long de sa ligne.
        if (fight.charge != null) {
            Charge.Result r = fight.charge.step(world, store, now);
            if (r == Charge.Result.RUNNING) {
                return;
            }
            fight.charge = null;
            if (r == Charge.Result.WALL) {
                // Il percute un mur : étourdi (reste figé), la fenêtre pour le frapper.
                Telegraphs.sound(store, HIT_SOUND, at);
                fight.stunnedUntil = now + Telegraphs.nanos(CHARGE_STUN_SECONDS);
                return;
            }
            store.tryRemoveComponent(boss, Frozen.getComponentType());
            fight.next = now + Telegraphs.nanos(health < PHASES[1] ? ENRAGED_COOLDOWN : COOLDOWN);
            return;
        }
        if (fight.stunnedUntil != 0) {
            if (now < fight.stunnedUntil) {
                return;
            }
            fight.stunnedUntil = 0;
            store.tryRemoveComponent(boss, Frozen.getComponentType());
            fight.next = now + Telegraphs.nanos(health < PHASES[1] ? ENRAGED_COOLDOWN : COOLDOWN);
            return;
        }

        // Annonce en cours : dessin, puis coup.
        if (fight.shape != null) {
            if (fight.shape.step(store, now)) {
                if (fight.shape instanceof Telegraphs.Strip strip && CHARGERS.contains(RequestSpawns.role(store, boss))) {
                    // La ligne annoncée devient sa course (il reste figé, le Java le déplace).
                    fight.charge = new Charge(store, boss, strip, CHARGE_SPEED, fight.damage, CHARGE_KNOCKBACK, now);
                    fight.shape = null;
                    return;
                }
                hit(world, store, boss, fight.shape, fight.damage);
                fight.shape = null;
                store.tryRemoveComponent(boss, Frozen.getComponentType());
                fight.next = now + Telegraphs.nanos(health < PHASES[1] ? ENRAGED_COOLDOWN : COOLDOWN);
            }
            return;
        }

        // Renforts aux seuils de vie.
        if (fight.phases < PHASES.length && health < PHASES[fight.phases]) {
            fight.phases++;
            Summoner s = summoner;
            if (s != null) {
                s.summon(store, key, boss, at);
            }
            Telegraphs.sound(store, SUMMON_SOUND, at);
            notifyNear(world, store, at, Message.translation(KEYS + "summon"), NotificationStyle.Warning);
            return;
        }

        if (now < fight.next) {
            return;
        }
        Vector3d target = nearestPlayer(world, store, at, ENGAGE_RANGE);
        if (target == null) {
            fight.next = now + Telegraphs.nanos(1f);
            return;
        }
        double facing = Telegraphs.angle(at, target);
        Vector3d ground = new Vector3d(at.x(), Math.floor(at.y()), at.z());
        switch (fight.ability++ % 3) {
            case 0 -> {
                fight.shape = new Telegraphs.Circle(ground, SLAM_RADIUS, now, SLAM_SECONDS);
                fight.damage = SLAM_DAMAGE;
            }
            case 1 -> {
                fight.shape = new Telegraphs.Cone(ground, facing, Math.toRadians(CONE_DEGREES), CONE_RADIUS, now, CONE_SECONDS);
                fight.damage = CONE_DAMAGE;
            }
            default -> {
                fight.shape = new Telegraphs.Strip(ground, facing, LINE_LENGTH, LINE_WIDTH, now, LINE_SECONDS);
                fight.damage = LINE_DAMAGE;
            }
        }
        // Figé pendant l'annonce : la zone reste juste (le chef ne marche pas hors de son cercle).
        store.ensureAndGetComponent(boss, Frozen.getComponentType());
        fight.shape.step(store, now);
    }

    /** Dégâts aux joueurs dans la zone, au nom du chef. */
    private static void hit(World world, Store<EntityStore> store, Ref<EntityStore> boss, Telegraphs.Shape shape, float damage) {
        Telegraphs.sound(store, HIT_SOUND, shape.origin());
        DamageCause cause = DamageCause.getAssetMap().getAsset("Physical");
        if (cause == null) {
            return;
        }
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            TransformComponent t = ref == null || !ref.isValid() ? null : store.getComponent(ref, TransformComponent.getComponentType());
            if (t != null && shape.contains(t.getPosition())) {
                DamageSystems.executeDamage(ref, store, new Damage(new Damage.EntitySource(boss), cause, damage));
            }
        }
    }

    private static Vector3d nearestPlayer(World world, Store<EntityStore> store, Vector3d at, double range) {
        Vector3d best = null;
        double bestDistance = range * range;
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            TransformComponent t = ref == null || !ref.isValid() ? null : store.getComponent(ref, TransformComponent.getComponentType());
            if (t == null || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                continue;
            }
            double d = t.getPosition().distanceSquared(at);
            if (d <= bestDistance) {
                bestDistance = d;
                best = new Vector3d(t.getPosition());
            }
        }
        return best;
    }

    private static void notifyNear(World world, Store<EntityStore> store, Vector3d at, Message message, NotificationStyle style) {
        List<PlayerRef> near = new ArrayList<>();
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> ref = p.getReference();
            TransformComponent t = ref == null || !ref.isValid() ? null : store.getComponent(ref, TransformComponent.getComponentType());
            if (t != null && t.getPosition().distanceSquared(at) <= 48.0 * 48.0) {
                near.add(p);
            }
        }
        for (PlayerRef p : near) {
            NotificationUtil.sendNotification(p.getPacketHandler(), message, style);
        }
    }

    /** Part de vie restante (0..1) ; 1 si l'entité n'a pas de vie. */
    public static float healthFraction(Store<EntityStore> store, Ref<EntityStore> ref) {
        EntityStatMap stats = ref == null || !ref.isValid() ? null : store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        return health == null ? 1f : health.get() / Math.max(1f, health.getMax());
    }

    /** Met la vie à `fraction` de son max (un chef réapparu reprend où il en était ; jamais plus qu'avant). */
    public static void setHealthFraction(Store<EntityStore> store, Ref<EntityStore> ref, float fraction) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.max(1f, health.getMax() * Math.min(1f, fraction)));
        }
    }

    /** Vrai si un chef est en pleine course (le système avance alors à chaque image). */
    private static boolean charging() {
        synchronized (FIGHTS) {
            for (Fight f : FIGHTS.values()) {
                if (f.charge != null) {
                    return true;
                }
            }
        }
        return false;
    }

    public static void clearAll() {
        FIGHTS.clear();
    }
}
