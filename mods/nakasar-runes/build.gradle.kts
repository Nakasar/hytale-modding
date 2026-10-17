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
