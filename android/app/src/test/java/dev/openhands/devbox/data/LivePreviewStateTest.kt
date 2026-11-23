package dev.openhands.devbox.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LivePreviewStateTest {
    @Test fun emptyInputIsNotConfigured() {
        val state = resolveLivePreviewState("")
        assertEquals(LivePreviewStatus.NOT_CONFIGURED, state.status)
        assertFalse(state.isReady)
        assertEquals("", state.displayUrl)
    }

    @Test fun whitespaceOnlyInputIsNotConfigured() {
        val state = resolveLivePreviewState("   ")
        assertEquals(LivePreviewStatus.NOT_CONFIGURED, state.status)
        assertFalse(state.isReady)
    }

    @Test fun acceptsHttpUrlWithHost() {
        val state = resolveLivePreviewState("http://localhost:5173")
        assertEquals(LivePreviewStatus.READY, state.status)
        assertTrue(state.isReady)
        assertEquals("http://localhost:5173", state.displayUrl)
    }

    @Test fun acceptsHttpsUrlWithPath() {
        val state = resolveLivePreviewState("https://app.example.com/dashboard?tab=1#section")
        assertEquals(LivePreviewStatus.READY, state.status)
        assertTrue(state.isReady)
    }

    @Test fun trimsSurroundingWhitespace() {
        val state = resolveLivePreviewState("  https://example.com/  ")
        assertEquals(LivePreviewStatus.READY, state.status)
        assertEquals("https://example.com/", state.displayUrl)
    }

    @Test fun rejectsUnsupportedScheme() {
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("file:///etc/passwd").status)
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("ftp://example.com").status)
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("javascript:alert(1)").status)
    }

    @Test fun rejectsUrlWithoutHost() {
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("http:///path-only").status)
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("https://").status)
    }

    @Test fun rejectsUrlWithoutScheme() {
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("example.com").status)
        assertEquals(LivePreviewStatus.INVALID_URL, resolveLivePreviewState("not a url at all").status)
    }
}