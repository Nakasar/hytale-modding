package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * Un village : son état sauvegardé avec le monde (ressource {@link VillageRegistry}), ancré sur le bloc cœur invisible
 * {@value Villages#HEART_BLOCK} (GDD, section Villages vivants). Le dépôt (coffre vanilla du peuple) et le tableau
 * (panneau du peuple) sont posés à côté du cœur et retrouvés par leurs coordonnées.
 *
 * <p>Étape 1 : nom, peuple, palier et jauge d'essor. Les demandes (étape 3), la réputation de village (étape 4), les
 * bâtiments posés (étape 5) et le raid en attente (étape 6) s'ajoutent à ce même objet.
 */
public final class Village {

    public static final BuilderCodec<Village> CODEC = BuilderCodec.builder(Village.class, Village::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (v, s) -> v.id = s, v -> v.id)
            .documentation("Identifiant unique du village.")
            .add()
            .append(new KeyedCodec<>("Name", Codec.STRING), (v, s) -> v.name = s, v -> v.name)
            .documentation("Nom du village, affiché en titre du tableau.")
            .add()
            .append(new KeyedCodec<>("People", Codec.STRING), (v, s) -> v.people = s, v -> v.people)
            .documentation("Peuple du village (Kweebec...).")
            .add()
            .append(new KeyedCodec<>("X", Codec.INTEGER), (v, i) -> v.x = i, v -> v.x).add()
            .append(new KeyedCodec<>("Y", Codec.INTEGER), (v, i) -> v.y = i, v -> v.y).add()
            .append(new KeyedCodec<>("Z", Codec.INTEGER), (v, i) -> v.z = i, v -> v.z).add()
            .append(new KeyedCodec<>("DepositX", Codec.INTEGER), (v, i) -> v.depositX = i, v -> v.depositX).add()
            .append(new KeyedCodec<>("DepositY", Codec.INTEGER), (v, i) -> v.depositY = i, v -> v.depositY).add()
            .append(new KeyedCodec<>("DepositZ", Codec.INTEGER), (v, i) -> v.depositZ = i, v -> v.depositZ).add()
            .append(new KeyedCodec<>("BoardX", Codec.INTEGER), (v, i) -> v.boardX = i, v -> v.boardX).add()
            .append(new KeyedCodec<>("BoardY", Codec.INTEGER), (v, i) -> v.boardY = i, v -> v.boardY).add()
            .append(new KeyedCodec<>("BoardZ", Codec.INTEGER), (v, i) -> v.boardZ = i, v -> v.boardZ).add()
            .append(new KeyedCodec<>("Tier", Codec.INTEGER), (v, i) -> v.tier = Tiers.clamp(i), v -> v.tier)
            .documentation("Palier : 0 campement, 1 hameau, 2 village, 3 bourg.")
            .add()
            .append(new KeyedCodec<>("Essor", Codec.INTEGER), (v, i) -> v.essor = Math.max(0, i == null ? 0 : i), v -> v.essor)
            .documentation("Jauge d'essor partagée par tous les joueurs, vers le palier suivant.")
            .add()
            .append(new KeyedCodec<>("Created", Codec.LONG), (v, l) -> v.created = l == null ? 0L : l, v -> v.created)
            .documentation("Date de fondation (epoch, ms).")
            .add()
            .build();

    String id = "";
    String name = "";
    String people = People.KWEEBEC.id();
    int x;
    int y;
    int z;
    int depositX;
    int depositY;
    int depositZ;
    int boardX;
    int boardY;
    int boardZ;
    int tier;
    int essor;
    long created;

    Village() {
    }

    Village(String id, String name, People people, int x, int y, int z) {
        this.id = id;
        this.name = name;
        this.people = people.id();
        this.x = x;
        this.y = y;
        this.z = z;
        this.created = System.currentTimeMillis();
    }

    Village copy() {
        Village v = new Village();
        v.id = id;
        v.name = name;
        v.people = people;
        v.x = x;
        v.y = y;
        v.z = z;
        v.depositX = depositX;
        v.depositY = depositY;
        v.depositZ = depositZ;
        v.boardX = boardX;
        v.boardY = boardY;
        v.boardZ = boardZ;
        v.tier = tier;
        v.essor = essor;
        v.created = created;
        return v;
    }

    public String id() {
        return id;
    }

    public String name() {
        return name;
    }

    /** Peuple du village ; Kweebec si l'id sauvegardé n'existe plus. */
    public People people() {
        People p = People.byId(people);
        return p == null ? People.KWEEBEC : p;
    }

    public int x() {
        return x;
    }

    public int y() {
        return y;
    }

    public int z() {
        return z;
    }

    public int tier() {
        return tier;
    }

    public int essor() {
        return essor;
    }

    public boolean isBoard(int bx, int by, int bz) {
        return bx == boardX && by == boardY && bz == boardZ;
    }

    public boolean isDeposit(int bx, int by, int bz) {
        return bx == depositX && by == depositY && bz == depositZ;
    }

    public int[] deposit() {
        return new int[] {depositX, depositY, depositZ};
    }

    public int[] board() {
        return new int[] {boardX, boardY, boardZ};
    }

    void setDeposit(int dx, int dy, int dz) {
        depositX = dx;
        depositY = dy;
        depositZ = dz;
    }

    void setBoard(int bx, int by, int bz) {
        boardX = bx;
        boardY = by;
        boardZ = bz;
    }

    /** Distance au carré du cœur à (px, py, pz). */
    public double distanceSquared(double px, double py, double pz) {
        double dx = px - (x + 0.5);
        double dy = py - (y + 0.5);
        double dz = pz - (z + 0.5);
        return dx * dx + dy * dy + dz * dz;
    }

    /**
     * Ajoute `amount` (négatif : retire) à la jauge d'essor, bornée entre 0 et le seuil du palier suivant : une jauge
     * pleine attend son chantier (étape 5) au lieu de déborder. Rend le gain réel.
     */
    int addEssor(int amount) {
        int before = essor;
        essor = Math.max(0, Math.min(Tiers.threshold(tier), essor + amount));
        return essor - before;
    }

    void setTier(int value) {
        tier = Tiers.clamp(value);
        essor = Math.min(essor, Tiers.threshold(tier));
    }
}
