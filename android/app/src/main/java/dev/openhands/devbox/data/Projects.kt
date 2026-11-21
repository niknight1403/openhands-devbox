package dev.openhands.devbox.data

/**
 * Projekte aus `projects/` der Devbox. Ein Projekt bringt Zielrepository,
 * Auftrag und optional eine laufende Vorschau mit.
 */
data class ProjectChoice(
    val slug: String,
    val targetShort: String,
    val label: String,
    val description: String,
    val previewUrl: String = "",
)

object Projects {
    /**
     * Die Liste ist bewusst lokal versioniert: Nur Projekte, die in
     * config/targets.txt freigegeben sind, dürfen aus der App gestartet werden.
     */
    val alle: List<ProjectChoice> = listOf(
        ProjectChoice(
            slug = "vision",
            targetShort = "Vision",
            label = "Vision",
            description = "Vision-Analyse, Spezialisten und mobile App gezielt weiterentwickeln.",
        ),
        ProjectChoice(
            slug = "cybersarah-control-center",
            targetShort = "CyberSarah-Control-Center",
            label = "CyberSarah Control Center",
            description = "Analyse, Optimierung und Qualitätssicherung des Control Centers.",
        ),
    )

    fun findBySlug(slug: String): ProjectChoice? = alle.firstOrNull { it.slug == slug }
}
