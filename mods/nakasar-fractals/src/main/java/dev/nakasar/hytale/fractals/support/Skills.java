package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Les 14 runes et les objets de soutien des fractales (Kevin, 26 octobre 2026). Chaque effet est lancé par
 * {@link SupportCastInteraction} sur le thread du monde ; il rend faux s'il n'a rien pu faire (pas de cible), et alors
 * ni mana, ni recharge, ni objet ne sont dépensés.
 *
 * <p>Toutes les tailles (rayons, longueurs, angles) sont ici : la même constante sert au dessin de la zone et au test
 * de qui est dedans (consigne permanente n° 3). Les nombres sont repris par tools/generate_support.py pour les
 * descriptions : les deux se modifient ensemble.
 */
public final class Skills {

    // --- particules : vanilla d'abord (soin, feu, givre, glace), les autres de tools/generate_support.py ----------
    static final String FX_HEAL = "Effect_Health_Pack";
    static final String FX_FROST = "Effect_Snow";
    static final String FX_FIRE = "Effect_Fire";
    static final String FX_ICE = "Impact_Ice";
    static final String FX_SANCTUARY = "Nakasar_Fractal_Support_Sanctuary";
    static final String FX_GRAVITY = "Nakasar_Fractal_Support_Gravity";
    static final String FX_SMOKE = "Nakasar_Fractal_Support_Smoke";
    static final String FX_BEAM = "Nakasar_Fractal_Support_Beam";
    static final String FX_BANNER = "Nakasar_Fractal_Support_Banner";
    static final String FX_WARD = "Nakasar_Fractal_Support_Ward";
    static final String FX_SHOCK = "Nakasar_Fractal_Support_Shock";
    static final String FX_ROOTS = "Nakasar_Fractal_Support_Roots";
    static final String FX_FLASH = "Nakasar_Fractal_Support_Flash";
    static final String FX_TRAIL = "Nakasar_Fractal_Support_Trail";
    /** Onde au sol du jeu (déjà employée par la barre de défiance). */
    static final String FX_SLAM = "Stick_Slam_Ground_Large";

    static final String EFFECT_REGEN = "Nakasar_Fractal_Support_Regen";
    static final String EFFECT_AEGIS = "Nakasar_Fractal_Support_Aegis";
    static final String EFFECT_REPRIEVE = "Nakasar_Fractal_Support_Reprieve";
    static final String EFFECT_SPARED = "Nakasar_Fractal_Support_Spared";
    static final String EFFECT_SLOWED = "Nakasar_Fractal_Support_Slowed";
    static final String EFFECT_FEARED = "Nakasar_Fractal_Support_Feared";
    static final String EFFECT_DAZED = "Nakasar_Fractal_Support_Dazed";
    static final String EFFECT_MIGHT = "Nakasar_Fractal_Support_Might";
    static final String EFFECT_GUARD = "Nakasar_Fractal_Support_Guard";
    /** Brûlure du jeu (déjà posée par les fractales). */
    static final String EFFECT_BURN = "Burn";

    // --- tailles et valeurs -------------------------------------------------------------------------
    static final double AIM_RANGE = 12;

    static final double BREATH_RANGE = 6;
    static final double BREATH_ANGLE = 60;
    static final float BREATH_HEAL = 20f;
    static final float BREATH_REGEN = 4f;
    static final float BREATH_REGEN_SECONDS = 5f;

    static final double TRANSFUSION_RANGE = 16;
    static final double TRANSFUSION_BREAK = 20;
    static final float TRANSFUSION_SECONDS = 3f;
    static final float TRANSFUSION_HEAL = 10f;
    static final float TRANSFUSION_COST = 5f;

    static final double AEGIS_RADIUS = 5;
    static final float AEGIS_SECONDS = 8f;

    static final double REPRIEVE_RADIUS = 6;
    static final float REPRIEVE_SECONDS = 10f;
    static final float REPRIEVE_SPARE = 1.5f;

    static final double SHOCK_RADIUS = 4;
    static final float SHOCK_DAMAGE = 8f;
    static final double SHOCK_PUSH = 9;
    static final int SHOCK_DEFIANCE = 3;

    static final double DAZE_RANGE = 20;
    static final float DAZE_SECONDS = 3f;
    static final int DAZE_DEFIANCE = 2;

    static final double WELL_RADIUS = 4;
    static final float WELL_DELAY = 1.5f;
    static final float WELL_STUN = 1f;
    static final int WELL_DEFIANCE = 4;

    static final double FEAR_RADIUS = 6;
    static final float FEAR_SECONDS = 2f;
    static final int FEAR_DEFIANCE = 2;

    static final double HEAL_WELL_RADIUS = 4;
    static final float HEAL_WELL_SECONDS = 6f;
    static final float HEAL_WELL_HEAL = 5f;
    static final float HEAL_WELL_STAMINA = 3f;

    static final double GLYPH_RADIUS = 4;
    static final float GLYPH_SECONDS = 8f;
    static final float GLYPH_SLOW = 0.5f;

    static final double BRAZIER_RADIUS = 3;
    static final float BRAZIER_SECONDS = 5f;
    static final float BRAZIER_DAMAGE = 6f;
    static final float BRAZIER_BURN = 3f;

    static final double LINE_LENGTH = 7;
    static final double LINE_WIDTH = 1;
    static final double LINE_AHEAD = 3;
    static final float LINE_SECONDS = 8f;
    static final float LINE_ROOT = 1.5f;

    static final double SANCTUARY_RADIUS = 4;
    static final float SANCTUARY_SECONDS = 5f;

    static final double STAFF_RANGE = 12;
    static final float STAFF_REGEN = 6f;
    static final float STAFF_SECONDS = 3f;
    static final float STAFF_COOLDOWN = 8f;

    static final double GRIMOIRE_RADIUS = 2.5;
    static final float GRIMOIRE_SECONDS = 5f;
    static final float GRIMOIRE_COOLDOWN = 15f;

    static final double VINES_LENGTH = 6;
    static final double VINES_WIDTH = 1;
    static final float VINES_ROOT = 1f;
    static final int VINES_DEFIANCE = 2;
    static final float VINES_COOLDOWN = 15f;

    static final double TOTEM_RADIUS = 5;
    static final float TOTEM_SECONDS = 15f;
    static final float TOTEM_HEAL = 4f;
    static final float TOTEM_SLOW = 0.4f;

    static final double BOMB_RADIUS = 3;
    static final float BOMB_STUN = 2f;
    static final int BOMB_DEFIANCE = 3;
    static final float THROW_SECONDS = 0.4f;

    static final double SMOKE_RADIUS = 4;
    static final float SMOKE_SECONDS = 6f;

    static final double BANNER_RADIUS = 8;
    static final float BANNER_SECONDS = 30f;
    static final float BANNER_COOLDOWN = 60f;

    /** Totems posés par monde : un de chaque sorte par groupe, le dernier posé remplace l'autre. */
    private static final Map<World, Map<String, Zone>> TOTEMS = new WeakHashMap<>();

    private Skills() {
    }

    // --- soins --------------------------------------------------------------------------------------

    /** Souffle régénérant : cône devant soi ; soin immédiat et régénération, lanceur compris. */
    static boolean healingBreath(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d from = Telegraphs.position(store, caster);
        if (from == null) {
            return false;
        }
        Vector3d flat = Moves.flatLook(store, caster);
        double facing = Math.atan2(flat.z(), flat.x());
        double half = Math.toRadians(BREATH_ANGLE / 2);
        for (Ref<EntityStore> player : Support.playersNear(world, store, from, BREATH_RANGE)) {
            Vector3d at = Telegraphs.position(store, player);
            boolean inCone = player.equals(caster) || Math.abs(wrap(Telegraphs.angle(from, at) - facing)) <= half
                    + Math.atan2(Telegraphs.BODY, Math.max(0.5, Telegraphs.horizontal(from, at)));
            if (inCone) {
                Support.heal(store, player, BREATH_HEAL);
                regen(world, player, BREATH_REGEN, BREATH_REGEN_SECONDS);
            }
        }
        // Dessin : l'arc au bout du cône, ses deux bords et des points dedans.
        for (int k = 0; k <= 10; k++) {
            double a = facing - half + 2 * half * k / 10;
            Telegraphs.particle(store, FX_HEAL, new Vector3d(from).add(Math.cos(a) * BREATH_RANGE, 0.6, Math.sin(a) * BREATH_RANGE), 1f);
        }
        for (int k = 1; k <= 5; k++) {
            double r = BREATH_RANGE * k / 6;
            for (double a : new double[]{facing - half, facing, facing + half}) {
                Telegraphs.particle(store, FX_HEAL, new Vector3d(from).add(Math.cos(a) * r, 0.8, Math.sin(a) * r), 1f);
            }
        }
        Telegraphs.sound(store, "SFX_Light_Melee_T2_Swing", from);
        return true;
    }

    /** Régénération : `perSecond` PV par seconde pendant `seconds` s (icône d'effet le temps qu'elle dure). */
    static void regen(World world, Ref<EntityStore> player, float perSecond, float seconds) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Hurt.effect(store, player, EFFECT_REGEN, seconds);
        long[] next = {-1};
        long[] end = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (end[0] < 0) {
                end[0] = now + Telegraphs.seconds(seconds);
                next[0] = now + Telegraphs.seconds(1f);
            }
            if (!player.isValid() || Telegraphs.position(s, player) == null) {
                return true;
            }
            if (now >= next[0]) {
                next[0] += Telegraphs.seconds(1f);
                Support.heal(s, player, perSecond);
                Vector3d at = Telegraphs.position(s, player);
                Telegraphs.particle(s, FX_HEAL, new Vector3d(at).add(0, 1.0, 0), 0.8f);
            }
            return now >= end[0];
        });
    }

    /** Transfusion : rayon canalisé vers un allié visé ; il gagne des PV, le lanceur en perd (jamais jusqu'à mourir). */
    static boolean transfusion(World world, Store<EntityStore> store, Ref<EntityStore> caster, Ref<EntityStore> ally) {
        if (ally == null || !ally.isValid()) {
            return false;
        }
        Hurt.effect(store, ally, EFFECT_REGEN, TRANSFUSION_SECONDS);
        float step = 0.25f;
        long[] next = {-1};
        long[] end = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (end[0] < 0) {
                end[0] = now + Telegraphs.seconds(TRANSFUSION_SECONDS);
                next[0] = now;
            }
            Vector3d a = Telegraphs.position(s, caster);
            Vector3d b = Telegraphs.position(s, ally);
            if (a == null || b == null || a.distance(b) > TRANSFUSION_BREAK) {
                return true;
            }
            if (now >= next[0]) {
                next[0] += Telegraphs.seconds(step);
                Support.heal(s, ally, TRANSFUSION_HEAL * step);
                Support.drain(s, caster, TRANSFUSION_COST * step);
                beam(s, a, b);
            }
            return now >= end[0];
        });
        return true;
    }

    private static void beam(Store<EntityStore> store, Vector3d a, Vector3d b) {
        int n = Math.max(3, (int) Math.ceil(a.distance(b) / 1.5));
        for (int k = 0; k <= n; k++) {
            Telegraphs.particle(store, FX_BEAM, new Vector3d(a).add(0, 1.1, 0).lerp(new Vector3d(b).add(0, 1.1, 0), (double) k / n), 0.7f);
        }
    }

    /** Égide des Brumes : le lanceur et les joueurs à {@value #AEGIS_RADIUS} blocs ignorent le prochain coup direct. */
    static boolean aegis(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        long until = System.nanoTime() + Telegraphs.seconds(AEGIS_SECONDS);
        for (Ref<EntityStore> player : Support.playersNear(world, store, at, AEGIS_RADIUS)) {
            SupportStates.AEGIS.put(player, until);
            Hurt.effect(store, player, EFFECT_AEGIS, AEGIS_SECONDS);
            Vector3d p = Telegraphs.position(store, player);
            Telegraphs.particle(store, FX_WARD, new Vector3d(p).add(0, 1.0, 0), 1f);
        }
        Support.disk(store, FX_WARD, at, AEGIS_RADIUS, 1.2, 0, 0.6f);
        Telegraphs.sound(store, "SFX_Light_Melee_T2_Swing", at);
        return true;
    }

    /** Sursis : les joueurs à {@value #REPRIEVE_RADIUS} blocs sont couverts ; le premier coup mortel est évité. */
    static boolean reprieve(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        long until = System.nanoTime() + Telegraphs.seconds(REPRIEVE_SECONDS);
        SupportStates.Reprieve shared = new SupportStates.Reprieve(until);
        for (Ref<EntityStore> player : Support.playersNear(world, store, at, REPRIEVE_RADIUS)) {
            SupportStates.REPRIEVE.put(player, shared);
            Hurt.effect(store, player, EFFECT_REPRIEVE, REPRIEVE_SECONDS);
        }
        Support.disk(store, FX_WARD, at, REPRIEVE_RADIUS, 1.2, 6, 0.6f);
        return true;
    }

    // --- perturbation ------------------------------------------------------------------------------

    /** Onde de choc : recul et dégâts autour de soi ; défiance sur un boss. */
    static boolean shockwave(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        for (Ref<EntityStore> foe : Support.foesNear(world, store, at, SHOCK_RADIUS)) {
            Support.damage(store, caster, foe, SHOCK_DAMAGE);
            if (Support.immune(store, foe)) {
                Support.defiance(world, store, foe, SHOCK_DEFIANCE);
            } else {
                Support.push(store, foe, at, SHOCK_PUSH, 3);
            }
        }
        Telegraphs.particle(store, FX_SLAM, at, 1f);
        Support.disk(store, FX_SHOCK, at, SHOCK_RADIUS, 0.8, 6, 1f);
        Telegraphs.sound(store, "SFX_Mace_T2_Signature_Impact", at);
        return true;
    }

    /** Hébètement : la cible visée n'attaque plus pendant {@value #DAZE_SECONDS} s (son attaque en cours est coupée). */
    static boolean daze(World world, Store<EntityStore> store, Ref<EntityStore> caster, Ref<EntityStore> foe) {
        if (foe == null || !foe.isValid()) {
            return false;
        }
        trail(world, store, caster, foe);
        if (Support.immune(store, foe)) {
            Support.defiance(world, store, foe, DAZE_DEFIANCE);
            return true;
        }
        Hurt.effect(store, foe, EFFECT_DAZED, DAZE_SECONDS);
        long[] end = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (end[0] < 0) {
                end[0] = now + Telegraphs.seconds(DAZE_SECONDS);
            }
            if (!foe.isValid() || Telegraphs.position(s, foe) == null) {
                return true;
            }
            BossStun.interrupt(w, s, foe);
            return now >= end[0];
        });
        return true;
    }

    /** Traînée de particules de l'œil du lanceur vers la cible (projectile visuel). */
    private static void trail(World world, Store<EntityStore> store, Ref<EntityStore> caster, Ref<EntityStore> target) {
        Vector3d a = Telegraphs.position(store, caster);
        Vector3d b = Telegraphs.position(store, target);
        if (a == null || b == null) {
            return;
        }
        Vector3d from = new Vector3d(a).add(0, 1.5, 0);
        Vector3d to = new Vector3d(b).add(0, 1.0, 0);
        int n = Math.max(3, (int) Math.ceil(from.distance(to) / 1.2));
        for (int k = 0; k <= n; k++) {
            Telegraphs.particle(store, FX_TRAIL, new Vector3d(from).lerp(to, (double) k / n), 0.6f);
        }
    }

    /** Puits gravitationnel : au bout de {@value #WELL_DELAY} s, attire les ennemis au centre et les étourdit. */
    static boolean gravityWell(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = Support.aimGround(world, store, caster, AIM_RANGE);
        if (center == null) {
            return false;
        }
        long[] start = {-1};
        long[] nextDraw = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (start[0] < 0) {
                start[0] = now;
                nextDraw[0] = now;
            }
            if (now >= nextDraw[0]) {
                nextDraw[0] += Telegraphs.seconds(0.3f);
                Support.disk(s, FX_GRAVITY, center, WELL_RADIUS, 1.0, 8, 0.8f);
            }
            if (now - start[0] < Telegraphs.seconds(WELL_DELAY)) {
                return false;
            }
            for (Ref<EntityStore> foe : Support.foesNear(w, s, center, WELL_RADIUS)) {
                if (Support.immune(s, foe)) {
                    Support.defiance(w, s, foe, WELL_DEFIANCE);
                    continue;
                }
                Vector3d at = Telegraphs.position(s, foe);
                double d = Telegraphs.horizontal(at, center);
                double a = Telegraphs.angle(at, center);
                double speed = Math.min(14, d / 0.5);
                Support.velocity(s, foe, new Vector3d(Math.cos(a) * speed, 3, Math.sin(a) * speed));
                w.execute(() -> {
                    Store<EntityStore> s2 = w.getEntityStore().getStore();
                    if (foe.isValid()) {
                        TelegraphSystem.start(w, delayed(0.5f, (w3, s3) -> Support.stun(w3, s3, foe, WELL_STUN, 0)));
                    }
                });
            }
            Telegraphs.particle(s, FX_SLAM, center, 0.8f);
            Telegraphs.sound(s, "SFX_Mace_T2_Signature_Impact", center);
            return true;
        });
        return true;
    }

    /** Épouvante : les ennemis à {@value #FEAR_RADIUS} blocs fuient le lanceur. */
    static boolean fear(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        long until = System.nanoTime() + Telegraphs.seconds(FEAR_SECONDS);
        for (Ref<EntityStore> foe : Support.foesNear(world, store, at, FEAR_RADIUS)) {
            if (Support.immune(store, foe)) {
                Support.defiance(world, store, foe, FEAR_DEFIANCE);
                continue;
            }
            BossStun.interrupt(world, store, foe);
            SupportStates.FEARS.put(foe, new SupportStates.Fear(new Vector3d(at), until));
            Hurt.effect(store, foe, EFFECT_FEARED, FEAR_SECONDS);
        }
        Support.disk(store, FX_GRAVITY, at, FEAR_RADIUS, 1.2, 6, 0.6f);
        return true;
    }

    // --- zones --------------------------------------------------------------------------------------

    /**
     * Zone au sol qui dure : `apply` toutes les `every` secondes, dessin toutes les `drawEvery` secondes. Une zone
     * se retire d'elle-même à la fin ou quand on la {@link #stop}.
     */
    static final class Zone implements TelegraphSystem.Task {
        final float seconds;
        final float every;
        final float drawEvery;
        final ZoneStep apply;
        final ZoneStep draw;
        long end = -1;
        long nextApply;
        long nextDraw;
        volatile boolean stopped;

        Zone(float seconds, float every, float drawEvery, ZoneStep apply, ZoneStep draw) {
            this.seconds = seconds;
            this.every = every;
            this.drawEvery = drawEvery;
            this.apply = apply;
            this.draw = draw;
        }

        void stop() {
            stopped = true;
        }

        @Override
        public boolean step(World world, Store<EntityStore> store, long now) {
            if (end < 0) {
                end = now + Telegraphs.seconds(seconds);
                nextApply = now;
                nextDraw = now;
            }
            if (stopped) {
                return true;
            }
            if (now >= nextDraw) {
                nextDraw += Telegraphs.seconds(drawEvery);
                draw.run(world, store, now);
            }
            if (now >= nextApply) {
                nextApply += Telegraphs.seconds(every);
                apply.run(world, store, now);
            }
            return now >= end;
        }
    }

    interface ZoneStep {
        void run(World world, Store<EntityStore> store, long now);
    }

    interface Later {
        void run(World world, Store<EntityStore> store);
    }

    static TelegraphSystem.Task delayed(float seconds, Later action) {
        long[] at = {-1};
        return (w, s, now) -> {
            if (at[0] < 0) {
                at[0] = now + Telegraphs.seconds(seconds);
            }
            if (now < at[0]) {
                return false;
            }
            action.run(w, s);
            return true;
        };
    }

    /** Puits de soin : les joueurs dedans regagnent PV et endurance chaque seconde. */
    static boolean healingWell(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = Telegraphs.position(store, caster);
        if (center == null) {
            return false;
        }
        Vector3d c = new Vector3d(center);
        TelegraphSystem.start(world, healZone(c, HEAL_WELL_RADIUS, HEAL_WELL_SECONDS, HEAL_WELL_HEAL, HEAL_WELL_STAMINA));
        return true;
    }

    static Zone healZone(Vector3d center, double radius, float seconds, float heal, float stamina) {
        return new Zone(seconds, 1f, 0.5f,
                (w, s, now) -> {
                    for (Ref<EntityStore> p : Support.playersNear(w, s, center, radius)) {
                        Support.heal(s, p, heal);
                        Support.stamina(s, p, stamina);
                    }
                },
                (w, s, now) -> Support.disk(s, FX_HEAL, center, radius, 1.2, (int) Math.ceil(radius * 2), 1f));
    }

    /** Ralentit les ennemis dans le disque (part `slow`, {@value Support#MECHANIC_SLOW} au plus sur un PNJ de mécanique). */
    static Zone slowZone(String source, Vector3d center, double radius, float seconds, float slow) {
        return new Zone(seconds, 0.25f, 0.5f,
                (w, s, now) -> {
                    for (Ref<EntityStore> foe : Support.foesNear(w, s, center, radius)) {
                        slowFoe(s, foe, source, slow, 0.5f);
                    }
                },
                (w, s, now) -> Support.disk(s, FX_FROST, center, radius, 1.0, (int) Math.ceil(radius * 3), 1f));
    }

    /** Ralentit un ennemi pendant `seconds` s (un boss l'est aussi : seul le PNJ de mécanique est plafonné). */
    static void slowFoe(Store<EntityStore> store, Ref<EntityStore> foe, String source, float slow, float seconds) {
        float part = Support.isMechanic(store, foe) ? Math.min(slow, Support.MECHANIC_SLOW) : slow;
        SupportStates.slow(foe, source, part, System.nanoTime() + Telegraphs.seconds(seconds));
        if (Hurt.remaining(store, foe, EFFECT_SLOWED) < 0.3f) {
            Hurt.effect(store, foe, EFFECT_SLOWED, seconds + 0.3f);
        }
    }

    /** Glyphe de gel : disque visé où les ennemis sont ralentis. */
    static boolean frostGlyph(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        return glyph(world, store, caster, GLYPH_RADIUS, GLYPH_SECONDS);
    }

    static boolean glyph(World world, Store<EntityStore> store, Ref<EntityStore> caster, double radius, float seconds) {
        Vector3d center = Support.aimGround(world, store, caster, AIM_RANGE);
        if (center == null) {
            return false;
        }
        TelegraphSystem.start(world, slowZone("Glyph", center, radius, seconds, GLYPH_SLOW));
        Telegraphs.sound(store, "SFX_Light_Melee_T2_Swing", center);
        return true;
    }

    /** Brasier des Brumes : disque visé qui brûle les ennemis ; en sortir les laisse brûler un peu. */
    static boolean brazier(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = Support.aimGround(world, store, caster, AIM_RANGE);
        if (center == null) {
            return false;
        }
        Set<Ref<EntityStore>> inside = new HashSet<>();
        TelegraphSystem.start(world, new Zone(BRAZIER_SECONDS, 1f, 0.4f,
                (w, s, now) -> {
                    List<Ref<EntityStore>> now2 = Support.foesNear(w, s, center, BRAZIER_RADIUS);
                    for (Ref<EntityStore> left : inside) {
                        if (!now2.contains(left) && left.isValid()) {
                            Hurt.effect(s, left, EFFECT_BURN, BRAZIER_BURN);
                        }
                    }
                    inside.clear();
                    for (Ref<EntityStore> foe : now2) {
                        Support.damage(s, caster, foe, BRAZIER_DAMAGE);
                        inside.add(foe);
                    }
                },
                (w, s, now) -> Support.disk(s, FX_FIRE, center, BRAZIER_RADIUS, 0.9, 10, 1f)));
        return true;
    }

    /** Ligne de givre : barrière en travers du regard ; le premier passage d'un ennemi l'immobilise. */
    static boolean frostLine(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d feet = Telegraphs.position(store, caster);
        if (feet == null) {
            return false;
        }
        Vector3d flat = Moves.flatLook(store, caster);
        Vector3d center = new Vector3d(feet).add(flat.x() * LINE_AHEAD, 0, flat.z() * LINE_AHEAD);
        double axis = Math.atan2(flat.z(), flat.x()) + Math.PI / 2;
        Set<Ref<EntityStore>> caught = new HashSet<>();
        TelegraphSystem.start(world, new Zone(LINE_SECONDS, 0.1f, 0.5f,
                (w, s, now) -> {
                    for (Ref<EntityStore> foe : Support.foes(w, s)) {
                        Vector3d at = Telegraphs.position(s, foe);
                        if (at == null || caught.contains(foe) || !Support.inStrip(at, center, axis, LINE_LENGTH, LINE_WIDTH)) {
                            continue;
                        }
                        caught.add(foe);
                        if (Support.isMechanic(s, foe)) {
                            slowFoe(s, foe, "Line", Support.MECHANIC_SLOW, LINE_ROOT);
                        } else if (!Support.immune(s, foe)) {
                            Support.stun(w, s, foe, LINE_ROOT, 0);
                            Telegraphs.particle(s, FX_ICE, at, 1.2f);
                        }
                    }
                },
                (w, s, now) -> Support.strip(s, FX_ICE, center, axis, LINE_LENGTH, LINE_WIDTH, 0.7, 0.8f)));
        return true;
    }

    /** Sanctuaire : dôme autour du lanceur qui détruit les projectiles ennemis ({@link SanctuarySystem}). */
    static boolean sanctuary(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        Vector3d center = new Vector3d(at);
        SanctuarySystem.Dome dome = SanctuarySystem.raise(world, center, SANCTUARY_RADIUS, SANCTUARY_SECONDS);
        TelegraphSystem.start(world, new Zone(SANCTUARY_SECONDS, 1f, 0.4f, (w, s, now) -> {
        }, (w, s, now) -> {
            Support.disk(s, FX_SANCTUARY, center, SANCTUARY_RADIUS, 1.2, 4, 0.9f);
            // la voûte : trois anneaux qui se resserrent vers le sommet (rayon × cos, hauteur rayon × sin)
            for (double lat : new double[]{0.5, 0.95, 1.3}) {
                double r = SANCTUARY_RADIUS * Math.cos(lat);
                int n = Math.max(4, (int) Math.ceil(2 * Math.PI * r / 1.6));
                for (int k = 0; k < n; k++) {
                    double a = 2 * Math.PI * k / n;
                    Telegraphs.particle(s, FX_SANCTUARY, new Vector3d(center).add(Math.cos(a) * r,
                            SANCTUARY_RADIUS * Math.sin(lat), Math.sin(a) * r), 0.8f);
                }
            }
        }));
        return dome != null;
    }

    // --- objets ------------------------------------------------------------------------------------

    /** Bâton (clic droit) : régénération sur l'allié visé. */
    static boolean staffMend(World world, Store<EntityStore> store, Ref<EntityStore> caster, Ref<EntityStore> ally) {
        if (ally == null || !ally.isValid()) {
            return false;
        }
        regen(world, ally, STAFF_REGEN, STAFF_SECONDS);
        Vector3d a = Telegraphs.position(store, caster);
        Vector3d b = Telegraphs.position(store, ally);
        beam(store, a, b);
        return true;
    }

    /** Grimoire (clic droit) : petite glyphe de gel. */
    static boolean grimoireGlyph(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        return glyph(world, store, caster, GRIMOIRE_RADIUS, GRIMOIRE_SECONDS);
    }

    /** Baguette (clic droit) : vrilles en ligne droite devant soi qui enracinent. */
    static boolean wandVines(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d feet = Telegraphs.position(store, caster);
        if (feet == null) {
            return false;
        }
        Vector3d flat = Moves.flatLook(store, caster);
        double half = 0.5 + VINES_LENGTH / 2;
        Vector3d center = new Vector3d(feet).add(flat.x() * half, 0, flat.z() * half);
        double axis = Math.atan2(flat.z(), flat.x());
        for (Ref<EntityStore> foe : Support.foes(world, store)) {
            Vector3d at = Telegraphs.position(store, foe);
            if (at != null && Support.inStrip(at, center, axis, VINES_LENGTH, VINES_WIDTH)) {
                Support.stun(world, store, foe, VINES_ROOT, VINES_DEFIANCE);
            }
        }
        Support.strip(store, FX_ROOTS, center, axis, VINES_LENGTH, VINES_WIDTH, 0.6, 1f);
        return true;
    }

    /** Totem de soin des Brumes : zone de soin à ses pieds (un par groupe). */
    static boolean healingTotem(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        replaceTotem(world, "Heal", healZone(new Vector3d(at), TOTEM_RADIUS, TOTEM_SECONDS, TOTEM_HEAL, 0f));
        return true;
    }

    /** Totem de lenteur des Brumes : zone de ralentissement à ses pieds (un par groupe). */
    static boolean slownessTotem(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        replaceTotem(world, "Slow", slowZone("Totem", new Vector3d(at), TOTEM_RADIUS, TOTEM_SECONDS, TOTEM_SLOW));
        return true;
    }

    private static void replaceTotem(World world, String kind, Zone zone) {
        synchronized (TOTEMS) {
            Zone old = TOTEMS.computeIfAbsent(world, w -> new java.util.HashMap<>()).put(kind, zone);
            if (old != null) {
                old.stop();
            }
        }
        TelegraphSystem.start(world, zone);
    }

    /** Bombe hébétante : lancée au point visé, étourdit les ennemis autour de l'impact. */
    static boolean dazeBomb(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = throwAt(world, store, caster);
        if (center == null) {
            return false;
        }
        TelegraphSystem.start(world, delayed(THROW_SECONDS, (w, s) -> {
            for (Ref<EntityStore> foe : Support.foesNear(w, s, center, BOMB_RADIUS)) {
                Support.stun(w, s, foe, BOMB_STUN, BOMB_DEFIANCE);
            }
            Support.disk(s, FX_FLASH, center, BOMB_RADIUS, 0.8, 8, 1f);
            Telegraphs.sound(s, "SFX_Mace_T2_Signature_Impact", center);
        }));
        return true;
    }

    /** Fumigène : nuage au point visé ; les ennemis dedans perdent leur cible. */
    static boolean smokeBomb(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = throwAt(world, store, caster);
        if (center == null) {
            return false;
        }
        TelegraphSystem.start(world, delayed(THROW_SECONDS, (w, s) -> TelegraphSystem.start(w, new Zone(SMOKE_SECONDS, 0.1f, 0.5f,
                (w2, s2, now) -> {
                    for (Ref<EntityStore> foe : Support.foesNear(w2, s2, center, SMOKE_RADIUS)) {
                        if (!Support.immune(s2, foe)) {
                            Decoys.clearTarget(s2, foe, null);
                        }
                    }
                },
                (w2, s2, now) -> Support.disk(s2, FX_SMOKE, center, SMOKE_RADIUS, 1.0, 12, 1f)))));
        return true;
    }

    /** Lance l'objet vers le sol visé : traînée de particules ; rend le point d'impact. */
    private static Vector3d throwAt(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        Vector3d center = Support.aimGround(world, store, caster, AIM_RANGE);
        Vector3d from = Telegraphs.position(store, caster);
        if (center == null || from == null) {
            return null;
        }
        Vector3d a = new Vector3d(from).add(0, 1.5, 0);
        int n = Math.max(3, (int) Math.ceil(a.distance(center) / 1.2));
        for (int k = 0; k <= n; k++) {
            double t = (double) k / n;
            Vector3d p = new Vector3d(a).lerp(center, t).add(0, 1.5 * Math.sin(Math.PI * t), 0);
            Telegraphs.particle(store, FX_TRAIL, p, 0.6f);
        }
        return center;
    }

    /** Bannière : plantée à ses pieds pour {@value #BANNER_SECONDS} s ; une par groupe. */
    static boolean banner(World world, Store<EntityStore> store, Ref<EntityStore> caster, boolean might) {
        Vector3d at = Telegraphs.position(store, caster);
        if (at == null) {
            return false;
        }
        Vector3d center = new Vector3d(at);
        SupportStates.Banner banner = new SupportStates.Banner(center, BANNER_RADIUS, might,
                System.nanoTime() + Telegraphs.seconds(BANNER_SECONDS));
        SupportStates.BANNERS.put(world, banner);
        String effect = might ? EFFECT_MIGHT : EFFECT_GUARD;
        TelegraphSystem.start(world, new Zone(BANNER_SECONDS, 1f, 1f,
                (w, s, now) -> {
                    if (SupportStates.BANNERS.get(w) != banner) {
                        return;
                    }
                    for (Ref<EntityStore> p : Support.playersNear(w, s, center, BANNER_RADIUS)) {
                        Hurt.effect(s, p, effect, 1.5f);
                    }
                },
                (w, s, now) -> {
                    if (SupportStates.BANNERS.get(w) != banner) {
                        return;
                    }
                    for (double y = 0.2; y <= 3.0; y += 0.7) {
                        Telegraphs.particle(s, FX_BANNER, new Vector3d(center).add(0, y, 0), 1f);
                    }
                    Support.disk(s, FX_BANNER, center, BANNER_RADIUS, 1.6, 0, 0.7f);
                }));
        return true;
    }

    /** Fiole de purge : retire les états négatifs ordinaires, jamais ceux des mécaniques. */
    static boolean purge(World world, Store<EntityStore> store, Ref<EntityStore> caster) {
        for (String effect : PURGED) {
            Hurt.clear(store, caster, effect);
        }
        dev.nakasar.hytale.fractals.snowblind.Snowblind.relieveCold(world, caster, PURGE_COLD);
        Vector3d at = Telegraphs.position(store, caster);
        if (at != null) {
            Telegraphs.particle(store, FX_HEAL, new Vector3d(at).add(0, 1, 0), 1.2f);
        }
        return true;
    }

    /**
     * États retirés par la fiole de purge : poison, brûlure, saignement, ralentissement, tourment. Jamais l'agonie, la
     * Corruption du marteau, la malédiction des trésors, la peur de Kanaxai ni l'Hypothermie au-delà de
     * {@value #PURGE_COLD} piles : ce sont des règles de fractale.
     */
    static final String[] PURGED = {"Poison_T1", "Burn", "Nakasar_Fractal_Bleeding", "Ability_Frost_Slow",
            "Nakasar_Fractal_Torment"};
    static final int PURGE_COLD = 2;

    private static double wrap(double a) {
        while (a > Math.PI) {
            a -= 2 * Math.PI;
        }
        while (a < -Math.PI) {
            a += 2 * Math.PI;
        }
        return a;
    }

    public static void clearAll() {
        synchronized (TOTEMS) {
            TOTEMS.clear();
        }
    }
}
