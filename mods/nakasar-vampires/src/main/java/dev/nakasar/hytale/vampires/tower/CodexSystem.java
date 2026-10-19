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
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
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
 * Combat du Codex vivant, gardien de la bibliothèque de la Tour de l'Alchimiste.
 *
 * <p>Les effets de zone (sorts, éboulements des rayonnages, sceau de la rampe) sont des volumes déclencheurs de
 * l'instance ({@code tools/alchemist_traps.py}, {@code Traps.codex}) : ce système ne fait que poser leurs tags.
 * <ul>
 *   <li><b>Chapitre</b> ({@link CodexChapterInteraction}) : un livre de chapitre (PNJ fragile, jamais sauvegardé)
 *   apparaît sur un des trois pupitres avec le sort qu'il prépare (feu, givre, pluie de livres ; jamais deux fois le
 *   même de suite). Livre détruit avant la fin de l'incantation : le Codex est gelé et étourdi
 *   ({@value #STUN_EFFECT}, il subit plus de dégâts) pendant {@value #STUN_SECONDS} s. Sinon le livre disparaît et le
 *   volume du sort reçoit {@code Cast = On} : il annonce sa zone au sol puis frappe.</li>
 *   <li><b>Effondrement</b> : sous la moitié de sa vie, un rayonnage (volume {@code Codex_Collapse_i}, dans un ordre
 *   aléatoire) s'écroule toutes les {@value #COLLAPSE_INTERVAL} s ; ses zones sont annoncées avant de se remplir de
 *   gravats.</li>
 *   <li><b>Remise à zéro</b> : plus aucun joueur dans l'arène pendant {@value #RESET_SECONDS} s alors que le Codex est
 *   engagé (groupe mort ou parti) : gravats retirés ({@code Codex_Arena Reset = On}), livre retiré, vie pleine.</li>
 *   <li><b>Mort</b> : le sceau de la rampe vers l'étage de la transmutation s'ouvre ({@code Codex_Seal Codex = On}).</li>
 * </ul>
 */
public final class CodexSystem extends TickingSystem<EntityStore> {

    public static final String ROLE = "Nakasar_Living_Codex";
    static final String CHAPTER_ROLE = "Nakasar_Codex_Chapter_";
    static final String STUN_EFFECT = "Nakasar_Codex_Stunned";
    static final float STUN_SECONDS = 6f;
    static final float COLLAPSE_INTERVAL = 14f;
    static final float RESET_SECONDS = 8f;
    private static final float INTERVAL = 0.25f;
    /** Marge autour du mur de l'arène (rayon intérieur de la rotonde) où un joueur compte encore comme présent. */
    private static final double ARENA_MARGIN = 4;
    private static final double ARENA_HEIGHT = 14;

    private static final String SOUND_CHARGE = "SFX_Skeleton_Mage_Spellbook_Charge";
    private static final String SOUND_IMPACT = "SFX_Skeleton_Mage_Spellbook_Impact";
    private static final String PARTICLE_STUN = "Stunned";

    enum Spell {
        FIRE("Fire"), FROST("Frost"), RAIN("Rain");

        final String suffix;

        Spell(String suffix) {
            this.suffix = suffix;
        }
    }

    /** Livre de chapitre en cours. */
    private record Chapter(Ref<EntityStore> book, Spell spell, int lectern, long deadline) {
    }

    /** État du combat par Codex (le monde de l'instance n'en a qu'un). */
    private static final class Fight {
        Chapter chapter;
        Spell last;
        long stunnedUntil;
        boolean frozenByUs;
        long nextCollapse;
        List<Integer> collapseOrder;
        float absent;
        boolean sealed;
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

    /** Ouvre un chapitre (appelé par {@link CodexChapterInteraction}, sur le thread du monde). */
    static void openChapter(World world, Ref<EntityStore> codex, float castTime) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (!alive(codex, store) || !TowerFallSystem.isTower(store)) {
            return;
        }
        Fight fight = FIGHTS.computeIfAbsent(codex, ref -> new Fight());
        long now = System.nanoTime();
        if (fight.chapter != null || now < fight.stunnedUntil) {
            return;
        }
        ThreadLocalRandom random = ThreadLocalRandom.current();
        List<Spell> spells = new ArrayList<>(List.of(Spell.values()));
        spells.remove(fight.last);
        Spell spell = spells.get(random.nextInt(spells.size()));
        int lectern = random.nextInt(TowerLayout.CODEX_LECTERNS.length);
        Vector3d top = new Vector3d(TowerLayout.CODEX_LECTERNS[lectern]).add(0, 0.6, 0);
        String role = CHAPTER_ROLE + spell.suffix;
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, top, new Rotation3f());
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Codex : impossible de faire apparaître '%s'", role);
            return;
        }
        // Jamais sauvegardé : un livre ne survit pas à un rechargement de l'instance.
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        fight.chapter = new Chapter(spawned.first(), spell, lectern, now + (long) (castTime * 1_000_000_000L));
        fight.last = spell;
        sound(SOUND_CHARGE, top, store);
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        List<Ref<EntityStore>> codexes = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> buffer) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (npc != null && ROLE.equals(npc.getRoleName())) {
                    codexes.add(chunk.getReferenceTo(i));
                }
            }
        });
        // Codex disparus du monde (chunk déchargé) : on retire leur livre.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            removeBook(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> codex : codexes) {
            update(world, store, codex, FIGHTS.computeIfAbsent(codex, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> codex, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        if (!alive(codex, store)) {
            removeBook(fight, store);
            if (!fight.sealed && volumes != null) {
                fight.sealed = true;
                volumes.setTag(TowerLayout.CODEX_SEAL, "Codex", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
            }
            return;
        }

        // Fin de l'étourdissement.
        if (fight.frozenByUs && now >= fight.stunnedUntil) {
            fight.frozenByUs = false;
            store.tryRemoveComponent(codex, Frozen.getComponentType());
        }

        // Chapitre en cours : interrompu (livre détruit) ou sort lancé (incantation terminée).
        Chapter chapter = fight.chapter;
        if (chapter != null) {
            if (!alive(chapter.book(), store)) {
                fight.chapter = null;
                stun(store, codex, fight, now);
            } else if (now >= chapter.deadline()) {
                fight.chapter = null;
                store.removeEntity(chapter.book(), RemoveReason.REMOVE);
                if (volumes != null) {
                    volumes.setTag(spellVolume(chapter), "Cast", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
                }
            }
        }

        EntityStatMap stats = store.getComponent(codex, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        boolean engaged = isEngaged(codex, store, health);

        // Remise à zéro : groupe mort ou sorti de l'arène.
        if (engaged && !playerInArena(world, store)) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                reset(store, codex, fight, stats, volumes);
            }
            return;
        }
        fight.absent = 0f;

        // Effondrement des rayonnages sous la moitié de la vie.
        if (engaged && health != null && health.get() < health.getMax() * 0.5f && volumes != null) {
            if (fight.collapseOrder == null) {
                fight.collapseOrder = new ArrayList<>();
                for (int i = 0; i < TowerLayout.CODEX_COLLAPSE.length; i++) {
                    fight.collapseOrder.add(i);
                }
                Collections.shuffle(fight.collapseOrder, ThreadLocalRandom.current());
                fight.nextCollapse = now;
            }
            if (!fight.collapseOrder.isEmpty() && now >= fight.nextCollapse) {
                int sector = fight.collapseOrder.removeFirst();
                volumes.setTag(TowerLayout.CODEX_COLLAPSE[sector], "Collapse", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
                fight.nextCollapse = now + (long) (COLLAPSE_INTERVAL * 1_000_000_000L);
            }
        }
    }

    private static String spellVolume(Chapter chapter) {
        return switch (chapter.spell()) {
            case FIRE -> TowerLayout.CODEX_FIRE;
            case RAIN -> TowerLayout.CODEX_RAIN;
            case FROST -> TowerLayout.CODEX_FROST[chapter.lectern()];
        };
    }

    /** Livre détruit à temps : gel de l'IA et effet d'étourdissement (dégâts subis augmentés). */
    private static void stun(Store<EntityStore> store, Ref<EntityStore> codex, Fight fight, long now) {
        fight.stunnedUntil = now + (long) (STUN_SECONDS * 1_000_000_000L);
        if (store.getComponent(codex, Frozen.getComponentType()) == null) {
            store.ensureAndGetComponent(codex, Frozen.getComponentType());
            fight.frozenByUs = true;
        }
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(STUN_EFFECT);
        EffectControllerComponent effects = store.getComponent(codex, EffectControllerComponent.getComponentType());
        if (effect != null && effects != null) {
            effects.addEffect(codex, effect, STUN_SECONDS, OverlapBehavior.OVERWRITE, store);
        }
        TransformComponent transform = store.getComponent(codex, TransformComponent.getComponentType());
        if (transform != null) {
            Vector3d position = new Vector3d(transform.getPosition()).add(0, 2.6, 0);
            sound(SOUND_IMPACT, position, store);
            ParticleUtil.spawnParticleEffect(PARTICLE_STUN, position, 0f, 0f, 0f, 1.5f, STUN_SECONDS, store);
        }
    }

    private static void reset(Store<EntityStore> store, Ref<EntityStore> codex, Fight fight, EntityStatMap stats,
                              TriggerVolumeManager volumes) {
        removeBook(fight, store);
        if (fight.frozenByUs) {
            store.tryRemoveComponent(codex, Frozen.getComponentType());
        }
        if (stats != null) {
            stats.maximizeStatValue(DefaultEntityStatTypes.getHealth());
        }
        if (volumes != null) {
            volumes.setTag(TowerLayout.CODEX_ARENA, "Reset", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
        }
        Fight fresh = new Fight();
        fresh.sealed = fight.sealed;
        FIGHTS.put(codex, fresh);
    }

    private static void removeBook(Fight fight, Store<EntityStore> store) {
        Chapter chapter = fight.chapter;
        fight.chapter = null;
        if (chapter != null && chapter.book().isValid()) {
            store.removeEntity(chapter.book(), RemoveReason.REMOVE);
        }
    }

    private static boolean playerInArena(World world, Store<EntityStore> store) {
        Vector3d center = TowerLayout.CODEX_CENTER;
        double radius = TowerLayout.CODEX_ARENA_RADIUS + ARENA_MARGIN;
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
            double dx = position.x() - center.x();
            double dz = position.z() - center.z();
            double dy = position.y() - center.y();
            if (dx * dx + dz * dz <= radius * radius && dy > -2 && dy < ARENA_HEIGHT) {
                return true;
            }
        }
        return false;
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

    /** Oublie les combats en cours (arrêt du plugin). Les livres partent avec le monde. */
    public static void clearAll() {
        FIGHTS.clear();
    }
}
