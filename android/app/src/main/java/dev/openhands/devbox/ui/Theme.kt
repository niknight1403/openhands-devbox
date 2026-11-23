package dev.openhands.devbox.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Nebula Command — Design 1
private val NebulaCyan = Color(0xFF55E6FF)
private val NebulaViolet = Color(0xFF9B8CFF)
private val NebulaBackground = Color(0xFF080D1A)
private val NebulaSurface = Color(0xFF101A2D)
private val NebulaSurfaceRaised = Color(0xFF172541)
private val NebulaText = Color(0xFFEAF4FF)
private val NebulaMuted = Color(0xFF9BAEC8)
private val NebulaGreen = Color(0xFF55D6A4)
private val NebulaRed = Color(0xFFFF7185)

private val NebulaScheme = darkColorScheme(
    primary = NebulaCyan,
    onPrimary = Color(0xFF03131B),
    secondary = NebulaViolet,
    onSecondary = Color(0xFF100D27),
    tertiary = NebulaGreen,
    background = NebulaBackground,
    onBackground = NebulaText,
    surface = NebulaSurface,
    onSurface = NebulaText,
    surfaceVariant = NebulaSurfaceRaised,
    onSurfaceVariant = NebulaMuted,
    error = NebulaRed,
    onError = Color(0xFF2A0710),
)

@Composable
fun OpenHandsTheme(useDark: Boolean = true, content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = NebulaScheme, content = content)
}
