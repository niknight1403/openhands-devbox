package dev.openhands.devbox.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.openhands.devbox.data.ProjectChoice
import dev.openhands.devbox.data.Projects
import dev.openhands.devbox.data.WorkflowRun

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun ProjectHubScreen(
    selectedProject: String,
    model: String,
    onSelectProject: (String) -> Unit,
    onOpenLiveApp: () -> Unit,
    projectMemory: String,
    projectMemoryStatus: String,
    onRefreshMemory: () -> Unit,
    routeStatus: String,
    routeDetails: String,
    onRefreshRoutes: () -> Unit,
    workflowRuns: List<WorkflowRun>,
    workflowRunsStatus: String,
    onRefreshWorkflowRuns: () -> Unit,
    onBack: () -> Unit,
) {
    val selected = Projects.findBySlug(selectedProject)
    LaunchedEffect(selectedProject) { onRefreshMemory(); onRefreshRoutes(); onRefreshWorkflowRuns() }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Projektzentrale") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Chat") } },
                actions = { TextButton(onClick = onOpenLiveApp) { Text("Live App") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Verschiedene Projekte", style = MaterialTheme.typography.headlineSmall)
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Agenten-Crew", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Die Crew nutzt die tatsächlich konfigurierten GitHub-Action-Profile. Superagent führt drei getrennte Sitzungen nacheinander aus; die spezialisierten Profile starten jeweils eine eigene Sitzung.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    AgentRoleRow("ARCHITEKT", "Analysiert Repository, Risiken und Prüfplan.")
                    AgentRoleRow("IMPLEMENTIERER", "Setzt den begrenzten Plan im Projekt um.")
                    AgentRoleRow("REVIEWER", "Prüft Diff, Sicherheit und Regressionen.")
                    AgentRoleRow("FRONTEND", "Spezialisierter UI-/UX-Durchlauf.")
                    AgentRoleRow("SECURITY", "Prüft Authentifizierung, Eingaben und Secrets.")
                    AgentRoleRow("QUALITY", "Führt passende Tests, Lint und Builds aus.")
                    Text(
                        "Hinweis: Rollenprofile sind keine parallel laufenden Agenten. Live-Status erscheint erst, wenn GitHub Actions einen echten Lauf meldet.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                }
            }
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("GitHub Actions · Runs", style = MaterialTheme.typography.titleMedium)
                        TextButton(onClick = onRefreshWorkflowRuns) { Text("Aktualisieren") }
                    }
                    Text(workflowRunsStatus, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    workflowRuns.take(6).forEach { run ->
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(run.name ?: "Workflow", style = MaterialTheme.typography.bodyMedium)
                                val state = when {
                                    run.status == "in_progress" -> "LÄUFT"
                                    run.status == "queued" -> "WARTET"
                                    run.conclusion == "success" -> "ERFOLGREICH"
                                    run.conclusion == "failure" -> "FEHLGESCHLAGEN"
                                    run.conclusion == "cancelled" -> "ABGEBROCHEN"
                                    else -> run.conclusion?.uppercase() ?: run.status?.uppercase() ?: "UNBEKANNT"
                                }
                                Text(state, style = MaterialTheme.typography.labelSmall, color = when (run.conclusion) {
                                    "success" -> MaterialTheme.colorScheme.tertiary
                                    "failure" -> MaterialTheme.colorScheme.error
                                    else -> MaterialTheme.colorScheme.primary
                                })
                            }
                            Text(
                                "${run.headBranch ?: "Branch unbekannt"} · Run #${run.id}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text("MCP-Verbindungen", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "In diesem Repository ist aktuell keine MCP-Server-Registry und kein MCP-Verbindungsworkflow nachweisbar. Deshalb werden hier keine verbundenen Server oder grünen Healthchecks vorgetäuscht.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        "Vorhanden sind AgentSkills- und Plugin-Packs. Eine echte MCP-Verwaltung benötigt anschließend einen definierten Server-Katalog, Transport-/Auth-Verträge und sichere Laufzeitprüfungen.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                }
            }
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("Werkzeug- & Entwickler-Packs", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Kuratierte lokale Agent-Skills aus .agents/skills. Die App zeigt den versionierten Katalog; Installation und Kopieren erfolgen weiterhin über den geprüften CLI-Installer.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    ToolPackRow("ENTWICKLUNG", "Autonomous Development · Automated Refactoring")
                    ToolPackRow("QUALITÄT", "Quality Engineering · Security")
                    ToolPackRow("OBERFLÄCHE", "Frontend UX")
                    ToolPackRow("INTEGRATIONEN", "Integrations")
                    Text(
                        "Installationsschutz: nur vorhandene Skills mit SKILL.md; Symlinks und Überschreiben werden abgewiesen. Kein automatischer Installationslauf aus dieser Ansicht.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                }
            }
            Text(
                "Wähle ein freigegebenes Projekt. Mit gültigem GitHub-Zugang startet beim Wechsel eine Analyse mit Verbesserungsvorschlägen und höchstens einer kleinen Optimierung. Den Lauf siehst du im Chat.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Projects.alle.forEach { project ->
                ProjectCard(
                    project = project,
                    selected = project.slug == selectedProject,
                    onClick = { onSelectProject(project.slug) },
                )
            }
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Projektgedächtnis", style = MaterialTheme.typography.titleMedium)
                        TextButton(onClick = onRefreshMemory, enabled = selectedProject.isNotBlank()) { Text("Aktualisieren") }
                    }
                    Text(
                        projectMemoryStatus,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (projectMemory.isNotBlank()) {
                        Text(
                            projectMemory,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                    } else {
                        Text(
                            "Hier erscheinen dokumentierte Läufe, Entscheidungen, Befunde, Wiederholungswarnungen und offene Punkte aus projects/$selectedProject/GEDAEHNTNIS.md.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Free Route Hunter", style = MaterialTheme.typography.titleMedium)
                        TextButton(onClick = onRefreshRoutes) { Text("Aktualisieren") }
                    }
                    Text(
                        if (model.isBlank()) "Automatische Routenwahl ist für neue Agentenläufe konfiguriert."
                        else "Manuelles Modell vorgegeben: $model",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(routeStatus, style = MaterialTheme.typography.bodyMedium)
                    if (routeDetails.isNotBlank()) {
                        Text(routeDetails, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    FilterChip(
                        selected = model.isBlank(),
                        onClick = {},
                        enabled = false,
                        label = { Text(if (model.isBlank()) "Automatische Route" else "Modell fest vorgegeben") },
                    )
                }
            }
            if (selected != null) {
                Button(onClick = onOpenLiveApp, modifier = Modifier.fillMaxWidth()) {
                    Text("${selected.label} live öffnen")
                }
            }
        }
    }
}

@Composable
private fun ProjectCard(project: ProjectChoice, selected: Boolean, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(project.label, style = MaterialTheme.typography.titleMedium)
                FilterChip(selected = selected, onClick = onClick, label = { Text(if (selected) "aktiv" else "wählen") })
            }
            Text(project.description, style = MaterialTheme.typography.bodyMedium)
            Text(
                "Ziel: ${project.targetShort}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun AgentRoleRow(role: String, description: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(role, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
    }
}

@Composable
private fun ToolPackRow(name: String, skills: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(name, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text(skills, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
    }
}
