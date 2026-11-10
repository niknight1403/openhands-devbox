package dev.openhands.devbox.data

import org.junit.Assert.assertEquals
import org.junit.Test

class ProjectsTest {
    @Test
    fun selectedProjectUsesItsConfiguredTargetOwnerNotTheControlOwner() {
        val project = Projects.findBySlug("cybersarah-control-center")

        assertEquals(
            "niknight1403/CyberSarah-Control-Center",
            Projects.targetRepoFor(project, "another-owner/openhands-devbox"),
        )
    }

    @Test
    fun missingProjectKeepsConfiguredFallbackTarget() {
        assertEquals(
            "another-owner/custom-target",
            Projects.targetRepoFor(null, "another-owner/custom-target"),
        )
    }
}
