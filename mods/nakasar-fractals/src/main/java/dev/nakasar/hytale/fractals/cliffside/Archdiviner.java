package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.boss.GroupHealth;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.TelegraphInteraction;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.defiance.Defiance;
import dev.nakasar.hytale.fractals.hammer.Hammer;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * L'Archidevin, boss de la Falaise. Son IA (JSON) frappe au marteau, lance le cône annoncé (défiance ouverte), le sol
 * corrompu et le brise-échine ; le Java mène le reste, quatre fois par seconde :
 * <ul>
 *   <li>transitions à 75, 50 et 25 % de vie, puis à 1 PV : la vie ne descend pas sous le seuil, le boss se fige,
 *   invulnérable, et puise dans le sceau du cou, qui perd sa bulle ; quatre incantateurs arrivent (de quoi charger le
 *   marteau, lâché aux pieds du boss si personne ne le porte). Un coup chargé sur le sceau met fin à la transition
 *   (onde qui étourdit 1 s, marteaux repris, bulle revenue) ; à la dernière, il achève le boss ;</li>
 *   <li>entre 50 et 25 % : protection (dégâts subis −33 %), cage toutes les {@value #CAGE_INTERVAL} s (cercle rouge
 *   sous un joueur, rayon 2 + niveau / 50 ; resté dedans, il est enfermé, {@link Cages}), deux dévoreurs toutes les
 *   {@value #DEVOURER_INTERVAL} s ({@value #DEVOURER_CAP} au plus) ;</li>
 *   <li>sous 25 % : hâte, frappes marquées toutes les {@value #MARK_INTERVAL} s sur trois joueurs au plus ; dès le
 *   niveau 71, forme démoniaque (dégâts ×1,3, {@link CliffsideDamageFilter}) ;</li>
 *   <li>dès le niveau 25 : ruée toutes les {@value #RUSH_INTERVAL} s (le boss surgit sur un joueur) ; dès le niveau 51,
 *   mur anti-projectiles avant 50 % ({@value #WALL_ON} s sur {@value #WALL_CYCLE}).</li>
 * </ul>
 * Personne dans l'arène pendant {@value #RESET_SECONDS} s : le boss revient, vie pleine. Vie selon le groupe
 * ({@link GroupHealth}) et le niveau (+1 % par niveau).
 */
final class Archdiviner {

    static final String ROLE = "Nakasar_Fractal_Archdiviner";
    static final String HASTE = "Nakasar_Fractal_Archdiviner_Haste";
    static final String PROTECTION = "Nakasar_Fractal_Archdiviner_Protection";
    static final String DEMON = "Nakasar_Fractal_Archdiviner_Demon";
    static final float CAGE_INTERVAL = 20f;
    static final float DEVOURER_INTERVAL = 30f;
    static final int DEVOURER_CAP = 4;
    static final float MARK_INTERVAL = 8f;
    static final float RUSH_INTERVAL = 16f;
    static final float WALL_CYCLE = 20f;
    static final float WALL_ON = 5f;
    static final float RESET_SECONDS = 20f;
    static final float HAMMER_AGAIN = 30f;
    private static final float[] THRESHOLDS = {0.75f, 0.50f, 0.25f, 0f};
    private static final String SCALE_MODIFIER = "Nakasar_Fractal_Boss_Scale";

    Ref<EntityStore> ref;
    /** Seuil suivant (index de {@link #THRESHOLDS}) ; 4 une fois vaincu. */
    int threshold;
    boolean transition;
    /** Seuil franchi, transition pas encore posée (le filtre annule déjà les coups). */
    volatile boolean pending;
    boolean victory;
    boolean wall;
    boolean demon;
    private boolean engaged;
    private float idle;
    private float cageClock;
    private float devourerClock;
    private float markClock;
    private float rushClock;
    private float wallClock;
    private float hammerClock;
    private float buffClock;
    private final List<Ref<EntityStore>> adds = new ArrayList<>();

    // --- pas de jeu ------------------------------------------------------------------------------

    void step(World world, Store<EntityStore> store, Cliffside.State st, List<PlayerRef> players, float dt) {
        if (victory) {
            return;
        }
        if (ref == null || !ref.isValid()) {
            spawn(world, store);
            if (ref == null) {
                return;
            }
        }
        adds.removeIf(a -> !Cliffside.alive(store, a));
        List<PlayerRef> inArena = new ArrayList<>();
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && Cliffside.inArena(at)) {
                inArena.add(player);
            }
        }
        if (inArena.isEmpty()) {
            idle(world, store, st, dt);
            return;
        }
        idle = 0f;
        engaged = true;
        if (transition) {
            keepHammer(world, store, dt);
            return;
        }
        int level = FractalRuns.level(world);
        float wf = FractalRuns.windupFactor(world);
        buffs(store, dt, level);
        if (threshold == 2) {
            cageClock += dt;
            if (cageClock >= CAGE_INTERVAL) {
                cageClock = 0f;
                cage(world, store, st, pick(inArena, 1), level, wf);
            }
            devourerClock += dt;
            if (devourerClock >= DEVOURER_INTERVAL) {
                devourerClock = 0f;
                devourers(world, store);
            }
        }
        if (threshold == 3) {
            markClock += dt;
            if (markClock >= MARK_INTERVAL) {
                markClock = 0f;
                for (PlayerRef p : pick(inArena, 3)) {
                    Vector3d at = Telegraphs.position(store, p.getReference());
                    if (at != null) {
                        TelegraphInteraction.spec("Mark", 2.4f * wf).damage(32f, "Physical")
                                .mark("Nakasar_Fractal_Corruption_Pulse", 0.8f).hit("Nakasar_Fractal_Bomb_Blast")
                                .launch(world, ref, p.getReference(), at, 0);
                    }
                }
            }
        }
        if (level >= 25) {
            rushClock += dt;
            if (rushClock >= RUSH_INTERVAL) {
                rushClock = 0f;
                for (PlayerRef p : pick(inArena, 1)) {
                    Vector3d at = Telegraphs.position(store, p.getReference());
                    if (at != null) {
                        TelegraphInteraction.spec("Circle", 1.6f * wf).radius(3f).damage(30f, "Physical")
                                .knockback(7f, 4f).playersOnly().teleportCaster()
                                .impact("Stick_Slam_Ground_Large", "SFX_Goblin_Feastmaster_Slam")
                                .launch(world, ref, p.getReference(), at, 0);
                    }
                }
            }
        }
        wallClock = (wallClock + dt) % WALL_CYCLE;
        boolean wallNow = level >= 51 && threshold <= 1 && wallClock < WALL_ON;
        if (wallNow && !wall) {
            Vector3d at = Telegraphs.position(store, ref);
            if (at != null) {
                Telegraphs.particle(store, "Nakasar_Fractal_Shield_Glow", new Vector3d(at).add(0, 1, 0), 2.2f);
            }
        }
        wall = wallNow;
    }

    /** Personne dans l'arène : au bout de {@value #RESET_SECONDS} s, le combat repart de zéro. */
    void idle(World world, Store<EntityStore> store, Cliffside.State st, float dt) {
        if (!engaged || victory) {
            return;
        }
        idle += dt;
        if (idle >= RESET_SECONDS) {
            reset(world, store, st);
        }
    }

    private void buffs(Store<EntityStore> store, float dt, int level) {
        buffClock -= dt;
        if (buffClock > 0f) {
            return;
        }
        buffClock = 1f;
        if (threshold == 2) {
            Hurt.effect(store, ref, PROTECTION, 1.5f);
        }
        if (threshold == 3) {
            Hurt.effect(store, ref, HASTE, 1.5f);
            if (level >= 71) {
                demon = true;
                Hurt.effect(store, ref, DEMON, 1.5f);
            }
        }
    }

    private void spawn(World world, Store<EntityStore> store) {
        double[] at = CliffsideLayout.BOSS_SPAWN;
        double[] c = CliffsideLayout.ARENA_CENTER;
        Vector3d where = new Vector3d(at[0], at[1], at[2]);
        ref = Cliffside.spawn(store, ROLE, where, Telegraphs.yawToward(where, new Vector3d(c[0], c[1], c[2])));
        if (ref != null) {
            float scale = GroupHealth.multiplier(FractalRuns.partySize(world)) * (1f + FractalRuns.level(world) / 100f);
            GroupHealth.apply(store.getComponent(ref, EntityStatMap.getComponentType()), SCALE_MODIFIER, scale);
        }
    }

    // --- seuils et transitions ------------------------------------------------------------------------

    /**
     * Filtre d'un coup sur le boss (thread du monde, groupe de filtres) : annule tout pendant une transition, les
     * projectiles derrière le mur, et arrête la vie au seuil suivant (la transition est posée juste après).
     */
    void filter(World world, Store<EntityStore> store, Ref<EntityStore> boss, Damage damage) {
        if (!boss.equals(ref) || victory || transition || pending) {
            damage.setCancelled(true);
            return;
        }
        if (wall && damage.getSource() instanceof Damage.ProjectileSource) {
            damage.setCancelled(true);
            return;
        }
        EntityStatMap stats = store.getComponent(boss, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || threshold >= THRESHOLDS.length) {
            return;
        }
        float floor = Math.max(1f, health.getMax() * THRESHOLDS[threshold]);
        if (health.get() - damage.getAmount() > floor) {
            return;
        }
        damage.setAmount(Math.max(0f, health.get() - floor));
        pending = true;
        world.execute(() -> begin(world, world.getEntityStore().getStore(), Cliffside.state(world)));
    }

    private void begin(World world, Store<EntityStore> store, Cliffside.State st) {
        pending = false;
        if (ref == null || !ref.isValid() || victory) {
            return;
        }
        transition = true;
        wall = false;
        store.ensureAndGetComponent(ref, Invulnerable.getComponentType());
        BossStun.hold(world, store, ref);
        st.seals[Cliffside.NECK].shielded = false;
        String key = threshold == THRESHOLDS.length - 1 ? "boss.final" : "boss.transition";
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(Cliffside.MESSAGES + key));
        }
        double[] c = CliffsideLayout.ARENA_CENTER;
        for (int k = 0; k < 4; k++) {
            double a = Math.PI / 4 + k * Math.PI / 2;
            Ref<EntityStore> add = Cliffside.spawnFoe(world, store, Cliffside.CHANTER,
                    new double[]{c[0] + Math.cos(a) * 9, c[1], c[2] + Math.sin(a) * 9});
            if (add != null) {
                adds.add(add);
            }
        }
        hammerClock = HAMMER_AGAIN;
        keepHammer(world, store, 0f);
    }

    /** Pendant une transition : si personne ne porte le marteau, il tombe aux pieds du boss (de nouveau toutes les 30 s). */
    private void keepHammer(World world, Store<EntityStore> store, float dt) {
        hammerClock += dt;
        if (hammerClock < HAMMER_AGAIN) {
            return;
        }
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> r = p.getReference();
            if (r != null && r.isValid() && Hammer.carries(store, r)) {
                hammerClock = HAMMER_AGAIN;   // regardé de nouveau au prochain passage
                return;
            }
        }
        hammerClock = 0f;
        Vector3d at = Telegraphs.position(store, ref);
        if (at != null) {
            Hammer.drop(store, new Vector3d(at).add(0, 0.5, 2));
        }
    }

    /** Coup chargé sur le sceau du cou : fin de la transition, ou victoire à la dernière. */
    void onNeckHit(World world, Store<EntityStore> store, Cliffside.State st) {
        if (!transition) {
            return;
        }
        if (threshold >= THRESHOLDS.length - 1) {
            win(world, store, st);
            return;
        }
        transition = false;
        threshold++;
        cageClock = 0f;
        devourerClock = DEVOURER_INTERVAL - 5f;
        markClock = 0f;
        st.seals[Cliffside.NECK].shielded = true;
        store.tryRemoveComponent(ref, Invulnerable.getComponentType());
        BossStun.release(store, ref);
        double[] c = CliffsideLayout.ARENA_CENTER;
        Vector3d center = new Vector3d(c[0], c[1], c[2]);
        Telegraphs.particle(store, "Stick_Slam_Ground_Large", center, 2f);
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> r = p.getReference();
            Vector3d at = Telegraphs.position(store, r);
            if (at != null && at.distance(center) <= 20) {
                Hurt.effect(store, r, "Hazard_Electric_Stun", 1f);
            }
            if (r != null && r.isValid() && Hammer.carries(store, r)) {
                Hammer.remove(store, r);
            }
            p.sendMessage(Message.translation(Cliffside.MESSAGES + "boss.transitionEnd"));
        }
    }

    private void win(World world, Store<EntityStore> store, Cliffside.State st) {
        victory = true;
        transition = false;
        threshold = THRESHOLDS.length;
        Defiance.forget(ref);
        BossStun.release(store, ref);
        Vector3d at = Telegraphs.position(store, ref);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Seal_Break", at, 2f);
        }
        removeAll(store);
        Cliffside.Seal neck = st.seals[Cliffside.NECK];
        neck.broken = true;
        if (neck.ref != null && neck.ref.isValid()) {
            store.removeEntity(neck.ref, RemoveReason.REMOVE);
        }
        neck.ref = null;
        st.cages.releaseAll(world, store);
        st.stage = Cliffside.Stage.DONE;
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> r = p.getReference();
            if (r != null && r.isValid() && Hammer.carries(store, r)) {
                Hammer.remove(store, r);
            }
        }
        ChunkStore chunks = world.getChunkStore();
        int[] chest = CliffsideLayout.REWARD;
        int[] exit = CliffsideLayout.END_EXIT;
        WorldBlocks.setFacingOpen(chunks, chest[0], chest[1], chest[2], "Nakasar_Fractal_Reward_Chest");
        WorldBlocks.setFacingOpen(chunks, exit[0], exit[1], exit[2], "Nakasar_Fractal_Exit_Stone");
        FractalRuns.complete(world);
        EventTitleUtil.showEventTitleToWorld(Message.translation(Cliffside.MESSAGES + "title.victory"),
                Message.translation(Cliffside.MESSAGES + "boss.victory"), EventTitleStyle.Major, null, 4f, 0.4f, 1f, world);
    }

    private void reset(World world, Store<EntityStore> store, Cliffside.State st) {
        engaged = false;
        idle = 0f;
        threshold = 0;
        transition = false;
        pending = false;
        wall = false;
        demon = false;
        cageClock = devourerClock = markClock = rushClock = wallClock = 0f;
        if (ref != null) {
            Defiance.forget(ref);
        }
        removeAll(store);
        st.seals[Cliffside.NECK].shielded = true;
        st.cages.releaseAll(world, store);
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(Cliffside.MESSAGES + "boss.reset"));
        }
    }

    private void removeAll(Store<EntityStore> store) {
        if (ref != null && ref.isValid()) {
            store.removeEntity(ref, RemoveReason.REMOVE);
        }
        ref = null;
        for (Ref<EntityStore> add : adds) {
            if (add.isValid()) {
                store.removeEntity(add, RemoveReason.REMOVE);
            }
        }
        adds.clear();
    }

    // --- mécaniques ---------------------------------------------------------------------------------------

    /** Cercle rouge sous la cible ; restée dedans au coup, elle part en cage. */
    private void cage(World world, Store<EntityStore> store, Cliffside.State st, List<PlayerRef> targets, int level, float wf) {
        for (PlayerRef target : targets) {
            Ref<EntityStore> r = target.getReference();
            Vector3d at = Telegraphs.position(store, r);
            if (at == null) {
                continue;
            }
            Vector3d center = new Vector3d(at);
            double radius = 2 + level / 50.0;
            float seconds = 2.2f * wf;
            Telegraphs.circle(store, center, radius, seconds);
            Delayed.later(world, seconds, s -> {
                Vector3d now = Telegraphs.position(s, r);
                if (now != null && !victory && Telegraphs.horizontal(now, center) <= radius && Math.abs(now.y() - center.y()) <= 2.5) {
                    if (st.cages.imprison(world, s, r, target)) {
                        target.sendMessage(Message.translation(Cliffside.MESSAGES + "cage.jailed"));
                    }
                }
            });
        }
    }

    private void devourers(World world, Store<EntityStore> store) {
        long alive = adds.stream().filter(a -> Cliffside.DEVOURER.equals(Cliffside.role(store, a))).count();
        double[] c = CliffsideLayout.ARENA_CENTER;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int k = 0; k < 2 && alive < DEVOURER_CAP; k++, alive++) {
            double a = random.nextDouble(Math.PI * 2);
            Ref<EntityStore> add = Cliffside.spawnFoe(world, store, Cliffside.DEVOURER,
                    new double[]{c[0] + Math.cos(a) * 11, c[1], c[2] + Math.sin(a) * 11});
            if (add != null) {
                adds.add(add);
            }
        }
    }

    private static List<PlayerRef> pick(List<PlayerRef> players, int count) {
        List<PlayerRef> copy = new ArrayList<>(players);
        Collections.shuffle(copy);
        return copy.subList(0, Math.min(count, copy.size()));
    }
}
