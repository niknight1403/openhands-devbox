package dev.openhands.devbox.data

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AutopilotStatusTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun decodesRouteToolAndSkillPackReadiness() {
        val report = json.decodeFromString(
            AutopilotStatus.serializer(),
            """
                {
                  "generated_at": "2026-11-23T12:00:00+00:00",
                  "mode": "cloud",
                  "tool_probe": true,
                  "routes": [
                    {"provider": "OpenRouter", "model": "model-a", "chat_ok": true, "tools_ok": true, "latency_ms": 240},
                    {"provider": "Fallback", "model": "model-b", "chat_ok": true, "tools_ok": false, "latency_ms": 510}
                  ],
                  "best": {"provider": "OpenRouter", "model": "model-a", "chat_ok": true, "tools_ok": true, "latency_ms": 240},
                  "packs": [
                    {"name": "anthropic-skills", "ok": true, "reason": "geprüft, nicht kopiert (mode=validate)", "installed": 0,
                     "skills": [{"name": "frontend-design", "ok": true, "reason": "valide"}]}
                  ],
                  "warnings": [],
                  "duration_s": 3.1
                }
            """.trimIndent(),
        )

        assertEquals("2026-11-23T12:00:00+00:00", report.generatedAt)
        assertTrue(report.toolProbe == true)
        assertEquals("OpenRouter", report.best?.provider)
        assertTrue(report.best?.toolsOk == true)
        assertEquals(2, report.routes.size)
        assertFalse(report.routes[1].toolsOk)
        assertEquals("anthropic-skills", report.packs.single().name)
        assertTrue(report.packs.single().ok)
        assertEquals("frontend-design", report.packs.single().skills.single().name)
    }
}
