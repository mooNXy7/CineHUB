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
        versionCode = 104
        versionName = "1.0.4"
        buildConfigField("String", "CINEHUB_REMOTE_URL", "\"\"")
    }

    signingConfigs {
        getByName("debug") {
            // CI usa a chave debug do ambiente para garantir um APK assinado.
            // Uma chave de release privada estável será configurada antes de updates de produção.
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
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
