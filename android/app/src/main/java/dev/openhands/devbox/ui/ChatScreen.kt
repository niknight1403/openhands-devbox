package dev.openhands.devbox.ui

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
    onStop: () -> Unit,
    onOpenSettings: () -> Unit,
    onMerge: (Int) -> Unit,
) {
    var draft by remember { mutableStateOf("") }
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
                        Text("OpenHands Devbox", fontWeight = FontWeight.SemiBold)
                        Text(
                            text = statusText,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    if (runUrl != null) {
                        TextButton(onClick = { runUrl.let { uriHandler.openUri(it) } }) { Text("Lauf") }
                    }
                    TextButton(onClick = onOpenSettings) { Text("Einstellungen") }
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
                Spacer(Modifier.height(6.dp))
                Row(verticalAlignment = Alignment.Bottom) {
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
            }
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxWidth()) {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxWidth().weight(1f),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(messages, key = { it.id }) { message ->
                    MessageBubble(message, onOpen = { url -> uriHandler.openUri(url) }, onMerge = onMerge)
                }
            }
            HorizontalDivider()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
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
