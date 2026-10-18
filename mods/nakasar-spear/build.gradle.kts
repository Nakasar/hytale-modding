// Pack d'assets pur (pas de code Java) : la lance à deux mains.
// Le résultat est un zip déposable tel quel dans le dossier mods/ du serveur.
plugins {
    base
    `jvm-toolchains`
}

val modVersion = project.version.toString()
val modGroup = rootProject.property("mod_group").toString()
val modAuthor = rootProject.property("mod_author").toString()
val serverRange = rootProject.property("hytale_server_range").toString()

val packZip = tasks.register<Zip>("packZip") {
    group = "build"
    description = "Construit le pack d'assets de la lance (zip)."
    archiveBaseName.set("Nakasar-Spear")
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

// Décode les assets avec les codecs du serveur (clés inconnues, valeurs invalides, interactions en ligne
// comprises), grâce à l'outil du fragment Halloween.
val hytaleServer: Configuration by configurations.creating
dependencies {
    hytaleServer("com.hypixel.hytale:Server:${rootProject.property("hytale_version")}")
}

val javaToolchains = extensions.getByType<JavaToolchainService>()

val validateAssets = tasks.register<Exec>("validateAssets") {
    group = "verification"
    description = "Valide les assets de la lance avec les codecs du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    val tool = project(":mods:nakasar-halloween").file("tools/ValidateAssets.java")
    inputs.dir("pack/Server")
    inputs.file(tool)
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateAssets.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        args("-Dstdout.encoding=UTF-8", "-cp", hytaleServer.asPath, tool.absolutePath, file("pack/Server").absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

tasks.named("check") {
    dependsOn(validateAssets)
}
