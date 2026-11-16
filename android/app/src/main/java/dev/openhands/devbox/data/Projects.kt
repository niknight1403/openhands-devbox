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
    val targetOwner: String,
    val targetShort: String,
    val label: String,
) {
    val targetRepoFullName: String get() = "$targetOwner/$targetShort"
}

object Projects {
    val alle: List<ProjectChoice> = listOf(
        ProjectChoice(
            slug = "cybersarah-control-center",
            targetOwner = "niknight1403",
            targetShort = "CyberSarah-Control-Center",
            label = "CyberSarah Control Center",
        ),
    )

    fun findBySlug(slug: String): ProjectChoice? = alle.firstOrNull { it.slug == slug }

    /**
     * A selected project's repository owner is explicit project configuration.
     * The control-repository owner is not necessarily the target-repository owner.
     */
    fun targetRepoFor(project: ProjectChoice?, fallbackTargetRepo: String): String =
        project?.targetRepoFullName ?: fallbackTargetRepo
}
