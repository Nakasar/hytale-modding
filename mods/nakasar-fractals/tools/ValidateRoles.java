/*
 * Valide les rôles de PNJ du pack avec le BuilderManager du serveur Hytale, sans lancer le jeu :
 * attributs inconnus, types de briques (Sensor, Action, BodyMotion...) inexistants, valeurs invalides.
 * Les références vers d'autres assets (modèles, interactions, groupes...) ne peuvent pas être résolues
 * hors jeu : elles sont listées en "REF".
 *
 * Usage : java -cp Server-0.7.2.jar ValidateRoles.java <dossier Server du pack> [dossiers Server des packs requis...]
 *         java -cp Server-0.7.2.jar ValidateRoles.java --descriptors <fichier .md>  (référence de toutes les briques)
 */
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.asset.builder.BuilderManager;
import java.lang.reflect.*;
import java.nio.file.Path;
import java.util.List;
@SuppressWarnings({"removal", "unchecked", "rawtypes"})
public class ValidateRoles {
  public static void main(String[] a) throws Throwable { try { run(a); } catch (Throwable t) { t.printStackTrace(System.out); System.exit(2); } System.exit(0); }
  @SuppressWarnings({"unchecked","rawtypes"})
  static void reg(String cn) throws Throwable {
    Class c = Class.forName(cn);
    var map = new com.hypixel.hytale.assetstore.map.IndexedLookupTableAssetMap(n -> java.lang.reflect.Array.newInstance(c, n));
    var b = com.hypixel.hytale.server.core.asset.HytaleAssetStore.builder(c, map);
    b.setPath("X/" + c.getSimpleName());
    b.setCodec((com.hypixel.hytale.assetstore.codec.AssetCodec) c.getField("CODEC").get(null));
    Method gid = c.getMethod("getId");
    b.setKeyFunction(o -> { try { return gid.invoke(o); } catch (Exception e) { throw new RuntimeException(e); } });
    b.setReplaceOnRemove(k -> null);
    com.hypixel.hytale.assetstore.AssetRegistry.register(b.build());
  }
  static void mod(String cn) throws Throwable {
    sun.misc.Unsafe u = unsafe();
    Class<?> c = Class.forName(cn);
    Object o = u.allocateInstance(c);
    for (Field f : c.getDeclaredFields()) if (Modifier.isStatic(f.getModifiers()) && f.getType() == c) { f.setAccessible(true); u.putObject(u.staticFieldBase(f), u.staticFieldOffset(f), o); }
  }
  static void run(String[] a) throws Throwable {
    // Le journal du serveur (sur stdout comme sur stderr) signale les clés inconnues ("Unknown JSON attribute") et les
    // assets rejetés (SEVERE) sans lever d'erreur : on compte ces lignes comme des erreurs. Hors jeu, les parents vanilla
    // des interactions en ligne (InteractionVars) n'existent pas : ce rejet-là est attendu, on le note en REF.
    // Les piles d'appels qui suivent un message ne s'affichent qu'avec VALIDATE_TRACE (elles deviendraient des
    // annotations d'erreur dans GitHub Actions).
    java.io.PrintStream out = System.out;
    int[] warnings = {0};
    java.util.Set<String> vanillaParents = new java.util.TreeSet<>();
    boolean trace = System.getenv("VALIDATE_TRACE") != null;
    java.util.function.Consumer<String> filter = l -> {
      java.util.regex.Matcher parent = MISSING_PARENT.matcher(l);
      if (parent.find()) {
        if (parent.group(1).startsWith("Nakasar_")) { warnings[0]++; out.println("ERROR parent du mod introuvable : " + parent.group(1)); }
        else vanillaParents.add(parent.group(1));
      } else if (l.contains("Unknown JSON attribute") || l.contains("SEVERE]")) {
        warnings[0]++; out.println("ERROR " + l.substring(0, Math.min(l.length(), 240)));
      } else if (l.contains("INFO]") || l.contains("Removing child asset")) {
        // bruit
      } else if (trace || !STACK_LINE.matcher(l).find()) {
        out.println(l);
      }
    };
    System.setOut(lineStream(filter));
    System.setErr(lineStream(filter));
    com.hypixel.hytale.server.core.Options.parse(new String[0]);
    sun.misc.Unsafe u = unsafe();
    Class<?> sc = com.hypixel.hytale.server.core.HytaleServer.class;
    Object server = u.allocateInstance(sc);
    Field eb = sc.getDeclaredField("eventBus");
    u.putObject(server, u.objectFieldOffset(eb), new com.hypixel.hytale.event.EventBus(false));
    Field inst = sc.getDeclaredField("instance"); inst.setAccessible(true); inst.set(null, server);
    try { Class.forName("com.hypixel.hytale.server.core.asset.AssetRegistryLoader"); } catch (Throwable t) { System.out.println("WARN  AssetRegistryLoader : " + t); }
    reg("com.hypixel.hytale.server.core.modules.entitystats.asset.EntityStatType");
    reg("com.hypixel.hytale.builtin.tagset.config.NPCGroup");
    // Les InteractionVars des rôles déclarent des interactions en ligne : leur magasin doit exister pour les décoder.
    reg("com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction");
    reg("com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction");
    mod("com.hypixel.hytale.server.core.modules.entity.EntityModule");
    NPCPlugin p = (NPCPlugin) u.allocateInstance(NPCPlugin.class);
    BuilderManager bm = new BuilderManager();
    Field f = NPCPlugin.class.getDeclaredField("builderManager");
    u.putObject(p, u.objectFieldOffset(f), bm);
    Field lg = com.hypixel.hytale.server.core.plugin.PluginBase.class.getDeclaredField("logger");
    u.putObject(p, u.objectFieldOffset(lg), com.hypixel.hytale.logger.HytaleLogger.get("NPC"));
    Field pi = NPCPlugin.class.getDeclaredField("instance"); pi.setAccessible(true); pi.set(null, p);
    try { p.setupNPCLoading(); } catch (NullPointerException expected) { /* lit la config du plugin après l'enregistrement des briques */ }
    if (a[0].equals("--descriptors")) {
      writeDescriptors(bm, Path.of(a[1]));
      return;
    }
    Path pack = Path.of(a[0]);
    Path root = pack.resolve("NPC/Roles");
    java.util.Set<String> provided = new java.util.HashSet<>();
    // Ids fournis par ce pack et par les packs dont il dépend (arguments suivants).
    for (int i = 0; i < a.length; i++) {
      try (var walk = java.nio.file.Files.walk(Path.of(a[i]))) {
        walk.filter(x -> x.toString().endsWith(".json") || x.toString().endsWith(".particlesystem"))
            .forEach(x -> provided.add(x.getFileName().toString().replaceFirst("\\.(json|particlesystem)$", "")));
      }
    }

    if (!java.nio.file.Files.isDirectory(root)) { out.println("0 rôle dans " + root + " (pas encore de PNJ dans le pack)"); return; }
    List<Path> files;
    try (var walk = java.nio.file.Files.walk(root)) { files = walk.filter(x -> x.toString().endsWith(".json")).sorted().toList(); }
    int errors = 0;
    java.util.Set<String> refs = new java.util.TreeSet<>();
    for (Path file : files) {
      List<String> errs = new java.util.ArrayList<>();
      try {
        bm.loadFile(file, true, errs);
      } catch (Throwable t) { errs.add("chargement : " + t); }
      for (String e : errs) {
        java.util.regex.Matcher m = MISSING.matcher(e);
        if (m.find()) { refs.add(m.group(1) + " (" + m.group(2) + ")"); continue; }
        System.out.println("ERROR " + root.relativize(file) + " : " + e); errors++;
      }
    }
    errors += checkAttackTags(files, a);
    errors += checkForcedDespawn(files, root);
    errors += checkWalkMotions(files, root);
    for (String r : refs) {
      String id = r.substring(0, r.indexOf(" ("));
      // Nos ids sont préfixés Nakasar_ : s'il n'est fourni par aucun pack, c'est une faute de frappe.
      if (!provided.contains(id) && id.matches("(Root_)?Nakasar_.*")) { System.out.println("ERROR asset du mod introuvable : " + r); errors++; continue; }
      System.out.println((provided.contains(id) ? "REF   mod     " : "REF   vanilla ") + r);
    }
    List<String> errs = new java.util.ArrayList<>();
    try { bm.validateAllLoadedBuilders(bm.getAllBuilders(), true, errs); } catch (Throwable t) { errs.add("validation : " + t); t.printStackTrace(System.out); }
    for (String e : errs) { if (MISSING.matcher(e).find()) continue; System.out.println("ERROR " + e); errors++; }
    vanillaParents.forEach(id -> System.out.println("REF   vanilla " + id + " (Parent d'interaction en ligne)"));
    errors += warnings[0];
    System.setOut(out);
    System.out.println((errors == 0 ? "OK    " : "FAIL  ") + files.size() + " rôle(s), " + errors + " erreur(s)");
    if (errors > 0) System.exit(1);
  }
  /**
   * Une action {"Type": "Despawn", "Force": true} retire le PNJ pendant son propre tick : le serveur 0.7.2 relit
   * ensuite son NPCEntity sur une référence invalide (Role.computeActionsAndSteering) et le monde entier plante.
   * Sans Force, le PNJ est marqué à retirer (setToDespawn) et part proprement.
   */
  static int checkForcedDespawn(List<Path> roles, Path root) throws Exception {
    int errors = 0;
    java.util.regex.Pattern forced = java.util.regex.Pattern.compile(
        "\"Type\"\\s*:\\s*\"Despawn\"\\s*,\\s*\"Force\"\\s*:\\s*true|\"Force\"\\s*:\\s*true\\s*,\\s*\"Type\"\\s*:\\s*\"Despawn\"");
    for (Path file : roles) {
      if (forced.matcher(java.nio.file.Files.readString(file)).find()) {
        System.out.println("ERROR " + root.relativize(file) + " : action Despawn avec \"Force\": true (fait planter le monde en 0.7.2, retirer Force)");
        errors++;
      }
    }
    return errors;
  }
  /**
   * Certains mouvements (MaintainDistance, TakeOff, Land) exigent un contrôleur Walk : le serveur 0.7.2 refuse le rôle au
   * chargement (« Missing required motion controller: MotionControllerWalk », NPCLoadTimeValidationHelper), mais cette
   * vérification a besoin du modèle et ne tourne pas hors jeu. Un PNJ qui vole et garde ses distances lévite donc en
   * marchant (Walk avec MinHover/MaxHover), comme les esprits et les spectres vanilla.
   */
  static int checkWalkMotions(List<Path> roles, Path root) throws Exception {
    int errors = 0;
    java.util.regex.Pattern needsWalk = java.util.regex.Pattern.compile("\"Type\"\\s*:\\s*\"(MaintainDistance|TakeOff|Land)\"");
    java.util.regex.Pattern walk = java.util.regex.Pattern.compile("\"MotionControllerList\"\\s*:\\s*\\[[^\\]]*\"Type\"\\s*:\\s*\"Walk\"");
    for (Path file : roles) {
      String text = java.nio.file.Files.readString(file);
      java.util.regex.Matcher m = needsWalk.matcher(text);
      if (m.find() && !walk.matcher(text).find()) {
        System.out.println("ERROR " + root.relativize(file) + " : mouvement " + m.group(1) + " sans contrôleur Walk dans MotionControllerList (rôle refusé en jeu)");
        errors++;
      }
    }
    return errors;
  }
  /**
   * Les RootInteractions ne sont pas chargées hors jeu, donc le CombatInteractionValidator du serveur ne tourne pas.
   * On refait sa vérification sur les fichiers des packs : une interaction utilisée par une action "Attack" doit porter
   * le tag "Attack" (Tags: {"Attack": ["Melee"|"Ranged"|"Block"]}), avec un seul type d'attaque.
   */
  static int checkAttackTags(List<Path> roles, String[] packs) throws Exception {
    java.util.Map<String, Path> roots = new java.util.HashMap<>();
    for (String pack : packs) {
      Path dir = Path.of(pack).resolve("Item/RootInteractions");
      if (!java.nio.file.Files.isDirectory(dir)) continue;
      try (var walk = java.nio.file.Files.walk(dir)) {
        walk.filter(x -> x.toString().endsWith(".json")).forEach(x -> roots.put(x.getFileName().toString().replaceFirst("\\.json$", ""), x));
      }
    }
    java.util.Map<String, Path> interactions = new java.util.HashMap<>();
    for (String pack : packs) {
      Path dir = Path.of(pack).resolve("Item/Interactions");
      if (!java.nio.file.Files.isDirectory(dir)) continue;
      try (var walk = java.nio.file.Files.walk(dir)) {
        walk.filter(x -> x.toString().endsWith(".json")).forEach(x -> interactions.put(x.getFileName().toString().replaceFirst("\\.json$", ""), x));
      }
    }
    int errors = 0;
    java.util.Set<String> seen = new java.util.HashSet<>();
    for (Path role : roles) {
      java.util.List<String> attacks = new java.util.ArrayList<>();
      collectAttacks(org.bson.BsonDocument.parse(java.nio.file.Files.readString(role)), attacks);
      for (String id : attacks) {
        Path file = roots.get(id);
        if (file == null || !seen.add(id)) continue;
        org.bson.BsonDocument root = org.bson.BsonDocument.parse(java.nio.file.Files.readString(file));
        org.bson.BsonValue tags = root.get("Tags");
        org.bson.BsonValue attack = tags != null && tags.isDocument() ? tags.asDocument().get("Attack") : null;
        if (attack == null) {
          System.out.println("ERROR " + id + " : utilisée par une action Attack sans le tag \"Attack\" (ajouter \"Tags\": {\"Attack\": [\"Melee\"]} ou [\"Ranged\"])");
          errors++;
        } else if (attack.isArray() && attack.asArray().stream().filter(v -> v.isString() && List.of("Melee", "Ranged", "Block").contains(v.asString().getValue())).count() > 1) {
          System.out.println("ERROR " + id + " : plusieurs types d'attaque dans le tag \"Attack\" (un seul parmi Melee, Ranged, Block)");
          errors++;
        }
        int aiming = countAiming(root.get("Interactions"), interactions, new java.util.HashSet<>());
        if (aiming > 1) {
          System.out.println("ERROR " + id + " : " + aiming + " interactions portent le tag \"AimingReference\" dans la chaîne (une seule permise : la première LaunchProjectile)");
          errors++;
        }
      }
    }
    return errors;
  }
  /**
   * Nombre d'interactions de la chaîne qui portent le tag "AimingReference" (le CombatInteractionValidator du serveur
   * en accepte une seule) : chaque interaction en ligne compte, une interaction nommée du pack compte une fois.
   */
  static int countAiming(org.bson.BsonValue v, java.util.Map<String, Path> interactions, java.util.Set<String> visited) throws Exception {
    if (v == null) return 0;
    if (v.isString()) {
      String id = v.asString().getValue();
      Path file = interactions.get(id);
      if (file == null || !visited.add(id)) return 0;
      return countAiming(org.bson.BsonDocument.parse(java.nio.file.Files.readString(file)), interactions, visited);
    }
    int n = 0;
    if (v.isDocument()) {
      org.bson.BsonDocument d = v.asDocument();
      org.bson.BsonValue tags = d.get("Tags");
      if (tags != null && tags.isDocument() && tags.asDocument().containsKey("AimingReference")) n++;
      for (var e : d.entrySet()) {
        if (e.getKey().equals("Tags") || e.getKey().equals("Effects") || e.getKey().startsWith("$")) continue;
        n += countAiming(e.getValue(), interactions, visited);
      }
    } else if (v.isArray()) {
      for (org.bson.BsonValue c : v.asArray()) n += countAiming(c, interactions, visited);
    }
    return n;
  }
  static void collectAttacks(org.bson.BsonValue v, List<String> out) {
    if (v.isDocument()) {
      org.bson.BsonDocument d = v.asDocument();
      org.bson.BsonValue type = d.get("Type"), attack = d.get("Attack");
      if (type != null && type.isString() && type.asString().getValue().equals("Attack") && attack != null && attack.isString()) out.add(attack.asString().getValue());
      for (org.bson.BsonValue c : d.values()) collectAttacks(c, out);
    } else if (v.isArray()) {
      for (org.bson.BsonValue c : v.asArray()) collectAttacks(c, out);
    }
  }
  // Les assets (modèles, interactions, groupes...) ne sont pas chargés hors jeu : ces références sont listées, pas comptées.
  static final java.util.regex.Pattern MISSING_PARENT = java.util.regex.Pattern.compile("Failed to find parent(?: with key)? '([^']+)'");
  // Lignes d'une pile d'appels ou d'un extrait JSON qui suivent un message d'erreur du serveur.
  static final java.util.regex.Pattern STACK_LINE = java.util.regex.Pattern.compile(
      "^(\\s+at |\\s*\\.\\.\\. \\d+ more|Caused by: |com\\.hypixel\\.hytale\\.\\S*Exception|java\\.lang\\.\\S*Exception|From: |Buffer RawJsonReader|L\\s+\\d+>|\\s*\\|-*\\^|-*\\^|'$|\\s*$)");

  static java.io.PrintStream lineStream(java.util.function.Consumer<String> sink) {
    return new java.io.PrintStream(new java.io.OutputStream() {
      private final java.io.ByteArrayOutputStream line = new java.io.ByteArrayOutputStream();
      @Override public synchronized void write(int b) {
        if (b != '\n') { line.write(b); return; }
        String l = line.toString(java.nio.charset.StandardCharsets.UTF_8); line.reset();
        sink.accept(l);
      }
    }, true, java.nio.charset.StandardCharsets.UTF_8);
  }

  static final java.util.regex.Pattern MISSING = java.util.regex.Pattern.compile("\"([^\"]+)\" does not exist (?:for|in) attribute \"([^\"]+)\"");
  /**
   * Écrit la référence de toutes les briques de rôle (ce que produit la commande serveur /npc descriptors),
   * en Markdown : catégorie, nom, description et attributs (type, obligatoire, défaut, description).
   */
  static void writeDescriptors(BuilderManager bm, Path out) throws Exception {
    Path json = java.nio.file.Files.createTempFile("npc_descriptors", ".json");
    BuilderManager.saveDescriptors((List) bm.generateDescriptors(), json);
    var array = com.google.gson.JsonParser.parseString(java.nio.file.Files.readString(json)).getAsJsonArray();
    List<com.google.gson.JsonObject> builders = new java.util.ArrayList<>();
    array.forEach(e -> builders.add(e.getAsJsonObject()));
    builders.sort(java.util.Comparator.comparing((com.google.gson.JsonObject o) -> str(o, "Category")).thenComparing(o -> str(o, "Name")));
    StringBuilder md = new StringBuilder("# Briques des rôles de PNJ (serveur Hytale 0.7.2)\n\n"
        + "Généré par `java -cp Server-0.7.2.jar mods/nakasar-fractals/tools/ValidateRoles.java --descriptors docs/npc-reference-0.7.2.md`.\n"
        + "`*` = obligatoire ; `(computable)` = accepte `{\"Compute\": \"...\"}`.\n\n");
    for (var b : builders) {
      md.append("## ").append(str(b, "Category")).append(" / ").append(str(b, "Name")).append("  [").append(str(b, "State")).append("]\n");
      String desc = str(b, "LongDescription").isEmpty() ? str(b, "ShortDescription") : str(b, "LongDescription");
      md.append(desc.strip()).append("\n");
      for (var e : b.getAsJsonArray("Attributes")) {
        var at = e.getAsJsonObject();
        md.append("- ").append(str(at, "Name")).append("REQUIRED".equals(str(at, "Required")) ? "*" : "").append(": ").append(str(at, "Type"));
        if (!str(at, "Domain").isEmpty()) md.append(" <").append(str(at, "Domain")).append(">");
        if (!str(at, "DefaultValue").isEmpty()) md.append(" = ").append(str(at, "DefaultValue"));
        if (at.has("Computable") && at.get("Computable").getAsBoolean()) md.append(" (computable)");
        md.append(" — ").append(str(at, "ShortDescription").strip()).append("\n");
      }
      md.append("\n");
    }
    java.nio.file.Files.writeString(out, md);
    System.out.println("OK    " + builders.size() + " briques écrites dans " + out);
  }

  static String str(com.google.gson.JsonObject o, String key) {
    var v = o.get(key);
    return v == null || v.isJsonNull() ? "" : v.isJsonPrimitive() ? v.getAsString() : v.toString();
  }

  static sun.misc.Unsafe unsafe() throws Exception { Field uf = sun.misc.Unsafe.class.getDeclaredField("theUnsafe"); uf.setAccessible(true); return (sun.misc.Unsafe) uf.get(null); }
}
