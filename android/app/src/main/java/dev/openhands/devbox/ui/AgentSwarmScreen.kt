package dev.openhands.devbox.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.openhands.devbox.data.AutopilotStatus
import dev.openhands.devbox.data.WorkflowRun

private val agentProfiles = listOf(
    "superagent" to "Superagent",
    "implementer" to "Implementierer",
    "frontend" to "Frontend",
    "security" to "Sicherheit",
    "quality" to "Qualität",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentSwarmScreen(
    profile: String,
    busy: Boolean,
    statusText: String,
    routeStatus: String,
    routeDetails: String,
    autopilotStatus: AutopilotStatus?,
    auditStatus: String,
    auditBusy: Boolean,
    workflowRuns: List<WorkflowRun>,
    workflowRunsStatus: String,
    onRefresh: () -> Unit,
    onStartAudit: () -> Unit,
    onSelectProfile: (String) -> Unit,
    onOpenChat: () -> Unit,
    onBack: () -> Unit,
) {
    LaunchedEffect(Unit) { onRefresh() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Agenten-Swarm", fontWeight = FontWeight.SemiBold)
                        Text("SUPERAGENT  /  KOMPETENZ-WÄCHTER", style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                },
                navigationIcon = { TextButton(onClick = onBack) { Text("Zurück") } },
                actions = { TextButton(onClick = onRefresh) { Text("Aktualisieren") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text("Superagent & Agent Swarm", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(
                    "Auftragsphasen und tatsächlich geprüfte Werkzeuge an einem Ort. Statuswerte stammen aus GitHub Actions, nicht aus simulierten Agenten-Heartbeats.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("SUPERAGENT-ORCHESTRATOR", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    Text(if (busy) "Lauf aktiv · $statusText" else "Bereit für den nächsten Auftrag",
                        style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(
                        "Der Superagent führt drei getrennte Phasen nacheinander aus. Das ist ein koordinierter Agenten-Schwarm, kein parallel laufender Pool.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    AgentPhase("01", "Architekt", "Prüft Repository, Risiken und passenden Prüfplan.")
                    AgentPhase("02", "Implementierer", "Setzt den begrenzten Plan im vorhandenen Projektstil um.")
                    AgentPhase("03", "Qualitätsprüfer", "Kontrolliert Diff, Sicherheit, Tests und Regressionen.")
                    Button(onClick = onOpenChat, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
                        Text(if (busy) "Auftrag läuft" else "Auftrag im Chat starten")
                    }
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("Spezialisierte Agentenprofile", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Wähle ein Profil für den nächsten Lauf. Die Auswahl öffnet den Chat und startet nicht automatisch einen Auftrag.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    agentProfiles.chunked(2).forEach { rowProfiles ->
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            rowProfiles.forEach { (id, label) ->
                                FilterChip(selected = profile == id, onClick = { onSelectProfile(id) }, label = { Text(label) }, enabled = !busy)
                            }
                        }
                    }
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically) {
                        Text("Modell- & Tool-Readiness", style = MaterialTheme.typography.titleMedium)
                        TextButton(onClick = onRefresh) { Text("Status laden") }
                    }
                    Text(routeStatus, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                    if (routeDetails.isNotBlank()) {
                        Text(routeDetails, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    val toolCallState = when {
                        autopilotStatus == null -> "Noch kein aktueller Prüfbericht"
                        autopilotStatus.toolProbe != true -> "Tool-Call-Prüfung nicht bestätigt"
                        autopilotStatus.best?.toolsOk == true -> "Echter Tool-Call bestätigt"
                        autopilotStatus.routes.any { it.chatOk } -> "Chat erreichbar, aber kein Tool-Call bestätigt"
                        else -> "Keine nutzbare Route bestätigt"
                    }
                    val toolCallReady = when {
                        autopilotStatus == null || autopilotStatus.toolProbe != true -> null
                        autopilotStatus.best?.toolsOk == true -> true
                        else -> false
                    }
                    ReadinessRow("LLM-Tool-Calling", toolCallState, toolCallReady)
                    if (autopilotStatus?.warnings.orEmpty().isNotEmpty()) {
                        Text("Hinweise: ${autopilotStatus.warnings.take(3).joinToString(" · ")}",
                            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Werkzeuge & Fähigkeiten", style = MaterialTheme.typography.titleMedium)
                    ReadinessRow(
                        "Web-Recherche",
                        "control/scripts/webtools.py enthält Suche und Seitentext; die Live-Erreichbarkeit wird separat geprüft.",
                        ready = null,
                    )
                    ReadinessRow(
                        "Lokale Agent-Skills",
                        "Kuratiertes Entwicklungs-, Qualitäts/Sicherheits-, UI- und Integrations-Pack wird im Agentenlauf übernommen; hier nicht live geprüft.",
                        ready = null,
                    )
                    val externalPackSummary = when {
                        autopilotStatus == null -> "Noch kein Autopilot-Bericht für externe Packs."
                        autopilotStatus.packs.isEmpty() -> "Kein externes Pack im letzten Bericht konfiguriert."
                        else -> "${autopilotStatus.packs.count { it.ok }} von ${autopilotStatus.packs.size} externen Packs strukturell validiert; nicht automatisch installiert."
                    }
                    ReadinessRow("Externe Skill-Packs", externalPackSummary, ready = null)
                    autopilotStatus?.packs.orEmpty().forEach { pack ->
                        Text(
                            "${pack.name}: ${pack.reason ?: if (pack.ok) "bereit" else "nicht verfügbar"}" +
                                if (pack.installed > 0) " · ${pack.installed} installiert" else "",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (pack.ok) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.error,
                        )
                    }
                    ReadinessRow(
                        "MCP / externe Konten",
                        "Nicht automatisch verbunden: Server, Berechtigungen und Secrets brauchen eine konkrete Freigabe.",
                        ready = null,
                    )
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Kompetenz-Wächter", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Der Autopilot läuft planmäßig alle sechs Stunden, prüft Modell- und Tool-Aufrufe und veröffentlicht den echten Bericht. Bei Bedarf kannst du denselben Check jetzt starten.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    OutlinedButton(onClick = onStartAudit, modifier = Modifier.fillMaxWidth(), enabled = !auditBusy) {
                        Text(if (auditBusy) "Prüfung wird gestartet …" else "Autopilot jetzt prüfen")
                    }
                    if (auditStatus.isNotBlank()) {
                        Text(auditStatus, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
                    }
                    Text(
                        "Der Check startet GitHub Actions und fragt die konfigurierten Modellrouten tatsächlich an; Provider-Kontingente oder Kosten können betroffen sein. Unbekannte Plugins oder MCP-Rechte werden nicht automatisch hinzugefügt.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically) {
                        Text("Letzte GitHub-Läufe", style = MaterialTheme.typography.titleMedium)
                        TextButton(onClick = onRefresh) { Text("Aktualisieren") }
                    }
                    Text(workflowRunsStatus, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (workflowRuns.isEmpty()) {
                        Text("Noch keine Laufdaten geladen.", style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        workflowRuns.take(5).forEach { run ->
                            val state = when {
                                run.status == "in_progress" -> "LÄUFT"
                                run.status == "queued" -> "WARTET"
                                run.conclusion == "success" -> "ERFOLGREICH"
                                run.conclusion == "failure" -> "FEHLGESCHLAGEN"
                                else -> run.conclusion?.uppercase() ?: run.status?.uppercase() ?: "UNBEKANNT"
                            }
                            Text(
                                "${run.name ?: "Workflow"} · $state · ${run.headBranch ?: "Branch unbekannt"} · #${run.id}",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (run.conclusion == "failure") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
                            )
                        }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun AgentPhase(number: String, name: String, description: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(number, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.secondary,
            fontWeight = FontWeight.Bold)
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
            Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun ReadinessRow(title: String, detail: String, ready: Boolean?) {
    val color = when (ready) {
        true -> MaterialTheme.colorScheme.tertiary
        false -> MaterialTheme.colorScheme.error
        null -> MaterialTheme.colorScheme.secondary
    }
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(title, style = MaterialTheme.typography.labelLarge, color = color, fontWeight = FontWeight.SemiBold)
        Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
