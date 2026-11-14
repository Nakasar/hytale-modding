package dev.nakasar.hytale.peuples.village;

import java.util.Locale;

/**
 * Les peuples qui ont des villages (GDD, section Progression des zones). Chaque peuple réemploie ses blocs vanilla :
 * le dépôt est un coffre vanilla du peuple, le tableau un panneau vanilla du peuple dont seule l'interaction change
 * ({@code Nakasar_Peuples_Board_<Peuple>}, objet enfant du panneau vanilla).
 *
 * <p>Étape 1 (socle) : seuls les Kweebecs. Les autres peuples s'ajoutent ici aux étapes 7 à 9.
 */
public enum People {

    KWEEBEC("Kweebec", "Furniture_Kweebec_Chest_Small", "Nakasar_Peuples_Board_Kweebec");

    private final String id;
    private final String depositBlock;
    private final String boardBlock;

    People(String id, String depositBlock, String boardBlock) {
        this.id = id;
        this.depositBlock = depositBlock;
        this.boardBlock = boardBlock;
    }

    /** Id du peuple dans les assets et les sauvegardes ({@code Kweebec}). */
    public String id() {
        return id;
    }

    /** Coffre vanilla qui sert de dépôt au village. */
    public String depositBlock() {
        return depositBlock;
    }

    /** Panneau du tableau du village. */
    public String boardBlock() {
        return boardBlock;
    }

    /** Clé de traduction du nom du peuple. */
    public String nameKey() {
        return "nakasar_peuples.people." + id + ".name";
    }

    /** Peuple d'id `id` (insensible à la casse), ou null. */
    public static People byId(String id) {
        if (id == null) {
            return null;
        }
        for (People people : values()) {
            if (people.id.equalsIgnoreCase(id) || people.name().equals(id.toUpperCase(Locale.ROOT))) {
                return people;
            }
        }
        return null;
    }
}
