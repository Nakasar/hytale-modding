package dev.nakasar.hytale.peuples.reputation;

import com.hypixel.hytale.builtin.adventure.reputation.assets.ReputationRank;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;

import java.util.Locale;

/**
 * Les rangs d'un joueur auprès d'un village ou d'un peuple (GDD, Récompenses, Par rang), du plus bas au plus haut. Ce
 * sont aussi des rangs du ReputationPlugin vanilla : assets {@code Server/NPC/Reputation/Ranks/<assetId>.json}, mêmes
 * bornes (vérifiées par {@code validateAssets}) et même attitude des PNJ du peuple envers le joueur.
 *
 * <table>
 *   <tr><th>Rang</th><th>Réputation</th><th>Attitude</th><th>Ce que le village ouvre (étape 4)</th></tr>
 *   <tr><td>Honni</td><td>-1000 à -101</td><td>hostile</td><td>les gardes attaquent ; une seule demande pour se racheter</td></tr>
 *   <tr><td>Étranger</td><td>-100 à 49</td><td>neutre</td><td>une seule demande, échoppe fermée, gardes méfiants</td></tr>
 *   <tr><td>Toléré</td><td>50 à 199</td><td>neutre</td><td>les trois demandes, première échoppe</td></tr>
 *   <tr><td>Ami</td><td>200 à 499</td><td>amical</td><td>échoppe avancée, les Kweebecs ne fuient plus</td></tr>
 *   <tr><td>Hôte</td><td>500 à 999</td><td>amical</td><td>réserve de l'hôte (tenue kweebec)</td></tr>
 *   <tr><td>Champion</td><td>1000 et plus</td><td>vénéré</td><td>titre ; avant-poste à l'étape 9</td></tr>
 * </table>
 * Les bornes du ReputationPlugin vont de la borne basse (comprise) à la borne haute (exclue).
 */
public enum Rank {

    HONNI("Honni", -1000, Attitude.HOSTILE),
    ETRANGER("Etranger", -100, Attitude.NEUTRAL),
    TOLERE("Tolere", 50, Attitude.NEUTRAL),
    AMI("Ami", 200, Attitude.FRIENDLY),
    HOTE("Hote", 500, Attitude.FRIENDLY),
    CHAMPION("Champion", 1000, Attitude.REVERED);

    /** Borne haute (exclue) du dernier rang : la réputation ne la dépasse jamais. */
    public static final int CEILING = 100_000;
    /** Plus basse réputation possible. */
    public static final int FLOOR = -1000;

    private static final String ASSET_PREFIX = "Nakasar_Peuples_";

    private final String id;
    private final int min;
    private final Attitude attitude;

    Rank(String id, int min, Attitude attitude) {
        this.id = id;
        this.min = min;
        this.attitude = attitude;
    }

    /** Id court, celui des conditions de dialogue ({@code "Min": "Tolere"}) et des clés de traduction. */
    public String id() {
        return id;
    }

    /** Id de l'asset de rang du ReputationPlugin vanilla. */
    public String assetId() {
        return ASSET_PREFIX + id;
    }

    /** Réputation minimale du rang (comprise). */
    public int min() {
        return min;
    }

    /** Réputation maximale du rang (exclue) : le minimum du rang suivant. */
    public int max() {
        Rank next = next();
        return next == null ? CEILING : next.min;
    }

    /** Attitude des PNJ du peuple envers un joueur de ce rang (celle de l'asset si le jeu l'a chargé). */
    public Attitude attitude() {
        ReputationRank asset = ReputationRank.getAssetMap() == null ? null : ReputationRank.getAssetMap().getAsset(assetId());
        return asset != null && asset.getAttitude() != null ? asset.getAttitude() : attitude;
    }

    /** Attitude prévue par le mod (sans lire les assets) : contrôlée par le validateur. */
    public Attitude defaultAttitude() {
        return attitude;
    }

    /** Rang suivant, ou null pour le champion. */
    public Rank next() {
        int i = ordinal() + 1;
        return i < values().length ? values()[i] : null;
    }

    /** Clé de traduction du nom du rang. */
    public String nameKey() {
        return "nakasar_peuples.rank." + id;
    }

    /** Clé de traduction de ce que le rang ouvre. */
    public String perksKey() {
        return "nakasar_peuples.rank." + id + ".perks";
    }

    public boolean atLeast(Rank other) {
        return other == null || ordinal() >= other.ordinal();
    }

    /** Rang d'une réputation. */
    public static Rank of(int value) {
        Rank found = HONNI;
        for (Rank r : values()) {
            if (value >= r.min) {
                found = r;
            }
        }
        return found;
    }

    /** Réputation ramenée dans les bornes des rangs. */
    public static int clamp(long value) {
        return (int) Math.max(FLOOR, Math.min(CEILING - 1, value));
    }

    /** Rang d'id `id` (insensible à la casse et aux accents simples : « Tolere », « toléré »), ou null. */
    public static Rank byId(String id) {
        if (id == null) {
            return null;
        }
        String wanted = id.trim().toLowerCase(Locale.ROOT).replace('é', 'e').replace('ô', 'o').replace('è', 'e');
        for (Rank r : values()) {
            if (r.id.toLowerCase(Locale.ROOT).equals(wanted) || r.name().toLowerCase(Locale.ROOT).equals(wanted)) {
                return r;
            }
        }
        return null;
    }
}
