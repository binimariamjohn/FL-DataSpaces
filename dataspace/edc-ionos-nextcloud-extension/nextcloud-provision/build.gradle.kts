plugins {
    id("java")
    id("maven-publish")
}

val edcGroup: String by project
val edcVersion: String by project

val extensionsGroup: String by project
val extensionsVersion: String by project
val gitHubPkgsName: String by project
val gitHubPkgsUrl: String by project
val gitHubUser: String? by project
val gitHubToken: String? by project

repositories {
    mavenCentral()
}

dependencies {

    implementation("${edcGroup}:transfer-spi:${edcVersion}")
    implementation("${edcGroup}:core-spi:${edcVersion}")
    implementation("${edcGroup}:http-spi:${edcVersion}")
    implementation("${edcGroup}:http:${edcVersion}")
    implementation("${edcGroup}:web-spi:${edcVersion}")
    implementation("${edcGroup}:control-plane-spi:${edcVersion}")


    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("dev.failsafe:failsafe:3.2.4")
    implementation(project(":edc-ionos-nextcloud-extension:nextcloud-core"))
    implementation("com.google.code.gson:gson:2.8.6")
    implementation("io.swagger.core.v3:swagger-annotations:2.2.20")
    implementation("com.apicatalog:titanium-json-ld:1.3.3")

    testImplementation(platform("org.junit:junit-bom:5.9.1"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testImplementation("${edcGroup}:json-ld:${edcVersion}")
}

tasks.test {
    useJUnitPlatform()
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            groupId = extensionsGroup
            artifactId = "provision-ionos-nextcloud"
            version = extensionsVersion

            from(components["java"])

            pom {
                name.set("provision-ionos-nextcloud")
                description.set("Extension to manage an Nextcloud")
            }
        }
    }
    repositories {
        maven {
            name = "GitHubPackages"
            url = uri("https://maven.pkg.github.com/${project.properties["github_owner"]}/${project.properties["github_repo"]}")

            credentials {
                username = gitHubUser
                password = gitHubToken
            }
        }
    }
}