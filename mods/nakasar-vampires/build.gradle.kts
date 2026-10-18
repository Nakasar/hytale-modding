// Le mod « Vampires » : plugin Java + pack d'assets embarqué dans le jar.
// Il réunit l'ancien quatuor Runes / Spear / Mobs / Halloween : runes et autel, lance, mobs du domaine du Comte
// et fragment d'Orbis. Les ids d'assets gardent leur préfixe Nakasar_ (mondes et prefabs existants intacts).
// Les prefabs, la génération du monde et les modèles générés sont produits par les scripts de tools/ (voir README).
plugins {
    java
}

description = "Vampires : le domaine du Comte vampire (fragment, mobs, runes, autel, lance)"

val hytaleVersion: String = rootProject.property("hytale_version").toString()
val hytaleServerRange: String = rootProject.property("hytale_server_range").toString()
val modGroup: String = rootProject.property("mod_group").toString()
val modAuthor: String = rootProject.property("mod_author").toString()

tasks.named<Jar>("jar") {
    archiveBaseName.set("Nakasar-Vampires")
}

// Le manifest.json est versionné dans src/main/resources ; on y injecte la version et la plage serveur.
tasks.named<ProcessResources>("processResources") {
    filesMatching("manifest.json") {
        expand(
            "version" to project.version.toString(),
            "serverRange" to hytaleServerRange,
            "group" to modGroup,
            "author" to modAuthor,
        )
    }
}

val hytaleServer: Configuration by configurations.creating
dependencies {
    hytaleServer("com.hypixel.hytale:Server:$hytaleVersion")
}

val serverAssets = "src/main/resources/Server"

// Valide les rôles de PNJ avec le BuilderManager du serveur (briques et clés inconnues, valeurs invalides).
val validateRoles = tasks.register<Exec>("validateRoles") {
    group = "verification"
    description = "Valide les rôles de PNJ du mod avec le chargeur de rôles du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    inputs.dir(serverAssets)
    inputs.file("tools/ValidateRoles.java")
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateRoles.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        args("-Dstdout.encoding=UTF-8", "--sun-misc-unsafe-memory-access=allow", "-cp", hytaleServer.asPath, file("tools/ValidateRoles.java").absolutePath,
            file(serverAssets).absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

// Décode tous les assets du pack (biome, structure de monde, instance, portail, objets, modèles, effets, butins,
// interactions, apparitions...) avec les codecs du serveur, et vérifie les ids de blocs des prefabs.
val validateAssets = tasks.register<Exec>("validateAssets") {
    group = "verification"
    description = "Valide les assets du mod avec les codecs du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    val blocks = file("tools/vanilla-block-ids-0.7.2.txt")
    val gradients = file("tools/vanilla-gradient-sets-0.7.2.txt")
    val refs = file("tools/vanilla-refs-0.7.2.txt")
    inputs.dir(serverAssets)
    inputs.file("tools/ValidateAssets.java")
    inputs.files(blocks, gradients, refs)
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateAssets.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        // -Dblocks : ids de blocs vanilla, pour repérer dans les prefabs les blocs inconnus (damier rose en jeu).
        // -Drefs : listes de butin et rôles vanilla cités par le mod (un id inconnu fait échouer le mod en jeu).
        args("-Dstdout.encoding=UTF-8", "--sun-misc-unsafe-memory-access=allow", "-Dblocks=" + blocks.absolutePath, "-Dgradients=" + gradients.absolutePath,
            "-Drefs=" + refs.absolutePath,
            "-cp", hytaleServer.asPath, file("tools/ValidateAssets.java").absolutePath, file(serverAssets).absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

tasks.named("check") {
    dependsOn(validateRoles, validateAssets)
}
