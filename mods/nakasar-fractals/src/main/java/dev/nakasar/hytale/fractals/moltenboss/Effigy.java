package dev.nakasar.hytale.fractals.moltenboss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * L'Effigie en fusion, championne de la fonderie (GW2). Coups et souffle : rôle JSON. En Java :
 * <ul>
 *   <li>protections en chaîne : le second résonateur rend le Protecteur invulnérable, le Protecteur rend l'Effigie
 *   invulnérable (rayon de lumière et icône) ;</li>
 *   <li>toutes les {@value #SHOCK_EVERY} s, elle frappe le sol : une onde blanche ({@link Shockwaves}) à sauter, qui
 *   repousse ;</li>
 *   <li>toutes les {@value #MIGHT_EVERY} s, une charge de Puissance (au plus {@value #MIGHT_MAX}) : ses coups
 *   font {@value #MIGHT_BONUS} de plus par charge.</li>
 * </ul>
 * Personne dans la fonderie : tout attend, avec les PV du moment (un boss ne revient jamais neuf, retour du
 * 2026-10-28 : l'Effigie avait repris ses PV en réapparaissant avec son Protecteur).
 */
final class Effigy {

    static final float SHOCK_FIRST = 8f;
    static final float SHOCK_EVERY = 12f;
    static final float SHOCK_WINDUP = 1.2f;
    static final float SHOCK_PART = 0.15f;
    static final float MIGHT_EVERY = 15f;
    static final int MIGHT_MAX = 5;
    static final float MIGHT_BONUS = 0.12f;

    /** Charges de Puissance par Effigie, pour la barre de boss. */
    private static final Map<Ref<EntityStore>, Integer> MIGHT = java.util.Collections.synchronizedMap(new WeakHashMap<>());

    private final Shockwaves waves = new Shockwaves();
    private Ref<EntityStore> effigy;
    private Ref<EntityStore> protector;
    private Ref<EntityStore> resonator;
    private final List<Ref<EntityStore>> adds = new ArrayList<>();
    private boolean engaged;
    private float shock;
    private float might;
    private int stacks;
    private int beat;

    static String label(Ref<EntityStore> boss) {
        Integer n = MIGHT.get(boss);
        return n == null || n <= 0 ? null : "▲".repeat(n);
    }

    float might() {
        return 1f + MIGHT_BONUS * stacks;
    }

    boolean shielded(Store<EntityStore> store, String role) {
        return switch (role) {
            case MoltenBoss.PROTECTOR -> resonator != null && Spawns.alive(store, resonator);
            case MoltenBoss.EFFIGY -> protector != null && Spawns.alive(store, protector);
            default -> false;
        };
    }

    /** Vrai quand l'Effigie est vaincue. */
    boolean step(World world, Store<EntityStore> store, MoltenBoss.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(MoltenBossLayout.EFFIGY);
        double radius = MoltenBossLayout.EFFIGY_RADIUS;
        if (!engaged) {
            if (!MoltenBoss.near(store, players, c, radius - 2).isEmpty()) {
                engage(world, store, c);
            }
            return false;
        }
        if (effigy == null || !Spawns.alive(store, effigy)) {
            clear();
            return true;
        }
        if (MoltenBoss.near(store, players, c, radius + 3).isEmpty()) {
            // Personne : tout s'arrête et attend, PV compris (ni soin ni retour à neuf, AGENTS.md).
            return false;
        }
        Leash.keepOnDisc(store, effigy, c, radius - 2, 2, MoltenBoss.FALL_LIMIT);
        if (resonator != null && !Spawns.alive(store, resonator)) {
            resonator = null;
        }
        if (protector != null && !Spawns.alive(store, protector)) {
            protector = null;
            Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "effigy.protector"));
        }
        boolean beam = ++beat % 4 == 0;
        if (protector != null) {
            Leash.keepOnDisc(store, protector, c, radius - 2, 2, MoltenBoss.FALL_LIMIT);
            MoltenBoss.link(store, protector, effigy, beam);
            if (resonator != null) {
                MoltenBoss.link(store, resonator, protector, beam);
            }
        }
        might += dt;
        if (might >= MIGHT_EVERY && stacks < MIGHT_MAX) {
            might = 0f;
            stacks++;
            MIGHT.put(effigy, stacks);
            Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "effigy.might").param("stacks", stacks));
        }
        shock += dt;
        if (shock >= SHOCK_EVERY) {
            shock = 0f;
            slam(world, store);
        }
        return false;
    }

    /** Annonce (poussière au sol sous l'Effigie), puis l'onde part de là où elle se tient. */
    private void slam(World world, Store<EntityStore> store) {
        Vector3d at = Telegraphs.position(store, effigy);
        if (at == null) {
            return;
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Windup_Ground", at, 2f);
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "effigy.shock"));
        Ref<EntityStore> boss = effigy;
        Delayed.later(world, SHOCK_WINDUP, s -> {
            if (boss != effigy || !Spawns.alive(s, boss)) {
                return;
            }
            Vector3d from = Telegraphs.position(s, boss);
            if (from != null) {
                Telegraphs.particle(s, "Stick_Slam_Ground_Large", from, 1.5f);
                waves.add(s, from, MoltenBossLayout.SHOCK_REACH_EFFIGY, Shockwaves.Kind.GROUND, SHOCK_PART);
            }
        });
    }

    void tick(World world, Store<EntityStore> store, float dt) {
        waves.tick(world, store, dt);
    }

    private void engage(World world, Store<EntityStore> store, Vector3d c) {
        Vector3d gate = Spawns.point(MoltenBossLayout.CHECKPOINT_B);
        effigy = Spawns.spawnBoss(world, store, MoltenBoss.EFFIGY, c, Telegraphs.yawToward(c, gate));
        if (effigy == null) {
            return;
        }
        engaged = true;
        protector = Spawns.spawnFoe(world, store, MoltenBoss.PROTECTOR, MoltenBossLayout.PROTECTOR);
        resonator = Spawns.spawnFoe(world, store, MoltenBoss.RESONATOR, MoltenBossLayout.RESONATOR_2);
        for (int i = 0; i < MoltenBossLayout.EFFIGY_ADDS.length; i++) {
            Ref<EntityStore> ref = Spawns.spawnFoe(world, store, MoltenBossLayout.EFFIGY_ADD_ROLES[i],
                    MoltenBossLayout.EFFIGY_ADDS[i]);
            if (ref != null) {
                adds.add(ref);
            }
        }
        shock = SHOCK_EVERY - SHOCK_FIRST;
        might = 0f;
        stacks = 0;
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Upgrade", c, 2f);
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "effigy.enter"));
    }

    /** Fin du combat (l'Effigie tombée) : ses gardes restent, à achever ou non. */
    private void clear() {
        waves.clear();
        if (effigy != null) {
            MIGHT.remove(effigy);
        }
        adds.clear();
        effigy = null;
        protector = null;
        resonator = null;
        stacks = 0;
    }
}
