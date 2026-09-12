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
    implementation("${edcGroup}:boot:${edcVersion}")
    implementation("${edcGroup}:connector-core:${edcVersion}")
    implementation("${edcGroup}:core-spi:${edcVersion}")
    implementation("${edcGroup}:http:${edcVersion}")
    implementation("${edcGroup}:control-plane-core:${edcVersion}")

    implementation("com.squareup.okhttp3:okhttp:4.9.1")
    implementation("org.jsoup:jsoup:1.14.3")

    testImplementation(platform("org.junit:junit-bom:5.9.1"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    
}

tasks.test {
    useJUnitPlatform()
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            groupId = extensionsGroup
            artifactId = "core-ionos-nextcloud"
            version = extensionsVersion

            from(components["java"])

            pom {
                name.set("core-ionos-nextcloud")
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