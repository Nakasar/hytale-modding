package dev.nakasar.hytale.fractals.party;

import com.hypixel.hytale.server.core.Message;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Fractales du jour (GDD, récompenses) : {@value #COUNT} fractales ouvertes tirées chaque jour pour tout le serveur
 * (graine = date du serveur). Terminer l'une d'elles donne, la première fois du jour pour chaque joueur, le coffre
 * des fractales du jour ({@value #BAG}) en plus du coffre de fin ({@code ClaimRewardInteraction}).
 */
public final class DailyFractals {

    public static final int COUNT = 3;
    public static final String BAG = "Nakasar_Fractal_Daily_Bag";

    private DailyFractals() {
    }

    /** Les fractales du jour `day`, dans l'ordre du catalogue. */
    public static List<String> of(LocalDate day) {
        List<String> open = new ArrayList<>();
        for (String id : FractalCatalog.IDS) {
            if (FractalCatalog.isOpen(id)) {
                open.add(id);
            }
        }
        List<String> drawn = new ArrayList<>(open);
        Collections.shuffle(drawn, new Random(day.toEpochDay() * 7919L + 17L));
        List<String> out = new ArrayList<>(drawn.subList(0, Math.min(COUNT, drawn.size())));
        out.sort((a, b) -> Integer.compare(FractalCatalog.IDS.indexOf(a), FractalCatalog.IDS.indexOf(b)));
        return List.copyOf(out);
    }

    public static List<String> today() {
        return of(LocalDate.now());
    }

    public static long day() {
        return LocalDate.now().toEpochDay();
    }

    public static boolean isDaily(String fractal) {
        return today().contains(fractal);
    }

    /** Les fractales du jour, une par ligne ; `done` : celles déjà faites aujourd'hui par le joueur (cochées). */
    public static Message describe(List<String> done) {
        Message out = Message.translation("nakasar_fractals_progress.daily.title");
        for (String id : today()) {
            out.insert(Message.raw("\n" + (done.contains(id) ? "  ✔ " : "  ◇ "))).insert(FractalCatalog.name(id).bold(true));
        }
        return out;
    }
}
