package dev.openhands.devbox.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            OpenHandsTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DevboxApp()
                }
            }
        }
    }
}

@Composable
private fun DevboxApp(viewModel: ChatViewModel = viewModel()) {
    var showSettings by remember { mutableStateOf(false) }

    if (showSettings) {
        SettingsScreen(
            settings = viewModel.settings,
            connectionCheck = viewModel.connectionCheck,
            onSave = { updated ->
                viewModel.updateSettings(updated)
                showSettings = false
            },
            onTest = viewModel::testConnection,
            onBack = { showSettings = false },
        )
    } else {
        ChatScreen(
            messages = viewModel.messages,
            busy = viewModel.busy,
            statusText = viewModel.statusText,
            runUrl = viewModel.runUrl,
            profile = viewModel.settings.profile,
            autoMerge = viewModel.settings.autoMerge,
            onProfileChange = { viewModel.updateSettings(viewModel.settings.copy(profile = it)) },
            onAutoMergeChange = { viewModel.updateSettings(viewModel.settings.copy(autoMerge = it)) },
            attachments = viewModel.anhaengsel,
            onAttach = viewModel::addAttachment,
            onRemoveAttachment = viewModel::removeAttachment,
            onSend = viewModel::sendTask,
            onStop = viewModel::stop,
            onOpenSettings = { showSettings = true },
            onMerge = viewModel::mergePr,
        )
    }
}
