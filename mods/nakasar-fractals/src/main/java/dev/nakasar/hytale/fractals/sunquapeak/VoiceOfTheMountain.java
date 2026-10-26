package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * La Voix de la montagne, sur son plateau (GW2 : premier boss du Pic de Sunqua). Ondes d'orbes, décharge et coup de
 * foudre : rôle JSON. En Java, à 66 et 33 % : elle se retire dans une tornade au centre (on ne peut plus la blesser) et
 * quatre nuages d'orage ({@link StormClouds}) s'allument ; les orbes de foudre du plateau donnent le Bond chargé qu'il
 * faut pour les disperser. Les quatre dispersés, elle redevient vulnérable. Personne sur le plateau pendant
 * {@value SunquaPeak#RESET_SECONDS} s : elle disparaît (pas de soin) et revient neuve au prochain venu.
 */
final class VoiceOfTheMountain {

    static final float[] STORMS_AT = {0.66f, 0.33f};

    private final StormClouds clouds = new StormClouds(SunquaPeakLayout.VOICE_CLOUDS);
    private Ref<EntityStore> boss;
    private boolean engaged;
    private boolean orbs;
    private final List<Float> thresholds = new ArrayList<>();
    private float idle;
    private float swirl;

    boolean shielded() {
        return clouds.active();
    }

    /** Vrai quand la Voix est vaincue. */
    boolean step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(SunquaPeakLayout.VOICE);
        double radius = SunquaPeakLayout.VOICE_RADIUS;
        List<PlayerRef> here = SunquaPeak.near(store, players, c, radius + 3);
        if (!orbs && !here.isEmpty()) {
            orbs = true;
            Gates.checkpoint(world, SunquaPeakLayout.VOICE, SunquaPeak.MESSAGES + "checkpoint");
            for (int[] at : SunquaPeakLayout.VOICE_ORBS) {
                st.leap.site(world, at, true);
            }
        }
        if (!engaged) {
            if (!SunquaPeak.near(store, players, c, radius - 3).isEmpty()) {
                engage(world, store, st, c);
            }
            return false;
        }
        if (boss == null || !boss.isValid() || !Spawns.alive(store, boss)) {
            clear(store);
            st.leap.remove(world, SunquaPeakLayout.VOICE_ORBS);
            return true;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= SunquaPeak.RESET_SECONDS) {
                clear(store);
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "voice.reset"));
                return false;
            }
        } else {
            idle = 0f;
        }
        if (clouds.active()) {
            BossStun.hold(world, store, boss);
            swirl += dt;
            if (swirl >= 0.5f) {
                swirl = 0f;
                Telegraphs.particle(store, "Nakasar_Fractal_Tornado", c, 2f);
            }
            if (clouds.step(world, store, here, dt)) {
                BossStun.release(store, boss);
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "voice.back"));
            }
            return false;
        }
        Leash.keepOnDisc(store, boss, c, radius - 2, 2, SunquaPeak.FALL_LIMIT);
        float health = Hurt.healthFraction(store, boss);
        if (!thresholds.isEmpty() && health <= thresholds.get(0) + 0.001f) {
            thresholds.remove(0);
            BossStun.interrupt(world, store, boss);
            SunquaPeak.move(store, boss, c, Spawns.point(SunquaPeakLayout.COLUMN_1[SunquaPeakLayout.COLUMN_1.length - 1]));
            clouds.begin();
            Telegraphs.sound(store, "SFX_Ability_Wind_Strike_Slash", c);
            Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "voice.storm"));
        }
        return false;
    }

    private void engage(World world, Store<EntityStore> store, SunquaPeak.State st, Vector3d c) {
        boss = Spawns.spawnBoss(world, store, SunquaPeak.VOICE, c, Telegraphs.yawToward(c,
                Spawns.point(SunquaPeakLayout.COLUMN_1[SunquaPeakLayout.COLUMN_1.length - 1])));
        if (boss == null) {
            return;
        }
        engaged = true;
        idle = 0f;
        thresholds.clear();
        for (float f : STORMS_AT) {
            thresholds.add(f);
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Storm_Disperse", c, 2f);
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "voice.enter"));
    }

    private void clear(Store<EntityStore> store) {
        clouds.stop();
        if (boss != null) {
            BossStun.release(store, boss);
        }
        Spawns.remove(store, boss);
        boss = null;
        engaged = false;
    }
}
