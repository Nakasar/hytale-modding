package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import dev.nakasar.hytale.peuples.request.BoardPage;
import dev.nakasar.hytale.peuples.request.PlayerRequest;
import dev.nakasar.hytale.peuples.request.RequestType;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Les conditions et effets de dialogue du socle (étape 1), enregistrés dans {@link DialogueCondition#CODEC} et
 * {@link DialogueEffect#CODEC} au chargement de {@link Dialogue} (le validateur hors ligne décode donc les dialogues
 * sans démarrer le plugin).
 *
 * <p>Conditions : {@code Flag}, {@code NotFlag}, {@code InVillage}, {@code VillageTier}, {@code HasItem}.
 * Effets : {@code SetFlag}, {@code ClearFlag}, {@code GiveItem}, {@code TakeItem}, {@code AddEssor},
 * {@code SendMessage}, {@code OpenBoard}.
 *
 * <p>Étape 3 : condition {@code HasRequest} (le joueur a une demande dans ce village, type optionnel) ; effets
 * {@code OpenRequests} (tableau à boutons) et {@code TurnInRequests} (rendre les objets portés).
 */
public final class DialogueTypes {

    private static boolean registered;

    private DialogueTypes() {
    }

    static synchronized void registerBuiltins() {
        if (registered) {
            return;
        }
        registered = true;
        DialogueCondition.CODEC.register("Flag", FlagCondition.class, FlagCondition.CODEC);
        DialogueCondition.CODEC.register("NotFlag", NotFlagCondition.class, NotFlagCondition.CODEC);
        DialogueCondition.CODEC.register("InVillage", InVillageCondition.class, InVillageCondition.CODEC);
        DialogueCondition.CODEC.register("VillageTier", VillageTierCondition.class, VillageTierCondition.CODEC);
        DialogueCondition.CODEC.register("HasItem", HasItemCondition.class, HasItemCondition.CODEC);
        DialogueEffect.CODEC.register("SetFlag", SetFlagEffect.class, SetFlagEffect.CODEC);
        DialogueEffect.CODEC.register("ClearFlag", ClearFlagEffect.class, ClearFlagEffect.CODEC);
        DialogueEffect.CODEC.register("GiveItem", GiveItemEffect.class, GiveItemEffect.CODEC);
        DialogueEffect.CODEC.register("TakeItem", TakeItemEffect.class, TakeItemEffect.CODEC);
        DialogueEffect.CODEC.register("AddEssor", AddEssorEffect.class, AddEssorEffect.CODEC);
        DialogueEffect.CODEC.register("SendMessage", SendMessageEffect.class, SendMessageEffect.CODEC);
        DialogueEffect.CODEC.register("OpenBoard", OpenBoardEffect.class, OpenBoardEffect.CODEC);
        DialogueCondition.CODEC.register("HasRequest", HasRequestCondition.class, HasRequestCondition.CODEC);
        DialogueEffect.CODEC.register("OpenRequests", OpenRequestsEffect.class, OpenRequestsEffect.CODEC);
        DialogueEffect.CODEC.register("TurnInRequests", TurnInRequestsEffect.class, TurnInRequestsEffect.CODEC);
    }

    static CombinedItemContainer inventory(DialogueContext context) {
        return InventoryComponent.getCombined(context.store(), context.ref(), InventoryComponent.HOTBAR_STORAGE_BACKPACK);
    }

    static int quantity(Integer value) {
        return value == null || value < 1 ? 1 : value;
    }

    // ---- Conditions ----

    /** {@code {"Type": "Flag", "Flag": "x"}} : le joueur porte le drapeau. */
    public static final class FlagCondition extends DialogueCondition {
        public static final BuilderCodec<FlagCondition> CODEC = BuilderCodec.builder(FlagCondition.class, FlagCondition::new)
                .append(new KeyedCodec<>("Flag", Codec.STRING), (c, v) -> c.flag = v, c -> c.flag)
                .documentation("Drapeau que le joueur doit porter.")
                .add()
                .build();

        String flag;

        @Override
        public boolean test(DialogueContext context) {
            return flag != null && context.player().hasFlag(flag);
        }

        public String flag() {
            return flag;
        }
    }

    /** {@code {"Type": "NotFlag", "Flag": "x"}} : le joueur ne porte pas le drapeau. */
    public static final class NotFlagCondition extends DialogueCondition {
        public static final BuilderCodec<NotFlagCondition> CODEC = BuilderCodec.builder(NotFlagCondition.class, NotFlagCondition::new)
                .append(new KeyedCodec<>("Flag", Codec.STRING), (c, v) -> c.flag = v, c -> c.flag)
                .documentation("Drapeau que le joueur ne doit pas porter.")
                .add()
                .build();

        String flag;

        @Override
        public boolean test(DialogueContext context) {
            return flag == null || !context.player().hasFlag(flag);
        }

        public String flag() {
            return flag;
        }
    }

    /** {@code {"Type": "InVillage"}} : le joueur est dans un village (peuple optionnel). */
    public static final class InVillageCondition extends DialogueCondition {
        public static final BuilderCodec<InVillageCondition> CODEC = BuilderCodec.builder(InVillageCondition.class, InVillageCondition::new)
                .append(new KeyedCodec<>("People", Codec.STRING), (c, v) -> c.people = v, c -> c.people)
                .documentation("Peuple du village (vide : n'importe lequel).")
                .add()
                .build();

        String people;

        @Override
        public boolean test(DialogueContext context) {
            return context.village() != null && (people == null || people.equalsIgnoreCase(context.village().people().id()));
        }
    }

    /** {@code {"Type": "VillageTier", "Min": 1}} : le village du joueur a au moins ce palier. */
    public static final class VillageTierCondition extends DialogueCondition {
        public static final BuilderCodec<VillageTierCondition> CODEC = BuilderCodec.builder(VillageTierCondition.class, VillageTierCondition::new)
                .append(new KeyedCodec<>("Min", Codec.INTEGER), (c, v) -> c.min = v == null ? 0 : v, c -> c.min)
                .documentation("Palier minimal (0 campement à 3 bourg).")
                .add()
                .build();

        int min;

        @Override
        public boolean test(DialogueContext context) {
            return context.village() != null && context.village().tier() >= min;
        }
    }

    /** {@code {"Type": "HasItem", "ItemId": "x", "Quantity": 3}} : le joueur porte ces objets. */
    public static final class HasItemCondition extends DialogueCondition {
        public static final BuilderCodec<HasItemCondition> CODEC = BuilderCodec.builder(HasItemCondition.class, HasItemCondition::new)
                .append(new KeyedCodec<>("ItemId", Codec.STRING), (c, v) -> c.itemId = v, c -> c.itemId)
                .documentation("Id de l'objet.")
                .add()
                .append(new KeyedCodec<>("Quantity", Codec.INTEGER), (c, v) -> c.quantity = quantity(v), c -> c.quantity)
                .documentation("Quantité (1 par défaut).")
                .add()
                .build();

        String itemId;
        int quantity = 1;

        @Override
        public boolean test(DialogueContext context) {
            return itemId != null && inventory(context).canRemoveItemStack(new ItemStack(itemId, quantity));
        }

        public String itemId() {
            return itemId;
        }
    }

    // ---- Effets ----

    /** {@code {"Type": "SetFlag", "Flag": "x"}} : pose un drapeau sur le joueur. */
    public static final class SetFlagEffect extends DialogueEffect {
        public static final BuilderCodec<SetFlagEffect> CODEC = BuilderCodec.builder(SetFlagEffect.class, SetFlagEffect::new)
                .append(new KeyedCodec<>("Flag", Codec.STRING), (e, v) -> e.flag = v, e -> e.flag)
                .documentation("Drapeau à poser.")
                .add()
                .build();

        String flag;

        @Override
        public boolean apply(DialogueContext context) {
            context.player().setFlag(flag, true);
            return true;
        }

        public String flag() {
            return flag;
        }
    }

    /** {@code {"Type": "ClearFlag", "Flag": "x"}} : retire un drapeau. */
    public static final class ClearFlagEffect extends DialogueEffect {
        public static final BuilderCodec<ClearFlagEffect> CODEC = BuilderCodec.builder(ClearFlagEffect.class, ClearFlagEffect::new)
                .append(new KeyedCodec<>("Flag", Codec.STRING), (e, v) -> e.flag = v, e -> e.flag)
                .documentation("Drapeau à retirer.")
                .add()
                .build();

        String flag;

        @Override
        public boolean apply(DialogueContext context) {
            context.player().setFlag(flag, false);
            return true;
        }
    }

    /** {@code {"Type": "GiveItem", "ItemId": "x", "Quantity": 2}} : donne des objets s'il y a la place (rien au sol). */
    public static final class GiveItemEffect extends DialogueEffect {
        public static final BuilderCodec<GiveItemEffect> CODEC = BuilderCodec.builder(GiveItemEffect.class, GiveItemEffect::new)
                .append(new KeyedCodec<>("ItemId", Codec.STRING), (e, v) -> e.itemId = v, e -> e.itemId)
                .documentation("Id de l'objet.")
                .add()
                .append(new KeyedCodec<>("Quantity", Codec.INTEGER), (e, v) -> e.quantity = quantity(v), e -> e.quantity)
                .documentation("Quantité (1 par défaut).")
                .add()
                .build();

        String itemId;
        int quantity = 1;

        @Override
        public boolean apply(DialogueContext context) {
            if (itemId == null) {
                return false;
            }
            CombinedItemContainer inventory = inventory(context);
            ItemStack stack = new ItemStack(itemId, quantity);
            if (!inventory.canAddItemStack(stack)) {
                context.playerRef().sendMessage(Message.translation("nakasar_peuples.dialogue.inventoryFull"));
                return false;
            }
            inventory.addItemStack(stack);
            return true;
        }

        public String itemId() {
            return itemId;
        }
    }

    /** {@code {"Type": "TakeItem", "ItemId": "x", "Quantity": 2}} : prend des objets au joueur (tous ou aucun). */
    public static final class TakeItemEffect extends DialogueEffect {
        public static final BuilderCodec<TakeItemEffect> CODEC = BuilderCodec.builder(TakeItemEffect.class, TakeItemEffect::new)
                .append(new KeyedCodec<>("ItemId", Codec.STRING), (e, v) -> e.itemId = v, e -> e.itemId)
                .documentation("Id de l'objet.")
                .add()
                .append(new KeyedCodec<>("Quantity", Codec.INTEGER), (e, v) -> e.quantity = quantity(v), e -> e.quantity)
                .documentation("Quantité (1 par défaut).")
                .add()
                .build();

        String itemId;
        int quantity = 1;

        @Override
        public boolean apply(DialogueContext context) {
            return itemId != null && inventory(context).removeItemStack(new ItemStack(itemId, quantity), true, true).succeeded();
        }

        public String itemId() {
            return itemId;
        }
    }

    /** {@code {"Type": "AddEssor", "Amount": 10}} : ajoute de l'essor au village du joueur. */
    public static final class AddEssorEffect extends DialogueEffect {
        public static final BuilderCodec<AddEssorEffect> CODEC = BuilderCodec.builder(AddEssorEffect.class, AddEssorEffect::new)
                .append(new KeyedCodec<>("Amount", Codec.INTEGER), (e, v) -> e.amount = v == null ? 0 : v, e -> e.amount)
                .documentation("Essor ajouté (négatif : retiré).")
                .add()
                .build();

        int amount;

        @Override
        public boolean apply(DialogueContext context) {
            if (context.village() == null) {
                return false;
            }
            int gained = Villages.addEssor(context.village(), amount);
            context.playerRef().sendMessage(Message.translation("nakasar_peuples.village.essorGained")
                    .param("amount", gained).param("name", context.village().name()));
            return true;
        }
    }

    /** {@code {"Type": "SendMessage", "TextKey": "..."}} : écrit une ligne dans le tchat du joueur. */
    public static final class SendMessageEffect extends DialogueEffect {
        public static final BuilderCodec<SendMessageEffect> CODEC = BuilderCodec.builder(SendMessageEffect.class, SendMessageEffect::new)
                .append(new KeyedCodec<>("TextKey", Codec.STRING), (e, v) -> e.textKey = v, e -> e.textKey)
                .documentation("Clé de traduction du message.")
                .add()
                .build();

        String textKey;

        @Override
        public boolean apply(DialogueContext context) {
            if (textKey != null) {
                context.playerRef().sendMessage(Message.translation(textKey));
            }
            return true;
        }

        public String textKey() {
            return textKey;
        }
    }

    /** {@code {"Type": "OpenBoard"}} : ferme le dialogue et ouvre le tableau du village du joueur. */
    public static final class OpenBoardEffect extends DialogueEffect {
        public static final BuilderCodec<OpenBoardEffect> CODEC = BuilderCodec.builder(OpenBoardEffect.class, OpenBoardEffect::new)
                .build();

        @Override
        public boolean apply(DialogueContext context) {
            if (context.village() == null) {
                return false;
            }
            VillageBoard.open(context.world(), context.store(), context.ref(), context.playerRef(), context.village());
            return true;
        }

        @Override
        public boolean closesDialogue() {
            return true;
        }
    }

    // ---- Demandes (étape 3) ----

    /** {@code {"Type": "HasRequest", "RequestType": "Gather"}} : le joueur a une demande de ce village (de ce type). */
    public static final class HasRequestCondition extends DialogueCondition {
        public static final BuilderCodec<HasRequestCondition> CODEC = BuilderCodec.builder(HasRequestCondition.class, HasRequestCondition::new)
                .append(new KeyedCodec<>("RequestType", Codec.STRING), (c, v) -> c.type = v, c -> c.type)
                .documentation("Type de demande (Gather, Craft, Hunt, Delivery, Escort, Defense ; vide : n'importe lequel).")
                .add()
                .build();

        String type;

        @Override
        public boolean test(DialogueContext context) {
            if (context.village() == null) {
                return false;
            }
            RequestType wanted = type == null ? null : RequestType.byId(type);
            for (PlayerRequest r : context.player().requests()) {
                if (r.villageId().equals(context.village().id())
                        && (wanted == null || (r.template() != null && r.template().type() == wanted))) {
                    return true;
                }
            }
            return false;
        }
    }

    /** {@code {"Type": "OpenRequests"}} : ouvre le tableau à boutons du village (ferme le dialogue). */
    public static final class OpenRequestsEffect extends DialogueEffect {
        public static final BuilderCodec<OpenRequestsEffect> CODEC = BuilderCodec.builder(OpenRequestsEffect.class, OpenRequestsEffect::new)
                .build();

        @Override
        public boolean apply(DialogueContext context) {
            if (context.village() == null) {
                return false;
            }
            BoardPage.open(context.world(), context.store(), context.ref(), context.playerRef(), context.village());
            return true;
        }

        @Override
        public boolean closesDialogue() {
            return true;
        }
    }

    /** {@code {"Type": "TurnInRequests"}} : rend les objets portés pour les demandes de ce village. */
    public static final class TurnInRequestsEffect extends DialogueEffect {
        public static final BuilderCodec<TurnInRequestsEffect> CODEC = BuilderCodec.builder(TurnInRequestsEffect.class, TurnInRequestsEffect::new)
                .build();

        @Override
        public boolean apply(DialogueContext context) {
            if (context.village() == null) {
                return false;
            }
            Requests.turnIn(context.world(), context.store(), context.ref(), context.playerRef(), context.village());
            return true;
        }
    }
}
