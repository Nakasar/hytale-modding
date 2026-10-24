package dev.nakasar.hytale.fractals.volcanic;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.arena.CrouchPickup;
import dev.nakasar.hytale.fractals.boss.PinnedHealth;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Le Champion chaman des grawls. Son IA (JSON) frappe et lance les flammes sous chaque joueur ; le Java mène le reste :
 * <ul>
 *   <li>{@value #STACKS} charges de protection : invulnérable tant qu'il en garde une ; seule une pierre
 *   imprégnée lancée sur lui en retire une ; elle se ramasse accroupi, une par joueur, et se garde en main
 *   ({@link CrouchPickup}). À 50 % de vie, deuxième phase de protection : il reprend {@value #RESHIELD_STACKS} charge
 *   (une fois) ;</li>
 *   <li>pierres imprégnées seulement pendant les phases de protection, vétérans seulement pendant la première (Kevin,
 *   2026-10-24) ; à la dernière charge retirée, les
 *   pierres disparaissent (sol et mains) : on frappe avec ses armes ;</li>
 *   <li>sa vie ne remonte jamais d'elle-même ({@link PinnedHealth#noRegen}) : pas de répit pendant qu'on attend les
 *   pierres ;</li>
 *   <li>des rochers tombent toutes les {@value #ROCK_INTERVAL} s ; protégé, un sur trois laisse une pierre imprégnée ;</li>
 *   <li>toutes les {@value #VETERAN_INTERVAL} s, des vétérans sortent des grottes et marchent vers un captif (leur
 *   point d'attache) ; un vétéran à {@value #PUSH_RANGE} blocs d'un captif pendant {@value #PUSH_TIME} s le jette dans
 *   la lave. Tous perdus : la rencontre repart de zéro. Tous sauvés : {@value #BONUS} éclats de Brume par joueur ;</li>
 *   <li>personne dans l'arène pendant {@value #RESET_SECONDS} s : tout repart de zéro.</li>
 * </ul>
 */
final class Champion {

    static final int STACKS = 8;
    static final int RESHIELD_STACKS = 1;
    static final float ROCK_INTERVAL = 6f;
    static final float VETERAN_INTERVAL = 20f;
    static final double PUSH_RANGE = 2;
    static final float PUSH_TIME = 1.5f;
    static final float RESET_SECONDS = 20f;
    static final int BONUS = 5;
    static final String SHARD = "Nakasar_Fractal_Mist_Shard";

    /** Charges de chaque Champion, pour la barre de boss. */
    private static final Map<Ref<EntityStore>, Integer> LABELS = Collections.synchronizedMap(new WeakHashMap<>());

    private Ref<EntityStore> boss;
    private int stacks = STACKS;
    private boolean reshielded;
    private boolean engaged;
    volatile boolean down;
    private float idle;
    private float rockClock;
    private float veteranClock;
    private final Ref<EntityStore>[] captives;
    private final boolean[] lost;
    private final float[] near;
    private final Map<Ref<EntityStore>, Integer> veterans = new HashMap<>();

    @SuppressWarnings("unchecked")
    Champion() {
        captives = new Ref[VolcanicLayout.CAPTIVES.length];
        lost = new boolean[captives.length];
        near = new float[captives.length];
    }

    static String label(Ref<EntityStore> ref) {
        Integer n = LABELS.get(ref);
        return n == null || n <= 0 ? null : "◆ " + n;
    }

    static void clearLabels() {
        LABELS.clear();
    }

    static List<PlayerRef> inArena(Store<EntityStore> store, List<PlayerRef> players) {
        return Volcanic.inCylinder(store, players, VolcanicLayout.CHAMPION, VolcanicLayout.CHAMPION_RADIUS, 8);
    }

    /** Un pas de jeu ; vrai à la victoire (une seule fois). */
    boolean step(World world, Store<EntityStore> store, Volcanic.State st, List<PlayerRef> players, float dt) {
        if (down) {
            return finish(world, store);
        }
        keepCaptives(store);
        if (boss == null || !boss.isValid()) {
            double[] c = VolcanicLayout.CHAMPION;
            boss = Spawns.spawnBoss(world, store, Volcanic.CHAMPION, Spawns.point(c), 0f);
            stacks = STACKS;
            reshielded = false;
            showStacks();
            if (boss == null) {
                return false;
            }
            PinnedHealth.noRegen(boss);
        }
        List<PlayerRef> inArena = inArena(store, players);
        if (inArena.isEmpty()) {
            idle(world, store, dt);
            return false;
        }
        idle = 0f;
        if (!engaged) {
            engaged = true;
            veteranClock = VETERAN_INTERVAL - 6f;
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.enter"));
        }
        if (!reshielded && Hurt.healthFraction(store, boss) < 0.5f) {
            reshielded = true;
            stacks = Math.max(stacks, RESHIELD_STACKS);
            showStacks();
            Vector3d at = Telegraphs.position(store, boss);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Shield_Glow", new Vector3d(at).add(0, 1, 0), 2f);
            }
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.shield"));
        }
        rockClock += dt;
        if (rockClock >= ROCK_INTERVAL) {
            rockClock = 0f;
            Volcanic.fallingRocks(world, store, st, inArena, 2 + (FractalRuns.partySize(world) >= 3 ? 1 : 0), stacks > 0);
        }
        veteranClock += stacks > 0 && !reshielded ? dt : 0f;   // vétérans : première phase de protection seulement
        if (veteranClock >= VETERAN_INTERVAL) {
            veteranClock = 0f;
            veterans(world, store);
        }
        march(world, store, dt);
        return false;
    }

    /** Phase de protection en cours (charges restantes) : vétérans et pierres imprégnées. */
    boolean shielded() {
        return stacks > 0;
    }

    private void showStacks() {
        if (boss != null) {
            LABELS.put(boss, stacks);
        }
    }

    private void keepCaptives(Store<EntityStore> store) {
        double[] c = VolcanicLayout.CHAMPION;
        for (int i = 0; i < captives.length; i++) {
            if (lost[i] || (captives[i] != null && captives[i].isValid())) {
                continue;
            }
            Vector3d at = Spawns.point(VolcanicLayout.CAPTIVES[i]);
            captives[i] = Spawns.spawn(store, Volcanic.CAPTIVE, at, Telegraphs.yawToward(at, Spawns.point(c)));
            if (captives[i] != null) {
                store.ensureAndGetComponent(captives[i], Frozen.getComponentType());
                store.ensureAndGetComponent(captives[i], Invulnerable.getComponentType());
            }
        }
    }

    /** Un vétéran par grotte (deux dès trois joueurs), chacun vers un captif encore là. */
    private void veterans(World world, Store<EntityStore> store) {
        List<Integer> left = new ArrayList<>();
        for (int i = 0; i < captives.length; i++) {
            if (!lost[i]) {
                left.add(i);
            }
        }
        if (left.isEmpty()) {
            return;
        }
        int count = FractalRuns.partySize(world) >= 3 ? 2 : 1;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int k = 0; k < count; k++) {
            double[] gate = VolcanicLayout.VETERAN_GATES[random.nextInt(VolcanicLayout.VETERAN_GATES.length)];
            Ref<EntityStore> vet = Spawns.spawnFoe(world, store, Volcanic.VETERAN, gate);
            if (vet == null) {
                continue;
            }
            int target = left.get(random.nextInt(left.size()));
            aim(store, vet, target);
        }
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.veterans"));
    }

    /** Le captif `index` devient le point d'attache du vétéran : il y marche (état ReturnHome du rôle). */
    private void aim(Store<EntityStore> store, Ref<EntityStore> vet, int index) {
        veterans.put(vet, index);
        NPCEntity npc = store.getComponent(vet, NPCEntity.getComponentType());
        if (npc != null) {
            npc.setLeashPoint(Spawns.point(VolcanicLayout.CAPTIVES[index]));
        }
    }

    /** Vétérans arrivés près d'un captif : au bout de {@value #PUSH_TIME} s, le captif est jeté dans la lave. */
    private void march(World world, Store<EntityStore> store, float dt) {
        veterans.keySet().removeIf(vet -> !Spawns.alive(store, vet));
        boolean[] threatened = new boolean[captives.length];
        for (Map.Entry<Ref<EntityStore>, Integer> e : veterans.entrySet()) {
            int i = e.getValue();
            Vector3d at = Telegraphs.position(store, e.getKey());
            if (!lost[i] && at != null && at.distance(Spawns.point(VolcanicLayout.CAPTIVES[i])) <= PUSH_RANGE) {
                threatened[i] = true;
            }
        }
        for (int i = 0; i < captives.length; i++) {
            near[i] = threatened[i] ? near[i] + dt : 0f;
            if (near[i] >= PUSH_TIME) {
                lose(world, store, i);
            }
        }
    }

    private void lose(World world, Store<EntityStore> store, int index) {
        lost[index] = true;
        near[index] = 0f;
        Vector3d at = Spawns.point(VolcanicLayout.CAPTIVES[index]);
        Telegraphs.particle(store, "Nakasar_Fractal_Captive_Fall", at, 1.2f);
        Spawns.remove(store, captives[index]);
        captives[index] = null;
        int count = 0;
        List<Integer> left = new ArrayList<>();
        for (int i = 0; i < lost.length; i++) {
            if (lost[i]) {
                count++;
            } else {
                left.add(i);
            }
        }
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "captive.lost").param("count", count)
                .param("total", lost.length));
        if (left.isEmpty()) {
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "captive.allLost"));
            reset(store);
            return;
        }
        for (Map.Entry<Ref<EntityStore>, Integer> e : new ArrayList<>(veterans.entrySet())) {
            if (e.getValue() == index) {
                aim(store, e.getKey(), left.get(ThreadLocalRandom.current().nextInt(left.size())));
            }
        }
    }

    // --- charges -----------------------------------------------------------------------------------------

    /** Coup sur le Champion (groupe de filtres) : invulnérable tant qu'il lui reste une charge (Kevin, 2026-10-24). */
    void filter(Ref<EntityStore> victim, Damage damage) {
        if (victim.equals(boss) && stacks > 0) {
            damage.setCancelled(true);
        }
    }

    /** Pierre imprégnée arrivée sur `target`. */
    void stone(World world, Store<EntityStore> store, Ref<EntityStore> target) {
        if (!target.equals(boss) || stacks <= 0) {
            return;
        }
        stacks--;
        showStacks();
        Vector3d at = Telegraphs.position(store, boss);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Rock_Impact", new Vector3d(at).add(0, 1.5, 0), 1f);
        }
        Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.stack").param("count", stacks));
        if (stacks == 0) {
            clearStones(world, store);
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.exposed"));
        }
    }

    /** Plus de pierres imprégnées, au sol comme en main : sans protection, elles ne servent à rien et bloquent la main. */
    private static void clearStones(World world, Store<EntityStore> store) {
        CrouchPickup.removeGround(world, store, Volcanic.STONE);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref != null && ref.isValid()) {
                CrouchPickup.removeAll(store, ref, Volcanic.STONE);
            }
        }
    }

    // --- remise à zéro et victoire ------------------------------------------------------------------------

    void idle(World world, Store<EntityStore> store, float dt) {
        if (!engaged || down) {
            return;
        }
        idle += dt;
        if (idle >= RESET_SECONDS) {
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.reset"));
            reset(store);
        }
    }

    /** Tout repart de zéro : Champion à pleine vie et charges, captifs revenus, vétérans retirés. */
    private void reset(Store<EntityStore> store) {
        engaged = false;
        idle = 0f;
        Spawns.removeAll(store, new ArrayList<>(veterans.keySet()));
        veterans.clear();
        if (boss != null) {
            LABELS.remove(boss);
            PinnedHealth.unpin(boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        for (int i = 0; i < captives.length; i++) {
            lost[i] = false;
            near[i] = 0f;
        }
    }

    private boolean finish(World world, Store<EntityStore> store) {
        down = false;
        engaged = false;
        Spawns.removeAll(store, new ArrayList<>(veterans.keySet()));
        veterans.clear();
        if (boss != null) {
            LABELS.remove(boss);
            PinnedHealth.unpin(boss);
        }
        clearStones(world, store);
        boolean allSaved = true;
        for (boolean l : lost) {
            allSaved &= !l;
        }
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            if (allSaved) {
                for (int k = 0; k < BONUS; k++) {
                    Carried.give(store, ref, SHARD);
                }
            }
        }
        if (allSaved) {
            Spawns.tellAll(world, Message.translation(Volcanic.MESSAGES + "champion.bonus"));
        }
        return true;
    }
}
