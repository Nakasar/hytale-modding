package dev.nakasar.hytale.peuples.outpost;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * Un avant-poste du champion (étape 9), gardé dans la ressource des zones : le peuple choisi, le cœur prévu (x, z), le
 * joueur qui a posé la pierre, le jour de la pose et, une fois les colons arrivés, l'id du village bâti. {@code Refund} :
 * la fondation a échoué pendant que le joueur était absent, la pierre lui sera rendue à son retour.
 */
public final class Outpost {

    public static final BuilderCodec<Outpost> CODEC = BuilderCodec.builder(Outpost.class, Outpost::new)
            .append(new KeyedCodec<>("People", Codec.STRING), (o, v) -> o.people = v, o -> o.people)
            .add()
            .append(new KeyedCodec<>("X", Codec.INTEGER), (o, v) -> o.x = v == null ? 0 : v, o -> o.x)
            .add()
            .append(new KeyedCodec<>("Z", Codec.INTEGER), (o, v) -> o.z = v == null ? 0 : v, o -> o.z)
            .add()
            .append(new KeyedCodec<>("Owner", Codec.STRING), (o, v) -> o.owner = v, o -> o.owner)
            .add()
            .append(new KeyedCodec<>("OwnerName", Codec.STRING), (o, v) -> o.ownerName = v, o -> o.ownerName)
            .add()
            .append(new KeyedCodec<>("Day", Codec.LONG), (o, v) -> o.day = v == null ? 0L : v, o -> o.day)
            .add()
            .append(new KeyedCodec<>("VillageId", Codec.STRING), (o, v) -> o.villageId = v, o -> o.villageId)
            .add()
            .append(new KeyedCodec<>("Refund", Codec.BOOLEAN), (o, v) -> o.refund = v != null && v, o -> o.refund)
            .add()
            .append(new KeyedCodec<>("From", Codec.STRING), (o, v) -> o.from = v, o -> o.from)
            .documentation("Village d'où vient le colon qui a lancé cette fondation (Settlers) ; absent : pierre de fondation.")
            .add()
            .build();

    String people;
    int x;
    int z;
    String owner;
    String ownerName;
    long day;
    String villageId;
    boolean refund;
    /** Village du colon (fondation sans pierre : rien à rembourser, le colon rentre chez lui si elle échoue). */
    String from;
    /** Génération lancée (non sauvegardé : un redémarrage la relance au matin). */
    transient boolean building;

    public Outpost() {
    }

    Outpost(String people, int x, int z, String owner, String ownerName, long day) {
        this.people = people;
        this.x = x;
        this.z = z;
        this.owner = owner;
        this.ownerName = ownerName;
        this.day = day;
    }

    public String people() {
        return people;
    }

    public int x() {
        return x;
    }

    public int z() {
        return z;
    }

    public String owner() {
        return owner;
    }

    public String ownerName() {
        return ownerName;
    }

    public long day() {
        return day;
    }

    public String villageId() {
        return villageId;
    }

    public String from() {
        return from;
    }

    public boolean refund() {
        return refund;
    }

    /** En attente de ses colons (ni bâti, ni échoué). */
    public boolean waiting() {
        return villageId == null && !refund;
    }

    public Outpost copy() {
        Outpost c = new Outpost(people, x, z, owner, ownerName, day);
        c.villageId = villageId;
        c.refund = refund;
        c.from = from;
        return c;
    }
}
