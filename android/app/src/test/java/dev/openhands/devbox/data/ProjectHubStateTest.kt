package dev.openhands.devbox.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProjectHubStateTest {
    private val knownSlug = "cybersarah-control-center"

    @Test fun blankModelSelectsAutomaticRoute() {
        val state = resolveProjectHubState(project = "", model = "  ")
        assertEquals(RouteMode.AUTOMATIC_ROUTE, state.routeMode)
        assertTrue(state.usesAutomaticRoute)
        assertEquals("Automatische Route", state.routeChipLabel)
        assertEquals(
            "Automatisch aktiv: Vor jedem Lauf wird eine erreichbare Gratis-Route gesucht und geprüft.",
            state.hunterDescription,
        )
    }

    @Test fun nonBlankModelSelectsManualModel() {
        val state = resolveProjectHubState(project = "", model = "gpt-oss-120b")
        assertEquals(RouteMode.MANUAL_MODEL, state.routeMode)
        assertFalse(state.usesAutomaticRoute)
        assertEquals("Modell fest vorgegeben", state.routeChipLabel)
        assertEquals(
            "Manuelles Modell aktiv: gpt-oss-120b. Leere das Modellfeld, um den Hunter zu verwenden.",
            state.hunterDescription,
        )
    }

    @Test fun knownSlugResolvesSelectedProject() {
        val state = resolveProjectHubState(project = knownSlug, model = "")
        assertEquals(knownSlug, state.selectedProject?.slug)
        assertEquals("CyberSarah Control Center live öffnen", state.liveOpenLabel)
    }

    @Test fun unknownSlugLeavesProjectUnselected() {
        val state = resolveProjectHubState(project = "nicht-freigegeben", model = "")
        assertNull(state.selectedProject)
        assertNull(state.liveOpenLabel)
    }

    @Test fun nullProjectLeavesProjectUnselected() {
        val state = resolveProjectHubState(project = null, model = "")
        assertNull(state.selectedProject)
        assertNull(state.liveOpenLabel)
    }

    @Test fun findBySlugOnlyMatchesReleasedProjects() {
        val project = Projects.findBySlug(knownSlug)
        assertEquals(knownSlug, project?.slug)
        assertEquals("CyberSarah-Control-Center", project?.targetShort)
        assertNull(Projects.findBySlug("andere-projekt"))
        assertTrue(Projects.alle.any { it.slug == "vision" })
        assertTrue(Projects.alle.any { it.slug == knownSlug })
    }
}
