package dev.openhands.devbox.data

/** Ein begrenzter Erstlauf beim Laden eines Zielrepositorys. */
object ProjectAnalysis {
    val task = """
        Analysiere das geladene GitHub-Projekt zuerst: Architektur, vorhandene Aufgaben,
        Tests, CI, Sicherheit, Bedienbarkeit und dokumentierte Projektentscheidungen.
        Prüfe nur belegbare Befunde. Erstelle eine priorisierte Liste konkreter
        Verbesserungen mit Nutzen, Risiko und passendem Prüfschritt in
        docs/openhands/STATUS.md. Wähle anschließend höchstens eine kleine,
        sichere Verbesserung aus und setze sie vollständig um. Führe die
        betroffenen Checks aus und dokumentiere das Ergebnis samt Grenzen.
        Kein Merge, keine kostenpflichtige Infrastruktur, keine Secrets und
        keine externen Veröffentlichungen. Der Workflow erstellt einen Draft-PR.
    """.trimIndent()
}
