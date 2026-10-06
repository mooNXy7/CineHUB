plugins {
    id("com.android.application")
}

android {
    namespace = "com.cinehub.tv"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.cinehub.tv"
        minSdk = 23
        targetSdk = 35
        versionCode = 106
        versionName = "1.0.6"
        buildConfigField("String", "CINEHUB_REMOTE_URL", "\"\"")
    }

    signingConfigs {
        getByName("debug") {
            // Desenvolvimento/local.
        }
        create("release") {
            val ks = System.getenv("CINEHUB_TV_KEYSTORE_PATH")
            val kp = System.getenv("CINEHUB_TV_KEYSTORE_PASSWORD")
            val ka = System.getenv("CINEHUB_TV_KEY_ALIAS")
            val ap = System.getenv("CINEHUB_TV_KEY_PASSWORD")
            if (!ks.isNullOrBlank() && !kp.isNullOrBlank() && !ka.isNullOrBlank() && !ap.isNullOrBlank()) {
                storeFile = file(ks)
                storePassword = kp
                keyAlias = ka
                keyPassword = ap
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            val stableKey = System.getenv("CINEHUB_TV_KEYSTORE_PATH")
            signingConfig = if (!stableKey.isNullOrBlank()) signingConfigs.getByName("release") else signingConfigs.getByName("debug")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    buildFeatures { buildConfig = true }
}

configurations.all {
    resolutionStrategy.eachDependency {
        if (requested.group == "org.jetbrains.kotlin") useVersion("1.8.22")
    }
}

dependencies {
    implementation("androidx.core:core:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.webkit:webkit:1.12.1")
}
