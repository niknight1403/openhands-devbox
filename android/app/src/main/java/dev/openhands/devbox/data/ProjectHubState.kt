package dev.openhands.devbox.data

/**
 * Anzeigezustand der Projektzentrale: Projekt-Auswahl und
 * Free-Route-Hunter-Modellmode. Bewusst ohne Android-Klassen, damit die
 * Logik in JUnit-Tests ohne Robolectric geprüft werden kann.
 */
enum class RouteMode { AUTOMATIC_ROUTE, MANUAL_MODEL }

data class ProjectHubState(
    val selectedProject: ProjectChoice?,
    val routeMode: RouteMode,
    val hunterDescription: String,
    val routeChipLabel: String,
    val liveOpenLabel: String?,
) {
    val usesAutomaticRoute: Boolean
        get() = routeMode == RouteMode.AUTOMATIC_ROUTE
}

fun resolveProjectHubState(project: String?, model: String): ProjectHubState {
    val selected = if (project == null) null else Projects.findBySlug(project)
    val automaticRoute = model.isBlank()
    return ProjectHubState(
        selectedProject = selected,
        routeMode = if (automaticRoute) RouteMode.AUTOMATIC_ROUTE else RouteMode.MANUAL_MODEL,
        hunterDescription = if (automaticRoute) {
            "Automatisch aktiv: Vor jedem Lauf wird eine erreichbare Gratis-Route gesucht und geprüft."
        } else {
            "Manuelles Modell aktiv: $model. Leere das Modellfeld, um den Hunter zu verwenden."
        },
        routeChipLabel = if (automaticRoute) "Automatische Route" else "Modell fest vorgegeben",
        liveOpenLabel = selected?.let { "${it.label} live öffnen" },
    )
}