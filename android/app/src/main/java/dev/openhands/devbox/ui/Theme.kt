package dev.openhands.devbox.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Accent = Color(0xFFE2582B)
private val AccentDark = Color(0xFFFF8A5B)

private val DarkScheme = darkColorScheme(
    primary = AccentDark,
    onPrimary = Color(0xFF2A1206),
    secondary = Color(0xFF8AB4F8),
    background = Color(0xFF12100F),
    surface = Color(0xFF1C1917),
    surfaceVariant = Color(0xFF2A2624),
    error = Color(0xFFFF6B6B),
)

private val LightScheme = lightColorScheme(
    primary = Accent,
    secondary = Color(0xFF2A5CB8),
    background = Color(0xFFFDF9F6),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFF1E9E3),
    error = Color(0xFFB3261E),
)

@Composable
fun OpenHandsTheme(useDark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (useDark) DarkScheme else LightScheme, content = content)
}
