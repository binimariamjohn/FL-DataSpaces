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

    implementation("${edcGroup}:data-plane-spi:${edcVersion}")
    implementation("${edcGroup}:util-lib:${edcVersion}")
    implementation("${edcGroup}:transfer-spi:${edcVersion}")
    implementation("${edcGroup}:data-plane-util:${edcVersion}")
    implementation("${edcGroup}:data-plane-core:${edcVersion}")
    implementation("${edcGroup}:http-spi:${edcVersion}")
    implementation("${edcGroup}:control-api-configuration:${edcVersion}")

    implementation("io.swagger.core.v3:swagger-annotations:2.2.20")
    implementation("com.google.code.gson:gson:2.8.6")
    implementation("org.springframework:spring-web:4.3.11.RELEASE")

    implementation(project(":edc-ionos-nextcloud-extension:nextcloud-core"))

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
            artifactId = "dataplane-ionos-nextcloud"
            version = extensionsVersion

            from(components["java"])

            pom {
                name.set("dataplane-ionos-nextcloud")
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