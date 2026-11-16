package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

import java.util.LinkedHashMap;
import java.util.Map;

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
            .append(new KeyedCodec<>("ConvoyItems", Codec.STRING), (a, v) -> a.convoyItems = decode(v), a -> encode(a.convoyItems))
            .documentation("Cargaison du convoi, « Objet*quantité|... » (le total est ConvoyCargo). Vide : un seul lot, l'objet livré par l'avant-poste.")
            .add()
            .append(new KeyedCodec<>("Chest", Codec.BOOLEAN), (a, v) -> a.chest = v != null && v, a -> a.chest)
            .documentation("Vrai si le coffre de dépôt de l'avant-poste est posé (ChestX/Y/Z).")
            .add()
            .append(new KeyedCodec<>("ChestX", Codec.INTEGER), (a, v) -> a.chestX = v == null ? 0 : v, a -> a.chestX).add()
            .append(new KeyedCodec<>("ChestY", Codec.INTEGER), (a, v) -> a.chestY = v == null ? 0 : v, a -> a.chestY).add()
            .append(new KeyedCodec<>("ChestZ", Codec.INTEGER), (a, v) -> a.chestZ = v == null ? 0 : v, a -> a.chestZ).add()
            .append(new KeyedCodec<>("Stock", Codec.STRING), (a, v) -> a.stock = decode(v), a -> encode(a.stock))
            .documentation("Production pas encore entrée dans le coffre de l'avant-poste (coffre pas chargé ou plein), « Objet*quantité|... ».")
            .add()
            .append(new KeyedCodec<>("ProduceDay", Codec.LONG), (a, l) -> a.produceDay = l == null ? Long.MIN_VALUE : l, a -> a.produceDay)
            .documentation("Jour de jeu de la dernière production déposée au coffre de l'avant-poste.")
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
    Map<String, Integer> convoyItems = new LinkedHashMap<>();
    boolean chest;
    int chestX;
    int chestY;
    int chestZ;
    Map<String, Integer> stock = new LinkedHashMap<>();
    long produceDay = Long.MIN_VALUE;

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

    /** Un convoi part avec la cargaison `items` (id → quantité), portée par `porters` villageois. */
    public void startConvoy(Map<String, Integer> items, int porters) {
        this.convoyItems = new LinkedHashMap<>(items);
        this.convoyCargo = total(convoyItems);
        this.convoyPorters = porters;
        this.convoyAt = 0;
    }

    /**
     * Cargaison du convoi (id → quantité, copie). Les convois partis avant les coffres d'avant-poste n'ont que leur
     * total : l'objet livré par l'avant-poste, `fallback`.
     */
    public Map<String, Integer> convoyItems(String fallback) {
        if (convoyItems.isEmpty() && convoyCargo > 0 && fallback != null) {
            Map<String, Integer> one = new LinkedHashMap<>();
            one.put(fallback, convoyCargo);
            return one;
        }
        return new LinkedHashMap<>(convoyItems);
    }

    /** Ce qui reste de la cargaison après une livraison partielle (dépôt du village plein). */
    public void setConvoyItems(Map<String, Integer> items) {
        this.convoyItems = new LinkedHashMap<>(items);
        this.convoyCargo = total(convoyItems);
    }

    /**
     * Retire `count` objets de la cargaison (porteur tué, embuscade), en commençant par le plus gros lot ; rend ce qui a
     * été retiré. `fallback` : voir {@link #convoyItems(String)}.
     */
    public Map<String, Integer> takeCargo(int count, String fallback) {
        if (convoyItems.isEmpty() && fallback == null) {
            // Convoi d'avant les coffres sans l'objet livré sous la main : on ne retire que du total.
            this.convoyCargo = Math.max(0, convoyCargo - Math.max(0, count));
            return new LinkedHashMap<>();
        }
        Map<String, Integer> items = convoyItems(fallback);
        Map<String, Integer> taken = new LinkedHashMap<>();
        int left = Math.min(count, total(items));
        while (left > 0) {
            String best = null;
            for (Map.Entry<String, Integer> e : items.entrySet()) {
                if (best == null || e.getValue() > items.get(best)) {
                    best = e.getKey();
                }
            }
            if (best == null) {
                break;
            }
            int n = Math.min(left, items.get(best));
            taken.merge(best, n, Integer::sum);
            left -= n;
            if (items.get(best) == n) {
                items.remove(best);
            } else {
                items.put(best, items.get(best) - n);
            }
        }
        this.convoyItems = items;
        this.convoyCargo = total(items);
        return taken;
    }

    public void setConvoyAt(double at) {
        this.convoyAt = at;
    }

    /** Un porteur est mort (sa part de la cargaison, déjà retirée par {@link #takeCargo}, reste au sol). */
    public void loseConvoyPorter() {
        this.convoyPorters = Math.max(0, convoyPorters - 1);
        if (convoyPorters == 0) {
            this.convoyCargo = 0;
            this.convoyItems = new LinkedHashMap<>();
        }
    }

    /** Une embuscade sans témoin (monde vivant) : le convoi perd `lost` objets (jamais tout), ses porteurs s'en tirent. */
    public void raidCargo(int lost, String fallback) {
        takeCargo(Math.min(lost, convoyCargo - 1), fallback);
    }

    public void endConvoy() {
        this.convoyCargo = 0;
        this.convoyPorters = 0;
        this.convoyAt = 0;
        this.convoyItems = new LinkedHashMap<>();
    }

    // ---- Coffre de dépôt de l'avant-poste ----

    public boolean hasChest() {
        return chest;
    }

    /** {x, y, z} du coffre de l'avant-poste, ou null s'il n'est pas encore posé. */
    public int[] chest() {
        return chest ? new int[] {chestX, chestY, chestZ} : null;
    }

    public void setChest(int x, int y, int z) {
        this.chest = true;
        this.chestX = x;
        this.chestY = y;
        this.chestZ = z;
    }

    /** Le coffre a disparu (cassé) : il sera reposé. */
    public void clearChest() {
        this.chest = false;
    }

    /** Production en attente d'entrer dans le coffre (copie). */
    public Map<String, Integer> stock() {
        return new LinkedHashMap<>(stock);
    }

    public int stockTotal() {
        return total(stock);
    }

    public void setStock(Map<String, Integer> items) {
        this.stock = new LinkedHashMap<>(items);
        this.stock.values().removeIf(n -> n == null || n <= 0);
    }

    public void addStock(String itemId, int count) {
        if (count > 0) {
            stock.merge(itemId, count, Integer::sum);
        }
    }

    public long produceDay() {
        return produceDay;
    }

    public void setProduceDay(long day) {
        this.produceDay = day;
    }

    public static int total(Map<String, Integer> items) {
        int n = 0;
        for (int v : items.values()) {
            n += v;
        }
        return n;
    }

    static Map<String, Integer> decode(String text) {
        Map<String, Integer> out = new LinkedHashMap<>();
        if (text == null || text.isBlank()) {
            return out;
        }
        for (String part : text.split("\\|")) {
            int star = part.lastIndexOf('*');
            if (star <= 0) {
                continue;
            }
            try {
                int n = Integer.parseInt(part.substring(star + 1).trim());
                if (n > 0) {
                    out.merge(part.substring(0, star).trim(), n, Integer::sum);
                }
            } catch (NumberFormatException ignored) {
                // Entrée abîmée : ignorée.
            }
        }
        return out;
    }

    static String encode(Map<String, Integer> items) {
        StringBuilder b = new StringBuilder();
        for (Map.Entry<String, Integer> e : items.entrySet()) {
            if (e.getValue() == null || e.getValue() <= 0) {
                continue;
            }
            if (b.length() > 0) {
                b.append('|');
            }
            b.append(e.getKey()).append('*').append(e.getValue());
        }
        return b.toString();
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
        c.convoyItems = new LinkedHashMap<>(convoyItems);
        c.chest = chest;
        c.chestX = chestX;
        c.chestY = chestY;
        c.chestZ = chestZ;
        c.stock = new LinkedHashMap<>(stock);
        c.produceDay = produceDay;
        return c;
    }
}
