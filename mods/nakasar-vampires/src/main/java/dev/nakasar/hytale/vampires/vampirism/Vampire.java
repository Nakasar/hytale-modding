package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Le joueur est un vampire (rituel de l'autel, {@link VampireRitualInteraction}). Composant sauvegardé avec le
 * joueur (id {@value #ID}) : seule la réserve de sang l'est, le reste se recalcule à chaque passage de
 * {@link VampireSystem}.
 *
 * <p>Le sang va de 0 (affamé) à 1 (rassasié) ; il baisse de rassasié à affamé en {@value #DAYS_TO_STARVE} jours de
 * jeu et remonte par le Baiser du Vampire ({@link BloodFeedInteraction}) ou les fioles de sang
 * ({@link DrinkBloodInteraction}).
 */
public final class Vampire implements Component<EntityStore> {

    public static final String ID = "Nakasar_Vampire";
    /** Jours de jeu (jour + nuit du monde) pour passer de rassasié à affamé. */
    public static final float DAYS_TO_STARVE = 1.5f;

    public static final BuilderCodec<Vampire> CODEC = BuilderCodec.builder(Vampire.class, Vampire::new)
            .append(new KeyedCodec<>("Blood", Codec.FLOAT), (v, blood) -> v.blood = clamp(blood), v -> v.blood)
            .documentation("Reserve de sang du vampire, de 0 (affame) a 1 (rassasie).")
            .add()
            .build();

    private static ComponentType<EntityStore, Vampire> componentType;

    /** Réserve de sang, de 0 à 1. */
    float blood = 0.5f;

    // État recalculé, jamais sauvegardé.
    /** Palier affiché (effet de statut posé), ou {@code null} avant le premier passage. */
    transient BloodStage shownStage;
    /** Intensité du soleil subi au dernier passage (0 à 1, protections comprises). */
    transient float sun;
    /** Secondes avant le prochain battement de cœur entendu (affamé). */
    transient float heartbeatIn;
    /** Instant (ms) du dernier coup porté, pour le malus de vitesse d'attaque ({@link VampireDamageSystem}). */
    transient long lastHitMillis;
    /** Part des dégâts du dernier coup, reprise pour les autres cibles du même coup. */
    transient float lastHitFactor = 1f;
    /** Fraction d'une seconde de dégâts du soleil ou de la lumière purificatrice, cumulée entre deux passages. */
    transient float pendingSunDamage;
    transient float pendingLightDamage;

    public static ComponentType<EntityStore, Vampire> getComponentType() {
        return componentType;
    }

    public static void setComponentType(ComponentType<EntityStore, Vampire> type) {
        componentType = type;
    }

    public float getBlood() {
        return blood;
    }

    public void setBlood(float blood) {
        this.blood = clamp(blood);
    }

    /** Ajoute du sang (négatif pour en retirer), borné entre 0 et 1. */
    public void addBlood(float amount) {
        setBlood(blood + amount);
    }

    public BloodStage getStage() {
        return BloodStage.of(blood);
    }

    /** Intensité du soleil subi (0 à 1), mise à jour par {@link VampireSystem}. */
    public float getSun() {
        return sun;
    }

    private static float clamp(float value) {
        return Float.isNaN(value) ? 0f : Math.max(0f, Math.min(1f, value));
    }

    @Override
    public Vampire clone() {
        Vampire copy = new Vampire();
        copy.blood = blood;
        copy.shownStage = shownStage;
        copy.sun = sun;
        copy.heartbeatIn = heartbeatIn;
        copy.lastHitMillis = lastHitMillis;
        copy.lastHitFactor = lastHitFactor;
        copy.pendingSunDamage = pendingSunDamage;
        copy.pendingLightDamage = pendingLightDamage;
        return copy;
    }
}
