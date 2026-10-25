import java.io.IOException;
import java.lang.classfile.ClassFile;
import java.lang.classfile.ClassModel;
import java.lang.classfile.CodeElement;
import java.lang.classfile.CodeModel;
import java.lang.classfile.Instruction;
import java.lang.classfile.MethodModel;
import java.lang.classfile.instruction.InvokeInstruction;
import java.lang.classfile.instruction.LoadInstruction;
import java.lang.classfile.instruction.StoreInstruction;
import java.util.HashMap;
import java.lang.constant.MethodTypeDesc;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Stream;

/**
 * Repère, dans les classes compilées d'un mod, deux appels {@code registerSystem(...)} avec la même classe de système.
 * Le serveur Hytale n'accepte qu'un système par classe : le second lève « System of type ... is already registered! »
 * et le plugin entier échoue à se charger (vu en jeu, 2026-10-25).
 *
 * <p>Le type de l'argument est lu sur l'instruction qui précède l'appel : {@code new X(...)} donne X, une fabrique
 * {@code Foo.system()} donne son type de retour, une variable locale le type de ce qu'on y a rangé. Un appel dont le type n'est pas reconnu est signalé sans faire
 * échouer la vérification.
 *
 * <p>Usage : {@code java tools/CheckSystemRegistrations.java <dossier de classes>...}
 */
public final class CheckSystemRegistrations {

    public static void main(String[] args) throws IOException {
        Map<String, List<String>> calls = new TreeMap<>();
        int unknown = 0;
        for (String dir : args) {
            Path root = Path.of(dir);
            if (!Files.isDirectory(root)) {
                continue;
            }
            List<Path> classes;
            try (Stream<Path> walk = Files.walk(root)) {
                classes = walk.filter(p -> p.toString().endsWith(".class")).sorted().toList();
            }
            for (Path file : classes) {
                ClassModel model = ClassFile.of().parse(file);
                String owner = model.thisClass().asInternalName().replace('/', '.');
                for (MethodModel method : model.methods()) {
                    CodeModel code = method.code().orElse(null);
                    if (code == null) {
                        continue;
                    }
                    Instruction previous = null;
                    Map<Integer, String> locals = new HashMap<>();
                    for (CodeElement element : code) {
                        if (!(element instanceof Instruction instruction)) {
                            continue;
                        }
                        if (instruction instanceof InvokeInstruction invoke && invoke.name().equalsString("registerSystem")) {
                            String where = owner + "." + method.methodName().stringValue();
                            String type = previous instanceof LoadInstruction load ? locals.get(load.slot()) : argumentType(previous);
                            if (type == null) {
                                unknown++;
                                System.out.println("checkSystemRegistrations : type inconnu pour un registerSystem dans " + where);
                            } else {
                                calls.computeIfAbsent(type, k -> new ArrayList<>()).add(where);
                            }
                        }
                        if (instruction instanceof StoreInstruction store) {
                            String stored = argumentType(previous);
                            if (stored == null) {
                                locals.remove(store.slot());
                            } else {
                                locals.put(store.slot(), stored);
                            }
                        }
                        previous = instruction;
                    }
                }
            }
        }
        int duplicates = 0;
        for (Map.Entry<String, List<String>> entry : calls.entrySet()) {
            if (entry.getValue().size() > 1) {
                duplicates++;
                System.err.println("Système enregistré " + entry.getValue().size() + " fois (le serveur refuse le plugin) : "
                        + entry.getKey() + " <- " + String.join(", ", entry.getValue()));
            }
        }
        if (duplicates > 0) {
            System.exit(1);
        }
        System.out.println("checkSystemRegistrations : " + calls.size() + " systèmes, aucun doublon"
                + (unknown > 0 ? " (" + unknown + " appel(s) non reconnu(s))" : "") + ".");
    }

    /** La classe du système passé à registerSystem, d'après l'instruction qui produit l'argument. */
    private static String argumentType(Instruction previous) {
        if (!(previous instanceof InvokeInstruction invoke)) {
            return null;
        }
        if (invoke.name().equalsString("<init>")) {
            return invoke.owner().asInternalName().replace('/', '.');
        }
        MethodTypeDesc type = invoke.typeSymbol();
        String descriptor = type.returnType().descriptorString();
        if (!descriptor.startsWith("L")) {
            return null;
        }
        return descriptor.substring(1, descriptor.length() - 1).replace('/', '.');
    }
}
