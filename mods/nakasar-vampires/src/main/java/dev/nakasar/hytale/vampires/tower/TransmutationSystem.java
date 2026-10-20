package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.builtin.triggervolumes.TriggerVolumesPlugin;
import com.hypixel.hytale.builtin.triggervolumes.manager.TriggerVolumeManager;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Combat du golem de cristal, dans la Salle des Transmutations ronde de la Tour de l'Alchimiste (Kevin, 19 octobre
 * 2026 ; revu le 20 octobre pour la lisibilité).
 *
 * <p>La salle a quatre quadrants élémentaires ({@link TowerLayout#TRANS_QUADRANTS} : terre, air, glace, feu), chacun un
 * volume ({@code Trans_<élément>}, tools/alchemist_traps.py, Traps.transmutation) dont ce système pose les étiquettes :
 * <ul>
 *   <li>dès que le golem est engagé, trois quadrants sont actifs ({@code State = Active} : effet au sol de l'élément,
 *   dégâts et effet) et le quatrième calme ({@code State = Off} : sol nu, rien) ;</li>
 *   <li><b>chutes annoncées</b>, chacune sous un petit cercle rouge de son rayon, {@value #FALL_WARN} s avant l'impact
 *   (éclair, boule de feu, pic de pierre, congère, selon le quadrant) : dans les zones calmes, une chute vise un joueur
 *   présent, tiré au hasard, toutes les {@value #CALM_FALL_SECONDS} s ; dans chaque zone active, une chute tombe au
 *   hasard toutes les {@value #ACTIVE_FALL_SECONDS} s, jamais sur un cercle déjà annoncé ;</li>
 *   <li><b>rotation</b> toutes les {@value #CYCLE_SECONDS} s, dans un sens tiré à l'engagement : {@value #WARN_SECONDS} s
 *   avant, le quadrant suivant se calme tout de suite, et un cône rouge se charge du centre vers le mur sur l'ancien
 *   quadrant calme ({@link TowerFx.Sweep}) ; plein, il redevient actif ;</li>
 *   <li><b>esprits</b> : chaque quadrant qui devient actif pendant le combat fait sortir un esprit de son élément
 *   ({@link TowerLayout#TRANS_SPIRITS}), au plus {@value #SPIRIT_MAX} en vie à la fois ; aucun à l'engagement, puisque ceux de la remise à zéro sont déjà
 *   là ;</li>
 *   <li>{@code Fx} est rejoué toutes les {@value #PULSE_SECONDS} s sur les quadrants actifs pour leurs particules ;</li>
 *   <li><b>remise à zéro</b> (plus aucun joueur dans la salle pendant {@value #RESET_SECONDS} s) : le golem regagne
 *   toute sa vie, les quadrants s'éteignent, tous les esprits disparaissent puis un esprit apparaît dans chaque
 *   quadrant, comme au chargement de l'instance ;</li>
 *   <li>mort du golem : les quadrants s'éteignent, les esprits disparaissent et le sceau du pied de l'hélice se dissout
 *   ({@code Trans_Seal Golem = On}).</li>
 * </ul>
 */
public final class TransmutationSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Crystal_Golem";
    static final float CYCLE_SECONDS = 16f;
    /** Charge du cône avant qu'un quadrant calme ne redevienne actif. */
    static final float WARN_SECONDS = 5f;
    /** = alchemist_traps.TRANS_PULSE (durée des particules au sol). */
    static final float PULSE_SECONDS = 3f;
    static final float RESET_SECONDS = 8f;
    static final float FALL_WARN = 1.5f;
    /** Au plus autant d'esprits en vie à la fois (Kevin, 20 octobre) : un groupe qui les ignore n'en accumule pas sans fin. */
    static final int SPIRIT_MAX = 20;
    static final float CALM_FALL_SECONDS = 2f;
    static final float ACTIVE_FALL_SECONDS = 1f;
    private static final float INTERVAL = 0.25f;
    private static final double ARENA_MARGIN = 1;
    /** Hauteur de la salle au-dessus du sol, pour savoir qui est dedans. */
    private static final double ROOM_HEIGHT = 16;
    /** Les chutes au hasard tombent entre ces rayons (le golem au centre, le mur au bord). */
    private static final double FALL_MIN_RADIUS = 3;
    private static final double FALL_WALL_MARGIN = 1.5;

    private static final String ACTIVE = "Active";
    private static final String OFF = "Off";

    /** Chute de chaque quadrant, dans l'ordre de {@link TowerLayout#TRANS_QUADRANTS} : rayon, part de la vie max, cause,
     * effet (et sa durée), projection vers le haut, particules et son de l'impact. */
    private enum Fall {
        EARTH(1.5, 0.14f, "Physical", null, 0f, 9.0, new String[]{"Block_Break_Dust", "Smoke_Floor"}, "SFX_Crystal_Break"),
        AIR(1.5, 0.15f, "Physical", "Hazard_Electric_Stun", 1f, 0, new String[]{"Lightning", "Goblin_Decorative_Lightning"},
                "SFX_Emit_Dungeon_Goblin_Void_Thunder"),
        ICE(2.0, 0.10f, "Physical", "Slow", 3f, 0, new String[]{"Ability_Ice_Explosion", "Ice_Blast"}, "SFX_Ice_Break"),
        FIRE(2.0, 0.12f, "Fire", "Burn", 3f, 0, new String[]{"Fire_AoE"}, "SFX_Emit_Goblin_Flame_Quadrant_Blast");

        final double radius;
        final float damage;
        final String cause;
        final String effect;
        final float effectSeconds;
        final double launch;
        final String[] particles;
        final String sound;

        Fall(double radius, float damage, String cause, String effect, float effectSeconds, double launch,
             String[] particles, String sound) {
            this.radius = radius;
            this.damage = damage;
            this.cause = cause;
            this.effect = effect;
            this.effectSeconds = effectSeconds;
            this.launch = launch;
            this.particles = particles;
            this.sound = sound;
        }
    }

    /** Chute annoncée : frappe à {@code hit}. */
    private record Strike(Vector3d at, Fall fall, long hit) {
    }

    /** État du combat par golem (le monde de l'instance n'en a qu'un). */
    private static final class Fight {
        boolean started;
        /** Esprits de repos (un par quadrant) posés. */
        boolean guarded;
        /** Sens de la rotation (+1 ou -1 dans l'ordre des quadrants). */
        int turn = 1;
        /** Quadrant calme ; `next` se calme WARN_SECONDS avant le changement (-1 sinon). */
        int calm = -1;
        int next = -1;
        long switchAt;
        long nextPulse;
        long nextCalmFall;
        long nextActiveFall;
        TowerFx.Sweep cone;
        final List<Strike> strikes = new ArrayList<>();
        float absent;
        boolean sealed;
        final List<Ref<EntityStore>> spirits = new ArrayList<>();
    }

    private static final Map<Ref<EntityStore>, Fight> FIGHTS = new ConcurrentHashMap<>();

    /** Système partagé par les mondes, chacun sur son thread : un compte à rebours par monde. */
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
        // Le store est en plein traitement : on regarde et on agit juste après.
        world.execute(() -> step(world, INTERVAL));
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Ref<EntityStore>> golems = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())) {
                    golems.add(chunk.getReferenceTo(i));
                }
            }
        });
        // Golem disparu du monde (chunk déchargé) : on retire ses esprits.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            removeSpirits(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> golem : golems) {
            update(world, store, golem, FIGHTS.computeIfAbsent(golem, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> golem, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        if (volumes == null) {
            return;
        }
        if (!alive(golem, store)) {
            if (!fight.sealed) {
                fight.sealed = true;
                stop(volumes, fight, store);
                setTag(volumes, TowerLayout.TRANS_SEAL, "Golem", "On");
            }
            return;
        }
        int count = TowerLayout.TRANS_ZONES.length;
        // Au chargement de l'instance et après une remise à zéro : un esprit attend dans chaque quadrant.
        if (!fight.guarded) {
            fight.guarded = true;
            for (int i = 0; i < count; i++) {
                spawnSpirit(store, fight, i);
            }
        }
        fight.spirits.removeIf(spirit -> !alive(spirit, store));
        keepSpiritsInRoom(store, fight);

        EntityStatMap stats = store.getComponent(golem, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        boolean engaged = fight.started || isEngaged(golem, store, health);
        boolean present = playerInRoom(world, store);
        // Remise à zéro : groupe mort ou sorti de la salle.
        if (engaged && !present) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                stop(volumes, fight, store);
                if (stats != null) {
                    stats.maximizeStatValue(DefaultEntityStatTypes.getHealth());
                }
                FIGHTS.put(golem, new Fight());
            }
            return;
        }
        fight.absent = 0f;
        if (!engaged) {
            return;
        }
        if (!fight.started) {
            // Éveil : un quadrant calme au hasard, les trois autres actifs, sans nouvel esprit.
            fight.started = true;
            ThreadLocalRandom random = ThreadLocalRandom.current();
            fight.calm = random.nextInt(count);
            fight.turn = random.nextBoolean() ? 1 : -1;
            for (int i = 0; i < count; i++) {
                setTag(volumes, TowerLayout.TRANS_ZONES[i], "State", i == fight.calm ? OFF : ACTIVE);
            }
            fight.switchAt = now + seconds(CYCLE_SECONDS);
            fight.nextPulse = now;
            fight.nextCalmFall = now + seconds(CALM_FALL_SECONDS);
            fight.nextActiveFall = now + seconds(ACTIVE_FALL_SECONDS);
        }

        // Annonce : le quadrant suivant se calme tout de suite, un cône se charge sur le quadrant calme.
        if (fight.next < 0 && now >= fight.switchAt - seconds(WARN_SECONDS)) {
            fight.next = Math.floorMod(fight.calm + fight.turn, count);
            setTag(volumes, TowerLayout.TRANS_ZONES[fight.next], "State", OFF);
            fight.cone = quadrantCone(fight.calm, now);
            TowerFx.sound(store, "SFX_Gobliterator_Arena_Door_Warning", TowerLayout.TRANS_CENTER);
        }
        if (fight.cone != null && fight.cone.step(store, now)) {
            fight.cone = null;
        }
        if (now >= fight.switchAt) {
            int woken = fight.calm;
            fight.calm = fight.next;
            fight.next = -1;
            fight.cone = null;
            fight.switchAt = now + seconds(CYCLE_SECONDS);
            setTag(volumes, TowerLayout.TRANS_ZONES[woken], "State", ACTIVE);
            pulse(volumes, woken);
            if (fight.spirits.size() < SPIRIT_MAX) {
                spawnSpirit(store, fight, woken);
            }
        }
        if (now >= fight.nextPulse) {
            fight.nextPulse = now + seconds(PULSE_SECONDS);
            for (int i = 0; i < count; i++) {
                if (isActive(fight, i)) {
                    pulse(volumes, i);
                }
            }
        }
        falls(world, store, fight, now);
    }

    /** Quart de disque du quadrant `zone`, du centre au mur, chargé en WARN_SECONDS. */
    private static TowerFx.Sweep quadrantCone(int zone, long now) {
        int[] signs = TowerLayout.TRANS_SIGNS[zone];
        double from = Math.atan2(0, signs[0]);
        double to = Math.atan2(signs[1], 0);
        double span = Math.IEEEremainder(to - from, Math.PI * 2);
        double start = span >= 0 ? from : to;
        return new TowerFx.Sweep(TowerLayout.TRANS_CENTER, start, Math.abs(span), 0, TowerLayout.TRANS_ARENA_RADIUS, now,
                WARN_SECONDS);
    }

    private static boolean isActive(Fight fight, int zone) {
        return fight.started && zone != fight.calm && zone != fight.next;
    }

    // --- chutes annoncées ------------------------------------------------------------------------------------------

    private static void falls(World world, Store<EntityStore> store, Fight fight, long now) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        Fall[] kinds = Fall.values();
        if (now >= fight.nextCalmFall) {
            fight.nextCalmFall = now + seconds(CALM_FALL_SECONDS);
            // Un joueur des zones calmes, tiré au hasard, sous l'élément du quadrant où il se tient.
            List<Pair<Vector3d, Integer>> calm = new ArrayList<>();
            for (Ref<EntityStore> player : playersInRoom(world, store)) {
                Vector3d at = new Vector3d(TowerFx.position(store, player));
                at.y = TowerLayout.TRANS_CENTER.y();
                int zone = zoneOf(at);
                if (!isActive(fight, zone)) {
                    calm.add(Pair.of(at, zone));
                }
            }
            if (!calm.isEmpty()) {
                Pair<Vector3d, Integer> target = calm.get(random.nextInt(calm.size()));
                announce(store, fight, target.first(), kinds[target.second()], now);
            }
        }
        if (now >= fight.nextActiveFall) {
            fight.nextActiveFall = now + seconds(ACTIVE_FALL_SECONDS);
            for (int zone = 0; zone < kinds.length; zone++) {
                if (!isActive(fight, zone)) {
                    continue;
                }
                Vector3d at = freeSpot(fight, zone, kinds[zone]);
                if (at != null) {
                    announce(store, fight, at, kinds[zone], now);
                }
            }
        }
        fight.strikes.removeIf(strike -> {
            if (now < strike.hit()) {
                return false;
            }
            Fall fall = strike.fall();
            for (String particle : fall.particles) {
                TowerFx.particle(store, particle, new Vector3d(strike.at()).add(0, 0.3, 0), (float) (fall.radius / 1.5));
            }
            TowerFx.sound(store, fall.sound, strike.at());
            for (Ref<EntityStore> player : TowerFx.playersIn(world, store, strike.at(), fall.radius)) {
                TowerFx.damage(store, player, fall.cause, fall.damage, "Nakasar_Crystal_Golem");
                if (fall.effect != null) {
                    TowerFx.effect(store, player, fall.effect, fall.effectSeconds);
                }
                if (fall.launch > 0) {
                    TowerFx.launch(store, player, fall.launch);
                }
            }
            return true;
        });
    }

    private static void announce(Store<EntityStore> store, Fight fight, Vector3d at, Fall fall, long now) {
        TowerFx.circle(store, at, fall.radius, FALL_WARN);
        fight.strikes.add(new Strike(new Vector3d(at), fall, now + seconds(FALL_WARN)));
    }

    /** Point au hasard du quadrant, loin de toute chute déjà annoncée (null si on n'en trouve pas). */
    private static Vector3d freeSpot(Fight fight, int zone, Fall fall) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int[] signs = TowerLayout.TRANS_SIGNS[zone];
        Vector3d center = TowerLayout.TRANS_CENTER;
        double outer = TowerLayout.TRANS_ARENA_RADIUS - FALL_WALL_MARGIN - fall.radius;
        for (int attempt = 0; attempt < 10; attempt++) {
            // Tirage uniforme sur la surface du quart d'anneau.
            double r = Math.sqrt(random.nextDouble(FALL_MIN_RADIUS * FALL_MIN_RADIUS, outer * outer));
            double a = random.nextDouble(Math.PI / 2);
            Vector3d at = new Vector3d(center.x() + signs[0] * r * Math.cos(a), center.y(), center.z() + signs[1] * r * Math.sin(a));
            boolean free = true;
            for (Strike strike : fight.strikes) {
                if (TowerFx.horizontal(at, strike.at()) < fall.radius + strike.fall().radius + 0.5) {
                    free = false;
                    break;
                }
            }
            if (free) {
                return at;
            }
        }
        return null;
    }

    /** Quadrant (index de TRANS_QUADRANTS) qui contient la position. */
    private static int zoneOf(Vector3d p) {
        int sx = p.x() >= TowerLayout.TRANS_CENTER.x() ? 1 : -1;
        int sz = p.z() >= TowerLayout.TRANS_CENTER.z() ? 1 : -1;
        for (int i = 0; i < TowerLayout.TRANS_SIGNS.length; i++) {
            if (TowerLayout.TRANS_SIGNS[i][0] == sx && TowerLayout.TRANS_SIGNS[i][1] == sz) {
                return i;
            }
        }
        return 0;
    }

    /** Rejoue l'effet au sol d'un quadrant actif : Fx repasse par None pour que le volume voie une nouvelle étiquette. */
    private static void pulse(TriggerVolumeManager volumes, int zone) {
        setTag(volumes, TowerLayout.TRANS_ZONES[zone], "Fx", "None");
        setTag(volumes, TowerLayout.TRANS_ZONES[zone], "Fx", ACTIVE);
    }

    /** Quadrants éteints, chutes et cône oubliés, esprits retirés. */
    private static void stop(TriggerVolumeManager volumes, Fight fight, Store<EntityStore> store) {
        for (String zone : TowerLayout.TRANS_ZONES) {
            setTag(volumes, zone, "State", OFF);
            setTag(volumes, zone, "Fx", "None");
        }
        fight.strikes.clear();
        fight.cone = null;
        removeSpirits(fight, store);
    }

    private static void spawnSpirit(Store<EntityStore> store, Fight fight, int zone) {
        Vector3d[] spots = TowerLayout.TRANS_SPIRIT_SPOTS[zone];
        Vector3d at = new Vector3d(spots[ThreadLocalRandom.current().nextInt(spots.length)]);
        String role = TowerLayout.TRANS_SPIRITS[zone];
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f());
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Golem de cristal : impossible de faire apparaître '%s'", role);
            return;
        }
        Ref<EntityStore> spirit = spawned.first();
        // Jamais sauvegardé : le combat repose tout au rechargement de l'instance.
        store.ensureAndGetComponent(spirit, EntityStore.REGISTRY.getNonSerializedComponentType());
        NPCEntity npc = store.getComponent(spirit, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(at);
        }
        fight.spirits.add(spirit);
    }

    /** Un esprit qui est passé sous le sol de la salle (ou sorti par le haut de l'hélice) revient à son quadrant. */
    private static void keepSpiritsInRoom(Store<EntityStore> store, Fight fight) {
        Vector3d center = TowerLayout.TRANS_CENTER;
        for (Ref<EntityStore> spirit : fight.spirits) {
            TransformComponent transform = store.getComponent(spirit, TransformComponent.getComponentType());
            if (transform == null || store.getComponent(spirit, Teleport.getComponentType()) != null) {
                continue;
            }
            Vector3d position = transform.getPosition();
            if (position.y() >= center.y() - 0.5 && horizontal(position, center) <= TowerLayout.TRANS_ARENA_RADIUS + 1) {
                continue;
            }
            NPCEntity npc = store.getComponent(spirit, NPCEntity.getComponentType());
            Vector3d leash = npc == null ? null : npc.getLeashPoint();
            if (leash != null) {
                store.putComponent(spirit, Teleport.getComponentType(), new Teleport(new Vector3d(leash), new Rotation3f()));
            }
        }
    }

    private static void removeSpirits(Fight fight, Store<EntityStore> store) {
        for (Ref<EntityStore> spirit : fight.spirits) {
            if (spirit.isValid()) {
                store.removeEntity(spirit, RemoveReason.REMOVE);
            }
        }
        fight.spirits.clear();
    }

    private static void setTag(TriggerVolumeManager volumes, String volume, String key, String value) {
        volumes.setTag(volume, key, value, null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
    }

    private static boolean playerInRoom(World world, Store<EntityStore> store) {
        return !playersInRoom(world, store).isEmpty();
    }

    private static List<Ref<EntityStore>> playersInRoom(World world, Store<EntityStore> store) {
        Vector3d center = TowerLayout.TRANS_CENTER;
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            Vector3d position = transform.getPosition();
            double dy = position.y() - center.y();
            if (horizontal(position, center) <= TowerLayout.TRANS_ARENA_RADIUS + ARENA_MARGIN && dy > -2 && dy < ROOM_HEIGHT) {
                out.add(ref);
            }
        }
        return out;
    }

    private static double horizontal(Vector3d a, Vector3d b) {
        double dx = a.x() - b.x();
        double dz = a.z() - b.z();
        return Math.sqrt(dx * dx + dz * dz);
    }

    private static boolean isEngaged(Ref<EntityStore> ref, Store<EntityStore> store, EntityStatValue health) {
        StateSupport state = StateSupport.get(ref, store);
        String name = state == null ? null : state.getStateName();
        if (name != null && name.startsWith("Combat")) {
            return true;
        }
        return health != null && health.get() < health.getMax() - 0.5f;
    }

    private static boolean alive(Ref<EntityStore> ref, Store<EntityStore> store) {
        if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return false;
        }
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        return health == null || health.get() > 0f;
    }

    private static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    /** Oublie les combats en cours (arrêt du plugin). Les esprits partent avec le monde. */
    public static void clearAll() {
        FIGHTS.clear();
    }
}
