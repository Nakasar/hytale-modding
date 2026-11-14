package dev.nakasar.hytale.peuples.village;

import java.util.Locale;

/**
 * Les peuples qui ont des villages (GDD, section Progression des zones). Chaque peuple réemploie ses blocs vanilla :
 * le dépôt est un coffre vanilla du peuple, le tableau un panneau vanilla du peuple dont seule l'interaction change
 * ({@code Nakasar_Peuples_Board_<Peuple>}, objet enfant du panneau vanilla).
 *
 * <p>Étape 3 : chaque peuple a sa faveur, sa missive, son crieur, son guetteur et son captif (objets et rôles
 * {@code Nakasar_Peuples_*}).
 *
 * <p>Étape 4 : chaque peuple a son marchand et ses échoppes de troc par rang, et son groupe de réputation vanilla
 * ({@code Nakasar_Peuples_<Peuple>}, voir {@link dev.nakasar.hytale.peuples.reputation.Reputations}).
 *
 * <p>Étapes 1 et 2 : seuls les Kweebecs (plan de village {@code Kweebec_Oak}, bannière de carte). Les autres peuples
 * s'ajoutent ici aux étapes 7 à 9.
 */
public enum People {

    KWEEBEC("Kweebec", "Furniture_Kweebec_Chest_Small", "Nakasar_Peuples_Board_Kweebec", "Nakasar_Peuples_Banner_Kweebec",
            "Kweebec_Oak"),
    /**
     * Étape 7 : le camp trork apprivoisable de la zone 1 (plan {@code Trork_Camp}, prefabs vanilla Npc/Trork), coffre et
     * panneau grossiers vanilla, bannière de crânes. Un joueur y commence Honni ({@link #initialReputation()}).
     */
    TRORK("Trork", "Furniture_Crude_Chest_Small", "Nakasar_Peuples_Board_Trork", "Nakasar_Peuples_Banner_Trork",
            "Trork_Camp"),
    // Étape 8 : les Feran de la zone 2 (oasis du désert) et les Outlanders renoncés de la zone 3 (id « Renonce » : un
    // rôle dont le nom contient « Outlander » tomberait dans le groupe vanilla Outlander, celui du culte).
    FERAN("Feran", "Furniture_Feran_Chest_Small", "Nakasar_Peuples_Board_Feran", "Nakasar_Peuples_Banner_Feran",
            "Feran_Oasis"),
    RENONCE("Renonce", "Furniture_Lumberjack_Chest_Small", "Nakasar_Peuples_Board_Renonce", "Nakasar_Peuples_Banner_Renonce",
            "Renonce_Givre"),
    /**
     * Étape 9 : le monastère slothian de la zone 4 (plan {@code Slothian_Monastere}, prefabs vanilla Npc/Slothian et
     * monuments slothians), au bord du Vide. Coffre de jungle vanilla, bannière = brasero de jungle vanilla.
     */
    SLOTHIAN("Slothian", "Furniture_Jungle_Chest_Small", "Nakasar_Peuples_Board_Slothian", "Nakasar_Peuples_Banner_Slothian",
            "Slothian_Monastere");

    /** Préfixe des objets et rôles propres à chaque peuple : {@code Nakasar_Peuples_<Quoi>_<Peuple>}. */
    private static final String PREFIX = "Nakasar_Peuples_";

    private final String id;
    private final String depositBlock;
    private final String boardBlock;
    private final String bannerBlock;
    private final String layout;

    People(String id, String depositBlock, String boardBlock, String bannerBlock, String layout) {
        this.id = id;
        this.depositBlock = depositBlock;
        this.boardBlock = boardBlock;
        this.bannerBlock = bannerBlock;
        this.layout = layout;
    }

    /** Bannière du peuple : bloc marqueur de carte posé sur la place du village. */
    public String bannerBlock() {
        return bannerBlock;
    }

    /** Plan de village par défaut du peuple ({@link VillageLayout}). */
    public String layout() {
        return layout;
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

    /** Faveur du peuple (GDD, Récompenses) : l'objet dont il paie les demandes remplies. */
    public String favorItem() {
        return PREFIX + "Favor_" + id;
    }

    /** Missive des demandes de livraison (objet marqué, rendu au guetteur). */
    public String missiveItem() {
        return PREFIX + "Missive_" + id;
    }

    /** Crieur du village : PNJ posé près du tableau, qui donne et reprend les demandes. */
    public String crierRole() {
        return PREFIX + id + "_Crier";
    }

    /** Guetteur à qui l'on porte la missive d'une livraison. */
    public String lookoutRole() {
        return PREFIX + id + "_Lookout";
    }

    /** Captif à ramener au village (escorte). */
    public String captiveRole() {
        return PREFIX + id + "_Captive";
    }

    /** Marchand du village (étape 4) : posé près du dépôt, ouvre les échoppes de troc selon le rang du joueur. */
    public String merchantRole() {
        return PREFIX + id + "_Merchant";
    }

    /** Chef du village (étape 6) : posé près du cœur, il mène la chaîne de quêtes du peuple. */
    public String chiefRole() {
        return PREFIX + id + "_Chief";
    }

    /** Dialogue du chef. */
    public String chiefDialogue() {
        return id + "_Chef";
    }

    /** Dialogue du marchand. */
    public String merchantDialogue() {
        return id + "_Marchand";
    }

    /**
     * Échoppe de troc vanilla (BarterShops) ouverte au rang `rank`, ou null si ce rang n'en a pas en propre :
     * {@code Nakasar_Peuples_<Peuple>_Tolere}, {@code _Ami}, {@code _Hote}.
     */
    public String shop(dev.nakasar.hytale.peuples.reputation.Rank rank) {
        return switch (rank) {
            case TOLERE, AMI, HOTE -> PREFIX + id + "_" + rank.id();
            default -> null;
        };
    }

    /** Dialogue du crieur. */
    public String crierDialogue() {
        return id + "_Crieur";
    }

    /**
     * Réputation de village d'un joueur qui n'a encore rien fait dans un village du peuple (étape 7). Les Kweebecs
     * accueillent l'étranger (0) ; un camp trork commence hostile (Honni, -250) et s'apprivoise par la viande. Même
     * valeur que l'InitialReputationValue du groupe de réputation du peuple (vérifié par validateAssets).
     */
    public int initialReputation() {
        return switch (this) {
            case TRORK -> -250;
            default -> 0;
        };
    }

    /** Zone du monde par défaut où vit le peuple (World/Default/Zones.json : Zone1 à Zone4). Étape 8. */
    public int zone() {
        return switch (this) {
            case FERAN -> 2;
            case RENONCE -> 3;
            case SLOTHIAN -> 4;
            default -> 1;
        };
    }

    /**
     * Peuple rival (étape 7, réputations croisées : GDD, Progression des zones) : aider l'un coûte auprès de l'autre, ou
     * null. Zone 1 : Kweebecs et Trorks.
     */
    public People rival() {
        return switch (this) {
            case KWEEBEC -> TRORK;
            case TRORK -> KWEEBEC;
            default -> null;
        };
    }

    /**
     * Peuples alliés (étape 9 ; GDD, Relations entre peuples) : aider les Feran ou les Renoncés se sait au monastère, les
     * Slothians y gagnent un quart ({@code reputation/Rivals#ALLY_SHARE}) de chaque gain de réputation de village.
     */
    public People ally() {
        return switch (this) {
            case FERAN, RENONCE -> SLOTHIAN;
            default -> null;
        };
    }

    /**
     * Sol posé sous les bâtiments et au fondu des emprises (VillageBuilder, chantiers) : herbe pour les Kweebecs, sable
     * pour les Feran, neige pour les Renoncés. Étape 8.
     */
    public String ground() {
        return switch (this) {
            case FERAN -> "Soil_Sand";
            case RENONCE -> "Soil_Snow";
            case SLOTHIAN -> "Soil_Mud_Dry";
            default -> Terrain.GRASS;
        };
    }

    /** Sol de la place centrale. Étape 8. */
    public String plaza() {
        return switch (this) {
            case FERAN -> "Soil_Gravel_Sand";
            case RENONCE -> "Soil_Gravel";
            case SLOTHIAN -> "Rock_Basalt_Cobble";
            default -> Terrain.PATHWAY;
        };
    }

    /** Un bloc de surface qui convient au site du village (recherche automatique). Étape 8. */
    public boolean suitsSite(String block) {
        if (block == null) {
            return false;
        }
        return switch (this) {
            case FERAN -> block.startsWith("Soil_Sand");
            case RENONCE -> block.startsWith("Soil_Snow") || block.startsWith("Soil_Grass_Cold") || block.startsWith("Soil_Dirt_Cold");
            // Zone 4 (Zones/Zone4_Tier4-5, tuiles vanilla) : herbe et terre brûlées, cendre, sable cendreux, boue sèche.
            case SLOTHIAN -> block.startsWith("Soil_Grass") || block.startsWith("Soil_Dirt_Burnt") || block.startsWith("Soil_Ash")
                    || block.startsWith("Soil_Sand_Ashen") || block.startsWith("Soil_Mud_Dry") || block.equals("Soil_Dirt");
            default -> block.startsWith("Soil_Grass");
        };
    }

    /**
     * Ennemi des raids sur ce peuple : les assaillants s'appellent {@code Nakasar_Peuples_Raider_<Ennemi>_*} et le
     * trophée du raid gagné {@code Nakasar_Peuples_Trophy_<Ennemi>}. Étape 8 : Scaraks sur les Feran, culte outlander
     * sur les Renoncés. Étape 9 : le Vide sur les Slothians.
     */
    public String raidEnemy() {
        return switch (this) {
            case FERAN -> "Scarak";
            case RENONCE -> "Cult";
            case SLOTHIAN -> "Void";
            default -> "Trork";
        };
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
