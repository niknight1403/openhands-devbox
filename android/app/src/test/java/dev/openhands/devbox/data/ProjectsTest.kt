package dev.openhands.devbox.data

import org.junit.Assert.assertEquals
import org.junit.Test

class ProjectsTest {
    @Test fun selectedProjectUsesConfiguredOwner() {
        for (slug in listOf("vision", "cybersarah-control-center")) {
            val project = Projects.findBySlug(slug)
            assertEquals("niknight1403/${project?.targetShort}", Projects.targetRepoFor(project, "other/control"))
        }
    }

    @Test fun unselectedProjectKeepsConfiguredFallback() {
        assertEquals("other/custom", Projects.targetRepoFor(null, "other/custom"))
    }
}
