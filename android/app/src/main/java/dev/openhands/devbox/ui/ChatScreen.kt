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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.ui.text.style.TextOverflow
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
    onOpenDashboard: () -> Unit,
    onMerge: (Int) -> Unit,
) {
    var draft by remember { mutableStateOf("") }
    var showSwarm by remember { mutableStateOf(false) }
    // Dateien, Fotos und Videos direkt vom Gerät; die App laedt sie danach
    // ins Zielprojekt und gibt die Adressen an den Lauf weiter.
    val dateiAuswahl = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) onAttach(uri)
    }
    val listState = rememberLazyListState()
    val uriHandler = LocalUriHandler.current

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Nebula Command", fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            text = statusText,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    var expanded by remember { mutableStateOf(false) }
                    TextButton(onClick = { expanded = true }) { Text("Menü") }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        DropdownMenuItem(text = { Text("Zentrale") }, onClick = { expanded = false; onOpenDashboard() })
                        DropdownMenuItem(text = { Text("Projekte") }, onClick = { expanded = false; onOpenProjects() })
                        DropdownMenuItem(text = { Text("Live App") }, onClick = { expanded = false; onOpenLiveApp() })
                        if (runUrl != null) {
                            DropdownMenuItem(text = { Text("Lauf") }, onClick = { expanded = false; uriHandler.openUri(runUrl) })
                        }
                        DropdownMenuItem(text = { Text("Einstellungen") }, onClick = { expanded = false; onOpenSettings() })
                    }
                },
            )
        },
        bottomBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface)
                    .imePadding()
                    .navigationBarsPadding()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = "Profil: $profile",
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text("Autonom", style = MaterialTheme.typography.labelMedium)
                    Switch(
                        checked = autoMerge,
                        onCheckedChange = onAutoMergeChange,
                        enabled = !busy,
                    )
                }
                if (attachments.isNotEmpty()) {
                    Spacer(Modifier.height(4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        attachments.forEach { name ->
                            FilterChip(
                                selected = true,
                                onClick = { onRemoveAttachment(name) },
                                label = { Text("$name ×", style = MaterialTheme.typography.labelSmall) },
                                enabled = !busy,
                            )
                        }
                    }
                }
                Spacer(Modifier.height(6.dp))
                if (!showSwarm) Row(verticalAlignment = Alignment.Bottom) {
                    OutlinedButton(
                        onClick = { dateiAuswahl.launch("*/*") },
                        enabled = !busy,
                    ) { Text("Datei") }
                    Spacer(Modifier.size(8.dp))
                    OutlinedTextField(
                        value = draft,
                        onValueChange = { draft = it },
                        modifier = Modifier
                            .weight(1f)
                            .heightIn(min = 56.dp, max = 160.dp),
                        placeholder = { Text("Was soll gebaut oder repariert werden?") },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        maxLines = 5,
                    )
                    Spacer(Modifier.size(8.dp))
                    if (busy) {
                        OutlinedButton(onClick = onStop) { Text("Stop") }
                    } else {
                        Button(
                            onClick = {
                                if (draft.isNotBlank()) {
                                    onSend(draft)
                                    draft = ""
                                }
                            },
                        ) { Text("Senden") }
                    }
                }
                NavigationBar(windowInsets = androidx.compose.foundation.layout.WindowInsets(0, 0, 0, 0)) {
                    NavigationBarItem(selected = false, onClick = onOpenDashboard, icon = { Text("⌂") }, label = { Text("Zentrale", maxLines = 1) })
                    NavigationBarItem(selected = !showSwarm, onClick = { showSwarm = false; if (!busy) onProfileChange("superagent") }, icon = { Text("✦") }, label = { Text("Agent", maxLines = 1) })
                    NavigationBarItem(selected = showSwarm, onClick = { showSwarm = true }, icon = { Text("◈") }, label = { Text("Swarm", maxLines = 1) })
                    NavigationBarItem(selected = false, onClick = onOpenProjects, icon = { Text("▣") }, label = { Text("Projekte", maxLines = 1) })
                    NavigationBarItem(selected = false, onClick = onOpenSettings, icon = { Text("⚙") }, label = { Text("Setup", maxLines = 1) })
                }
            }
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxWidth()) {
            if (showSwarm) {
                Column(Modifier.weight(1f).fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Agenten-Swarm", style = MaterialTheme.typography.headlineSmall)
                    Text("Orchestrierung noch nicht integriert. Hier werden später Aufgaben und Subagenten angezeigt.")
                    OutlinedButton(onClick = { showSwarm = false }) { Text("Zum Superagent") }
                }
            } else LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxWidth().weight(1f),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(messages, key = { it.id }) { message ->
                    MessageBubble(message, onOpen = { url -> uriHandler.openUri(url) }, onMerge = onMerge)
                }
            }
            if (!showSwarm) HorizontalDivider()
            if (!showSwarm) Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 12.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                profiles.forEach { entry ->
                    FilterChip(
                        selected = entry == profile,
                        onClick = { onProfileChange(entry) },
                        label = { Text(entry, style = MaterialTheme.typography.labelSmall) },
                        enabled = !busy,
                    )
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
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 320.dp)
                .background(container, RoundedCornerShape(14.dp))
                .padding(horizontal = 12.dp, vertical = 10.dp),
        ) {
            Text(text = message.text, color = contentColor, style = MaterialTheme.typography.bodyMedium)
            if (message.url != null) {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "Öffnen",
                    color = contentColor,
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.clickable { onOpen(message.url) },
                )
            }
            val prNumber = Regex("#(\\d+)").find(message.text)?.groupValues?.getOrNull(1)?.toIntOrNull()
            if (!isUser && prNumber != null && message.text.contains("Draft-PR")) {
                Spacer(Modifier.height(6.dp))
                OutlinedButton(onClick = { onMerge(prNumber) }) { Text("Jetzt mergen", style = MaterialTheme.typography.labelSmall) }
            }
            Spacer(Modifier.height(2.dp))
            Text(
                text = message.time,
                color = contentColor.copy(alpha = 0.6f),
                style = MaterialTheme.typography.labelSmall,
                fontFamily = FontFamily.Monospace,
            )
        }
    }
}
