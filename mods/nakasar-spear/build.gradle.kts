// Pack d'assets pur (pas de code Java) : la lance à deux mains.
// Le résultat est un zip déposable tel quel dans le dossier mods/ du serveur.
plugins {
    base
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
