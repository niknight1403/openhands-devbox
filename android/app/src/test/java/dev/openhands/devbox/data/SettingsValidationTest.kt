package dev.openhands.devbox.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SettingsValidationTest {

    @Test
    fun acceptsValidRepositoryAndWorkflowDefaults() {
        assertTrue(Settings(token = "test-token").isValid())
    }

    @Test
    fun rejectsTargetWithAdditionalPathSegments() {
        assertFalse(Settings(token = "test-token", targetRepo = "owner/repo/extra").isValid())
    }

    @Test
    fun rejectsTargetPathTraversal() {
        assertFalse(Settings(token = "test-token", targetRepo = "owner/../secrets").isValid())
    }

    @Test
    fun rejectsMalformedControlOwner() {
        assertFalse(Settings(token = "test-token", controlOwner = "owner?query=1").isValid())
    }

    @Test
    fun rejectsWorkflowPathTraversalAndQueryInjection() {
        assertFalse(Settings(token = "test-token", workflowFile = "../secrets.yml").isValid())
        assertFalse(Settings(token = "test-token", workflowFile = "build.yml?ref=main").isValid())
    }

    @Test
    fun acceptsNestedYamlWorkflowPath() {
        assertTrue(Settings(token = "test-token", workflowFile = "ci/android/build.yaml").isValid())
    }
}
