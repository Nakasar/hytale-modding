package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * La population d'un village, sauvegardée avec lui (champ {@code Population} de {@code Village}) : les fiches des
 * habitants vivants et morts, la chronique, et ce que le pas du matin ({@link Population}) doit retenir d'un jour à
 * l'autre (dernier jour traité, prochaine naissance possible, deuil, nouveau-né à nommer, refuge, postes vacants).
 */
public final class PopulationState {

    /** Lignes de chronique gardées (les plus anciennes partent). */
    public static final int CHRONICLE = 80;

    public static final BuilderCodec<PopulationState> CODEC = BuilderCodec.builder(PopulationState.class, PopulationState::new)
            .append(new KeyedCodec<>("Inhabitants", new ArrayCodec<>(Inhabitant.CODEC, Inhabitant[]::new)),
                    (p, a) -> p.inhabitants = a == null ? new ArrayList<>() : new ArrayList<>(Arrays.asList(a)),
                    p -> p.inhabitants.toArray(Inhabitant[]::new))
            .add()
            .append(new KeyedCodec<>("Chronicle", new ArrayCodec<>(ChronicleEntry.CODEC, ChronicleEntry[]::new)),
                    (p, a) -> p.chronicle = a == null ? new ArrayList<>() : new ArrayList<>(Arrays.asList(a)),
                    p -> p.chronicle.toArray(ChronicleEntry[]::new))
            .add()
            .append(new KeyedCodec<>("Seeded", Codec.BOOLEAN), (p, b) -> p.seeded = b != null && b, p -> p.seeded)
            .documentation("Vrai quand les fondateurs (villageois d'avant les générations) ont reçu leur fiche.")
            .add()
            .append(new KeyedCodec<>("LastDay", Codec.LONG), (p, l) -> p.lastDay = l == null ? Inhabitant.NONE : l, p -> p.lastDay)
            .documentation("Dernier jour de jeu dont le matin a été traité (rattrapage des jours manqués).")
            .add()
            .append(new KeyedCodec<>("NextBirth", Codec.LONG), (p, l) -> p.nextBirth = l == null ? Inhabitant.NONE : l, p -> p.nextBirth)
            .documentation("Premier jour où une naissance est possible (7 jours après la précédente).")
            .add()
            .append(new KeyedCodec<>("Mourning", Codec.LONG), (p, l) -> p.mourning = l == null ? Inhabitant.NONE : l, p -> p.mourning)
            .documentation("Dernier jour de deuil (pas de naissance).")
            .add()
            .append(new KeyedCodec<>("Newborn", Codec.STRING), (p, s) -> p.newborn = s, p -> p.newborn)
            .documentation("Habitant né ce jour dont un joueur Ami peut encore choisir le prénom, ou absent.")
            .add()
            .append(new KeyedCodec<>("NamingUntil", Codec.LONG), (p, l) -> p.namingUntil = l == null ? Inhabitant.NONE : l, p -> p.namingUntil)
            .add()
            .append(new KeyedCodec<>("Proposals", new ArrayCodec<>(Codec.STRING, String[]::new)),
                    (p, a) -> p.proposals = a == null ? new String[0] : a, p -> p.proposals)
            .documentation("Trois prénoms proposés pour le nouveau-né.")
            .add()
            .append(new KeyedCodec<>("Refuge", Codec.STRING), (p, s) -> p.refuge = s, p -> p.refuge)
            .documentation("Bâtiment refuge désigné par un Hôte (palier 2) : les sans-logis d'un bâtiment brûlé y dorment.")
            .add()
            .append(new KeyedCodec<>("OrientDay", Codec.LONG), (p, l) -> p.orientDay = l == null ? Inhabitant.NONE : l, p -> p.orientDay)
            .documentation("Jour de la dernière orientation d'apprenti (une par semaine).")
            .add()
            .append(new KeyedCodec<>("Vacancies", new ArrayCodec<>(Codec.STRING, String[]::new)),
                    (p, a) -> p.vacancies = a == null ? new String[0] : a, p -> p.vacancies)
            .documentation("Postes vides après une mort : « poste|jour ». Un arrivant s'installe au bout de 3 jours.")
            .add()
            .append(new KeyedCodec<>("NextId", Codec.INTEGER), (p, i) -> p.nextId = i == null ? 1 : i, p -> p.nextId).add()
            .append(new KeyedCodec<>("NextTomb", Codec.INTEGER), (p, i) -> p.nextTomb = i == null ? 0 : i, p -> p.nextTomb)
            .documentation("Prochain emplacement du cimetière (population/Cemetery).")
            .add()
            .build();

    List<Inhabitant> inhabitants = new ArrayList<>();
    List<ChronicleEntry> chronicle = new ArrayList<>();
    boolean seeded;
    long lastDay = Inhabitant.NONE;
    long nextBirth = Inhabitant.NONE;
    long mourning = Inhabitant.NONE;
    String newborn;
    long namingUntil = Inhabitant.NONE;
    String[] proposals = new String[0];
    String refuge;
    long orientDay = Inhabitant.NONE;
    String[] vacancies = new String[0];
    int nextId = 1;
    int nextTomb;

    public PopulationState() {
    }

    public PopulationState copy() {
        PopulationState p = new PopulationState();
        for (Inhabitant h : inhabitants) {
            p.inhabitants.add(h.copy());
        }
        for (ChronicleEntry e : chronicle) {
            p.chronicle.add(e.copy());
        }
        p.seeded = seeded;
        p.lastDay = lastDay;
        p.nextBirth = nextBirth;
        p.mourning = mourning;
        p.newborn = newborn;
        p.namingUntil = namingUntil;
        p.proposals = proposals.clone();
        p.refuge = refuge;
        p.orientDay = orientDay;
        p.vacancies = vacancies.clone();
        p.nextId = nextId;
        p.nextTomb = nextTomb;
        return p;
    }

    public List<Inhabitant> all() {
        return inhabitants;
    }

    public List<Inhabitant> living() {
        List<Inhabitant> out = new ArrayList<>();
        for (Inhabitant h : inhabitants) {
            if (h.alive()) {
                out.add(h);
            }
        }
        return out;
    }

    public Inhabitant byId(String id) {
        if (id == null) {
            return null;
        }
        for (Inhabitant h : inhabitants) {
            if (h.id.equals(id)) {
                return h;
            }
        }
        return null;
    }

    /** Habitant vivant qui tient le poste `job`, ou null. */
    public Inhabitant holder(String job) {
        if (job == null || job.isEmpty()) {
            return null;
        }
        for (Inhabitant h : inhabitants) {
            if (h.alive() && job.equals(h.job)) {
                return h;
            }
        }
        return null;
    }

    public List<ChronicleEntry> chronicle() {
        return chronicle;
    }

    public boolean seeded() {
        return seeded;
    }

    public String newborn() {
        return newborn;
    }

    public long namingUntil() {
        return namingUntil;
    }

    public String[] proposals() {
        return proposals;
    }

    public String refuge() {
        return refuge;
    }

    public long orientDay() {
        return orientDay;
    }

    public long mourning() {
        return mourning;
    }

    String newId() {
        return "h" + (nextId++);
    }

    void log(long day, String kind, String who, String other, String detail) {
        chronicle.add(new ChronicleEntry(day, kind, who, other, detail));
        while (chronicle.size() > CHRONICLE) {
            chronicle.remove(0);
        }
    }

    /** Jour depuis lequel le poste est vide après une mort, ou NONE. */
    long vacantSince(String job) {
        for (String v : vacancies) {
            int bar = v.lastIndexOf('|');
            if (bar > 0 && v.substring(0, bar).equals(job)) {
                try {
                    return Long.parseLong(v.substring(bar + 1));
                } catch (NumberFormatException e) {
                    return Inhabitant.NONE;
                }
            }
        }
        return Inhabitant.NONE;
    }

    void setVacant(String job, long day) {
        clearVacant(job);
        vacancies = Arrays.copyOf(vacancies, vacancies.length + 1);
        vacancies[vacancies.length - 1] = job + "|" + day;
    }

    void clearVacant(String job) {
        vacancies = Arrays.stream(vacancies).filter(v -> !v.startsWith(job + "|")).toArray(String[]::new);
    }
}
