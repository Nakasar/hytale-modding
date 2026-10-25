import groovy.json.JsonSlurper

// Configuration commune à tous les mods du dépôt.
// Chaque mod vit dans mods/<nom> et choisit son type :
//   - plugin Java (jar) avec pack d'assets embarqué : voir mods/nakasar-vampires
//   - pack d'assets pur (zip) : tâche Zip sur un dossier pack/ (aucun mod de ce type pour l'instant)

val hytaleVersion: String = project.property("hytale_version").toString()
val modVersion: String = project.property("mod_version").toString()

allprojects {
    group = "dev.nakasar.hytale"
    version = modVersion
}

subprojects {
    plugins.withId("java") {
        extensions.configure<JavaPluginExtension> {
            toolchain.languageVersion.set(JavaLanguageVersion.of(25))
        }
        dependencies {
            // Le serveur n'est jamais embarqué dans le jar : il est fourni à l'exécution.
            add("compileOnly", "com.hypixel.hytale:Server:$hytaleVersion")
        }
        tasks.withType<JavaCompile>().configureEach {
            options.encoding = "UTF-8"
            options.release.set(25)
            options.compilerArgs.add("-Xlint:deprecation")
        }
        tasks.withType<Javadoc>().configureEach {
            (options as StandardJavadocDocletOptions).addStringOption("Xdoclint:none", "-quiet")
        }

        // Le serveur refuse deux systèmes de la même classe (« is already registered! ») et le plugin entier échoue :
        // tools/CheckSystemRegistrations.java le repère dans les classes compilées.
        val launcher = extensions.getByType<JavaToolchainService>().launcherFor { languageVersion.set(JavaLanguageVersion.of(25)) }
        val tool = rootProject.file("tools/CheckSystemRegistrations.java")
        val classes = extensions.getByType<SourceSetContainer>().named("main").get().output.classesDirs
        val checkSystemRegistrations = tasks.register<Exec>("checkSystemRegistrations") {
            group = "verification"
            description = "Vérifie qu'aucune classe de système n'est enregistrée deux fois (registerSystem)."
            inputs.file(tool)
            inputs.files(classes)
            dependsOn(tasks.named("classes"))
            val marker = layout.buildDirectory.file("checkSystemRegistrations.ok")
            outputs.file(marker)
            doFirst {
                executable = launcher.get().executablePath.asFile.absolutePath
                args(listOf("-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", tool.absolutePath) + classes.files.map { it.absolutePath })
            }
            doLast {
                marker.get().asFile.writeText("ok")
            }
        }
        tasks.named("check") {
            dependsOn(checkSystemRegistrations)
        }
    }
}

// Vérifie que chaque fichier JSON d'assets est syntaxiquement valide.
// Les assets Hytale sont lus par un parseur strict : une virgule en trop fait échouer le chargement.
val validateJson = tasks.register("validateJson") {
    group = "verification"
    description = "Vérifie la syntaxe de tous les fichiers JSON des mods (assets et manifests)."
    val jsonFiles = fileTree("mods") {
        include("**/*.json")
        include("**/*.blockymodel") // JSON aussi (modèles client)
        exclude("**/build/**", "**/.gradle/**")
    }
    inputs.files(jsonFiles)
    doLast {
        val slurper = JsonSlurper()
        var errors = 0
        jsonFiles.forEach { file ->
            try {
                slurper.parse(file)
            } catch (e: Exception) {
                errors++
                logger.error("JSON invalide : ${file.relativeTo(rootDir)} -> ${e.message}")
            }
        }
        if (errors > 0) throw GradleException("$errors fichier(s) JSON invalide(s).")
        logger.lifecycle("validateJson : ${jsonFiles.files.size} fichiers JSON valides.")
    }
}

// Chaque `./gradlew check` (et donc `build`) d'un mod valide aussi les JSON.
subprojects {
    tasks.matching { it.name == "check" }.configureEach {
        dependsOn(validateJson)
    }
}

// Lit hytale.modsDir depuis -P, gradle.properties ou gradle-local.properties (non versionné).
fun resolveModsDir(): String? {
    val fromProject = (project.findProperty("hytale.modsDir") as String?)?.takeIf { it.isNotBlank() }
    if (fromProject != null) return fromProject
    val local = rootProject.file("gradle-local.properties")
    if (!local.exists()) return null
    val props = java.util.Properties().apply { local.inputStream().use { load(it) } }
    return props.getProperty("hytale.modsDir")?.takeIf { it.isNotBlank() }
}

// Copie les mods construits (jar et zip) dans le dossier mods/ d'un serveur local.
tasks.register<Copy>("deployToServer") {
    group = "hytale"
    description = "Copie les jars et zips construits dans le dossier mods/ du serveur (propriété hytale.modsDir)."
    dependsOn(subprojects.map { it.tasks.matching { t -> t.name == "assemble" } })
    val modsDir = resolveModsDir()
    onlyIf {
        if (modsDir == null) logger.warn("deployToServer : définissez hytale.modsDir (gradle-local.properties ou -Phytale.modsDir=...).")
        modsDir != null
    }
    from(subprojects.map { sp -> sp.layout.buildDirectory.dir("libs") })
    from(subprojects.map { sp -> sp.layout.buildDirectory.dir("distributions") })
    include("*.jar", "*.zip")
    into(modsDir ?: layout.buildDirectory.dir("deploy-noop"))
}

// Rassemble les jars et zips de tous les mods à plat dans build/mods-pack/ :
// le contenu de ce dossier se dépose tel quel dans le dossier mods/ d'une save ou d'un serveur.
val stageModsPack = tasks.register<Sync>("stageModsPack") {
    group = "hytale"
    description = "Copie à plat les jars et zips construits de tous les mods dans build/mods-pack/."
    dependsOn(subprojects.map { it.tasks.matching { t -> t.name == "assemble" } })
    from(subprojects.map { sp -> sp.layout.buildDirectory.dir("libs") })
    from(subprojects.map { sp -> sp.layout.buildDirectory.dir("distributions") })
    include("*.jar", "*.zip")
    into(layout.buildDirectory.dir("mods-pack"))
}

// Le « pack » : un seul zip avec les fichiers des mods à sa racine, à extraire directement dans mods/.
tasks.register<Zip>("packMods") {
    group = "hytale"
    description = "Construit build/distributions/Nakasar-Mods-Pack-<version>.zip (tous les mods, à extraire dans mods/)."
    archiveBaseName.set("Nakasar-Mods-Pack")
    archiveVersion.set(modVersion)
    destinationDirectory.set(layout.buildDirectory.dir("distributions"))
    from(stageModsPack)
}
