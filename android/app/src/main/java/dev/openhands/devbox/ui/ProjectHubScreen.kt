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
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.openhands.devbox.data.ProjectChoice
import dev.openhands.devbox.data.Projects

@Composable
fun ProjectHubScreen(
    selectedProject: String,
    model: String,
    onSelectProject: (String) -> Unit,
    onOpenLiveApp: () -> Unit,
    onBack: () -> Unit,
) {
    val selected = Projects.findBySlug(selectedProject)
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
            Text(
                "Wähle ein freigegebenes Projekt. Zielrepository und Projektauftrag werden automatisch an den OpenHands-Lauf übergeben.",
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
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Free Route Hunter", style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (model.isBlank()) {
                            "Automatisch aktiv: Vor jedem Lauf wird eine erreichbare Gratis-Route gesucht und geprüft."
                        } else {
                            "Manuelles Modell aktiv: $model. Leere das Modellfeld, um den Hunter zu verwenden."
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
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
