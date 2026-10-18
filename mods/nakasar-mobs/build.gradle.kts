plugins {
    java
}

description = "Mobs Nakasar : Comte Vampire (boss), rejetons de vampire, fantômes"

val hytaleVersion: String = rootProject.property("hytale_version").toString()
val hytaleServerRange: String = rootProject.property("hytale_server_range").toString()
val modGroup: String = rootProject.property("mod_group").toString()
val modAuthor: String = rootProject.property("mod_author").toString()

tasks.named<Jar>("jar") {
    archiveBaseName.set("Nakasar-Mobs")
}

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

// Valide les rôles de PNJ avec le BuilderManager du serveur (briques et clés inconnues, valeurs invalides).
val hytaleServer: Configuration by configurations.creating
dependencies {
    hytaleServer("com.hypixel.hytale:Server:$hytaleVersion")
}

val validateRoles = tasks.register<Exec>("validateRoles") {
    group = "verification"
    description = "Valide les rôles de PNJ du mod avec le chargeur de rôles du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    inputs.dir("src/main/resources/Server")
    inputs.file("tools/ValidateRoles.java")
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateRoles.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        args("-Dstdout.encoding=UTF-8", "-cp", hytaleServer.asPath, file("tools/ValidateRoles.java").absolutePath,
            file("src/main/resources/Server").absolutePath,
            project(":mods:nakasar-runes").file("src/main/resources/Server").absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

// Décode les autres assets (modèles, effets, butins, groupes, marqueurs, apparitions) avec les codecs du serveur,
// grâce à l'outil du fragment Halloween.
val validateAssets = tasks.register<Exec>("validateAssets") {
    group = "verification"
    description = "Valide les assets du mod Mobs avec les codecs du serveur Hytale."
    val launcher = javaToolchains.launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
    val tool = project(":mods:nakasar-halloween").file("tools/ValidateAssets.java")
    inputs.dir("src/main/resources/Server")
    inputs.file(tool)
    inputs.files(hytaleServer)
    val marker = layout.buildDirectory.file("validateAssets.ok")
    outputs.file(marker)
    doFirst {
        executable = launcher.get().executablePath.asFile.absolutePath
        args("-Dstdout.encoding=UTF-8", "-cp", hytaleServer.asPath, tool.absolutePath,
            file("src/main/resources/Server").absolutePath)
    }
    doLast {
        marker.get().asFile.writeText("ok")
    }
}

tasks.named("check") {
    dependsOn(validateRoles, validateAssets)
}
