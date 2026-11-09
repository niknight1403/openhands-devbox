package dev.openhands.devbox.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import dev.openhands.devbox.data.Settings

private val profileOptions = listOf("superagent", "implementer", "frontend", "security", "quality")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settings: Settings,
    connectionCheck: String?,
    onSave: (Settings) -> Unit,
    onTest: () -> Unit,
    onBack: () -> Unit,
) {
    var token by remember(settings.token) { mutableStateOf(settings.token) }
    var controlOwner by remember(settings.controlOwner) { mutableStateOf(settings.controlOwner) }
    var controlRepo by remember(settings.controlRepo) { mutableStateOf(settings.controlRepo) }
    var workflowFile by remember(settings.workflowFile) { mutableStateOf(settings.workflowFile) }
    var targetRepo by remember(settings.targetRepo) { mutableStateOf(settings.targetRepo) }
    var profile by remember(settings.profile) { mutableStateOf(settings.profile) }
    var model by remember(settings.model) { mutableStateOf(settings.model) }
    var autoMerge by remember(settings.autoMerge) { mutableStateOf(settings.autoMerge) }
    var autoIterate by remember(settings.autoIterate) { mutableStateOf(settings.autoIterate) }
    var maxIterations by remember(settings.maxIterations) { mutableStateOf(settings.maxIterations) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Einstellungen") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Zurück") } },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Zugang", style = MaterialTheme.typography.titleMedium)
            Text(
                "Fine-grained Token mit Zugriff auf Steuer- und Zielrepository. Benötigte Rechte: Actions (read/write), Contents (read/write), Pull requests (read/write). Der Token wird verschlüsselt auf dem Gerät gespeichert.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            OutlinedTextField(
                value = token,
                onValueChange = { token = it },
                label = { Text("GitHub-Token") },
                modifier = Modifier.fillMaxWidth(),
                visualTransformation = PasswordVisualTransformation(),
                singleLine = true,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedButton(
                    onClick = {
                        onSave(
                            settings.copy(
                                token = token.trim(),
                                controlOwner = controlOwner.trim(),
                                controlRepo = controlRepo.trim(),
                                workflowFile = workflowFile.trim(),
                                targetRepo = targetRepo.trim(),
                                profile = profile,
                                model = model.trim(),
                                autoMerge = autoMerge,
                                autoIterate = autoIterate,
                                maxIterations = maxIterations,
                            ),
                        )
                        onTest()
                    },
                ) { Text("Token prüfen") }
                if (connectionCheck != null) {
                    Text(connectionCheck, style = MaterialTheme.typography.bodySmall)
                }
            }

            Spacer(Modifier.height(4.dp))
            Text("Steuerung", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = controlOwner,
                onValueChange = { controlOwner = it },
                label = { Text("Owner des Steuer-Repos") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = controlRepo,
                onValueChange = { controlRepo = it },
                label = { Text("Steuer-Repo") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = workflowFile,
                onValueChange = { workflowFile = it },
                label = { Text("Workflow-Datei") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = targetRepo,
                onValueChange = { targetRepo = it },
                label = { Text("Zielprojekt (owner/repo)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(Modifier.height(4.dp))
            Text("Agentenprofil", style = MaterialTheme.typography.titleMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                profileOptions.forEach { option ->
                    FilterChip(
                        selected = profile == option,
                        onClick = { profile = option },
                        label = { Text(option, style = MaterialTheme.typography.labelSmall) },
                    )
                }
            }
            OutlinedTextField(
                value = model,
                onValueChange = { model = it },
                label = { Text("Modell (leer = automatische Gratis-Route)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(Modifier.height(4.dp))
            Text("Autonomie", style = MaterialTheme.typography.titleMedium)
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Draft-PR automatisch mergen", style = MaterialTheme.typography.bodyMedium)
                            Text(
                                "Nur wenn GitHub den PR als mergebar meldet. Ohne diesen Schalter bleibt der PR als Draft zur Prüfung liegen.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Switch(checked = autoMerge, onCheckedChange = { autoMerge = it })
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Folgedurchläufe", style = MaterialTheme.typography.bodyMedium)
                            Text(
                                "Nach dem Merge prüft ein weiterer Lauf das Ergebnis und schließt Lücken.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Switch(checked = autoIterate, onCheckedChange = { autoIterate = it })
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Maximale Durchläufe: $maxIterations", modifier = Modifier.weight(1f))
                        OutlinedButton(onClick = { if (maxIterations > 1) maxIterations -= 1 }) { Text("-") }
                        Spacer(Modifier.height(2.dp))
                        OutlinedButton(onClick = { if (maxIterations < 3) maxIterations += 1 }) { Text("+") }
                    }
                }
            }

            Spacer(Modifier.height(8.dp))
            Button(
                onClick = {
                    onSave(
                        settings.copy(
                            token = token.trim(),
                            controlOwner = controlOwner.trim(),
                            controlRepo = controlRepo.trim(),
                            workflowFile = workflowFile.trim(),
                            targetRepo = targetRepo.trim(),
                            profile = profile,
                            model = model.trim(),
                            autoMerge = autoMerge,
                            autoIterate = autoIterate,
                            maxIterations = maxIterations,
                        ),
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Speichern") }
            Spacer(Modifier.height(24.dp))
        }
    }
}
