package dev.nakasar.hytale.vampires.vampirism;

/**
 * Paliers de la faim de sang, comme les rangs de nourriture : la régénération de vie suit le palier, aux débits des
 * effets de régénération des repas du jeu (Food_Health_Regen_Large, Medium, Small, Tiny : 3 PV / 2 s, 2 PV / 2 s,
 * 1 PV / 2 s, 1 PV / 3 s), et l'affamé ne régénère plus du tout. Chaque palier a son effet de statut (icône dans la barre des effets).
 */
public enum BloodStage {
    /** Rassasié : régénère comme un grand repas (Food_Health_Regen_Large). */
    SATED(0.75f, 1.5f, "Nakasar_Blood_Sated"),
    /** Faim rang 3. */
    HUNGER_3(0.5f, 1.0f, "Nakasar_Blood_Hunger_3"),
    /** Faim rang 2. */
    HUNGER_2(0.25f, 0.5f, "Nakasar_Blood_Hunger_2"),
    /** Faim rang 1. */
    HUNGER_1(0.0001f, 0.33f, "Nakasar_Blood_Hunger_1"),
    /** Affamé : plus de régénération, malus de vitesse d'attaque, battements de cœur des vivants proches. */
    STARVING(0f, 0f, "Nakasar_Blood_Starving");

    /** Sang minimal (inclus) du palier. */
    final float minBlood;
    /** Points de vie régénérés par seconde. */
    final float regenPerSecond;
    /** Effet de statut affiché (durée infinie, remplacé au changement de palier). */
    final String effectId;

    BloodStage(float minBlood, float regenPerSecond, String effectId) {
        this.minBlood = minBlood;
        this.regenPerSecond = regenPerSecond;
        this.effectId = effectId;
    }

    public static BloodStage of(float blood) {
        for (BloodStage stage : values()) {
            if (blood >= stage.minBlood) {
                return stage;
            }
        }
        return STARVING;
    }
}
