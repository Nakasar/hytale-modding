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
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
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
 * Combat de la Chimère du laboratoire, second mini-boss de la Tour de l'Alchimiste : un dragon qui ne vole pas.
 *
 * <p>Ses coups (morsure, coup de griffes, fauchage de la queue) sont dans son rôle ; ce système mène le reste :
 * <ul>
 *   <li><b>Porteurs d'acide</b> : toutes les {@value #CARRIER_INTERVAL} s de combat ({@value #CARRIER_INTERVAL_HURT} s
 *   sous la moitié de sa vie), un zombie ({@value #CARRIER_ROLE}, seau à la main) sort à côté d'un des bassins
 *   secondaires ({@link TowerLayout#CHIMERA_FILLS}), y remplit son seau pendant {@value #FILL_SECONDS} s (il ne bouge
 *   pas), puis marche jusqu'à la margelle de la cuve centrale et y verse l'acide : la Chimère regagne
 *   {@value #CARRIER_HEAL} de sa vie. Un porteur tué avant de verser ne soigne rien. Au plus {@value #CARRIER_MAX}
 *   porteurs à la fois. Un seau plein luit en vert ; au versement, la cuve bouillonne et la Chimère s'éclaire pendant
 *   le soin.</li>
 *   <li><b>Seau renversé</b> : un porteur tué avec un seau plein laisse une flaque d'acide (rayon
 *   {@value #PUDDLE_RADIUS}, {@value #PUDDLE_SECONDS} s) : la Chimère y regagne {@value #PUDDLE_HEAL} de sa vie par
 *   seconde, les joueurs y perdent {@value #PUDDLE_DAMAGE} de la leur et sont empoisonnés.</li>
 *   <li><b>Acide ciblé</b> : toutes les {@value #ACID_INTERVAL} s, un jet d'acide jaillit sous chaque joueur, annoncé
 *   par un petit cercle rouge {@value #ACID_WARN} s avant l'impact (Kevin, 20 octobre 2026).</li>
 *   <li><b>Groupe</b> : à l'engagement, sa vie est adaptée au nombre de joueurs dans le laboratoire
 *   ({@link GroupHealth}).</li>
 *   <li><b>Remise à zéro</b> : plus aucun joueur dans le laboratoire pendant {@value #RESET_SECONDS} s alors qu'elle
 *   est engagée : elle regagne toute sa vie, les porteurs disparaissent.</li>
 *   <li><b>Mort</b> : le sceau de la porte nord se dissout ({@code Chimera_Seal Chimera = On}) ; les porteurs
 *   disparaissent.</li>
 * </ul>
 */
public final class ChimeraSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Lab_Chimera";
    static final String CARRIER_ROLE = "Nakasar_Chimera_Feeder";
    static final String HP_MODIFIER = "nakasar_chimera_group";
    static final float CARRIER_INTERVAL = 7f;
    static final float CARRIER_INTERVAL_HURT = 5f;
    static final int CARRIER_MAX = 4;
    static final float FILL_SECONDS = 2.5f;
    static final float CARRIER_HEAL = 0.05f;
    static final float ACID_INTERVAL = 10f;
    static final float ACID_WARN = 2.2f;
    static final double ACID_RADIUS = 1.9;
    private static final float ACID_DAMAGE = 0.10f;
    private static final float ACID_POISON = 4f;
    static final double PUDDLE_RADIUS = 2.5;
    static final float PUDDLE_SECONDS = 8f;
    static final float PUDDLE_HEAL = 0.01f;
    static final float PUDDLE_DAMAGE = 0.05f;
    private static final float PUDDLE_POISON = 2f;
    /** Lueur du seau plein, rejouée tant qu'il marche ; lueur de la Chimère pendant le soin. */
    private static final float GLOW_SECONDS = 0.5f;
    private static final int HEAL_GLOWS = 3;
    static final float RESET_SECONDS = 8f;
    private static final float INTERVAL = 0.25f;
    /** Un porteur verse son seau quand il touche la margelle de la cuve. */
    private static final double POUR_REACH = 3.2;
    private static final double ARENA_MARGIN = 2;
    private static final double ARENA_HEIGHT = 20;

    private static final String SOUND_SPLASH = "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts";
    private static final String PARTICLE_SPLASH = "Dungeon_Goblin_Toxic_Water";
    private static final String PARTICLE_POUR = "Impact_Poison";
    private static final String PARTICLE_STEAM = "Goblin_Decorative_Steam";
    private static final String PARTICLE_HEAL = "Effect_Health_Pack";
    private static final String PARTICLE_ACID = "Impact_Poison";
    /** tools/tower_fx.py : seau plein, flaque d'un seau renversé (1,47 bloc de rayon à l'échelle 1). */
    private static final String PARTICLE_BUCKET = "Nakasar_Bucket_Glow";
    private static final String PARTICLE_PUDDLE = "Nakasar_Acid_Puddle";

    /** Un zombie porteur : il remplit son seau au bassin `basin` jusqu'à `filledAt`, puis marche vers la cuve. */
    private static final class Carrier {
        final Ref<EntityStore> ref;
        final int basin;
        final long filledAt;
        boolean walking;
        long nextGlow;
        Vector3d last;

        Carrier(Ref<EntityStore> ref, int basin, long filledAt) {
            this.ref = ref;
            this.basin = basin;
            this.filledAt = filledAt;
        }
    }

    /** Flaque d'un seau renversé : soigne la Chimère, ronge les joueurs, une fois par seconde. */
    private static final class Puddle {
        final Vector3d at;
        final long until;
        long next;

        Puddle(Vector3d at, long now) {
            this.at = at;
            this.until = now + TowerFx.seconds(PUDDLE_SECONDS);
            this.next = now;
        }
    }

    /** Jet d'acide annoncé sous un joueur. */
    private record Jet(Vector3d at, long hit) {
    }

    /** État du combat par Chimère (le monde de l'instance n'en a qu'une). */
    private static final class Fight {
        final List<Carrier> carriers = new ArrayList<>();
        final List<Puddle> puddles = new ArrayList<>();
        final List<Jet> jets = new ArrayList<>();
        long nextCarrier;
        long nextAcid;
        /** Lueur de soin sur la Chimère : encore tant de bouffées, la suivante à `nextHealGlow`. */
        int healGlows;
        long nextHealGlow;
        float absent;
        boolean sealed;
        boolean scaled;
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
        List<Ref<EntityStore>> chimeras = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())) {
                    chimeras.add(chunk.getReferenceTo(i));
                }
            }
        });
        // Chimère disparue du monde (chunk déchargé) : on retire ses porteurs.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            removeCarriers(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> chimera : chimeras) {
            update(world, store, chimera, FIGHTS.computeIfAbsent(chimera, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        ArenaGate gate = ArenaGate.of(world, TowerLayout.CHIMERA_GATE, RESET_SECONDS, volumes);
        if (!alive(chimera, store)) {
            removeCarriers(fight, store);
            gate.finish(volumes);
            if (!fight.sealed && volumes != null) {
                fight.sealed = true;
                volumes.setTag(TowerLayout.CHIMERA_SEAL, "Chimera", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
            }
            return;
        }

        EntityStatMap stats = store.getComponent(chimera, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        boolean engaged = isEngaged(chimera, store, health);

        boolean present = playerInArena(world, store);
        gate.update(volumes, present, dt);
        // Remise à zéro : groupe mort ou sorti du laboratoire.
        if (engaged && !present) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                reset(store, chimera, fight, stats);
            }
            return;
        }
        fight.absent = 0f;
        if (!engaged) {
            return;
        }

        if (!fight.scaled) {
            fight.scaled = true;
            GroupHealth.apply(stats, HP_MODIFIER, GroupHealth.multiplier(playersInArena(world, store)));
            health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        }

        // Porteurs d'acide : un nouveau à intervalles, près d'un bassin au hasard.
        boolean hurt = health != null && health.get() < health.getMax() * 0.5f;
        if (fight.nextCarrier == 0) {
            fight.nextCarrier = now + seconds(3f);
        }
        spill(store, fight, now);
        if (now >= fight.nextCarrier) {
            fight.nextCarrier = now + seconds(hurt ? CARRIER_INTERVAL_HURT : CARRIER_INTERVAL);
            if (fight.carriers.size() < CARRIER_MAX) {
                spawnCarrier(store, fight, now);
            }
        }
        carry(store, fight, stats, health, now);
        puddles(world, store, chimera, fight, stats, now);
        healGlow(store, chimera, fight, now);

        // Acide ciblé : un jet sous chaque joueur, annoncé par un petit cercle rouge.
        if (fight.nextAcid == 0) {
            fight.nextAcid = now + seconds(ACID_INTERVAL * 0.5f);
        }
        if (now >= fight.nextAcid) {
            fight.nextAcid = now + seconds(ACID_INTERVAL);
            for (Ref<EntityStore> player : playerRefsInArena(world, store)) {
                Vector3d at = new Vector3d(TowerFx.position(store, player));
                at.y = TowerLayout.CHIMERA_VAT.y();
                TowerFx.circle(store, at, ACID_RADIUS, ACID_WARN);
                fight.jets.add(new Jet(at, now + seconds(ACID_WARN)));
            }
            TowerFx.sound(store, SOUND_SPLASH, TowerLayout.CHIMERA_VAT);
            TowerFx.particle(store, PARTICLE_SPLASH, new Vector3d(TowerLayout.CHIMERA_VAT).add(0, 0.5, 0), 2f);
        }
        fight.jets.removeIf(jet -> {
            if (now < jet.hit()) {
                return false;
            }
            TowerFx.particle(store, PARTICLE_ACID, new Vector3d(jet.at()).add(0, 0.5, 0), 1.5f);
            TowerFx.particle(store, "Effect_Poison", new Vector3d(jet.at()).add(0, 0.3, 0), 1f);
            TowerFx.sound(store, SOUND_SPLASH, jet.at());
            for (Ref<EntityStore> player : TowerFx.playersIn(world, store, jet.at(), ACID_RADIUS)) {
                TowerFx.damage(store, player, "Physical", ACID_DAMAGE, "Nakasar_Lab_Chimera");
                TowerFx.effect(store, player, "Poison_T1", ACID_POISON);
            }
            return true;
        });
    }

    /** Porteurs morts : celui qui portait un seau plein le renverse, une flaque d'acide reste où il est tombé. */
    private static void spill(Store<EntityStore> store, Fight fight, long now) {
        fight.carriers.removeIf(carrier -> {
            if (alive(carrier.ref, store)) {
                Vector3d position = TowerFx.position(store, carrier.ref);
                if (position != null) {
                    carrier.last = new Vector3d(position);
                }
                return false;
            }
            boolean full = carrier.walking || now >= carrier.filledAt;
            if (full && carrier.last != null) {
                Vector3d at = new Vector3d(carrier.last);
                at.y = TowerLayout.CHIMERA_VAT.y();
                fight.puddles.add(new Puddle(at, now));
                TowerFx.particle(store, PARTICLE_POUR, new Vector3d(at).add(0, 0.5, 0), 1.5f);
                TowerFx.sound(store, SOUND_SPLASH, at);
            }
            return true;
        });
    }

    /** Flaques : la Chimère y regagne de la vie, les joueurs y perdent de la leur, une fois par seconde. */
    private static void puddles(World world, Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight,
                                EntityStatMap stats, long now) {
        fight.puddles.removeIf(puddle -> {
            if (now >= puddle.until) {
                return true;
            }
            if (now < puddle.next) {
                return false;
            }
            puddle.next = now + seconds(1f);
            TowerFx.particle(store, PARTICLE_PUDDLE, puddle.at, (float) (PUDDLE_RADIUS / 1.47));
            for (Ref<EntityStore> player : TowerFx.playersIn(world, store, puddle.at, PUDDLE_RADIUS)) {
                TowerFx.damage(store, player, "Physical", PUDDLE_DAMAGE, "Nakasar_Lab_Chimera");
                TowerFx.effect(store, player, "Poison_T1", PUDDLE_POISON);
            }
            Vector3d self = TowerFx.position(store, chimera);
            EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
            // La Chimère est grande : on compte le bord de son corps, pas seulement son centre.
            if (self != null && health != null && TowerFx.horizontal(self, puddle.at) <= PUDDLE_RADIUS + 1.5
                    && Math.abs(self.y() - puddle.at.y()) < 3) {
                heal(stats, health, health.getMax() * PUDDLE_HEAL);
                startHealGlow(fight, now, 1);
            }
            return false;
        });
    }

    private static void startHealGlow(Fight fight, long now, int glows) {
        if (fight.healGlows < glows) {
            fight.healGlows = glows;
            fight.nextHealGlow = Math.min(fight.nextHealGlow == 0 ? now : fight.nextHealGlow, now);
        }
    }

    /** Lueur de soin sur la Chimère, quelques bouffées après chaque soin. */
    private static void healGlow(Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight, long now) {
        if (fight.healGlows <= 0 || now < fight.nextHealGlow) {
            return;
        }
        fight.healGlows--;
        fight.nextHealGlow = now + seconds(GLOW_SECONDS);
        Vector3d self = TowerFx.position(store, chimera);
        if (self != null) {
            TowerFx.particle(store, PARTICLE_HEAL, new Vector3d(self).add(0, 1.5, 0), 2.5f);
        }
    }

    /** Remplissage puis marche des porteurs ; ceux qui touchent la margelle versent leur seau et la soignent. */
    private static void carry(Store<EntityStore> store, Fight fight, EntityStatMap stats, EntityStatValue health, long now) {
        // Seuls les porteurs vivants avancent (les morts passent par `spill`).
        Vector3d vat = TowerLayout.CHIMERA_VAT;
        double reach = TowerLayout.CHIMERA_VAT_RADIUS + POUR_REACH;
        fight.carriers.removeIf(carrier -> {
            TransformComponent transform = store.getComponent(carrier.ref, TransformComponent.getComponentType());
            if (transform == null) {
                return false;
            }
            Vector3d position = transform.getPosition();
            if (!carrier.walking) {
                if (now < carrier.filledAt) {
                    return false;
                }
                // Seau plein : il se met en marche vers la cuve.
                carrier.walking = true;
                store.tryRemoveComponent(carrier.ref, Frozen.getComponentType());
                sound(SOUND_SPLASH, TowerLayout.CHIMERA_BASINS[carrier.basin], store);
            }
            if (horizontal(position, vat) <= reach) {
                if (stats != null && health != null) {
                    heal(stats, health, health.getMax() * CARRIER_HEAL);
                }
                ParticleUtil.spawnParticleEffect(PARTICLE_POUR, new Vector3d(position).add(0, 0.8, 0), 0f, 0f, 0f, 1.5f, 1f, store);
                splash(store, rim(position));
                // La cuve bouillonne, la Chimère s'éclaire pendant le soin.
                TowerFx.particle(store, PARTICLE_SPLASH, new Vector3d(TowerLayout.CHIMERA_VAT).add(0, 0.5, 0), 3f);
                TowerFx.particle(store, PARTICLE_STEAM, new Vector3d(TowerLayout.CHIMERA_VAT).add(0, 1.0, 0), 2f);
                startHealGlow(fight, now, HEAL_GLOWS);
                store.removeEntity(carrier.ref, RemoveReason.REMOVE);
                return true;
            }
            if (now >= carrier.nextGlow) {
                carrier.nextGlow = now + seconds(GLOW_SECONDS);
                TowerFx.particle(store, PARTICLE_BUCKET, new Vector3d(position).add(0, 1.1, 0), 1f);
            }
            NPCEntity npc = store.getComponent(carrier.ref, NPCEntity.getComponentType());
            if (npc != null) {
                // Le rôle du porteur va vers son point d'attache : la margelle, du côté de son bassin.
                npc.setLeashPoint(rim(position));
            }
            return false;
        });
    }

    private static void reset(Store<EntityStore> store, Ref<EntityStore> chimera, Fight fight, EntityStatMap stats) {
        removeCarriers(fight, store);
        fight.puddles.clear();
        fight.jets.clear();
        GroupHealth.clear(stats, HP_MODIFIER);
        Fight fresh = new Fight();
        fresh.sealed = fight.sealed;
        FIGHTS.put(chimera, fresh);
    }

    /** Un zombie sort à côté d'un bassin au hasard et y remplit son seau, immobile. */
    private static void spawnCarrier(Store<EntityStore> store, Fight fight, long now) {
        int basin = ThreadLocalRandom.current().nextInt(TowerLayout.CHIMERA_FILLS.length);
        Vector3d at = new Vector3d(TowerLayout.CHIMERA_FILLS[basin]);
        Vector3d pool = TowerLayout.CHIMERA_BASINS[basin];
        Ref<EntityStore> carrier = spawn(store, CARRIER_ROLE, at, facing(at, pool));
        if (carrier == null) {
            return;
        }
        store.ensureAndGetComponent(carrier, Frozen.getComponentType());
        ParticleUtil.spawnParticleEffect(PARTICLE_SPLASH, new Vector3d(pool).add(0, 0.2, 0), 0f, 0f, 0f, 1.2f, 1f, store);
        sound(SOUND_SPLASH, pool, store);
        fight.carriers.add(new Carrier(carrier, basin, now + seconds(FILL_SECONDS)));
    }

    private static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at, Rotation3f rotation) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, rotation);
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Chimère : impossible de faire apparaître '%s'", role);
            return null;
        }
        // Jamais sauvegardé : le combat repose tout au rechargement de l'instance.
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        return spawned.first();
    }

    private static void heal(EntityStatMap stats, EntityStatValue health, float amount) {
        stats.setStatValue(DefaultEntityStatTypes.getHealth(), Math.min(health.getMax(), health.get() + amount));
    }

    /** Point devant la margelle de la cuve, du côté de `from`. */
    private static Vector3d rim(Vector3d from) {
        Vector3d vat = TowerLayout.CHIMERA_VAT;
        Vector3d out = new Vector3d(from).sub(vat);
        out.y = 0;
        if (out.lengthSquared() < 1e-6) {
            out.set(1, 0, 0);
        }
        out.normalize().mul(TowerLayout.CHIMERA_VAT_RADIUS + 2.5).add(vat);
        return out;
    }

    private static Rotation3f facing(Vector3d from, Vector3d to) {
        // Même convention que SummonMinionsInteraction.facing (tourné vers `to`).
        return new Rotation3f(0f, (float) Math.atan2(to.x() - from.x(), to.z() - from.z()), 0f);
    }

    private static void splash(Store<EntityStore> store, Vector3d at) {
        ParticleUtil.spawnParticleEffect(PARTICLE_SPLASH, new Vector3d(at).add(0, 0.3, 0), 0f, 0f, 0f, 2f, 2f, store);
        sound(SOUND_SPLASH, at, store);
    }

    private static void removeCarriers(Fight fight, Store<EntityStore> store) {
        for (Carrier carrier : fight.carriers) {
            if (carrier.ref.isValid()) {
                store.removeEntity(carrier.ref, RemoveReason.REMOVE);
            }
        }
        fight.carriers.clear();
    }

    private static List<Ref<EntityStore>> playerRefsInArena(World world, Store<EntityStore> store) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d position = TowerFx.position(store, ref);
            if (position != null && alive(ref, store) && inArena(position)) {
                out.add(ref);
            }
        }
        return out;
    }

    private static int playersInArena(World world, Store<EntityStore> store) {
        int count = 0;
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform != null && inArena(transform.getPosition())) {
                count++;
            }
        }
        return count;
    }

    private static boolean playerInArena(World world, Store<EntityStore> store) {
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (!alive(ref, store)) {
                continue;
            }
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            if (transform != null && inArena(transform.getPosition())) {
                return true;
            }
        }
        return false;
    }

    private static boolean inArena(Vector3d position) {
        Vector3d vat = TowerLayout.CHIMERA_VAT;
        double radius = TowerLayout.CHIMERA_ARENA_RADIUS + ARENA_MARGIN;
        double dy = position.y() - vat.y();
        return horizontal(position, vat) <= radius && dy > -2 && dy < ARENA_HEIGHT;
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

    private static void sound(String id, Vector3d position, Store<EntityStore> store) {
        int index = SoundEvent.getAssetMap().getIndexOrDefault(id, -1);
        if (index >= 0) {
            SoundUtil.playSoundEvent3d(index, SoundCategory.SFX, position.x(), position.y(), position.z(), store);
        }
    }

    private static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    /** Oublie les combats en cours (arrêt du plugin). Les porteurs partent avec le monde. */
    public static void clearAll() {
        FIGHTS.clear();
    }
}
