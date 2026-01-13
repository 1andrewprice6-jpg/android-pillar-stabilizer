# Shizuku
-keep class rikka.shizuku.** { *; }
-keep interface rikka.shizuku.** { *; }

# Keep Kotlin coroutines
-keep class kotlinx.coroutines.** { *; }
-keep interface kotlinx.coroutines.** { *; }

# Keep Jetpack Compose
-keep class androidx.compose.** { *; }
-keep interface androidx.compose.** { *; }

# Keep Android Jetpack
-keep class androidx.** { *; }
-keep interface androidx.** { *; }

# Keep app classes
-keep class com.pillarstabilizer.** { *; }
-keep interface com.pillarstabilizer.** { *; }

# Keep data classes
-keepclassmembers class * {
    *** component*();
}

# Don't obfuscate for debugging
-dontobfuscate
