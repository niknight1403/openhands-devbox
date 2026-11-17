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
    var screen by remember { mutableStateOf(AppScreen.Chat) }

    when (screen) {
        AppScreen.Settings -> SettingsScreen(
            settings = viewModel.settings,
            connectionCheck = viewModel.connectionCheck,
            onSave = { updated ->
                viewModel.updateSettings(updated)
                screen = AppScreen.Chat
            },
            onTest = viewModel::testConnection,
            onBack = { screen = AppScreen.Chat },
        )
        AppScreen.Projects -> ProjectHubScreen(
            selectedProject = viewModel.settings.project,
            model = viewModel.settings.model,
            onSelectProject = { slug -> viewModel.updateSettings(viewModel.settings.copy(project = slug)) },
            onOpenLiveApp = { screen = AppScreen.LiveApp },
            onBack = { screen = AppScreen.Chat },
        )
        AppScreen.LiveApp -> LivePreviewScreen(
            url = viewModel.settings.livePreviewUrl,
            projectLabel = viewModel.settings.project.ifBlank { "Projekt" },
            onBack = { screen = AppScreen.Chat },
        )
        AppScreen.Chat -> ChatScreen(
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
            onOpenSettings = { screen = AppScreen.Settings },
            onOpenProjects = { screen = AppScreen.Projects },
            onOpenLiveApp = { screen = AppScreen.LiveApp },
            onMerge = viewModel::mergePr,
        )
    }
}

private enum class AppScreen { Chat, Projects, LiveApp, Settings }
