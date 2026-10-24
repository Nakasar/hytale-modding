package dev.nakasar.hytale.fractals.solidocean;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.CrouchPickup;
import dev.nakasar.hytale.fractals.boss.PinnedHealth;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import dev.nakasar.hytale.fractals.progress.Agony;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * L'Abîme de Jade, boss de l'Océan solide, d'après GW2. Il ne bouge pas et ses écailles denses le rendent
 * invulnérable : sa vie ne baisse que par un cristal chargé lancé ({@value #CRYSTAL_PART}) ou un tentacule abattu
 * ({@value #TENTACLE_PART}), deux coups au même instant n'en comptant qu'un ({@value #SAME_HIT} s).
 * <ul>
 *   <li>phase 1 : un test d'agonie à l'arrivée, deux tentacules devant lui ; tant qu'ils vivent, ni rayon ni
 *   colosse ;</li>
 *   <li>phase 2 : huit tentacules percent le jade (ils ne repoussent pas, un cristal chacun), un cristal posé près de chacun et
 *   le rayon aussitôt, un colosse sort toutes les
 *   {@value #COLOSSUS_EVERY} s ({@value #COLOSSUS_POOL} en tout, {@value #MAX_COLOSSI} en vie au plus, insensibles aux
 *   attaques à distance, un cristal chacun), le rayon toutes les {@value #BEAM_P2} s ;</li>
 *   <li>phase 3, quand le dernier colosse est tombé : retour à huit tentacules, chacun repousse
 *   {@value #TENTACLE_RESPAWN} s après sa mort et lâche un cristal ; le rayon toutes les {@value #BEAM_P3} s.</li>
 * </ul>
 * Le rayon : un joueur est visé ({@value #TARGET_SECONDS} s, effet {@value #TARGETED} dans la barre d'état, lueur
 * orange, crâne rouge au-dessus de lui). Au bout du compte, s'il tient un cristal, le cristal est chargé ; sinon il est
 * tué. Il n'y a pas de zone au sol : seul le joueur visé est touché. Sous {@value #LAST_BEAM_AT} de vie, un dernier
 * rayon vise tout le monde. Personne de vivant dans l'arène pendant {@value #RESET_SECONDS} s : tout recommence.
 */
final class JadeMaw {

    static final float CRYSTAL_PART = 0.05f;
    static final float TENTACLE_PART = 0.03f;
    static final float SAME_HIT = 0.5f;
    static final float BEAM_P2 = 40f;
    static final float BEAM_P3 = 30f;
    /** Cristal posé près de chacun des huit tentacules au début de la phase 2, à ce nombre de blocs vers le centre. */
    static final double FIRST_CRYSTAL_OFFSET = 2.0;
    static final float TARGET_SECONDS = 6f;
    static final float LAST_BEAM_AT = 0.08f;
    static final float LAST_TARGET_SECONDS = 7f;
    static final float RESET_SECONDS = 20f;
    static final float TENTACLE_RESPAWN = 30f;
    static final float COLOSSUS_EVERY = 30f;
    static final int COLOSSUS_POOL = 10;
    static final int MAX_COLOSSI = 3;
    /** Plancher de vie des deux premières phases : la fin et son dernier rayon arrivent toujours. */
    static final float PHASE_FLOOR = 0.4f;
    static final String CHARGED = "Nakasar_Fractal_Crystal_Charged";
    static final String TARGETED = "Nakasar_Fractal_Jade_Targeted";
    static final String SKULL = "Nakasar_Fractal_Jade_Skull";

    private static final Map<Ref<EntityStore>, String> LABELS = new ConcurrentHashMap<>();

    private Ref<EntityStore> maw;
    @SuppressWarnings("unchecked")
    private final Ref<EntityStore>[] tentacles = new Ref[SolidOceanLayout.TENTACLES.length];
    private final float[] regrow = new float[SolidOceanLayout.TENTACLES.length];
    private final List<Ref<EntityStore>> colossi = new ArrayList<>();
    private final List<Ref<EntityStore>> irukandji = new ArrayList<>();
    private final List<Vector3d> tentacleDeaths = new ArrayList<>();
    private final List<Vector3d> colossusDeaths = new ArrayList<>();
    private final Set<UUID> charged = new HashSet<>();
    private boolean engaged;
    private boolean victory;
    /** 1 : deux tentacules ; 2 : colosses ; 3 : fin. */
    private int phase;
    private float health = 1f;
    private long lastHit;
    private int p1Down;
    private int colossiDown;
    private int colossiSpawned;
    private float colossusClock;
    private float idle;

    // rayon en cours : cible(s) et temps restant
    private final List<PlayerRef> beamTargets = new ArrayList<>();
    private float beamClock;
    private float countdown = -1f;
    private boolean lastBeam;
    private boolean lastBeamDone;

    static String label(Ref<EntityStore> ref) {
        return LABELS.getOrDefault(ref, "");
    }

    static void clearLabels() {
        LABELS.clear();
    }

    static List<PlayerRef> inArena(Store<EntityStore> store, List<PlayerRef> players) {
        double[] c = SolidOceanLayout.ARENA_CENTER;
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && at.y() >= c[1] - 3 && at.y() <= c[1] + 12
                    && Math.hypot(at.x() - c[0], at.z() - c[2]) <= SolidOceanLayout.ARENA_RADIUS + 1) {
                out.add(player);
            }
        }
        return out;
    }

    synchronized void tentacleDown(Vector3d at) {
        tentacleDeaths.add(new Vector3d(at));
    }

    synchronized void colossusDown(Vector3d at) {
        colossusDeaths.add(new Vector3d(at));
    }

    /** Un pas de jeu ; vrai à la victoire (une seule fois). */
    boolean step(World world, Store<EntityStore> store, SolidOcean.State st, List<PlayerRef> players, float dt) {
        if (victory) {
            return false;
        }
        keepMaw(store);
        List<PlayerRef> inArena = inArena(store, players);
        if (inArena.isEmpty()) {
            idle(world, store, dt);
            return false;
        }
        idle = 0f;
        if (!engaged) {
            engage(world, store, inArena);
        }
        deaths(world, store, inArena);
        if (phase == 1 && p1Down >= 2) {
            awaken(world, store);
        }
        if (phase >= 2) {
            colossi(world, store, dt);
            regrowTentacles(world, store, dt);
            beam(world, store, st, inArena, dt);
        }
        sync(store);
        if (health <= 0f) {
            return win(world, store, players);
        }
        return false;
    }

    // --- l'Abîme et sa vie -----------------------------------------------------------------------------

    private void keepMaw(Store<EntityStore> store) {
        if (maw != null && maw.isValid()) {
            return;
        }
        Vector3d at = Spawns.point(SolidOceanLayout.MAW);
        maw = Spawns.spawn(store, SolidOcean.MAW, at, Telegraphs.yawToward(at, Spawns.point(SolidOceanLayout.ARENA_CENTER)));
        if (maw != null) {
            store.ensureAndGetComponent(maw, Frozen.getComponentType());
            store.ensureAndGetComponent(maw, Invulnerable.getComponentType());
            showLabel();
        }
    }

    /**
     * La barre de boss suit la vie tenue par le Java : fixée à chaque tick ({@link PinnedHealth}), sans quoi la
     * régénération naturelle des PNJ la ferait remonter entre deux pas.
     */
    private void sync(Store<EntityStore> store) {
        EntityStatMap stats = maw == null ? null : store.getComponent(maw, EntityStatMap.getComponentType());
        EntityStatValue value = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (value == null) {
            return;
        }
        float wanted = Math.max(1f, value.getMax() * health);
        PinnedHealth.pin(maw, wanted);
        if (Math.abs(value.get() - wanted) > 0.01f) {
            stats.setStatValue(DefaultEntityStatTypes.getHealth(), wanted);
        }
    }

    /** Retire `part` de la vie de l'Abîme ; faux si un coup vient de tomber (même instant). */
    private boolean hurt(Store<EntityStore> store, float part) {
        long now = System.nanoTime();
        if (now - lastHit < Telegraphs.seconds(SAME_HIT)) {
            return false;
        }
        lastHit = now;
        float floor = phase < 3 ? PHASE_FLOOR : lastBeamDone ? 0f : LAST_BEAM_AT * 0.5f;
        health = Math.max(floor, health - part);
        Vector3d at = Telegraphs.position(store, maw);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Maw_Hurt", new Vector3d(at).add(0, 4, 0), 2f);
        }
        return true;
    }

    private void showLabel() {
        if (maw == null) {
            return;
        }
        String text = switch (phase) {
            case 1 -> "Tentacules " + Math.min(2, p1Down) + "/2";
            case 2 -> "Colosses " + colossiDown + "/" + COLOSSUS_POOL;
            default -> "";
        };
        LABELS.put(maw, text);
    }

    // --- phases ------------------------------------------------------------------------------------------

    private void engage(World world, Store<EntityStore> store, List<PlayerRef> inArena) {
        engaged = true;
        phase = 1;
        health = 1f;
        p1Down = 0;
        lastBeamDone = false;
        Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "arena"));
        for (int i = 0; i < 2; i++) {
            spawnTentacle(world, store, i);
        }
        for (double[] at : SolidOceanLayout.ARENA_IRUKANDJI) {
            Ref<EntityStore> foe = Spawns.spawnFoe(world, store, SolidOcean.IRUKANDJI, at);
            if (foe != null) {
                irukandji.add(foe);
            }
        }
        if (FractalRuns.level(world) >= Agony.FIRST_LEVEL) {   // le test d'agonie de l'arrivée
            for (PlayerRef p : inArena) {
                Hurt.effect(store, p.getReference(), Agony.EFFECT, 9f);
                p.sendMessage(Message.translation(SolidOcean.MESSAGES + "agony"));
            }
        }
        showLabel();
    }

    /**
     * Les deux premiers tentacules sont tombés : huit tentacules, chacun avec un cristal à côté de lui, les colosses, et
     * le premier rayon aussitôt.
     */
    private void awaken(World world, Store<EntityStore> store) {
        phase = 2;
        colossiDown = 0;
        colossiSpawned = 0;
        colossusClock = COLOSSUS_EVERY - 5f;
        beamClock = BEAM_P2;
        fillTentacles(world, store);
        Vector3d center = Spawns.point(SolidOceanLayout.ARENA_CENTER);
        for (double[] point : SolidOceanLayout.TENTACLES) {
            Vector3d at = Spawns.point(point);
            Vector3d toward = new Vector3d(center.x() - at.x(), 0, center.z() - at.z());
            if (toward.lengthSquared() > 1e-6) {
                at.add(toward.normalize().mul(FIRST_CRYSTAL_OFFSET));
            }
            SolidOcean.dropCrystal(store, at);
        }
        Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "phase.colossi").param("count", COLOSSUS_POOL));
        showLabel();
    }

    /** Un colosse toutes les {@value #COLOSSUS_EVERY} s, jusqu'à {@value #COLOSSUS_POOL} ; le dernier abattu ouvre la fin. */
    private void colossi(World world, Store<EntityStore> store, float dt) {
        colossi.removeIf(ref -> !Spawns.alive(store, ref));
        if (phase == 2 && colossiDown >= COLOSSUS_POOL) {
            phase = 3;
            beamClock = Math.min(beamClock, BEAM_P3 - 10f);
            fillTentacles(world, store);
            Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "phase.final"));
            showLabel();
            return;
        }
        if (phase != 2 || colossiSpawned >= COLOSSUS_POOL) {
            return;
        }
        colossusClock += dt;
        if (colossusClock < COLOSSUS_EVERY || colossi.size() >= MAX_COLOSSI) {
            return;
        }
        colossusClock = 0f;
        double[][] points = SolidOceanLayout.COLOSSI;
        double[] point = points[colossiSpawned % points.length];
        Ref<EntityStore> c = Spawns.spawnFoe(world, store, SolidOcean.COLOSSUS, point);
        if (c != null) {
            colossi.add(c);
            colossiSpawned++;
            Telegraphs.particle(store, "Nakasar_Fractal_Tentacle_Emerge", Spawns.point(point), 2f);
        }
    }

    /** Un tentacule à chaque place libre. */
    private void fillTentacles(World world, Store<EntityStore> store) {
        for (int i = 0; i < tentacles.length; i++) {
            regrow[i] = 0f;
            if (!Spawns.alive(store, tentacles[i])) {
                spawnTentacle(world, store, i);
            }
        }
    }

    /** Phase 3 : chaque tentacule abattu repousse à sa place {@value #TENTACLE_RESPAWN} s plus tard. */
    private void regrowTentacles(World world, Store<EntityStore> store, float dt) {
        if (phase != 3) {
            return;
        }
        for (int i = 0; i < tentacles.length; i++) {
            if (Spawns.alive(store, tentacles[i])) {
                regrow[i] = 0f;
                continue;
            }
            regrow[i] += dt;
            if (regrow[i] >= TENTACLE_RESPAWN) {
                regrow[i] = 0f;
                spawnTentacle(world, store, i);
            }
        }
    }

    private void spawnTentacle(World world, Store<EntityStore> store, int index) {
        Vector3d at = Spawns.point(SolidOceanLayout.TENTACLES[index]);
        tentacles[index] = Spawns.spawnFoe(world, store, SolidOcean.TENTACLE, at,
                Telegraphs.yawToward(at, Spawns.point(SolidOceanLayout.ARENA_CENTER)));
        Telegraphs.particle(store, "Nakasar_Fractal_Tentacle_Emerge", at, 2f);
    }

    /** Morts de tentacules et de colosses reçues depuis le dernier pas. */
    private void deaths(World world, Store<EntityStore> store, List<PlayerRef> inArena) {
        List<Vector3d> tentacleAt;
        List<Vector3d> colossusAt;
        synchronized (this) {
            tentacleAt = new ArrayList<>(tentacleDeaths);
            colossusAt = new ArrayList<>(colossusDeaths);
            tentacleDeaths.clear();
            colossusDeaths.clear();
        }
        for (Vector3d at : tentacleAt) {
            if (phase == 1) {
                p1Down++;
            }
            hurt(store, TENTACLE_PART);
            if (phase >= 2) {   // les deux premiers (phase 1) ne lâchent rien
                dropCrystal(world, store, at);
            }
        }
        for (Vector3d at : colossusAt) {
            if (phase == 2) {
                colossiDown++;
            }
            dropCrystal(world, store, at);
        }
        if (!tentacleAt.isEmpty() || !colossusAt.isEmpty()) {
            showLabel();
        }
    }

    private void dropCrystal(World world, Store<EntityStore> store, Vector3d at) {
        SolidOcean.dropCrystal(store, at);
        Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "crystal.drop"));
    }

    // --- le rayon --------------------------------------------------------------------------------------

    private void beam(World world, Store<EntityStore> store, SolidOcean.State st, List<PlayerRef> inArena, float dt) {
        if (countdown < 0f) {
            if (phase == 3 && !lastBeamDone && health <= LAST_BEAM_AT) {
                mark(world, store, inArena, true);
                return;
            }
            beamClock += dt;
            if (beamClock >= (phase == 3 ? BEAM_P3 : BEAM_P2)) {
                beamClock = 0f;
                List<PlayerRef> picked = Spawns.pick(inArena, 1);
                if (!picked.isEmpty()) {
                    mark(world, store, picked, false);
                }
            }
            return;
        }
        countdown -= dt;
        for (PlayerRef p : beamTargets) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                Telegraphs.particle(store, SKULL, new Vector3d(at).add(0, 2.6, 0), 1.2f);
            }
        }
        if (countdown < 0f) {
            fire(world, store, st);
        }
    }

    /**
     * Nouvelle cible : les charges précédentes se perdent ; la (les) cible(s) reçoit l'effet {@value #TARGETED}
     * (tête de mort rouge dans la barre d'état, lueur orange) et un crâne flotte au-dessus d'elle.
     */
    private void mark(World world, Store<EntityStore> store, List<PlayerRef> targets, boolean everyone) {
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            if (charged.remove(p.getUuid())) {
                Hurt.clear(store, p.getReference(), CHARGED);
            }
        }
        beamTargets.clear();
        beamTargets.addAll(targets);
        lastBeam = everyone;
        countdown = (everyone ? LAST_TARGET_SECONDS : TARGET_SECONDS) * FractalRuns.windupFactor(world);
        for (PlayerRef p : targets) {
            Hurt.effect(store, p.getReference(), TARGETED, countdown + 0.5f);
        }
        if (everyone) {
            Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "last.beam"));
            return;
        }
        PlayerRef target = targets.get(0);
        target.sendMessage(Message.translation(SolidOcean.MESSAGES + "skull"));
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            if (!p.equals(target)) {
                p.sendMessage(Message.translation(SolidOcean.MESSAGES + "skull.other").param("name", target.getUsername()));
            }
        }
    }

    /** Fin du compte : chaque cible vivante est frappée, où qu'elle soit ; un cristal en main absorbe le rayon. */
    private void fire(World world, Store<EntityStore> store, SolidOcean.State st) {
        Vector3d eye = Telegraphs.position(store, maw);
        if (eye != null) {
            eye = new Vector3d(eye).add(0, 5, 0);
        }
        for (PlayerRef p : beamTargets) {
            Ref<EntityStore> ref = p.getReference();
            if (ref == null || !Spawns.alive(store, ref)) {
                continue;
            }
            Hurt.clear(store, ref, TARGETED);
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            if (eye != null) {
                drawBeam(store, eye, new Vector3d(at).add(0, 1, 0));
            }
            if (CrystalHold.holds(store, ref)) {
                charged.add(p.getUuid());
                Hurt.effect(store, ref, CHARGED, BEAM_P2);
                Telegraphs.particle(store, "Nakasar_Fractal_Crystal_Charge", at, 1.2f);
                SolidOcean.tell(st, p, "absorbed");
            } else {
                Hurt.percent(store, ref, 1f, SolidOcean.BEAM_CAUSE);
                p.sendMessage(Message.translation(SolidOcean.MESSAGES + "beam.hit"));
            }
        }
        if (lastBeam) {
            lastBeamDone = true;
        }
        beamTargets.clear();
        countdown = -1f;
    }

    private static void drawBeam(Store<EntityStore> store, Vector3d from, Vector3d to) {
        Vector3d step = new Vector3d(to).sub(from);
        int n = (int) Math.ceil(step.length() / 1.5);
        if (n <= 0) {
            return;
        }
        step.div(n);
        Vector3d at = new Vector3d(from);
        for (int i = 0; i <= n; i++) {
            Telegraphs.particle(store, "Nakasar_Fractal_Jade_Beam", at, 1f);
            at.add(step);
        }
        Telegraphs.sound(store, "SFX_Goblin_Lobber_Bomb_Death", to);
    }

    // --- cristaux et colosses -------------------------------------------------------------------------

    /** Un cristal lancé sur l'Abîme : chargé, il le blesse ; sinon il revient au lanceur. */
    void crystal(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player) {
        if (!charged.remove(player.getUuid())) {
            CrystalHold.give(store, ref);
            player.sendMessage(Message.translation(SolidOcean.MESSAGES + "crystal.uncharged"));
            return;
        }
        Hurt.clear(store, ref, CHARGED);
        if (hurt(store, CRYSTAL_PART)) {
            Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "crystal.hit"));
        }
    }

    /** Un colosse est insensible aux attaques à distance : il les renvoie (éclair blanc). */
    void reflect(World world, SolidOcean.State st, Ref<EntityStore> colossus, Ref<EntityStore> attacker, Damage damage) {
        damage.setCancelled(true);
        world.execute(() -> {
            Store<EntityStore> s = world.getEntityStore().getStore();
            Vector3d at = Telegraphs.position(s, colossus);
            if (at != null) {
                Telegraphs.particle(s, "Nakasar_Fractal_Colossus_Reflect", new Vector3d(at).add(0, 1.5, 0), 1f);
            }
            if (attacker != null && attacker.isValid()) {
                PlayerRef player = s.getComponent(attacker, PlayerRef.getComponentType());
                if (player != null) {
                    SolidOcean.tell(st, player, "reflect");
                }
            }
        });
    }

    // --- remise à zéro et victoire ------------------------------------------------------------------------

    /** Personne de vivant dans l'arène : au bout de {@value #RESET_SECONDS} s, tout recommence. */
    void idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged || victory) {
            return;
        }
        idle += dt;
        if (idle < RESET_SECONDS) {
            return;
        }
        Spawns.tellAll(world, Message.translation(SolidOcean.MESSAGES + "reset"));
        clear(world, store);
        engaged = false;
        phase = 0;
        health = 1f;
        idle = 0f;
        sync(store);
    }

    private void clear(World world, Store<EntityStore> store) {
        for (int i = 0; i < tentacles.length; i++) {
            Spawns.remove(store, tentacles[i]);
            tentacles[i] = null;
        }
        Spawns.removeAll(store, colossi);
        colossi.clear();
        Spawns.removeAll(store, irukandji);
        irukandji.clear();
        synchronized (this) {
            tentacleDeaths.clear();
            colossusDeaths.clear();
        }
        beamTargets.clear();
        countdown = -1f;
        lastBeam = false;
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            charged.remove(p.getUuid());
            Hurt.clear(store, p.getReference(), CHARGED);
            Hurt.clear(store, p.getReference(), TARGETED);
        }
        charged.clear();
        CrouchPickup.removeGround(world, store, SolidOcean.CRYSTAL);
    }

    private boolean win(World world, Store<EntityStore> store, List<PlayerRef> players) {
        victory = true;
        clear(world, store);
        for (PlayerRef p : players) {
            Ref<EntityStore> ref = p.getReference();
            if (ref != null && ref.isValid()) {
                CrystalHold.removeAll(store, ref);
            }
        }
        Vector3d at = Telegraphs.position(store, maw);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Maw_Hurt", new Vector3d(at).add(0, 4, 0), 3f);
        }
        if (maw != null) {
            LABELS.remove(maw);
        }
        PinnedHealth.unpin(maw);
        Spawns.remove(store, maw);
        maw = null;
        return true;
    }
}
