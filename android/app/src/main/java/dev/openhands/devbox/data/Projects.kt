package dev.openhands.devbox.data

/**
 * Projekte aus `projects/` der Devbox. Ein Projekt bringt Zielrepository und
 * Auftrag mit; der Workflow prüft das Ziel gegen seine Whitelist.
 *
 * Neue Projekte hier eintragen, solange die App keine Liste aus dem Repository
 * lädt. Der Kurzname muss dem Verzeichnis in `projects/` entsprechen.
 */
data class ProjectChoice(
    val slug: String,
    val targetShort: String,
    val label: String,
)

object Projects {
    val alle: List<ProjectChoice> = listOf(
        ProjectChoice(
            slug = "cybersarah-control-center",
            targetShort = "CyberSarah-Control-Center",
            label = "CyberSarah Control Center",
        ),
    )

    fun findBySlug(slug: String): ProjectChoice? = alle.firstOrNull { it.slug == slug }
}
