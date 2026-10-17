pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

plugins {
    // Télécharge automatiquement un JDK 25 si aucun n'est installé (toolchain).
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        maven {
            name = "HytaleRelease"
            url = uri("https://maven.hytale.com/release")
        }
    }
}

rootProject.name = "hytale-modding"

include(":mods:nakasar-runes")
include(":mods:nakasar-spear")
include(":mods:nakasar-halloween")

