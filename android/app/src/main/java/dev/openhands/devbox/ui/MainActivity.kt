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
    var screen by remember { mutableStateOf(AppScreen.Dashboard) }

    when (screen) {
        AppScreen.Dashboard -> DashboardScreen(
            busy = viewModel.busy,
            statusText = viewModel.statusText,
            selectedProject = viewModel.settings.project,
            model = viewModel.settings.model,
            profile = viewModel.settings.profile,
            onOpenChat = { screen = AppScreen.Chat },
            onOpenProjects = { screen = AppScreen.Projects },
            onOpenSettings = { screen = AppScreen.Settings },
            onOpenLiveApp = { screen = AppScreen.LiveApp },
        )
        AppScreen.Settings -> SettingsScreen(
            settings = viewModel.settings,
            connectionCheck = viewModel.connectionCheck,
            onSave = { updated ->
                viewModel.updateSettings(updated)
                screen = AppScreen.Chat
            },
            onTest = viewModel::testConnection,
            onBack = { screen = AppScreen.Dashboard },
        )
        AppScreen.Projects -> ProjectHubScreen(
            selectedProject = viewModel.settings.project,
            model = viewModel.settings.model,
            onSelectProject = { slug ->
                viewModel.updateSettings(viewModel.settings.copy(project = slug))
                screen = AppScreen.Chat
            },
            onOpenLiveApp = { screen = AppScreen.LiveApp },
            projectMemory = viewModel.projectMemory,
            projectMemoryStatus = viewModel.projectMemoryStatus,
            onRefreshMemory = viewModel::loadProjectMemory,
            routeStatus = viewModel.routeStatus,
            routeDetails = viewModel.routeDetails,
            onRefreshRoutes = viewModel::loadRouteStatus,
            onBack = { screen = AppScreen.Dashboard },
        )
        AppScreen.LiveApp -> LivePreviewScreen(
            url = viewModel.settings.livePreviewUrl,
            projectLabel = viewModel.settings.project.ifBlank { "Projekt" },
            onBack = { screen = AppScreen.Dashboard },
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
            onSend = { text -> viewModel.sendTask(text) },
            onStop = viewModel::stop,
            onOpenSettings = { screen = AppScreen.Settings },
            onOpenProjects = { screen = AppScreen.Projects },
            onOpenLiveApp = { screen = AppScreen.LiveApp },
            onOpenDashboard = { screen = AppScreen.Dashboard },
            onMerge = viewModel::mergePr,
        )
    }
}

private enum class AppScreen { Dashboard, Chat, Projects, LiveApp, Settings }
