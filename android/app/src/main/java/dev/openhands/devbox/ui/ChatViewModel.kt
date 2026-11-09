package dev.openhands.devbox.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.openhands.devbox.data.AutonomyEngine
import dev.openhands.devbox.data.GitHubApi
import dev.openhands.devbox.data.Settings
import dev.openhands.devbox.data.SettingsStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class ChatMessage(
    val id: Long,
    val fromUser: Boolean,
    val text: String,
    val time: String,
    val url: String? = null,
    val isError: Boolean = false,
)

class ChatViewModel(application: Application) : AndroidViewModel(application) {

    private val store = SettingsStore(application)
    private val engine = AutonomyEngine(GitHubApi { settings.token })

    var settings by mutableStateOf(store.load())
        private set

    val messages = mutableStateListOf<ChatMessage>()

    var busy by mutableStateOf(false)
        private set

    var statusText by mutableStateOf("Bereit")
        private set

    var runUrl by mutableStateOf<String?>(null)
        private set

    var connectionCheck by mutableStateOf<String?>(null)
        private set

    private var activeJob: Job? = null
    private var counter = 0L
    private var lastFailed = false

    init {
        if (!settings.isValid()) {
            push(
                fromUser = false,
                text = "Willkommen. Hinterlegen Sie in den Einstellungen einen GitHub-Token mit Actions- und Pull-Request-Rechten. Danach genügt eine Chat-Eingabe, um einen vollständigen Entwicklungsdurchlauf zu starten.",
            )
        } else {
            push(false, "Bereit. Beschreiben Sie im Chat, was gebaut oder repariert werden soll.")
        }
    }

    fun updateSettings(next: Settings) {
        store.save(next)
        settings = next
        push(false, "Einstellungen gespeichert. Zielprojekt: ${next.targetRepo}.")
    }

    fun testConnection() {
        connectionCheck = "Prüfe Token ..."
        viewModelScope.launch {
            connectionCheck = try {
                val login = GitHubApi { settings.token }.currentUser()
                "Token gültig, angemeldet als $login."
            } catch (error: GitHubApi.ApiException) {
                "Prüfung fehlgeschlagen: ${error.message}"
            } catch (error: Exception) {
                "Prüfung fehlgeschlagen: ${error.message ?: "unbekannter Fehler"}"
            }
        }
    }

    fun sendTask(text: String) {
        val task = text.trim()
        if (task.isEmpty() || busy) return
        if (!settings.isValid()) {
            push(false, "Bitte zuerst die Einstellungen ausfüllen: Token und Zielprojekt.", isError = true)
            return
        }
        push(true, task)
        busy = true
        lastFailed = false
        statusText = "Auftrag wird übergeben"

        val iterations = if (settings.autoIterate) settings.maxIterations.coerceIn(1, 3) else 1

        activeJob = viewModelScope.launch {
            try {
                for (iteration in 1..iterations) {
                    val prompt = if (iteration == 1) {
                        task
                    } else {
                        "Folgedurchlauf $iteration für ${settings.targetRepo}: Prüfe das Ergebnis des vorherigen Laufs gegen die ursprüngliche Aufgabe \"$task\". " +
                            "Schließe bestätigte Lücken, behebe Fehler und vervollständige fehlende Bedien- oder Fehlerzustände. Halte die Änderungen klein und prüfbar."
                    }
                    engine.execute(AutonomyEngine.Request(settings, prompt, iteration, iterations)) { event ->
                        handle(event)
                    }
                    if (lastFailed) break
                }
                if (!lastFailed) push(false, "Durchlauf abgeschlossen.")
            } catch (cancelled: CancellationException) {
                push(false, "Gestoppt. Ein bereits gestarteter Lauf in GitHub Actions läuft weiter.")
            } catch (error: Exception) {
                push(false, "Fehler: ${error.message ?: error::class.simpleName}", isError = true)
            } finally {
                busy = false
                statusText = "Bereit"
                activeJob = null
            }
        }
    }

    fun stop() {
        activeJob?.let {
            runUrl?.let { url -> push(false, "Abbruch angefordert. Lauf: $url") }
            it.cancel()
        }
    }

    fun mergePr(number: Int) {
        viewModelScope.launch {
            try {
                statusText = "Merge PR #$number"
                val result = GitHubApi { settings.token }.mergePullRequest(settings.targetRepo, number)
                push(false, "PR #$number: $result")
            } catch (error: GitHubApi.ApiException) {
                push(false, "Merge fehlgeschlagen: ${error.message}", isError = true)
            } finally {
                statusText = "Bereit"
            }
        }
    }

    private fun handle(event: AutonomyEngine.Event) {
        when (event) {
            is AutonomyEngine.Event.Info -> push(false, event.text)
            is AutonomyEngine.Event.StepUpdate -> {
                statusText = event.step
                event.runUrl?.let { runUrl = it }
                push(false, "Schritt: ${event.step} (${translateState(event.state)})")
            }
            is AutonomyEngine.Event.PullFound -> {
                statusText = "PR #${event.number} gefunden"
                push(
                    false,
                    "Draft-PR #${event.number} erstellt${event.changedFiles?.let { " mit $it geänderten Dateien" }.orEmpty()}.",
                    url = event.url,
                )
            }
            is AutonomyEngine.Event.Merged -> push(false, event.text)
            is AutonomyEngine.Event.Failure -> {
                lastFailed = true
                statusText = "Abgebrochen"
                event.runUrl?.let { runUrl = it }
                push(false, event.text, url = event.runUrl, isError = true)
            }
            AutonomyEngine.Event.Finished -> statusText = "Bereit"
        }
    }

    private fun translateState(state: String): String = when (state) {
        "success" -> "erfolgreich"
        "in_progress" -> "läuft"
        "queued" -> "wartet"
        "failure" -> "fehlgeschlagen"
        "skipped" -> "übersprungen"
        else -> state
    }

    private fun push(fromUser: Boolean, text: String, url: String? = null, isError: Boolean = false) {
        val time = SimpleDateFormat("HH:mm", Locale.GERMANY).format(Date())
        messages.add(ChatMessage(id = counter++, fromUser = fromUser, text = text, time = time, url = url, isError = isError))
    }
}
