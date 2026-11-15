package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Archetype;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.event.events.ecs.UseEntityEvent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;

/**
 * Un joueur utilise un PNJ du mod (touche d'interaction ; ses rôles se déclarent interactifs comme le marchand kweebec
 * vanilla, et l'événement vanilla {@link UseEntityEvent} arrive ici) :
 * <ul>
 *   <li>le crieur d'un village ouvre son dialogue ({@code <Peuple>_Crieur}) : voir les demandes, rendre ;</li>
 *   <li>le marchand d'un village ouvre le sien ({@code <Peuple>_Marchand}) : les échoppes de troc selon le rang ;</li>
 *   <li>le guetteur d'une livraison prend la missive et remplit la demande ;</li>
 *   <li>le captif d'une escorte répond qu'il suit le joueur ;</li>
 *   <li>un villageois à métier (étape 5) ouvre le dialogue de son métier ;</li>
 *   <li>le colon d'un village au palier max propose de fonder un village ({@code outpost/Settlers}).</li>
 * </ul>
 */
public final class VillagerUseSystem extends EntityEventSystem<EntityStore, UseEntityEvent.Post> {

    public VillagerUseSystem() {
        super(UseEntityEvent.Post.class);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Archetype.empty();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       UseEntityEvent.Post event) {
        Ref<EntityStore> target = event.getTargetEntity();
        InteractionContext context = event.getContext();
        Ref<EntityStore> user = context != null && context.getEntity() != null ? context.getEntity() : chunk.getReferenceTo(index);
        if (target == null || user == null || !user.isValid()) {
            return;
        }
        PlayerRef player = buffer.getComponent(user, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        String crierVillage = Criers.villageOf(target);
        String merchantVillage = Criers.merchantVillageOf(target);
        String chiefVillage = Criers.chiefVillageOf(target);
        RequestSpawns.Owner owner = RequestSpawns.owner(target);
        dev.nakasar.hytale.peuples.village.Villagers.Posted posted = dev.nakasar.hytale.peuples.village.Villagers.posted(target);
        // Étape 7 : les Trorks vanilla du camp n'ont pas de dialogue.
        dev.nakasar.hytale.peuples.village.Villagers.Posted villager =
                posted != null && posted.dialogue() != null && !posted.dialogue().isEmpty() ? posted : null;
        boolean klops = dev.nakasar.hytale.peuples.klops.Klops.isWanderer(target);
        boolean settler = dev.nakasar.hytale.peuples.outpost.Settlers.villageOf(target) != null;
        if (crierVillage == null && merchantVillage == null && chiefVillage == null && owner == null && villager == null && !klops && !settler) {
            return;
        }
        World world = store.getExternalData().getWorld();
        world.execute(() -> {
            Store<EntityStore> s = world.getEntityStore().getStore();
            if (!user.isValid()) {
                return;
            }
            if (settler) {
                dev.nakasar.hytale.peuples.outpost.Settlers.talk(world, s, user, player, target);
            } else if (klops) {
                Dialogue dialogue = Dialogue.get(dev.nakasar.hytale.peuples.klops.Klops.DIALOGUE);
                if (dialogue != null) {
                    Dialogues.openPage(world, s, user, player, dialogue, target);
                }
            } else if (villager != null) {
                Dialogue dialogue = Dialogue.get(villager.dialogue());
                if (dialogue == null) {
                    player.sendMessage(Message.translation(Dialogues.KEYS + "unknown").param("id", villager.dialogue()));
                } else {
                    Dialogues.openPage(world, s, user, player, dialogue, target);
                }
            } else if (crierVillage != null) {
                talk(world, s, user, player, crierVillage, false, target);
            } else if (merchantVillage != null) {
                talk(world, s, user, player, merchantVillage, true, target);
            } else if (chiefVillage != null) {
                Village village = Villages.registry(world).byId(chiefVillage);
                Dialogue dialogue = village == null ? null : Dialogue.get(village.people().chiefDialogue());
                if (dialogue != null) {
                    Dialogues.openPage(world, s, user, player, dialogue, target);
                }
            } else if (owner.kind() == RequestSpawns.Kind.LOOKOUT) {
                deliver(world, s, user, player, owner);
            } else if (owner.kind() == RequestSpawns.Kind.DEPARTING) {
                player.sendMessage(Message.translation(Requests.KEYS + "delivery.after"));
            } else if (owner.kind() == RequestSpawns.Kind.CAPTIVE) {
                player.sendMessage(Message.translation(Requests.KEYS + "escort.follow"));
            }
        });
    }

    /** Ouvre le dialogue du crieur ou du marchand du village. */
    private static void talk(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String villageId, boolean merchant,
                             Ref<EntityStore> npc) {
        Village village = Villages.registry(world).byId(villageId);
        if (village == null) {
            return;
        }
        String id = merchant ? village.people().merchantDialogue() : village.people().crierDialogue();
        Dialogue dialogue = Dialogue.get(id);
        if (dialogue == null) {
            player.sendMessage(Message.translation(Dialogues.KEYS + "unknown").param("id", id));
            return;
        }
        Dialogues.openPage(world, store, ref, player, dialogue, npc);
    }

    /** Le guetteur reçoit la missive : la livraison du joueur à qui il est destiné est remplie. */
    private static void deliver(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, RequestSpawns.Owner owner) {
        if (!owner.key().startsWith(player.getUuid() + "|")) {
            player.sendMessage(Message.translation(Requests.KEYS + "delivery.notYours"));
            return;
        }
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        String requestId = owner.key().substring(owner.key().indexOf('|') + 1);
        PlayerRequest r = data == null ? null : data.request(requestId);
        Village village = r == null ? null : Villages.registry(world).byId(r.villageId());
        if (r == null || village == null) {
            return;
        }
        if (!Requests.inventory(store, ref).canRemoveItemStack(new com.hypixel.hytale.server.core.inventory.ItemStack(village.people().missiveItem(), 1))) {
            player.sendMessage(Message.translation(Requests.KEYS + "delivery.noMissive")
                    .param("item", dev.nakasar.hytale.peuples.village.VillageBoard.itemName(village.people().missiveItem())));
            return;
        }
        player.sendMessage(Message.translation(Requests.KEYS + "delivery.thanks"));
        Requests.advance(world, store, ref, player, data, r, 1);
    }

    /** Toutes les demandes du joueur dans ce village (pour le dialogue). */
    static ArrayList<PlayerRequest> requestsIn(PeuplesPlayer data, Village village) {
        ArrayList<PlayerRequest> out = new ArrayList<>();
        if (data != null) {
            for (PlayerRequest r : data.requests()) {
                if (r.villageId().equals(village.id())) {
                    out.add(r);
                }
            }
        }
        return out;
    }
}
