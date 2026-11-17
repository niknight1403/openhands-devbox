package dev.openhands.devbox.data

/**
 * Anzeigezustände der Live-App-Vorschau. Die Berechnung ist bewusst frei
 * von Android-Klassen, damit sie in JUnit-Tests ohne Robolectric geprüft
 * werden kann.
 */
enum class LivePreviewStatus { NOT_CONFIGURED, INVALID_URL, READY }

data class LivePreviewState(
    val status: LivePreviewStatus,
    val displayUrl: String,
) {
    val isReady: Boolean
        get() = status == LivePreviewStatus.READY
}

/**
 * Gleiche Prüfungsregeln wie vorher im Composable: nach dem Trimmen muss
 * der Scheme http- oder https- und der Host nicht leer sein.
 */
fun resolveLivePreviewState(rawUrl: String): LivePreviewState {
    val url = rawUrl.trim()
    val status = when {
        url.isEmpty() -> LivePreviewStatus.NOT_CONFIGURED
        hasHttpSchemeAndHost(url) -> LivePreviewStatus.READY
        else -> LivePreviewStatus.INVALID_URL
    }
    return LivePreviewState(status = status, displayUrl = url)
}

private fun hasHttpSchemeAndHost(url: String): Boolean {
    val separator = url.indexOf("://")
    if (separator <= 0) return false
    val scheme = url.substring(0, separator).lowercase()
    if (scheme != "http" && scheme != "https") return false
    val hostPart = url.substring(separator + 3)
    val hostEnd = hostPart.indexOfFirst { it == '/' || it == '?' || it == '#' || it.isWhitespace() }
    val host = if (hostEnd < 0) hostPart else hostPart.substring(0, hostEnd)
    return host.isNotBlank()
}