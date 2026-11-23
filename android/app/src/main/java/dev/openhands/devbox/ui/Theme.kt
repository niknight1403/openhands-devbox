package dev.openhands.devbox.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AuroraCyan = Color(0xFF66E3F2)
private val AuroraBlue = Color(0xFF6C8CFF)
private val AuroraViolet = Color(0xFFB69CFF)
private val DeepNavy = Color(0xFF080F1D)
private val NavySurface = Color(0xFF111C30)
private val NavyElevated = Color(0xFF1A2942)

private val DarkScheme = darkColorScheme(
    primary = AuroraCyan, onPrimary = Color(0xFF06202A),
    secondary = AuroraViolet, onSecondary = Color(0xFF201438),
    tertiary = AuroraBlue, background = DeepNavy, onBackground = Color(0xFFEAF3FF),
    surface = NavySurface, onSurface = Color(0xFFEAF3FF),
    surfaceVariant = NavyElevated, onSurfaceVariant = Color(0xFFB6C6DD),
    outline = Color(0xFF40536F), error = Color(0xFFFF7A91),
)
private val LightScheme = lightColorScheme(
    primary = Color(0xFF006D7D), onPrimary = Color.White,
    secondary = Color(0xFF6650A4), onSecondary = Color.White,
    tertiary = Color(0xFF365CC8), background = Color(0xFFF3F7FC),
    onBackground = Color(0xFF101C2C), surface = Color.White,
    onSurface = Color(0xFF101C2C), surfaceVariant = Color(0xFFE5EDF6),
    onSurfaceVariant = Color(0xFF465A72), outline = Color(0xFF71849B),
    error = Color(0xFFBA1A3A),
)

@Composable
fun OpenHandsTheme(useDark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (useDark) DarkScheme else LightScheme, content = content)
}
