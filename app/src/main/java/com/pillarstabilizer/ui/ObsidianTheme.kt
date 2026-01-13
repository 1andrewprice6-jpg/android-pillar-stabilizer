package com.pillarstabilizer.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object ObsidianColors {
    val background = Color(0xFF0A0A0A)
    val surface = Color(0xFF1A1A1A)
    val primary = Color(0xFF00D9FF) // Cyan
    val secondary = Color(0xFF8B00FF) // Purple
    val accent = Color(0xFFFF6B35) // Orange
    val success = Color(0xFF00FF88)
    val error = Color(0xFFFF4444)
    val warning = Color(0xFFFFAA00)
    val onSurface = Color(0xFFE0E0E0)
    val onBackground = Color(0xFFE0E0E0)
}

private val ObsidianColorScheme = darkColorScheme(
    primary = ObsidianColors.primary,
    secondary = ObsidianColors.secondary,
    tertiary = ObsidianColors.accent,
    background = ObsidianColors.background,
    surface = ObsidianColors.surface,
    error = ObsidianColors.error,
    onPrimary = Color.Black,
    onSecondary = Color.White,
    onTertiary = Color.Black,
    onBackground = ObsidianColors.onBackground,
    onSurface = ObsidianColors.onSurface,
    onError = Color.White
)

@Composable
fun ObsidianTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = ObsidianColorScheme,
        content = content
    )
}
