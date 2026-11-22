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
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
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
    onBack: () -> Unit,
) {
    val selected = Projects.findBySlug(selectedProject)
    Scaffold(topBar = {
        TopAppBar(
            title = {
                Column {
                    Text("Workspace", style = MaterialTheme.typography.titleLarge)
                    Text("Projekte · Gedächtnis · Agenten", style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            },
            navigationIcon = { TextButton(onClick = onBack) { Text("‹  Chat") } },
            actions = { TextButton(onClick = onOpenLiveApp) { Text("Live App") } },
        )
    }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Card(modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("DEIN DEVELOPMENT HUB", style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary)
                    Text("Alles im Blick. Ein klarer nächster Schritt.", style = MaterialTheme.typography.headlineSmall)
                    Text("Wähle ein Projekt. OpenHands lädt Kontext und Projektgedächtnis, analysiert den aktuellen Stand und erstellt nachvollziehbare Verbesserungsvorschläge.",
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = true, onClick = {}, enabled = false, label = { Text("Projektgedächtnis") })
                        FilterChip(selected = true, onClick = {}, enabled = false, label = { Text("Mobile First") })
                    }
                }
            }

            SectionHeading("PROJEKTÜBERSICHT", "Freigegebene Entwicklungsziele")
            Projects.alle.forEach { project ->
                ProjectCard(project, project.slug == selectedProject) { onSelectProject(project.slug) }
            }

            SectionHeading("ROUTING & AGENTEN", "Live-Ergebnisse werden pro Actions-Lauf nachgewiesen")
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Free Route Hunter", style = MaterialTheme.typography.titleMedium)
                        FilterChip(selected = false, onClick = {}, enabled = false,
                            label = { Text("Prüfung je Lauf") })
                    }
                    Text(
                        if (model.isBlank())
                            "Automatische kostenlose Routensuche ist konfiguriert. Ob eine Route aktuell nutzbar ist, wird erst im jeweiligen Actions-Lauf durch einen echten Aufruf bestätigt."
                        else
                            "Manuelles Modell: $model. Die Verfügbarkeit wird im jeweiligen Actions-Lauf geprüft; eine gespeicherte Modell-ID ist kein Gesundheitsnachweis.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("Superagent-Team", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
                    Text("Architekt → Implementierer → Qualitätsprüfer. Drei getrennte, aufeinander aufbauende Phasen mit gemeinsamem Workspace.",
                        style = MaterialTheme.typography.bodySmall)
                }
            }

            SectionHeading("WERKZEUG- & ENTWICKLER-PACKS", "Sechs lokale Skills in vier kuratierten Packs")
            CapabilityCard(
                "Entwicklung",
                "Autonome Entwicklung und Refactoring",
                "2 Skills",
                "autonomous-development · automated-refactoring",
            )
            CapabilityCard(
                "Qualität & Sicherheit",
                "Regressionstests, Prüfungen und sichere Änderungen",
                "2 Skills",
                "quality-engineering · security",
            )
            CapabilityCard(
                "Frontend & UX",
                "Responsive Oberflächen und UX-Verbesserungen",
                "1 Skill",
                "frontend-ux",
            )
            CapabilityCard(
                "Integrationen",
                "MCP- und Connector-Integrationen",
                "1 Skill",
                "integrations",
            )
            CapabilityCard(
                "Externe Plugin-Packs",
                "Anthropic Skills: frontend-design und docx",
                "Validate-Modus",
                "Wird geprüft, nicht automatisch installiert",
            )

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Projektgedächtnis", style = MaterialTheme.typography.titleMedium)
                    Text("Der Workflow lädt frühere Entscheidungen, Befunde und offene Punkte aus projects/<projekt>/GEDAECHTNIS.md und schreibt nach dem Lauf einen nachvollziehbaren Eintrag zurück.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("Quelle: projects/<projekt>/GEDAECHTNIS.md",
                        style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                }
            }
            if (selected != null) Button(onClick = onOpenLiveApp, modifier = Modifier.fillMaxWidth()) {
                Text("${selected.label} · Live-Vorschau öffnen")
            }
        }
    }
}

@Composable
private fun SectionHeading(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(title, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
        Text(subtitle, style = MaterialTheme.typography.titleMedium)
    }
}

@Composable
private fun CapabilityCard(title: String, description: String, count: String, detail: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, style = MaterialTheme.typography.titleSmall)
                Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(detail, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(count, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Composable
private fun ProjectCard(project: ProjectChoice, selected: Boolean, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = if (selected)
            MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(project.label, style = MaterialTheme.typography.titleMedium)
                FilterChip(selected = selected, onClick = onClick, label = { Text(if (selected) "Aktiv" else "Auswählen") })
            }
            Text(project.description, style = MaterialTheme.typography.bodyMedium)
            Text("Ziel: ${project.targetShort}", style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
