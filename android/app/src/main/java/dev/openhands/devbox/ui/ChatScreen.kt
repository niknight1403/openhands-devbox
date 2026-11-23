package dev.openhands.devbox.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp

private val profiles = listOf("superagent", "implementer", "frontend", "security", "quality")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    messages: List<ChatMessage>,
    busy: Boolean,
    statusText: String,
    runUrl: String?,
    profile: String,
    autoMerge: Boolean,
    onProfileChange: (String) -> Unit,
    onAutoMergeChange: (Boolean) -> Unit,
    onSend: (String) -> Unit,
    attachments: List<String>,
    onAttach: (Uri) -> Unit,
    onRemoveAttachment: (String) -> Unit,
    onStop: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenProjects: () -> Unit,
    onOpenLiveApp: () -> Unit,
    onMerge: (Int) -> Unit,
) {
    var draft by remember { mutableStateOf("") }
    val dateiAuswahl = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) onAttach(uri)
    }
    val listState = rememberLazyListState()
    val uriHandler = LocalUriHandler.current
    val isOrchestrated = profile == "superagent"

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                        Text("OPENHANDS  /  DEVBOX", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Text(statusText, style = MaterialTheme.typography.labelSmall,
                            color = if (busy) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                },
                actions = {
                    TextButton(onClick = onOpenProjects) { Text("Workspace") }
                    if (runUrl != null) TextButton(onClick = { uriHandler.openUri(runUrl) }) { Text("Lauf") }
                    TextButton(onClick = onOpenSettings) { Text("Setup") }
                },
            )
        },
        bottomBar = {
            Column(modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surface)
                .imePadding().navigationBarsPadding().padding(horizontal = 12.dp, vertical = 8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(if (isOrchestrated) "SUPERAGENT · 3 PHASEN" else "SPEZIALISTEN-PROFIL",
                        modifier = Modifier.weight(1f), style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    Text("Autonom", style = MaterialTheme.typography.labelMedium)
                    Switch(checked = autoMerge, onCheckedChange = onAutoMergeChange, enabled = !busy)
                }
                if (attachments.isNotEmpty()) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        attachments.forEach { name ->
                            FilterChip(selected = true, onClick = { onRemoveAttachment(name) },
                                label = { Text("$name ×", style = MaterialTheme.typography.labelSmall) }, enabled = !busy)
                        }
                    }
                }
                Spacer(Modifier.height(6.dp))
                Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    OutlinedButton(onClick = { dateiAuswahl.launch("*/*") }, enabled = !busy) { Text("+ Datei") }
                    OutlinedTextField(value = draft, onValueChange = { draft = it },
                        modifier = Modifier.weight(1f).heightIn(min = 54.dp, max = 140.dp),
                        placeholder = { Text("Aufgabe an deine Agenten …") },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send), maxLines = 5)
                    if (busy) OutlinedButton(onClick = onStop) { Text("Stop") }
                    else Button(onClick = {
                        if (draft.isNotBlank()) { onSend(draft); draft = "" }
                    }) { Text("Start") }
                }
            }
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxWidth()) {
            Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("DEVELOPMENT CONTROL", style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary)
                            Text(if (isOrchestrated) "Superagent-Team aktiv" else "Agentenrolle: $profile",
                                style = MaterialTheme.typography.titleMedium)
                        }
                        FilterChip(selected = busy, onClick = {}, enabled = false, label = { Text(if (busy) "Läuft" else "Bereit") })
                    }
                    Text(if (isOrchestrated) "Architekt → Implementierer → Qualitätsprüfer · gemeinsamer Workspace"
                        else "Ein fokussierter Agentenlauf mit passendem Rollenprofil",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            LazyColumn(state = listState, modifier = Modifier.fillMaxWidth().weight(1f),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                verticalArrangement = Arrangement.spacedBy(9.dp)) {
                items(messages, key = { it.id }) { message ->
                    MessageBubble(message, onOpen = { url -> uriHandler.openUri(url) }, onMerge = onMerge)
                }
            }
            HorizontalDivider()
            Row(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 7.dp),
                horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                profiles.forEach { entry ->
                    FilterChip(selected = entry == profile, onClick = { onProfileChange(entry) },
                        label = { Text(when (entry) {
                            "superagent" -> "Superagent"
                            "implementer" -> "Build"
                            "frontend" -> "Frontend"
                            "security" -> "Security"
                            else -> "QA"
                        }, style = MaterialTheme.typography.labelSmall) }, enabled = !busy)
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(message: ChatMessage, onOpen: (String) -> Unit, onMerge: (Int) -> Unit) {
    val isUser = message.fromUser
    val container = when {
        isUser -> MaterialTheme.colorScheme.primary
        message.isError -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.surfaceVariant
    }
    val contentColor = when {
        isUser -> MaterialTheme.colorScheme.onPrimary
        message.isError -> MaterialTheme.colorScheme.onError
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        Column(modifier = Modifier.widthIn(max = 340.dp).background(container, RoundedCornerShape(18.dp))
            .padding(horizontal = 14.dp, vertical = 11.dp)) {
            Text(message.text, color = contentColor, style = MaterialTheme.typography.bodyMedium)
            if (message.url != null) {
                Spacer(Modifier.height(5.dp))
                Text("Öffnen ↗", color = contentColor, style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.clickable { onOpen(message.url) })
            }
            val prNumber = Regex("#(\\d+)").find(message.text)?.groupValues?.getOrNull(1)?.toIntOrNull()
            if (!isUser && prNumber != null && message.text.contains("Draft-PR")) {
                Spacer(Modifier.height(7.dp))
                OutlinedButton(onClick = { onMerge(prNumber) }) { Text("Jetzt mergen", style = MaterialTheme.typography.labelSmall) }
            }
            Spacer(Modifier.height(3.dp))
            Text(message.time, color = contentColor.copy(alpha = 0.62f),
                style = MaterialTheme.typography.labelSmall, fontFamily = FontFamily.Monospace)
        }
    }
}
