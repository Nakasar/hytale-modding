// Le mod « Fractales des Brumes » : plugin Java + pack d'assets embarqué dans le jar (docs/fractales/gdd.md).
// Les zones d'annonce (particules) sont produites par tools/generate_warnings.py.
plugins {
    java
}

description = "Fractales des Brumes : les fractales de Guild Wars 2 pour des groupes de 1 à 5 joueurs"

val hytaleVersion: String = rootProject.property("hytale_version").toString()
val hytaleServerRange: String = rootProject.property("hytale_server_range").toString()
val modGroup: String = rootProject.property("mod_group").toString()
val modAuthor: String = rootProject.property("mod_author").toString()

tasks.named<Jar>("jar") {
    archiveBaseName.set("Nakasar-Fractals")
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

// Décode tous les assets du pack avec les codecs du serveur (instances, portails, objets, effets, interactions,
// particules...) et vérifie les ids de blocs des prefabs.
val validateAssets = tasks.register<Exec>("validateAssets") {
    group = "verification"
    description = "Valide les assets du mod avec les codecs du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    val blocks = file("tools/vanilla-block-ids-0.7.2.txt")
    val gradients = file("tools/vanilla-gradient-sets-0.7.2.txt")
    val refs = file("tools/vanilla-refs-0.7.2.txt")
    val stereo = file("tools/vanilla-stereo-sounds-0.7.2.txt")
    inputs.dir(serverAssets)
    inputs.file("tools/ValidateAssets.java")
    inputs.files(blocks, gradients, refs, stereo)
    inputs.files(hytaleServer)
    // Les classes du plugin : types d'assets écrits en Java (aucun pour l'instant).
    val pluginClasses = sourceSets.main.get().output.classesDirs
    inputs.files(pluginClasses)
    dependsOn(tasks.named("classes"))
    val marker = layout.buildDirectory.file("validateAssets.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        // -Dblocks : ids de blocs vanilla, pour repérer dans les prefabs les blocs inconnus (damier rose en jeu).
        // -Drefs : listes de butin et rôles vanilla cités par le mod (un id inconnu fait échouer le mod en jeu).
        // -Dstereo : sons vanilla stéréo, refusés en WorldSoundEventId (l'interaction entière est rejetée en jeu).
        args("-Dstdout.encoding=UTF-8", "--sun-misc-unsafe-memory-access=allow", "-Dblocks=" + blocks.absolutePath, "-Dgradients=" + gradients.absolutePath,
            "-Drefs=" + refs.absolutePath, "-Dstereo=" + stereo.absolutePath,
            "-cp", (hytaleServer + pluginClasses).asPath, file("tools/ValidateAssets.java").absolutePath, file(serverAssets).absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

tasks.named("check") {
    dependsOn(validateRoles, validateAssets)
}
