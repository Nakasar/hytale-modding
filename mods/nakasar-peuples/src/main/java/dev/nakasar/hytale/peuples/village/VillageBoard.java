package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.BlockLorePage;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.RequestTemplate;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.request.VillageRequest;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Le tableau du village (GDD, section Le dépôt et le tableau) : la page texte vanilla {@link BlockLorePage} (celle des
 * notes et du tableau des brèches du mod Vampires, déjà éprouvée en jeu), remplie par le Java avec l'état du village
 * lu dans sa ressource : peuple et palier, jauge d'essor, rang du joueur, demandes, contenu du dépôt.
 *
 * <p>Étape 3 : les trois demandes du jour et leur état pour le joueur. Étape 4 : le rang du joueur dans le village,
 * ses deux jauges et ce que son rang ouvre ; les cases 2 et 3 restent fermées à l'étranger. La
 * page à boutons {@link dev.nakasar.hytale.peuples.request.BoardPage} reprend ce texte à droite.
 */
public final class VillageBoard {

    private static final String KEYS = "nakasar_peuples.board.";
    private static final int BAR = 20;
    private static final int MAX_DEPOSIT_LINES = 12;

    private VillageBoard() {
    }

    /** Ouvre le tableau de `village` au joueur (thread du monde). */
    public static void open(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village) {
        Player player = ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return;
        }
        Message title = Message.translation(KEYS + "title").param("name", village.name());
        Requests.refresh(store, village);
        BlockLorePage page = new BlockLorePage(playerRef, title, body(world, village, store, ref), BlockLorePage.TextAlignment.Left);
        player.getPageManager().openCustomPage(ref, store, page);
    }

    /** Texte du tableau, ligne par ligne (aussi envoyé dans le tchat par {@code /village info}), sans état personnel. */
    public static Message body(World world, Village village) {
        return body(world, village, null, null);
    }

    /**
     * Texte du tableau, avec le rang du joueur `ref` et l'état de ses demandes (`ref` null : sans état personnel).
     */
    public static Message body(World world, Village village, Store<EntityStore> store, Ref<EntityStore> ref) {
        PeuplesPlayer data = ref == null ? null : PeuplesPlayer.get(store, ref);
        List<Message> lines = new ArrayList<>();
        lines.add(Message.translation(KEYS + "people")
                .param("people", Message.translation(village.people().nameKey()))
                .param("tier", Message.translation(Tiers.nameKey(village.tier()))));
        lines.add(Message.empty());
        int threshold = Tiers.threshold(village.tier());
        if (threshold > 0) {
            lines.add(Message.translation(KEYS + "essor").param("essor", village.essor()).param("max", threshold));
            lines.add(Message.raw(bar(village.essor(), threshold)).color(village.essor() >= threshold ? "#7ed957" : "#e8c46a"));
            lines.add(Message.translation(village.essor() >= threshold ? KEYS + "essorFull" : KEYS + "nextTier")
                    .param("tier", Message.translation(Tiers.nameKey(village.tier() + 1))));
        } else {
            lines.add(Message.translation(KEYS + "maxTier"));
        }
        lines.add(Message.empty());
        Rank rank = Rank.ETRANGER;
        if (ref != null) {
            Reputations.Standing standing = Reputations.standing(store, ref, village);
            rank = standing.rank();
            lines.add(Message.translation(KEYS + "rank").param("rank", Reputations.describe(rank, standing.value())));
            lines.add(Message.translation(KEYS + "rankDetail").param("village", standing.village()).param("people", standing.people())
                    .param("peopleName", Message.translation(village.people().nameKey())));
            lines.add(Message.translation(KEYS + "perks").param("perks", Message.translation(rank.perksKey())));
            lines.add(Message.empty());
        }
        lines.add(Message.translation(KEYS + "requests"));
        VillageRequest[] board = village.requests();
        boolean any = false;
        for (int i = 0; i < board.length; i++) {
            RequestTemplate t = board[i] == null ? null : board[i].template();
            if (t == null) {
                continue;
            }
            any = true;
            boolean open = i == 0 || ref == null || rank.atLeast(Rank.TOLERE);
            String state = switch (Requests.status(data, board[i])) {
                case TAKEN -> "requestTaken";
                case DONE -> "requestDone";
                default -> open ? "requestOpen" : "requestLocked";
            };
            lines.add(Message.translation(KEYS + "requestLine").param("number", i + 1)
                    .param("type", Message.translation(t.type().nameKey())).param("title", Requests.title(t))
                    .param("state", Message.translation(KEYS + state)));
        }
        if (!any) {
            lines.add(Message.translation(KEYS + "requestsNone"));
        }
        lines.add(Message.empty());
        lines.add(Message.translation(KEYS + "deposit"));
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        if (deposit == null) {
            lines.add(Message.translation(KEYS + "depositMissing"));
        } else if (deposit.isEmpty()) {
            lines.add(Message.translation(KEYS + "depositEmpty"));
        } else {
            int shown = 0;
            for (Map.Entry<String, Integer> e : deposit.entrySet()) {
                if (shown++ == MAX_DEPOSIT_LINES) {
                    lines.add(Message.translation(KEYS + "depositMore").param("count", deposit.size() - MAX_DEPOSIT_LINES));
                    break;
                }
                lines.add(Message.translation(KEYS + "depositLine").param("count", e.getValue()).param("item", itemName(e.getKey())));
            }
        }
        Message body = Message.empty();
        for (int i = 0; i < lines.size(); i++) {
            if (i > 0) {
                body.insert("\n");
            }
            body.insert(lines.get(i));
        }
        return body;
    }

    /** Nom traduit d'un objet (son id brut si l'objet est inconnu). */
    public static Message itemName(String itemId) {
        Item item = Item.getAssetMap().getAsset(itemId);
        return item == null ? Message.raw(itemId) : item.getTranslationMessage();
    }

    static String bar(int value, int max) {
        int filled = max <= 0 ? BAR : Math.min(BAR, (int) Math.round((double) value * BAR / max));
        return "[" + "|".repeat(filled) + ".".repeat(BAR - filled) + "]";
    }
}
