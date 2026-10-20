package dev.nakasar.hytale.fractals.progress;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.inventory.container.filter.FilterActionType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.observatory.Observatory;

/**
 * Progression d'un joueur dans les fractales, sauvegardée avec lui (id {@value #ID}) : le plus haut niveau débloqué
 * et les {@value #SLOTS} emplacements de l'Autel des infusions (GDD, comme les emplacements de runes vanilla
 * {@code InventoryComponent.AbilitySlots} : portés par le joueur, ouverts par un bloc). Seules les infusions
 * ({@link #infusionLevel}) y entrent ; leur total est la résistance à l'agonie, partout où va le joueur.
 */
public final class FractalProgress implements Component<EntityStore> {

    public static final String ID = "Nakasar_Fractal_Progress";
    public static final short SLOTS = 12;
    public static final String INFUSION_PREFIX = "Nakasar_Fractal_Infusion_";
    public static final int MAX_INFUSION = 15;

    public static final BuilderCodec<FractalProgress> CODEC = BuilderCodec.builder(FractalProgress.class, FractalProgress::new)
            .append(new KeyedCodec<>("UnlockedLevel", Codec.INTEGER), (p, v) -> p.unlockedLevel = clampLevel(v), p -> p.unlockedLevel)
            .documentation("Plus haut niveau de fractale debloque (1 a 100).")
            .add()
            .append(new KeyedCodec<>("Infusions", ItemContainer.CODEC), (p, v) -> p.setInfusions(v), p -> p.infusions)
            .documentation("Emplacements de l'Autel des infusions.")
            .add()
            .build();

    private static ComponentType<EntityStore, FractalProgress> componentType;

    int unlockedLevel = Observatory.MIN_LEVEL;
    private SimpleItemContainer infusions = filtered(new SimpleItemContainer(SLOTS));

    public static ComponentType<EntityStore, FractalProgress> getComponentType() {
        return componentType;
    }

    public static void setComponentType(ComponentType<EntityStore, FractalProgress> type) {
        componentType = type;
    }

    /** Progression du joueur, ou null s'il n'a encore rien fait dans les fractales. */
    public static FractalProgress get(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player) {
        return player == null || !player.isValid() ? null : accessor.getComponent(player, componentType);
    }

    /** Progression du joueur, créée au besoin (hors du traitement du store). */
    public static FractalProgress ensure(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player) {
        return accessor.ensureAndGetComponent(player, componentType);
    }

    /** Plus haut niveau débloqué par le joueur (1 s'il n'a pas de progression). */
    public static int unlocked(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player) {
        FractalProgress progress = get(accessor, player);
        return progress == null ? Observatory.MIN_LEVEL : progress.unlockedLevel;
    }

    /** Résistance à l'agonie du joueur (0 sans progression). */
    public static int resistance(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player) {
        FractalProgress progress = get(accessor, player);
        return progress == null ? 0 : progress.resistance();
    }

    public int unlockedLevel() {
        return unlockedLevel;
    }

    /** Débloque le niveau suivant si {@code level} atteint le plus haut débloqué ; rend le nouveau niveau, ou 0. */
    public int completeAt(int level) {
        if (level < unlockedLevel || unlockedLevel >= Observatory.MAX_LEVEL) {
            return 0;
        }
        unlockedLevel++;
        return unlockedLevel;
    }

    public ItemContainer infusions() {
        return infusions;
    }

    /** Somme des infusions posées dans l'autel. */
    public int resistance() {
        int total = 0;
        for (short slot = 0; slot < infusions.getCapacity(); slot++) {
            ItemStack stack = infusions.getItemStack(slot);
            if (!ItemStack.isEmpty(stack)) {
                total += infusionLevel(stack.getItemId()) * stack.getQuantity();
            }
        }
        return total;
    }

    /** Résistance donnée par un objet : n pour {@code Nakasar_Fractal_Infusion_nn}, 0 pour le reste. */
    public static int infusionLevel(String itemId) {
        if (itemId == null || !itemId.startsWith(INFUSION_PREFIX)) {
            return 0;
        }
        try {
            int level = Integer.parseInt(itemId.substring(INFUSION_PREFIX.length()));
            return level >= 1 && level <= MAX_INFUSION ? level : 0;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private void setInfusions(ItemContainer container) {
        SimpleItemContainer slots = new SimpleItemContainer(SLOTS);
        if (container != null) {
            for (short slot = 0; slot < Math.min(SLOTS, container.getCapacity()); slot++) {
                ItemStack stack = container.getItemStack(slot);
                if (!ItemStack.isEmpty(stack)) {
                    slots.setItemStackForSlot(slot, stack);
                }
            }
        }
        infusions = filtered(slots);
    }

    /** Un emplacement n'accepte qu'une infusion, une seule à la fois. */
    private static SimpleItemContainer filtered(SimpleItemContainer container) {
        for (short slot = 0; slot < container.getCapacity(); slot++) {
            container.setSlotFilter(FilterActionType.ADD, slot, (action, c, s, stack) ->
                    stack == null || infusionLevel(stack.getItemId()) > 0 && stack.getQuantity() == 1);
        }
        return container;
    }

    private static int clampLevel(Integer level) {
        return level == null ? Observatory.MIN_LEVEL : Math.max(Observatory.MIN_LEVEL, Math.min(Observatory.MAX_LEVEL, level));
    }

    @Override
    public Component<EntityStore> clone() {
        FractalProgress copy = new FractalProgress();
        copy.unlockedLevel = unlockedLevel;
        copy.infusions = infusions.clone();
        return copy;
    }
}
