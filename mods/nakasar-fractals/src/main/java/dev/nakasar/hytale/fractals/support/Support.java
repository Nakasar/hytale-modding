package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.BossBarSystem;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Runes et objets de soutien des fractales (Kevin, 26 octobre 2026 ; tools/generate_support.py) : ce qui est partagé
 * par tous les effets.
 *
 * <ul>
 *   <li><b>Qui est visé.</b> Les soins ne visent que des joueurs ({@link #playersNear}), jamais un PNJ (consigne
 *   permanente : aucun PNJ ne se soigne). Les dégâts et contrôles visent les ennemis ({@link #foesNear}) : dans une
 *   fractale, les PNJ du camp des fractales ({@link Foes}) ; ailleurs, tout PNJ sauf ceux de l'Observatoire.</li>
 *   <li><b>Boss et élites</b> (rôles à barre de boss) et <b>PNJ de mécanique</b> ({@link #MECHANIC} : ils portent une
 *   règle de la fractale, comme les élémentaires qui éteignent le feu) ne sont ni étourdis, ni attirés, ni effrayés,
 *   ni détournés : un contrôle n'entame que la barre de défiance d'un boss quand elle est ouverte ({@link #defiance}),
 *   et un ralentissement ne dépasse pas {@value #MECHANIC_SLOW} sur un PNJ de mécanique.</li>
 *   <li><b>Pas de couleur au sol.</b> Une zone se voit à son effet (particules de soin, givre, flammes…) semé sur
 *   toute sa surface et sur son bord, jamais au-delà ({@link #disk}, {@link #strip}) : les mêmes constantes servent au
 *   dessin et au test d'appartenance ({@link Telegraphs#inCircle}). Le rouge reste réservé aux menaces.</li>
 * </ul>
 */
public final class Support {

    /** Cause des dégâts de soutien : la barre de défiance ne les compte pas comme des coups (on la touche à part). */
    public static final String CAUSE = "Nakasar_Fractal_Support";
    public static final String LANG = "nakasar_fractals_support.";
    /** Ralentissement maximal d'un PNJ de mécanique. */
    public static final float MECHANIC_SLOW = 0.25f;

    /**
     * PNJ de mécanique : leur course fait la difficulté d'une phase (élémentaires qui éteignent le feu de camp, vétérans
     * qui poussent les captifs, escrocs fantômes qui cachent les trésors). Traités comme des boss par les contrôles.
     */
    public static final Set<String> MECHANIC = Set.of(
            "Nakasar_Fractal_Ice_Elemental",
            "Nakasar_Fractal_Grawl_Veteran",
            "Nakasar_Fractal_Ghostly_Swindler");

    /** PNJ jamais visés hors des fractales (l'Observatoire et ses marchands). */
    private static final Set<String> NEUTRAL = Set.of(
            "Nakasar_Fractal_Archivist", "Nakasar_Fractal_Alchemist", "Nakasar_Fractal_Trial_Golem",
            Decoys.ROLE);

    /** Recharges des objets (les runes ont celles du jeu) : joueur → objet → fin (nanoTime). */
    private static final Map<UUID, Map<String, Long>> COOLDOWNS = new ConcurrentHashMap<>();

    private Support() {
    }

    // --- cibles -------------------------------------------------------------------------------------

    /** Joueurs vivants du monde dont le corps mord sur le disque `radius` posé en `center`. */
    public static List<Ref<EntityStore>> playersNear(World world, Store<EntityStore> store, Vector3d center, double radius) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (PlayerRef player : Spawns.alivePlayers(world, store)) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && Telegraphs.inCircle(at, center, radius)) {
                out.add(player.getReference());
            }
        }
        return out;
    }

    /** Ennemis vivants dont le corps mord sur le disque `radius` posé en `center`. */
    public static List<Ref<EntityStore>> foesNear(World world, Store<EntityStore> store, Vector3d center, double radius) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (Ref<EntityStore> ref : foes(world, store)) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at != null && Telegraphs.inCircle(at, center, radius)) {
                out.add(ref);
            }
        }
        return out;
    }

    /** Tous les ennemis vivants du monde. */
    public static List<Ref<EntityStore>> foes(World world, Store<EntityStore> store) {
        boolean fractal = FractalCatalog.fractalOf(world) != null;
        List<Ref<EntityStore>> candidates = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                String role = npc == null ? null : npc.getRoleName();
                if (role != null && !NEUTRAL.contains(role)) {
                    candidates.add(chunk.getReferenceTo(i));
                }
            }
        });
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (Ref<EntityStore> ref : candidates) {
            if (Telegraphs.position(store, ref) != null && (!fractal || Foes.inGroup(ref, store))) {
                out.add(ref);
            }
        }
        return out;
    }

    /** Vrai pour un boss, une élite ou un PNJ de mécanique : pas de contrôle (seulement la défiance des boss). */
    public static boolean immune(Store<EntityStore> store, Ref<EntityStore> ref) {
        String role = Spawns.role(store, ref);
        return role != null && (BossBarSystem.isElite(role) || MECHANIC.contains(role));
    }

    public static boolean isMechanic(Store<EntityStore> store, Ref<EntityStore> ref) {
        String role = Spawns.role(store, ref);
        return role != null && MECHANIC.contains(role);
    }

    /** Point visé au sol : le premier bloc plein le long du regard (à `range` au plus), posé sur le sol en dessous. */
    public static Vector3d aimGround(World world, Store<EntityStore> store, Ref<EntityStore> caster, double range) {
        Vector3d feet = Telegraphs.position(store, caster);
        Vector3d look = Moves.look(store, caster);
        if (feet == null) {
            return null;
        }
        if (look == null) {
            return new Vector3d(feet);
        }
        Vector3d eye = new Vector3d(feet).add(0, 1.6, 0);
        Vector3d hit = Moves.cast(world.getChunkStore(), eye, look, range);
        Vector3d end = hit != null ? hit : new Vector3d(look).normalize().mul(range).add(eye);
        Vector3d ground = Moves.cast(world.getChunkStore(), end, new Vector3d(0, -1, 0), 12);
        if (ground == null) {
            return new Vector3d(feet);
        }
        return new Vector3d(ground.x(), Math.floor(ground.y()) + 0.0, ground.z());
    }

    /** L'entité (joueur si `players`, sinon ennemi) la plus proche de l'axe du regard, dans un cône de `cone` degrés. */
    public static Ref<EntityStore> aimEntity(World world, Store<EntityStore> store, Ref<EntityStore> caster, double range,
                                             double cone, boolean players, boolean sight) {
        Vector3d feet = Telegraphs.position(store, caster);
        Vector3d look = Moves.look(store, caster);
        if (feet == null || look == null) {
            return null;
        }
        Vector3d eye = new Vector3d(feet).add(0, 1.6, 0);
        List<Ref<EntityStore>> candidates = new ArrayList<>();
        if (players) {
            for (PlayerRef p : Spawns.alivePlayers(world, store)) {
                if (!p.getReference().equals(caster)) {
                    candidates.add(p.getReference());
                }
            }
        } else {
            candidates = foes(world, store);
        }
        double cos = Math.cos(Math.toRadians(cone / 2));
        Ref<EntityStore> best = null;
        double bestDot = cos;
        for (Ref<EntityStore> ref : candidates) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            Vector3d chest = new Vector3d(at).add(0, 1.0, 0);
            Vector3d to = new Vector3d(chest).sub(eye);
            double d = to.length();
            if (d > range || d < 0.3) {
                continue;
            }
            double dot = to.dot(look) / d;
            if (dot >= bestDot && (!sight || WorldBlocks.clearLine(world.getChunkStore(), eye, chest))) {
                bestDot = dot;
                best = ref;
            }
        }
        return best;
    }

    // --- effets -------------------------------------------------------------------------------------

    /** Soigne un joueur de `amount` PV (jamais un PNJ). */
    public static void heal(Store<EntityStore> store, Ref<EntityStore> ref, float amount) {
        if (amount <= 0 || ref == null || !ref.isValid() || store.getComponent(ref, NPCEntity.getComponentType()) != null
                || store.getComponent(ref, PlayerRef.getComponentType()) == null) {
            return;
        }
        add(store, ref, DefaultEntityStatTypes.getHealth(), amount);
    }

    /** Rend `amount` d'endurance à un joueur. */
    public static void stamina(Store<EntityStore> store, Ref<EntityStore> ref, float amount) {
        if (ref != null && ref.isValid() && store.getComponent(ref, PlayerRef.getComponentType()) != null) {
            add(store, ref, DefaultEntityStatTypes.getStamina(), amount);
        }
    }

    private static void add(Store<EntityStore> store, Ref<EntityStore> ref, int index, float amount) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue value = stats == null ? null : stats.get(index);
        if (value != null && value.get() < value.getMax()) {
            stats.setStatValue(index, Math.min(value.getMax(), value.get() + amount));
        }
    }

    /** Points de vie actuels (0 sans vie). */
    public static float health(Store<EntityStore> store, Ref<EntityStore> ref) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue value = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        return value == null ? 0f : value.get();
    }

    /** Retire `amount` PV à un joueur sans jamais le tuer (prix de la Transfusion). */
    public static void drain(Store<EntityStore> store, Ref<EntityStore> ref, float amount) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        int index = DefaultEntityStatTypes.getHealth();
        EntityStatValue value = stats == null ? null : stats.get(index);
        if (value != null) {
            stats.setStatValue(index, Math.max(1f, value.get() - amount));
        }
    }

    /** Dégâts de soutien `amount` d'un joueur sur un ennemi (cause {@value #CAUSE}). */
    public static void damage(Store<EntityStore> store, Ref<EntityStore> caster, Ref<EntityStore> target, float amount) {
        DamageCause cause = DamageCause.getAssetMap().getAsset(CAUSE);
        if (cause == null) {
            FractalsPlugin.get().getLogger().atWarning().log("Cause de dégâts '%s' introuvable", CAUSE);
            return;
        }
        if (target == null || !target.isValid() || amount <= 0) {
            return;
        }
        Damage.Source source = caster != null && caster.isValid() ? new Damage.EntitySource(caster)
                : new Damage.EnvironmentSource(CAUSE);
        DamageSystems.executeDamage(target, store, new Damage(source, cause, amount));
    }

    /** `points` coups dans la barre de défiance d'un boss s'il en a une d'ouverte (rien sinon). */
    public static void defiance(World world, Store<EntityStore> store, Ref<EntityStore> boss, int points) {
        if (points > 0 && Defiance.isOpen(boss)) {
            Defiance.hit(world, store, boss, points);
        }
    }

    /** Étourdit un ennemi `seconds` s (un boss ou un PNJ de mécanique : défiance `points` seulement). */
    public static void stun(World world, Store<EntityStore> store, Ref<EntityStore> foe, float seconds, int points) {
        if (immune(store, foe)) {
            defiance(world, store, foe, points);
            return;
        }
        BossStun.stun(world, store, foe, seconds, EFFECT_ROOTED);
    }

    public static final String EFFECT_ROOTED = "Nakasar_Fractal_Support_Rooted";

    /** Pousse un ennemi horizontalement de `from` vers l'extérieur (vitesse `speed`, montée `up`). */
    public static void push(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d from, double speed, double up) {
        Vector3d at = Telegraphs.position(store, ref);
        if (at == null) {
            return;
        }
        double a = Telegraphs.angle(from, at);
        if (Telegraphs.horizontal(from, at) < 0.05) {
            a = ThreadLocalRandom.current().nextDouble(-Math.PI, Math.PI);
        }
        velocity(store, ref, new Vector3d(Math.cos(a) * speed, up, Math.sin(a) * speed));
    }

    public static void velocity(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d v) {
        Velocity velocity = ref != null && ref.isValid() ? store.getComponent(ref, Velocity.getComponentType()) : null;
        if (velocity != null) {
            velocity.addInstruction(new Vector3d(v), null, ChangeVelocityType.Set);
        }
    }

    // --- dessin -------------------------------------------------------------------------------------

    /**
     * Sème `particle` sur un disque de rayon `radius` : un anneau sur le bord (un point tous les `spacing` blocs) et
     * `inside` points au hasard dedans. Aucun point hors du disque.
     */
    public static void disk(Store<EntityStore> store, String particle, Vector3d center, double radius, double spacing,
                            int inside, float scale) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int ring = Math.max(6, (int) Math.ceil(2 * Math.PI * radius / spacing));
        double phase = random.nextDouble(0, 2 * Math.PI / ring);
        for (int k = 0; k < ring; k++) {
            double a = phase + 2 * Math.PI * k / ring;
            Telegraphs.particle(store, particle, new Vector3d(center).add(Math.cos(a) * radius, 0.15, Math.sin(a) * radius), scale);
        }
        for (int k = 0; k < inside; k++) {
            double r = radius * Math.sqrt(random.nextDouble());
            double a = random.nextDouble(0, 2 * Math.PI);
            Telegraphs.particle(store, particle, new Vector3d(center).add(Math.cos(a) * r, 0.15, Math.sin(a) * r), scale);
        }
    }

    /** Sème `particle` le long d'un rectangle (longueur `length` sur l'axe `yaw`, largeur `width`), centré en `center`. */
    public static void strip(Store<EntityStore> store, String particle, Vector3d center, double axis, double length,
                             double width, double spacing, float scale) {
        double ax = Math.cos(axis);
        double az = Math.sin(axis);
        int n = Math.max(2, (int) Math.ceil(length / spacing));
        for (int k = 0; k <= n; k++) {
            double t = -length / 2 + length * k / n;
            for (double w : new double[]{-width / 2, 0, width / 2}) {
                Telegraphs.particle(store, particle,
                        new Vector3d(center).add(ax * t - az * w, 0.15, az * t + ax * w), scale);
            }
        }
    }

    /** Vrai si le corps en `p` mord sur le rectangle de {@link #strip} (même marge que les télégraphes). */
    public static boolean inStrip(Vector3d p, Vector3d center, double axis, double length, double width) {
        double dx = p.x() - center.x();
        double dz = p.z() - center.z();
        double along = dx * Math.cos(axis) + dz * Math.sin(axis);
        double across = -dx * Math.sin(axis) + dz * Math.cos(axis);
        double dy = p.y() - center.y();
        return Math.abs(along) <= length / 2 + Telegraphs.BODY && Math.abs(across) <= width / 2 + Telegraphs.BODY
                && dy >= -1.5 && dy <= 3.5;
    }

    // --- recharges des objets -----------------------------------------------------------------------

    /** Vrai (et la recharge démarre) si l'objet `item` du joueur est prêt ; sinon le joueur est prévenu. */
    public static boolean ready(Store<EntityStore> store, Ref<EntityStore> player, String item, float seconds) {
        PlayerRef ref = store.getComponent(player, PlayerRef.getComponentType());
        if (ref == null || seconds <= 0) {
            return true;
        }
        long now = System.nanoTime();
        Map<String, Long> mine = COOLDOWNS.computeIfAbsent(ref.getUuid(), u -> new ConcurrentHashMap<>());
        Long until = mine.get(item);
        if (until != null && now < until) {
            ref.sendMessage(Message.translation(LANG + "cooldown")
                    .param("seconds", (int) Math.ceil((until - now) / 1e9)));
            return false;
        }
        mine.put(item, now + Telegraphs.seconds(seconds));
        return true;
    }

    public static void tell(Store<EntityStore> store, Ref<EntityStore> player, String key) {
        PlayerRef ref = player == null || !player.isValid() ? null : store.getComponent(player, PlayerRef.getComponentType());
        if (ref != null) {
            ref.sendMessage(Message.translation(LANG + key));
        }
    }

    /** Annule la recharge propre `item` du joueur (effet qui n'a rien pu faire). */
    static void forget(Store<EntityStore> store, Ref<EntityStore> player, String item) {
        PlayerRef ref = store.getComponent(player, PlayerRef.getComponentType());
        Map<String, Long> mine = ref == null ? null : COOLDOWNS.get(ref.getUuid());
        if (mine != null) {
            mine.remove(item);
        }
    }

    public static void clearAll() {
        COOLDOWNS.clear();
    }
}
