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
        versionCode = 40
        versionName = "1.4.0"
    }
    buildFeatures { buildConfig = true }
    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "CINEHUB_REMOTE_URL", """")
        }
        debug {
            buildConfigField("String", "CINEHUB_REMOTE_URL", """")
        }
    }
    packaging {
        resources.excludes += setOf("META-INF/DEPENDENCIES","META-INF/LICENSE","META-INF/LICENSE.txt","META-INF/NOTICE","META-INF/NOTICE.txt")
    }
}
dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.webkit:webkit:1.12.1")
}
