plugins {
    kotlin("jvm") version "2.0.0"
    alias(libs.plugins.shadow) // id("com.github.johnrengelman.shadow") version "8.1.1"
}

group = "com.sap.vt.smartkicker"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}