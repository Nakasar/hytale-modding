package dev.nakasar.hytale.fractals.defiance;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Barre de défiance des boss de fractales (la « breakbar » de GW2) : elle ne s'ouvre que pendant certaines attaques
 * ({@code Nakasar_Fractal_OpenDefiance}, au début de la préparation). Ouverte, chaque coup d'un joueur la fait baisser
 * ({@link DefianceDamageSystem}) ; vide, le boss est étourdi {@value #STUN_SECONDS} s ({@link BossStun}) et la barre se
 * remplit. Elle s'affiche à la suite du nom sur la barre de vie du boss ({@code BossBarSystem.label}).
 *
 * <p>Taille : {@value #BASE} + {@value #PER_PLAYER} par joueur de plus dans la partie. Coups : 1, 2 pour un coup lourd
 * (au moins {@value #HEAVY} dégâts), 3 pour le marteau du culte.
 */
public final class Defiance {

    public static final int BASE = 8;
    public static final int PER_PLAYER = 4;
    public static final float HEAVY = 25f;
    public static final float STUN_SECONDS = 5f;

    /** Barre par boss (thread de son monde). */
    private static final Map<Ref<EntityStore>, Bar> BARS = new ConcurrentHashMap<>();

    private static final class Bar {
        int max;
        int value;
        long openUntil;
    }

    private Defiance() {
    }

    /** Ouvre la barre du boss pour `seconds` secondes (la remplit si elle était vide ou neuve). */
    public static void open(World world, Ref<EntityStore> boss, float seconds) {
        Bar bar = BARS.computeIfAbsent(boss, r -> new Bar());
        int max = BASE + PER_PLAYER * (FractalRuns.partySize(world) - 1);
        if (bar.max != max || bar.value <= 0) {
            bar.max = max;
            bar.value = max;
        }
        bar.openUntil = System.nanoTime() + Telegraphs.seconds(seconds);
    }

    public static boolean isOpen(Ref<EntityStore> boss) {
        Bar bar = BARS.get(boss);
        return bar != null && System.nanoTime() < bar.openUntil;
    }

    /** Un coup de joueur pendant que la barre est ouverte ; vide, le boss est étourdi. Thread du monde. */
    public static void hit(World world, Store<EntityStore> store, Ref<EntityStore> boss, int points) {
        Bar bar = BARS.get(boss);
        if (bar == null || System.nanoTime() >= bar.openUntil || !boss.isValid()) {
            return;
        }
        bar.value -= points;
        if (bar.value > 0) {
            return;
        }
        bar.value = bar.max;
        bar.openUntil = 0;
        BossStun.stun(world, store, boss, STUN_SECONDS, BossStun.EFFECT);
        Vector3d at = Telegraphs.position(store, boss);
        if (at != null) {
            Telegraphs.particle(store, "Stick_Slam_Ground_Large", at, 1.2f);
            Telegraphs.sound(store, "SFX_Mace_T2_Signature_Impact", at);
        }
        for (PlayerRef player : world.getPlayerRefs()) {
            player.sendMessage(Message.translation("nakasar_fractals_cliffside.defiance.broken"));
        }
    }

    /** Texte de la barre pour la barre de boss : losanges pleins et vides, null si elle est fermée. */
    public static String label(Ref<EntityStore> boss) {
        Bar bar = BARS.get(boss);
        if (bar == null || System.nanoTime() >= bar.openUntil) {
            return null;
        }
        return "◆".repeat(Math.max(0, bar.value)) + "◇".repeat(Math.max(0, bar.max - bar.value));
    }

    public static void forget(Ref<EntityStore> boss) {
        BARS.remove(boss);
    }

    public static void clearAll() {
        BARS.clear();
    }
}
