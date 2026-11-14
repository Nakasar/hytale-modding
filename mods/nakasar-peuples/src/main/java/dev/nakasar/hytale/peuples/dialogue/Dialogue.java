package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.assetstore.AssetStore;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.codec.validation.ValidationResults;

import java.util.HashSet;
import java.util.Set;

/**
 * Un dialogue de PNJ, asset JSON du mod ({@value #PATH}/&lt;peuple&gt;/&lt;id&gt;.json ; GDD, section Dialogue avec les PNJ).
 *
 * <pre>
 * {
 *   "NpcNameKey": "nakasar_peuples.dialogue.X.npc",       nom du PNJ en en-tête
 *   "RoleKey": "nakasar_peuples.dialogue.X.role",         son métier (facultatif)
 *   "People": "Kweebec",                                  peuple (pastille de rang ; facultatif)
 *   "Entries": [ {"Node": "Retour", "Conditions": [...]}, {"Node": "Accueil"} ],
 *   "Nodes": [ {"Id": "Accueil", "TextKey": "...", "Responses": [ ... ]} ]
 * }
 * </pre>
 * Le nœud d'entrée est la première entrée dont les conditions sont remplies (GDD : priorité raid, tâche à rendre,
 * étape de chaîne, salutation du rang). Une réponse : {@code TextKey}, {@code HintKey} (ligne d'effet sous le bouton),
 * {@code Conditions}, {@code FailKey} (condition affichée quand elle n'est pas remplie), {@code Effects} et
 * {@code Next} (nœud suivant ; absent : la fenêtre se ferme).
 */
public final class Dialogue implements JsonAssetWithMap<String, DefaultAssetMap<String, Dialogue>> {

    public static final String PATH = "Nakasar/Dialogues";
    /** Quatre réponses au plus par nœud (maquette de la fenêtre de dialogue). */
    public static final int MAX_RESPONSES = 4;

    /** Entrée : nœud de départ si ses conditions sont remplies. */
    public static final class Entry {
        public static final BuilderCodec<Entry> CODEC = BuilderCodec.builder(Entry.class, Entry::new)
                .append(new KeyedCodec<>("Node", Codec.STRING), (e, v) -> e.node = v, e -> e.node)
                .documentation("Nœud de départ.")
                .add()
                .append(new KeyedCodec<>("Conditions", new ArrayCodec<>(DialogueCondition.CODEC, DialogueCondition[]::new)),
                        (e, v) -> e.conditions = v, e -> e.conditions)
                .documentation("Conditions de cette entrée (toutes).")
                .add()
                .build();

        String node;
        DialogueCondition[] conditions = new DialogueCondition[0];

        public String node() {
            return node;
        }

        public DialogueCondition[] conditions() {
            return conditions;
        }
    }

    public static final AssetBuilderCodec<String, Dialogue> CODEC = AssetBuilderCodec.builder(Dialogue.class, Dialogue::new,
                    Codec.STRING, (d, id) -> d.id = id, d -> d.id, (d, data) -> d.data = data, d -> d.data)
            .append(new KeyedCodec<>("NpcNameKey", Codec.STRING), (d, v) -> d.npcNameKey = v, d -> d.npcNameKey)
            .documentation("Clé de traduction du nom du PNJ.")
            .add()
            .append(new KeyedCodec<>("RoleKey", Codec.STRING), (d, v) -> d.roleKey = v, d -> d.roleKey)
            .documentation("Clé de traduction du métier du PNJ.")
            .add()
            .append(new KeyedCodec<>("People", Codec.STRING), (d, v) -> d.people = v, d -> d.people)
            .documentation("Peuple du PNJ.")
            .add()
            .append(new KeyedCodec<>("Entries", new ArrayCodec<>(Entry.CODEC, Entry[]::new)), (d, v) -> d.entries = v, d -> d.entries)
            .documentation("Nœuds d'entrée par priorité : le premier dont les conditions sont remplies.")
            .add()
            .append(new KeyedCodec<>("Nodes", new ArrayCodec<>(DialogueNode.CODEC, DialogueNode[]::new)), (d, v) -> d.nodes = v, d -> d.nodes)
            .documentation("Nœuds du dialogue.")
            .add()
            .validator(Dialogue::validate)
            .build();

    private static AssetStore<String, Dialogue, DefaultAssetMap<String, Dialogue>> assetStore;

    protected AssetExtraInfo.Data data;
    protected String id;
    String npcNameKey;
    String roleKey;
    String people;
    Entry[] entries = new Entry[0];
    DialogueNode[] nodes = new DialogueNode[0];

    Dialogue() {
    }

    @SuppressWarnings("unchecked")
    public static AssetStore<String, Dialogue, DefaultAssetMap<String, Dialogue>> getAssetStore() {
        if (assetStore == null) {
            assetStore = (AssetStore<String, Dialogue, DefaultAssetMap<String, Dialogue>>) (AssetStore<?, ?, ?>) AssetRegistry.getAssetStore(Dialogue.class);
        }
        return assetStore;
    }

    public static DefaultAssetMap<String, Dialogue> getAssetMap() {
        return getAssetStore().getAssetMap();
    }

    /** Dialogue d'id `id`, ou null. */
    public static Dialogue get(String id) {
        AssetStore<String, Dialogue, DefaultAssetMap<String, Dialogue>> store = getAssetStore();
        return store == null || id == null ? null : store.getAssetMap().getAsset(id);
    }

    @Override
    public String getId() {
        return id;
    }

    public String npcNameKey() {
        return npcNameKey;
    }

    public String roleKey() {
        return roleKey;
    }

    public String people() {
        return people;
    }

    public Entry[] entries() {
        return entries;
    }

    public DialogueNode[] nodes() {
        return nodes;
    }

    public DialogueNode node(String nodeId) {
        if (nodeId != null && nodes != null) {
            for (DialogueNode n : nodes) {
                if (n != null && nodeId.equals(n.id())) {
                    return n;
                }
            }
        }
        return null;
    }

    /** Nœud de départ pour ce joueur : première entrée remplie, sinon le premier nœud. */
    public DialogueNode start(DialogueContext context) {
        if (entries != null) {
            for (Entry e : entries) {
                if (e != null && DialogueCondition.all(e.conditions, context)) {
                    DialogueNode n = node(e.node);
                    if (n != null) {
                        return n;
                    }
                }
            }
        }
        return nodes == null || nodes.length == 0 ? null : nodes[0];
    }

    /** Cohérence du graphe : ids uniques, cibles existantes, au plus {@value #MAX_RESPONSES} réponses par nœud. */
    private static void validate(Dialogue d, ValidationResults results) {
        if (d.nodes == null || d.nodes.length == 0) {
            results.fail("Un dialogue a au moins un nœud (Nodes)");
            return;
        }
        Set<String> ids = new HashSet<>();
        for (DialogueNode n : d.nodes) {
            if (n == null || n.id() == null || n.id().isBlank()) {
                results.fail("Nœud sans Id");
            } else if (!ids.add(n.id())) {
                results.fail("Nœud en double : " + n.id());
            }
        }
        if (d.entries != null) {
            for (Entry e : d.entries) {
                if (e != null && !ids.contains(e.node)) {
                    results.fail("Entrée vers un nœud absent : " + e.node);
                }
            }
        }
        for (DialogueNode n : d.nodes) {
            if (n == null) {
                continue;
            }
            if (n.textKey() == null || n.textKey().isBlank()) {
                results.fail("Nœud " + n.id() + " sans TextKey");
            }
            DialogueResponse[] responses = n.responses();
            if (responses != null && responses.length > MAX_RESPONSES) {
                results.fail("Nœud " + n.id() + " : " + responses.length + " réponses, " + MAX_RESPONSES + " au plus");
            }
            if (responses != null) {
                for (DialogueResponse r : responses) {
                    if (r == null) {
                        continue;
                    }
                    if (r.textKey() == null || r.textKey().isBlank()) {
                        results.fail("Nœud " + n.id() + " : réponse sans TextKey");
                    }
                    if (r.next() != null && !ids.contains(r.next())) {
                        results.fail("Nœud " + n.id() + " : réponse vers un nœud absent (" + r.next() + ")");
                    }
                }
            }
        }
    }

    static {
        DialogueTypes.registerBuiltins();
    }
}
