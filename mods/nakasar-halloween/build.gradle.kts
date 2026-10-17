// Pack d'assets pur : le fragment d'Orbis « Halloween » (instance, génération, prefabs, PNJ).
// Le résultat est un zip déposable tel quel dans le dossier mods/ du serveur.
// Les prefabs et la génération du monde sont produits par les scripts de tools/ (voir README).
plugins {
    base
    `jvm-toolchains`
}

val modVersion = project.version.toString()
val modGroup = rootProject.property("mod_group").toString()
val modAuthor = rootProject.property("mod_author").toString()
val serverRange = rootProject.property("hytale_server_range").toString()
val hytaleVersion = rootProject.property("hytale_version").toString()

val packZip = tasks.register<Zip>("packZip") {
    group = "build"
    description = "Construit le pack d'assets du fragment Halloween (zip)."
    archiveBaseName.set("Nakasar-Halloween")
    destinationDirectory.set(layout.buildDirectory.dir("distributions"))
    from("pack") {
        filesMatching("manifest.json") {
            expand(
                "group" to modGroup,
                "version" to modVersion,
                "serverRange" to serverRange,
                "author" to modAuthor,
            )
        }
    }
}

tasks.named("assemble") {
    dependsOn(packZip)
}

// Décode les assets du pack avec les codecs du serveur (clés inconnues, valeurs invalides).
val hytaleServer: Configuration by configurations.creating
dependencies {
    hytaleServer("com.hypixel.hytale:Server:$hytaleVersion")
}

val javaToolchains = extensions.getByType<JavaToolchainService>()

val validateAssets = tasks.register<Exec>("validateAssets") {
    group = "verification"
    description = "Valide les assets du fragment Halloween avec les codecs du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    inputs.dir("pack/Server")
    inputs.file("tools/ValidateAssets.java")
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateAssets.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        args("-Dstdout.encoding=UTF-8", "-cp", hytaleServer.asPath, file("tools/ValidateAssets.java").absolutePath, file("pack/Server").absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

tasks.named("check") {
    dependsOn(validateAssets)
}
