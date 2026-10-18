plugins {
    java
}

description = "Runes d'abilities Nakasar : Baiser du Vampire, Domination, Téléportation, Chaînes spectrales"

val hytaleServerRange: String = rootProject.property("hytale_server_range").toString()
val modGroup: String = rootProject.property("mod_group").toString()
val modAuthor: String = rootProject.property("mod_author").toString()

tasks.named<Jar>("jar") {
    archiveBaseName.set("Nakasar-Runes")
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

// Décode les assets avec les codecs du serveur (clés inconnues, valeurs invalides, interactions en ligne
// comprises), grâce à l'outil du fragment Halloween. Les types d'interactions Java du plugin sont notés
// « non vérifiables hors jeu ».
val hytaleServer: Configuration by configurations.creating
dependencies {
    hytaleServer("com.hypixel.hytale:Server:${rootProject.property("hytale_version")}")
}

val validateAssets = tasks.register<Exec>("validateAssets") {
    group = "verification"
    description = "Valide les assets des runes avec les codecs du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    val tool = project(":mods:nakasar-halloween").file("tools/ValidateAssets.java")
    inputs.dir("src/main/resources/Server")
    inputs.file(tool)
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateAssets.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        args("-Dstdout.encoding=UTF-8", "-cp", hytaleServer.asPath, tool.absolutePath, file("src/main/resources/Server").absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

tasks.named("check") {
    dependsOn(validateAssets)
}
