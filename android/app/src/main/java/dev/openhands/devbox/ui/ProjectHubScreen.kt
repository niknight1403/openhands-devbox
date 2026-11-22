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
    onBack: () -> Unit,
) {
    val selected = Projects.findBySlug(selectedProject)
    LaunchedEffect(selectedProject) { onRefreshMemory(); onRefreshRoutes() }
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
