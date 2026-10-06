import java.util.Properties

plugins {
    id("com.android.application")
}

android {
    namespace = "com.cinehub.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.cinehub.mobile"
        minSdk = 23
        targetSdk = 35
        versionCode = 107
        versionName = "1.0.7"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            val ks = rootProject.file("keystore.properties")
            if (ks.exists()) {
                val p = Properties().apply { ks.inputStream().use { load(it) } }
                signingConfig = signingConfigs.create("cinehubRelease") {
                    storeFile = rootProject.file(p.getProperty("storeFile"))
                    storePassword = p.getProperty("storePassword")
                    keyAlias = p.getProperty("keyAlias")
                    keyPassword = p.getProperty("keyPassword")
                }
            } else {
                signingConfig = signingConfigs.getByName("debug")
            }
        }
    }

    buildFeatures { buildConfig = true }
}

configurations.all {
    exclude(group = "org.jetbrains.kotlin", module = "kotlin-stdlib-jdk7")
    exclude(group = "org.jetbrains.kotlin", module = "kotlin-stdlib-jdk8")
}

dependencies {
    implementation("androidx.core:core:1.15.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.webkit:webkit:1.12.1")
    implementation("org.jetbrains.kotlin:kotlin-stdlib:1.8.22")
}
