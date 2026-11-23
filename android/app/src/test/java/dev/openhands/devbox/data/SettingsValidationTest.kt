package dev.openhands.devbox.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SettingsValidationTest {
    @Test fun acceptsValidRepositoryAndWorkflowDefaults() {
        assertTrue(Settings(token = "test-token").isValid())
    }
    @Test fun rejectsTargetWithAdditionalPathSegments() {
        assertFalse(Settings(token = "test-token", targetRepo = "owner/repo/extra").isValid())
    }
    @Test fun rejectsTargetPathTraversal() {
        assertFalse(Settings(token = "test-token", targetRepo = "owner/../secrets").isValid())
    }
    @Test fun rejectsMalformedControlOwner() {
        assertFalse(Settings(token = "test-token", controlOwner = "owner?query=1").isValid())
    }
    @Test fun rejectsWorkflowPathTraversalAndQueryInjection() {
        assertFalse(Settings(token = "test-token", workflowFile = "../secrets.yml").isValid())
        assertFalse(Settings(token = "test-token", workflowFile = "build.yml?ref=main").isValid())
    }
    @Test fun acceptsNestedYamlWorkflowPath() {
        assertTrue(Settings(token = "test-token", workflowFile = "ci/android/build.yaml").isValid())
    }
    @Test fun sprint01RejectsEmptyToken() {
        assertFalse(Settings(token = "   ").isValid())
    }
    @Test fun sprint02RejectsTokenWithSurroundingWhitespace() {
        assertFalse(Settings(token = " token ").isValid())
    }
    @Test fun sprint03RejectsControlRepositoryTraversal() {
        assertFalse(Settings(token = "test-token", controlRepo = "..").isValid())
    }
    @Test fun sprint04RejectsTargetRepositoryTraversalAlias() {
        assertFalse(Settings(token = "test-token", targetRepo = "owner/..").isValid())
    }
    @Test fun sprint05RejectsRepositoryWithLeadingDash() {
        assertFalse(Settings(token = "test-token", targetRepo = "owner/-repo").isValid())
    }
    @Test fun sprint06RejectsZeroIterations() {
        assertFalse(Settings(token = "test-token", maxIterations = 0).isValid())
    }
    @Test fun sprint07RejectsExcessiveIterations() {
        assertFalse(Settings(token = "test-token", maxIterations = 100).isValid())
    }
    @Test fun sprint08AcceptsMaximumSafeIterations() {
        assertTrue(Settings(token = "test-token", maxIterations = 3).isValid())
    }
    @Test fun sprint09RejectsWorkflowBackslash() {
        assertFalse(Settings(token = "test-token", workflowFile = "ci\\\\build.yml").isValid())
    }
    @Test fun sprint10AcceptsHyphenatedOwnerAndRepository() {
        assertTrue(Settings(token = "test-token", controlOwner = "team-dev", controlRepo = "openhands-devbox").isValid())
    }

}
