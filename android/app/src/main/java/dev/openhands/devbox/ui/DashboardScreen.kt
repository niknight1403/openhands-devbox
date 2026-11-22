package dev.openhands.devbox.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    busy: Boolean,
    statusText: String,
    selectedProject: String,
    model: String,
    profile: String,
    onOpenChat: () -> Unit,
    onOpenProjects: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenLiveApp: () -> Unit,
) {
    val routeDescription = if (model.isBlank()) {
        "Automatische kostenlose Routensuche vor jedem Agentenlauf"
    } else {
        "Festgelegtes Modell: $model"
    }
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("NEBULA COMMAND", fontWeight = FontWeight.Bold)
                        Text("OPENHANDS DEVBOX  /  CONTROL CENTER", style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).background(MaterialTheme.colorScheme.background)
                .verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Deine Entwicklungszentrale", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text("Agenten, Projekte und Modellrouten an einem Ort.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                StatusTile("AGENT", if (busy) "AKTIV" else "BEREIT", if (busy) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary, Modifier.weight(1f))
                StatusTile("PROFIL", profile.uppercase(), MaterialTheme.colorScheme.secondary, Modifier.weight(1f))
            }
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(20.dp),
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("SYSTEMSTATUS", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    Text(statusText.ifBlank { "Warte auf den nächsten Auftrag" }, style = MaterialTheme.typography.titleMedium)
                    Text(if (busy) "Ein Workflow wurde gestartet oder wird überwacht." else "Kein laufender Auftrag wird von der App gemeldet.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Text("KERNMODULE", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, fontWeight = FontWeight.Bold)
            ModuleCard("01  SUPERAGENT CHAT", "Aufträge starten, Rollen wählen und GitHub-Läufe verfolgen.", "AUFTRAG ÖFFNEN", onOpenChat)
            ModuleCard("02  PROJEKTZENTRALE", "Aktives Projekt: ${selectedProject.ifBlank { "Keines ausgewählt" }}. Projektkontext und Live-App.", "PROJEKTE ÖFFNEN", onOpenProjects)
            ModuleCard("03  FREE ROUTE HUNTER", routeDescription + ". Live-Ergebnisse werden erst nach einem echten Prüflauf bestätigt.", "ROUTEN-KONFIGURATION", onOpenSettings)
            ModuleCard("04  LIVE VORSCHAU", "Öffne die konfigurierte Projektvorschau.", "VORSCHAU ÖFFNEN", onOpenLiveApp)
            Card(
                modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenSettings),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(18.dp),
            ) {
                Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("SYSTEM & INTEGRATIONEN", fontWeight = FontWeight.SemiBold)
                        Text("GitHub-Zugang, Workflow, Modell und Autonomie verwalten.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text("ÖFFNEN  →", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium)
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun StatusTile(label: String, value: String, accent: androidx.compose.ui.graphics.Color, modifier: Modifier = Modifier) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleMedium, color = accent, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ModuleCard(title: String, description: String, action: String, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(18.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
            Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(action + "  →", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
        }
    }
}
