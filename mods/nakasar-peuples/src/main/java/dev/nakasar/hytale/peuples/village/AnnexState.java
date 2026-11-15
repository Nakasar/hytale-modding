package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * L'état d'un avant-poste de métier d'un village (ferme, mine, scierie...), sauvegardé avec son village de rattachement
 * : la fondation remise au panneau, la place choisie par le joueur, le chantier d'une journée et le bâtiment debout.
 * Son niveau, son savoir-faire et ses commandes sont ceux de son bâtiment de métier ({@link WorkshopState} du même id).
 * Modifiable sur le thread du monde ({@code dev.nakasar.hytale.peuples.annex.Annexes}).
 */
public final class AnnexState {

    /** Fondation remise, pas encore posée. */
    public static final int GRANTED = 0;
    /** Fondation posée : la zone est marquée, les travaux durent une journée. */
    public static final int WORKS = 1;
    /** Bâtiment debout : l'avant-poste est ouvert. */
    public static final int BUILT = 2;

    public static final BuilderCodec<AnnexState> CODEC = BuilderCodec.builder(AnnexState.class, AnnexState::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (a, v) -> a.id = v == null ? "" : v, a -> a.id)
            .documentation("Bâtiment de métier de l'avant-poste (asset Workshop avec un champ Annex).")
            .add()
            .append(new KeyedCodec<>("Stage", Codec.INTEGER), (a, v) -> a.stage = v == null ? GRANTED : v, a -> a.stage)
            .documentation("0 fondation remise, 1 travaux, 2 debout.")
            .add()
            .append(new KeyedCodec<>("Granted", Codec.LONG), (a, l) -> a.granted = l == null ? Long.MIN_VALUE : l, a -> a.granted)
            .documentation("Jour de jeu où la fondation a été remise (ou remise de nouveau).")
            .add()
            .append(new KeyedCodec<>("Owner", Codec.STRING), (a, v) -> a.owner = v, a -> a.owner)
            .documentation("Joueur (UUID) qui a reçu la fondation.")
            .add()
            .append(new KeyedCodec<>("OwnerName", Codec.STRING), (a, v) -> a.ownerName = v, a -> a.ownerName)
            .add()
            .append(new KeyedCodec<>("X", Codec.INTEGER), (a, v) -> a.x = v == null ? 0 : v, a -> a.x).add()
            .append(new KeyedCodec<>("Y", Codec.INTEGER), (a, v) -> a.y = v == null ? 0 : v, a -> a.y).add()
            .append(new KeyedCodec<>("Z", Codec.INTEGER), (a, v) -> a.z = v == null ? 0 : v, a -> a.z).add()
            .append(new KeyedCodec<>("Rotation", Codec.INTEGER), (a, v) -> a.rotation = v == null ? 0 : v & 3, a -> a.rotation)
            .documentation("Quarts de tour du plan de l'avant-poste (0 : le joueur se tenait au sud de la fondation).")
            .add()
            .append(new KeyedCodec<>("Ground", Codec.INTEGER), (a, v) -> a.ground = v == null ? Integer.MIN_VALUE : v, a -> a.ground)
            .documentation("Hauteur de pose des prefabs (sol aplani de l'emprise).")
            .add()
            .append(new KeyedCodec<>("Start", Codec.LONG), (a, l) -> a.start = l == null ? 0L : l, a -> a.start)
            .documentation("Début des travaux (secondes de jeu).")
            .add()
            .append(new KeyedCodec<>("End", Codec.LONG), (a, l) -> a.end = l == null ? 0L : l, a -> a.end)
            .documentation("Fin des travaux (secondes de jeu).")
            .add()
            .append(new KeyedCodec<>("DeliveryDay", Codec.LONG), (a, l) -> a.deliveryDay = l == null ? Long.MIN_VALUE : l, a -> a.deliveryDay)
            .documentation("Jour de jeu de la dernière livraison au dépôt du village.")
            .add()
            .append(new KeyedCodec<>("ConvoyCargo", Codec.INTEGER), (a, v) -> a.convoyCargo = v == null ? 0 : v, a -> a.convoyCargo)
            .documentation("Convoi en route vers le dépôt : quantité qu'il porte encore (0 : pas de convoi).")
            .add()
            .append(new KeyedCodec<>("ConvoyPorters", Codec.INTEGER), (a, v) -> a.convoyPorters = v == null ? 0 : v, a -> a.convoyPorters)
            .documentation("Porteurs encore en vie dans le convoi.")
            .add()
            .append(new KeyedCodec<>("ConvoyAt", Codec.DOUBLE), (a, v) -> a.convoyAt = v == null ? 0 : v, a -> a.convoyAt)
            .documentation("Blocs parcourus par le convoi depuis l'avant-poste.")
            .add()
            .build();

    String id = "";
    int stage = GRANTED;
    long granted = Long.MIN_VALUE;
    String owner;
    String ownerName;
    int x;
    int y;
    int z;
    int rotation;
    int ground = Integer.MIN_VALUE;
    long start;
    long end;
    long deliveryDay = Long.MIN_VALUE;
    int convoyCargo;
    int convoyPorters;
    double convoyAt;

    AnnexState() {
    }

    AnnexState(String id) {
        this.id = id;
    }

    public String id() {
        return id;
    }

    public int stage() {
        return stage;
    }

    public boolean granted() {
        return stage == GRANTED;
    }

    public boolean working() {
        return stage == WORKS;
    }

    public boolean built() {
        return stage == BUILT;
    }

    public long grantedDay() {
        return granted;
    }

    public String owner() {
        return owner;
    }

    public String ownerName() {
        return ownerName;
    }

    /** Place de la fondation (puis du panneau de l'avant-poste) : {x, y, z}. */
    public int[] spot() {
        return new int[] {x, y, z};
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

    public int rotation() {
        return rotation;
    }

    public int ground() {
        return ground;
    }

    public long start() {
        return start;
    }

    public long end() {
        return end;
    }

    public long deliveryDay() {
        return deliveryDay;
    }

    public void grant(long day, String owner, String ownerName) {
        this.stage = GRANTED;
        this.granted = day;
        this.owner = owner;
        this.ownerName = ownerName;
    }

    public void startWorks(int x, int y, int z, int rotation, int ground, long start, long end) {
        this.stage = WORKS;
        this.x = x;
        this.y = y;
        this.z = z;
        this.rotation = rotation & 3;
        this.ground = ground;
        this.start = start;
        this.end = end;
    }

    /** Fin des travaux avancée (commande {@code /village finir}). */
    public void hurry(long end) {
        this.end = end;
    }

    public void markBuilt() {
        this.stage = BUILT;
    }

    public void setDeliveryDay(long day) {
        this.deliveryDay = day;
    }

    /** Vrai si un convoi de l'avant-poste est en route vers le dépôt du village. */
    public boolean convoy() {
        return convoyCargo > 0 && convoyPorters > 0;
    }

    public int convoyCargo() {
        return convoyCargo;
    }

    public int convoyPorters() {
        return convoyPorters;
    }

    public double convoyAt() {
        return convoyAt;
    }

    /** Un convoi part : `cargo` objets portés par `porters` villageois. */
    public void startConvoy(int cargo, int porters) {
        this.convoyCargo = cargo;
        this.convoyPorters = porters;
        this.convoyAt = 0;
    }

    public void setConvoyAt(double at) {
        this.convoyAt = at;
    }

    /** Un porteur est mort : sa part `lost` de la cargaison reste au sol. */
    public void loseConvoyPorter(int lost) {
        this.convoyPorters = Math.max(0, convoyPorters - 1);
        this.convoyCargo = convoyPorters == 0 ? 0 : Math.max(0, convoyCargo - lost);
    }

    public void endConvoy() {
        this.convoyCargo = 0;
        this.convoyPorters = 0;
        this.convoyAt = 0;
    }

    /** Distance horizontale au carré entre la fondation et (px, pz). */
    public double distanceSquared(double px, double pz) {
        double dx = x + 0.5 - px;
        double dz = z + 0.5 - pz;
        return dx * dx + dz * dz;
    }

    AnnexState copy() {
        AnnexState c = new AnnexState(id);
        c.stage = stage;
        c.granted = granted;
        c.owner = owner;
        c.ownerName = ownerName;
        c.x = x;
        c.y = y;
        c.z = z;
        c.rotation = rotation;
        c.ground = ground;
        c.start = start;
        c.end = end;
        c.deliveryDay = deliveryDay;
        c.convoyCargo = convoyCargo;
        c.convoyPorters = convoyPorters;
        c.convoyAt = convoyAt;
        return c;
    }
}
