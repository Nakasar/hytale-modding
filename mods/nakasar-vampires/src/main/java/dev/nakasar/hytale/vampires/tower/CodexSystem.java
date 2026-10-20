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
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
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
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.telegraph.Telegraphs;
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
 * <p>Trois phases (titre à l'écran à chaque passage) : sous {@value #PHASE_TWO} puis {@value #PHASE_THREE} de sa vie,
 * le Codex « tourne la page » : une onde annoncée par un cercle rouge de {@value #SHOCK_RADIUS} blocs part de lui.
 * <ul>
 *   <li><b>Jets d'encre</b> (toutes les phases, de plus en plus souvent, deux à la fois en dernière phase) : une ligne de
 *   cercles rouges part du Codex vers un joueur de l'arène ; l'encre éclabousse chaque cercle l'un après l'autre
 *   (dégâts, ralentissement), puis une flaque reste {@value #POOL_SECONDS} s (dégâts et ralentissement à qui s'y
 *   tient).</li>
 *   <li><b>Tourbillons de pages</b> (deuxième phase et suivante) : des tourbillons ({@value #VORTEX_ROLE}, annoncés au
 *   sol) poursuivent les joueurs et entaillent qui s'en approche ; ils se dissipent au bout de
 *   {@value #VORTEX_SECONDS} s, on peut aussi les détruire.</li>
 *   <li><b>Chapitre</b> ({@link CodexChapterInteraction}) : un livre de chapitre (PNJ fragile, jamais sauvegardé)
 *   apparaît sur un des trois pupitres avec le sort qu'il prépare (feu, givre, pluie de livres ; jamais deux fois le
 *   même de suite ; en dernière phase deux livres à la fois, sur deux pupitres, avec deux sorts différents). Le sort est
 *   tiré à l'apparition du livre et son pupitre s'allume dans sa couleur tant que le livre vit (rouge feu, bleu givre,
 *   blanc pluie de livres : tools/tower_fx.py), pour qu'on sache quoi éviter avant même l'échec. Tous les livres
 *   détruits avant la fin de l'incantation : le Codex est gelé et étourdi
 *   ({@value #STUN_EFFECT}, il subit plus de dégâts) pendant {@value #STUN_SECONDS} s. Sinon chaque livre encore debout
 *   disparaît et le volume de son sort reçoit {@code Cast = On} : il annonce sa zone au sol puis frappe.</li>
 *   <li><b>Effondrement</b> : en dernière phase, un rayonnage (volume {@code Codex_Collapse_i}, dans un ordre
 *   aléatoire) s'écroule toutes les {@value #COLLAPSE_INTERVAL} s ; un cône rouge se charge du mur vers le centre sur
 *   son pan ({@link Telegraphs.Sweep}), puis le pan se remplit de gravats.</li>
 *   <li><b>Groupe</b> : à l'engagement, sa vie est adaptée au nombre de joueurs dans l'arène ({@link GroupHealth}).</li>
 *   <li><b>Remise à zéro</b> : plus aucun joueur dans l'arène pendant {@value #RESET_SECONDS} s alors que le Codex est
 *   engagé (groupe mort ou parti) : gravats retirés ({@code Codex_Arena Reset = On}), livres, tourbillons et flaques
 *   retirés, vie de base pleine, retour à la première phase.</li>
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
    static final String HP_MODIFIER = "nakasar_codex_group";
    private static final float INTERVAL = 0.25f;
    /** Marge autour du mur de l'arène (rayon intérieur de la rotonde) où un joueur compte encore comme présent. */
    private static final double ARENA_MARGIN = 4;
    /** Marge pour la barrière de l'arène ({@link ArenaGate}) : la porte, dans l'épaisseur du mur, n'en fait pas partie. */
    private static final double GATE_MARGIN = 0.5;
    private static final double ARENA_HEIGHT = 14;

    private static final String SOUND_CHARGE = "SFX_Skeleton_Mage_Spellbook_Charge";
    private static final String SOUND_IMPACT = "SFX_Skeleton_Mage_Spellbook_Impact";
    private static final String PARTICLE_STUN = "Stunned";
    private static final String LANG = "nakasar_alchemist.trap.codex_phase";

    static final String PHASE_TWO = "70 %";
    static final String PHASE_THREE = "40 %";
    private static final float[] PHASE_HEALTH = {0.7f, 0.4f};
    /** Onde du changement de phase : rayon, annonce, part de la vie maximale. */
    static final double SHOCK_RADIUS = 8;
    private static final float SHOCK_WARN = 2.2f;
    private static final float SHOCK_DAMAGE = 0.18f;
    /** Jets d'encre : intervalle par phase, cercles de la ligne, annonce, dégâts. */
    private static final float[] INK_INTERVAL = {10f, 8f, 6.5f};
    private static final float INK_FIRST = 6f;
    private static final int INK_CIRCLES = 6;
    private static final double INK_RADIUS = 1.4;
    private static final double INK_STEP = 2.4;
    private static final float INK_WARN = 1.6f;
    /** Décalage entre deux cercles de la ligne : l'encre « court » du Codex vers la cible. */
    private static final float INK_TRAVEL = 0.1f;
    private static final float INK_DAMAGE = 0.10f;
    /** Trait sombre au sol sur tout le trajet de l'encre, une seconde avant qu'elle coure (tools/tower_fx.py). */
    private static final float INK_TRACE = 1f;
    private static final double INK_TRACE_STEP = 1.2;
    private static final float INK_TRACE_SCALE = 0.45f;
    private static final String PARTICLE_TRACE = "Nakasar_Ink_Trace";
    private static final String PARTICLE_LECTERN = "Nakasar_Lectern_";
    static final float POOL_SECONDS = 4f;
    private static final float POOL_DAMAGE = 0.03f;
    /** Tourbillons de pages : vague par phase (2 puis 3), au plus 4 en vie. */
    static final String VORTEX_ROLE = "Nakasar_Codex_Page_Vortex";
    static final float VORTEX_SECONDS = 22f;
    private static final float[] VORTEX_INTERVAL = {0f, 24f, 18f};
    private static final int[] VORTEX_WAVE = {0, 2, 3};
    private static final int VORTEX_MAX = 4;
    private static final float VORTEX_WARN = 1.5f;
    private static final double VORTEX_REACH = 1.8;
    private static final float VORTEX_DAMAGE = 0.03f;
    private static final float VORTEX_CUT = 0.5f;
    /** Cercles rouges qui se remplissent jusqu'au coup (tools/tower_warnings.py, 0,68 d'échelle par bloc de rayon). */
    private static final String WARNING_SHOCK = "Nakasar_Warning_22";
    /** Un cercle par dixième de seconde d'annonce : le cercle k de la ligne se remplit en 1,6 + 0,1 k s. */
    private static final String WARNING_INK = "Nakasar_Warning_";
    private static final String WARNING_VORTEX = "Nakasar_Warning_15";
    private static final float WARNING_SCALE = 0.68f;
    /** Encre (tools/alchemist_traps.py, ink_files) : flaque de 1,47 bloc de rayon à l'échelle 1. */
    private static final String PARTICLE_SPLASH = "Nakasar_Ink_Splash";
    private static final String PARTICLE_POOL = "Nakasar_Ink_Pool";
    private static final String PARTICLE_SHOCK = "Explosion_Medium";
    private static final String PARTICLE_VORTEX = "Block_Break_Dust";
    private static final String EFFECT_SLOW = "Slow";

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

    /** Zone annoncée au sol (onde, éclaboussure d'encre) : frappe une fois à {@code hit}, laisse parfois une flaque. */
    private record Strike(Vector3d at, double radius, long hit, float damage, String particle, float particleScale,
                          float slowSeconds, boolean pool) {
    }

    /** Flaque d'encre : ralentit et ronge qui s'y tient, une fois par seconde. */
    private static final class Pool {
        final Vector3d at;
        final long until;
        long next;

        Pool(Vector3d at, long now) {
            this.at = at;
            this.until = now + seconds(POOL_SECONDS);
            this.next = now;
        }
    }

    private static final class Vortex {
        final Ref<EntityStore> ref;
        final long until;
        long nextCut;

        Vortex(Ref<EntityStore> ref, long now) {
            this.ref = ref;
            this.until = now + seconds(VORTEX_SECONDS);
            this.nextCut = now + seconds(1f);
        }
    }

    /** Ligne d'encre annoncée par son trait : elle part à {@code start}. */
    private record InkLine(List<Vector3d> circles, long start) {
    }

    /** État du combat par Codex (le monde de l'instance n'en a qu'un). */
    private static final class Fight {
        final List<Chapter> chapters = new ArrayList<>();
        final List<InkLine> inkLines = new ArrayList<>();
        final List<Telegraphs.Sweep> cones = new ArrayList<>();
        long nextLecternGlow;
        final List<Strike> strikes = new ArrayList<>();
        final List<Pool> pools = new ArrayList<>();
        final List<Vortex> vortices = new ArrayList<>();
        /** Tourbillons annoncés au sol, pas encore apparus : position et instant d'apparition. */
        final List<Pair<Vector3d, Long>> summons = new ArrayList<>();
        int phase = 1;
        boolean started;
        long nextInk;
        long nextVortex;
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
        if (!fight.chapters.isEmpty() || now < fight.stunnedUntil) {
            return;
        }
        ThreadLocalRandom random = ThreadLocalRandom.current();
        List<Spell> spells = new ArrayList<>(List.of(Spell.values()));
        spells.remove(fight.last);
        Collections.shuffle(spells, random);
        List<Integer> lecterns = new ArrayList<>();
        for (int i = 0; i < TowerLayout.CODEX_LECTERNS.length; i++) {
            lecterns.add(i);
        }
        Collections.shuffle(lecterns, random);
        // Dernière phase : deux livres, deux sorts différents (jamais le dernier sort en premier).
        int count = Math.min(fight.phase >= 3 ? 2 : 1, Math.min(lecterns.size(), Spell.values().length));
        if (count > spells.size()) {
            spells.add(fight.last);
        }
        long deadline = now + seconds(castTime);
        for (int i = 0; i < count; i++) {
            Spell spell = spells.get(i);
            int lectern = lecterns.get(i);
            Vector3d top = new Vector3d(TowerLayout.CODEX_LECTERNS[lectern]).add(0, 0.6, 0);
            Ref<EntityStore> book = spawn(store, CHAPTER_ROLE + spell.suffix, top);
            if (book == null) {
                continue;
            }
            fight.chapters.add(new Chapter(book, spell, lectern, deadline));
            fight.last = spell;
            sound(SOUND_CHARGE, top, store);
        }
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
        // Codex disparus du monde (chunk déchargé) : on retire leurs livres et leurs tourbillons.
        FIGHTS.entrySet().removeIf(entry -> {
            if (entry.getKey().isValid()) {
                return false;
            }
            clear(entry.getValue(), store);
            return true;
        });
        long now = System.nanoTime();
        for (Ref<EntityStore> codex : codexes) {
            update(world, store, codex, FIGHTS.computeIfAbsent(codex, ref -> new Fight()), now, dt);
        }
    }

    private static void update(World world, Store<EntityStore> store, Ref<EntityStore> codex, Fight fight, long now, float dt) {
        TriggerVolumeManager volumes = store.getResource(TriggerVolumesPlugin.get().getManagerResourceType());
        ArenaGate gate = ArenaGate.of(world, TowerLayout.CODEX_GATE, RESET_SECONDS, volumes);
        if (!alive(codex, store)) {
            clear(fight, store);
            gate.finish(volumes);
            if (!fight.sealed && volumes != null) {
                fight.sealed = true;
                volumes.setTag(TowerLayout.CODEX_SEAL, "Codex", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
            }
            return;
        }
        // Barrière de la porte : seulement qui a passé le mur, pas qui attend sur le palier de la rampe.
        gate.update(volumes, playerInArena(world, store, GATE_MARGIN), dt);

        // Fin de l'étourdissement.
        if (fight.frozenByUs && now >= fight.stunnedUntil) {
            fight.frozenByUs = false;
            store.tryRemoveComponent(codex, Frozen.getComponentType());
        }

        // Pupitres des livres encore debout : allumés dans la couleur de leur sort.
        if (!fight.chapters.isEmpty() && now >= fight.nextLecternGlow) {
            fight.nextLecternGlow = now + seconds(1f);
            for (Chapter chapter : fight.chapters) {
                if (alive(chapter.book(), store)) {
                    Vector3d top = new Vector3d(TowerLayout.CODEX_LECTERNS[chapter.lectern()]).add(0, 0.2, 0);
                    ParticleUtil.spawnParticleEffect(PARTICLE_LECTERN + chapter.spell().suffix, top, 0f, 0f, 0f, 1f, 1f, store);
                }
            }
        }
        // Chapitres en cours : tous interrompus (livres détruits) ou sorts des livres restants lancés.
        if (!fight.chapters.isEmpty()) {
            List<Chapter> standing = fight.chapters.stream().filter(c -> alive(c.book(), store)).toList();
            if (standing.isEmpty()) {
                fight.chapters.clear();
                stun(store, codex, fight, now);
            } else if (now >= fight.chapters.getFirst().deadline()) {
                fight.chapters.clear();
                for (Chapter chapter : standing) {
                    store.removeEntity(chapter.book(), RemoveReason.REMOVE);
                    if (volumes != null) {
                        volumes.setTag(spellVolume(chapter), "Cast", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
                    }
                }
            }
        }

        EntityStatMap stats = store.getComponent(codex, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        boolean engaged = isEngaged(codex, store, health);

        // Remise à zéro : groupe mort ou sorti de l'arène.
        if (engaged && !playerInArena(world, store, ARENA_MARGIN)) {
            fight.absent += dt;
            if (fight.absent >= RESET_SECONDS) {
                reset(store, codex, fight, stats, volumes);
            }
            return;
        }
        fight.absent = 0f;

        // Coups déjà annoncés, flaques et tourbillons : ils vont au bout même si le Codex est étourdi.
        inkLines(store, fight, now);
        fight.cones.removeIf(cone -> cone.step(store, now));
        strikes(store, fight, now);
        pools(store, fight, now);
        vortices(store, fight, now);
        if (!engaged) {
            return;
        }
        if (!fight.started) {
            fight.started = true;
            fight.nextInk = now + seconds(INK_FIRST);
            GroupHealth.apply(stats, HP_MODIFIER, GroupHealth.multiplier(playersInArena(world, store, ARENA_MARGIN)));
        }
        TransformComponent transform = store.getComponent(codex, TransformComponent.getComponentType());
        Vector3d from = transform == null ? TowerLayout.CODEX_CENTER : transform.getPosition();

        // Changement de phase : onde annoncée autour du Codex, titre, puis les nouvelles attaques.
        if (health != null && fight.phase <= PHASE_HEALTH.length && health.get() < health.getMax() * PHASE_HEALTH[fight.phase - 1]) {
            fight.phase++;
            nextPhase(world, store, fight, from, now);
        }
        boolean stunned = now < fight.stunnedUntil;
        if (!stunned && now >= fight.nextInk) {
            fight.nextInk = now + seconds(INK_INTERVAL[fight.phase - 1]);
            ink(world, store, fight, from, now);
        }
        if (fight.phase >= 2 && !stunned && now >= fight.nextVortex) {
            fight.nextVortex = now + seconds(VORTEX_INTERVAL[fight.phase - 1]);
            summonVortices(store, fight, now);
        }

        // Effondrement des rayonnages en dernière phase.
        if (fight.phase >= 3 && volumes != null) {
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
                double[] arc = TowerLayout.CODEX_COLLAPSE_ARCS[sector];
                double[] radii = TowerLayout.CODEX_COLLAPSE_RADII;
                // Du mur (le rayonnage) vers le centre : la zone qui va se couvrir de gravats.
                fight.cones.add(Telegraphs.Sweep.arc(TowerLayout.CODEX_CENTER, arc[0], arc[1], radii[1], radii[0], now,
                        TowerLayout.CODEX_COLLAPSE_WARN));
                fight.nextCollapse = now + seconds(COLLAPSE_INTERVAL);
            }
        }
    }

    // --- phases ----------------------------------------------------------------------------------------------------

    private static void nextPhase(World world, Store<EntityStore> store, Fight fight, Vector3d from, long now) {
        for (PlayerRef player : world.getPlayerRefs()) {
            if (inArena(player.getReference(), store, ARENA_MARGIN)) {
                EventTitleUtil.showEventTitleToPlayer(player, Message.translation(LANG + fight.phase + ".title"),
                        Message.translation(LANG + fight.phase + ".subtitle"), EventTitleStyle.Major);
            }
        }
        Vector3d ground = new Vector3d(from.x(), TowerLayout.CODEX_CENTER.y(), from.z());
        ParticleUtil.spawnParticleEffect(WARNING_SHOCK, new Vector3d(ground).add(0, 0.1, 0), 0f, 0f, 0f,
                (float) (WARNING_SCALE * SHOCK_RADIUS), 1f, store);
        sound(SOUND_CHARGE, from, store);
        fight.strikes.add(new Strike(ground, SHOCK_RADIUS, now + seconds(SHOCK_WARN), SHOCK_DAMAGE, PARTICLE_SHOCK, 3f,
                3f, false));
        // Une respiration après l'onde, puis la phase commence vraiment.
        fight.nextInk = Math.max(fight.nextInk, now + seconds(SHOCK_WARN + 2f));
        fight.nextVortex = now + seconds(SHOCK_WARN + 1f);
    }

    // --- jets d'encre --------------------------------------------------------------------------------------------

    private static void ink(World world, Store<EntityStore> store, Fight fight, Vector3d from, long now) {
        List<Vector3d> targets = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (inArena(ref, store, 0)) {
                targets.add(store.getComponent(ref, TransformComponent.getComponentType()).getPosition());
            }
        }
        if (targets.isEmpty()) {
            return;
        }
        ThreadLocalRandom random = ThreadLocalRandom.current();
        Vector3d target = targets.get(random.nextInt(targets.size()));
        double base = Math.atan2(target.z() - from.z(), target.x() - from.x());
        // Dernière phase : un second jet, d'un côté ou de l'autre, coupe la fuite.
        double side = random.nextBoolean() ? 0.6 : -0.6;
        double[] angles = fight.phase >= 3 ? new double[]{base, base + side} : new double[]{base};
        double y = TowerLayout.CODEX_CENTER.y();
        Vector3d center = TowerLayout.CODEX_CENTER;
        double limit = TowerLayout.CODEX_ARENA_RADIUS - 1;
        for (double angle : angles) {
            List<Vector3d> circles = new ArrayList<>();
            for (int k = 0; k < INK_CIRCLES; k++) {
                double d = 2.0 + INK_STEP * k;
                Vector3d at = new Vector3d(from.x() + Math.cos(angle) * d, y, from.z() + Math.sin(angle) * d);
                double dx = at.x() - center.x();
                double dz = at.z() - center.z();
                if (dx * dx + dz * dz > limit * limit) {
                    break;
                }
                circles.add(at);
            }
            if (circles.isEmpty()) {
                continue;
            }
            // Trait sombre sur tout le trajet, du Codex au dernier cercle, une seconde avant que l'encre coure.
            double length = 2.0 + INK_STEP * (circles.size() - 1) + INK_RADIUS;
            for (double d = 1.0; d <= length; d += INK_TRACE_STEP) {
                Vector3d at = new Vector3d(from.x() + Math.cos(angle) * d, y + 0.05, from.z() + Math.sin(angle) * d);
                ParticleUtil.spawnParticleEffect(PARTICLE_TRACE, at, 0f, 0f, 0f, INK_TRACE_SCALE, 1f, store);
            }
            fight.inkLines.add(new InkLine(circles, now + seconds(INK_TRACE)));
        }
        sound(SOUND_CHARGE, from, store);
    }

    /** Lignes d'encre dont le trait a fait son temps : les cercles rouges se remplissent, l'encre court. */
    private static void inkLines(Store<EntityStore> store, Fight fight, long now) {
        fight.inkLines.removeIf(line -> {
            if (now < line.start()) {
                return false;
            }
            for (int k = 0; k < line.circles().size(); k++) {
                Vector3d at = line.circles().get(k);
                float warn = INK_WARN + INK_TRAVEL * k;
                ParticleUtil.spawnParticleEffect(WARNING_INK + Math.round(warn * 10), new Vector3d(at).add(0, 0.1, 0),
                        0f, 0f, 0f, (float) (WARNING_SCALE * INK_RADIUS), 1f, store);
                fight.strikes.add(new Strike(at, INK_RADIUS, now + seconds(warn), INK_DAMAGE, PARTICLE_SPLASH, 1f,
                        3f, true));
            }
            return true;
        });
    }

    private static void strikes(Store<EntityStore> store, Fight fight, long now) {
        fight.strikes.removeIf(strike -> {
            if (now < strike.hit()) {
                return false;
            }
            ParticleUtil.spawnParticleEffect(strike.particle(), new Vector3d(strike.at()).add(0, 0.2, 0), 0f, 0f, 0f,
                    strike.particleScale(), 1f, store);
            sound(SOUND_IMPACT, strike.at(), store);
            hurt(store, strike.at(), strike.radius(), strike.damage(), strike.slowSeconds());
            if (strike.pool()) {
                fight.pools.add(new Pool(strike.at(), now));
            }
            return true;
        });
    }

    private static void pools(Store<EntityStore> store, Fight fight, long now) {
        fight.pools.removeIf(pool -> {
            if (now >= pool.until) {
                return true;
            }
            if (now >= pool.next) {
                pool.next = now + seconds(1f);
                ParticleUtil.spawnParticleEffect(PARTICLE_POOL, pool.at, 0f, 0f, 0f, (float) (INK_RADIUS / 1.47), 1f, store);
                // La première seconde, l'éclaboussure vient de frapper : la flaque ne ronge qu'ensuite.
                if (now > pool.until - seconds(POOL_SECONDS - 0.5f)) {
                    hurt(store, pool.at, INK_RADIUS, POOL_DAMAGE, 1.5f);
                }
            }
            return false;
        });
    }

    // --- tourbillons de pages ------------------------------------------------------------------------------------

    private static void summonVortices(Store<EntityStore> store, Fight fight, long now) {
        int room = VORTEX_MAX - fight.vortices.size() - fight.summons.size();
        int count = Math.min(room, VORTEX_WAVE[fight.phase - 1]);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        double start = random.nextDouble(Math.PI * 2);
        for (int i = 0; i < count; i++) {
            double angle = start + Math.PI * 2 * i / count + random.nextDouble(-0.3, 0.3);
            double r = random.nextDouble(9, 13);
            Vector3d at = new Vector3d(TowerLayout.CODEX_CENTER).add(Math.cos(angle) * r, 0, Math.sin(angle) * r);
            ParticleUtil.spawnParticleEffect(WARNING_VORTEX, new Vector3d(at).add(0, 0.1, 0), 0f, 0f, 0f,
                    (float) (WARNING_SCALE * VORTEX_REACH), 1f, store);
            fight.summons.add(Pair.of(at, now + seconds(VORTEX_WARN)));
        }
    }

    private static void vortices(Store<EntityStore> store, Fight fight, long now) {
        fight.summons.removeIf(summon -> {
            if (now < summon.second()) {
                return false;
            }
            Vector3d at = summon.first();
            Ref<EntityStore> ref = spawn(store, VORTEX_ROLE, new Vector3d(at).add(0, 0.3, 0));
            ParticleUtil.spawnParticleEffect(PARTICLE_VORTEX, new Vector3d(at).add(0, 0.5, 0), 0f, 0f, 0f, 1.5f, 1f, store);
            sound(SOUND_IMPACT, at, store);
            if (ref != null) {
                fight.vortices.add(new Vortex(ref, now));
            }
            return true;
        });
        fight.vortices.removeIf(vortex -> {
            if (!alive(vortex.ref, store)) {
                return true;
            }
            TransformComponent transform = store.getComponent(vortex.ref, TransformComponent.getComponentType());
            if (now >= vortex.until || transform == null) {
                if (transform != null) {
                    ParticleUtil.spawnParticleEffect(PARTICLE_VORTEX, new Vector3d(transform.getPosition()).add(0, 0.8, 0),
                            0f, 0f, 0f, 1.5f, 1f, store);
                }
                store.removeEntity(vortex.ref, RemoveReason.REMOVE);
                return true;
            }
            if (now >= vortex.nextCut) {
                vortex.nextCut = now + seconds(VORTEX_CUT);
                hurt(store, transform.getPosition(), VORTEX_REACH, VORTEX_DAMAGE, 0f);
            }
            return false;
        });
    }

    // --- outils --------------------------------------------------------------------------------------------------

    /** Dégâts (part de la vie maximale) et ralentissement aux joueurs dans le cercle. */
    private static void hurt(Store<EntityStore> store, Vector3d at, double radius, float fraction, float slowSeconds) {
        World world = store.getExternalData().getWorld();
        DamageCause cause = DamageCause.getAssetMap().getAsset("Physical");
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
            double dx = position.x() - at.x();
            double dz = position.z() - at.z();
            double dy = position.y() - at.y();
            if (dx * dx + dz * dz > radius * radius || dy < -1 || dy > 3) {
                continue;
            }
            EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
            EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
            if (cause != null && health != null) {
                float amount = (float) Math.ceil(health.getMax() * fraction);
                DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource("Nakasar_Codex"), cause, amount));
            }
            if (slowSeconds > 0f) {
                EntityEffect effect = EntityEffect.getAssetMap().getAsset(EFFECT_SLOW);
                EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
                if (effect != null && effects != null) {
                    effects.addEffect(ref, effect, slowSeconds, OverlapBehavior.OVERWRITE, store);
                }
            }
        }
    }

    private static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f());
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Codex : impossible de faire apparaître '%s'", role);
            return null;
        }
        // Jamais sauvegardé : livres et tourbillons ne survivent pas à un rechargement de l'instance.
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        return spawned.first();
    }

    private static long seconds(float seconds) {
        return (long) (seconds * 1_000_000_000L);
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
        fight.stunnedUntil = now + seconds(STUN_SECONDS);
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
        clear(fight, store);
        if (fight.frozenByUs) {
            store.tryRemoveComponent(codex, Frozen.getComponentType());
        }
        GroupHealth.clear(stats, HP_MODIFIER);
        if (volumes != null) {
            volumes.setTag(TowerLayout.CODEX_ARENA, "Reset", "On", null, TriggerVolumeManager.ENVIRONMENT_ACTOR_UUID);
        }
        Fight fresh = new Fight();
        fresh.sealed = fight.sealed;
        FIGHTS.put(codex, fresh);
    }

    /** Retire livres, tourbillons, coups annoncés et flaques (mort, remise à zéro, Codex déchargé). */
    private static void clear(Fight fight, Store<EntityStore> store) {
        for (Chapter chapter : fight.chapters) {
            if (chapter.book().isValid()) {
                store.removeEntity(chapter.book(), RemoveReason.REMOVE);
            }
        }
        for (Vortex vortex : fight.vortices) {
            if (vortex.ref.isValid()) {
                store.removeEntity(vortex.ref, RemoveReason.REMOVE);
            }
        }
        fight.chapters.clear();
        fight.inkLines.clear();
        fight.cones.clear();
        fight.vortices.clear();
        fight.summons.clear();
        fight.strikes.clear();
        fight.pools.clear();
    }

    private static int playersInArena(World world, Store<EntityStore> store, double margin) {
        int count = 0;
        for (PlayerRef player : world.getPlayerRefs()) {
            if (inArena(player.getReference(), store, margin)) {
                count++;
            }
        }
        return count;
    }

    private static boolean playerInArena(World world, Store<EntityStore> store, double margin) {
        for (PlayerRef player : world.getPlayerRefs()) {
            if (inArena(player.getReference(), store, margin)) {
                return true;
            }
        }
        return false;
    }

    private static boolean inArena(Ref<EntityStore> ref, Store<EntityStore> store, double margin) {
        if (!alive(ref, store)) {
            return false;
        }
        TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
        if (transform == null) {
            return false;
        }
        Vector3d center = TowerLayout.CODEX_CENTER;
        double radius = TowerLayout.CODEX_ARENA_RADIUS + margin;
        Vector3d position = transform.getPosition();
        double dx = position.x() - center.x();
        double dz = position.z() - center.z();
        double dy = position.y() - center.y();
        return dx * dx + dz * dz <= radius * radius && dy > -2 && dy < ARENA_HEIGHT;
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
