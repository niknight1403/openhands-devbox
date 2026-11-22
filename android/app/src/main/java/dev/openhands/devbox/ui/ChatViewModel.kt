package dev.openhands.devbox.ui

import android.app.Application
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dev.openhands.devbox.data.AutonomyEngine
import dev.openhands.devbox.data.GitHubApi
import dev.openhands.devbox.data.Projects
import dev.openhands.devbox.data.ProjectAnalysis
import dev.openhands.devbox.data.Settings
import dev.openhands.devbox.data.SettingsStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
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

    /** Anzeigenamen der mitgegebenen Dateien, Fotos und Videos. */
    val anhaengsel = mutableStateListOf<String>()
    private val anhaengselDaten = linkedMapOf<String, ByteArray>()

    var busy by mutableStateOf(false)
        private set

    var statusText by mutableStateOf("Bereit")
        private set

    var runUrl by mutableStateOf<String?>(null)
        private set

    var connectionCheck by mutableStateOf<String?>(null)
        private set

    var projectMemory by mutableStateOf("")
        private set

    var projectMemoryStatus by mutableStateOf("Noch nicht geladen")
        private set


    private val maxAnhangBytes = 20 * 1024 * 1024
    private val maxAnhaengsel = 5

    private class AttachmentTooLargeException : Exception()

    private var activeJob: Job? = null
    private var pendingAnalysisTarget: String? = null
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
        val previousProject = settings.project
        val previousTarget = Projects.findBySlug(settings.project)?.targetShort ?: settings.targetRepo
        val nextTarget = Projects.findBySlug(next.project)?.targetShort ?: next.targetRepo
        store.save(next)
        settings = next
        val projekt = Projects.findBySlug(next.project)
        push(
            false,
            if (projekt != null) {
                "Einstellungen gespeichert. Projekt: ${projekt.label}. Ziel: ${projekt.targetShort}."
            } else {
                "Einstellungen gespeichert. Zielprojekt: ${next.targetRepo}."
            },
        )
        if (previousTarget != nextTarget || previousProject != next.project) {
            if (busy) {
                pendingAnalysisTarget = nextTarget
                push(false, "Projekt gewählt. Die Analyse startet nach dem laufenden Auftrag.")
            } else if (next.isValid()) {
                sendTask(ProjectAnalysis.task, analysis = true)
            } else {
                push(false, "Projekt gewählt. Automatische Analyse benötigt gültige GitHub-Einstellungen.", isError = true)
            }
        }
    }

    /** Lädt das Projektgedächtnis aus dem Steuer-Repository, in dem der Workflow es fortschreibt. */
    fun loadProjectMemory() {
        val slug = settings.project
        if (slug.isBlank()) {
            projectMemory = ""
            projectMemoryStatus = "Bitte zuerst ein Projekt auswählen."
            return
        }
        if (settings.token.isBlank()) {
            projectMemory = ""
            projectMemoryStatus = "GitHub-Token fehlt. Bitte in den Einstellungen hinterlegen."
            return
        }
        projectMemoryStatus = "Projektgedächtnis wird geladen ..."
        viewModelScope.launch {
            try {
                val repository = "${settings.controlOwner}/${settings.controlRepo}"
                val path = "projects/$slug/GEDAEHNTNIS.md"
                projectMemory = GitHubApi { settings.token }.readRepositoryFile(repository, path)
                projectMemoryStatus = "Aus $repository geladen · main"
            } catch (error: GitHubApi.ApiException) {
                projectMemory = ""
                projectMemoryStatus = if (error.code == 404) {
                    "Für dieses Projekt ist noch kein Gedächtnis gespeichert."
                } else {
                    "Laden fehlgeschlagen: ${error.message}"
                }
            } catch (error: Exception) {
                projectMemory = ""
                projectMemoryStatus = "Laden fehlgeschlagen: ${error.message ?: "unbekannter Fehler"}"
            }
        }
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

    fun sendTask(text: String, analysis: Boolean = false) {
        val task = text.trim()
        if (task.isEmpty() || busy) return
        if (!settings.isValid()) {
            push(false, "Bitte zuerst die Einstellungen ausfüllen: Token und Zielprojekt.", isError = true)
            return
        }
        push(true, if (analysis) "Projektanalyse starten: Befunde prüfen, Verbesserungen priorisieren und eine kleine Optimierung umsetzen." else task)
        busy = true
        lastFailed = false
        statusText = "Auftrag wird übergeben"

        val requestSettings = if (analysis) {
            settings.copy(profile = "superagent", autoMerge = false, autoIterate = false)
        } else {
            settings
        }
        val iterations = if (requestSettings.autoIterate) requestSettings.maxIterations.coerceIn(1, 3) else 1

        activeJob = viewModelScope.launch {
            try {
                val dateien = if (analysis) emptyList() else ladeAnhaengselHoch()
                for (iteration in 1..iterations) {
                    val prompt = if (iteration == 1) {
                        task
                    } else {
                        "Folgedurchlauf $iteration für ${settings.targetRepo}: Prüfe das Ergebnis des vorherigen Laufs gegen die ursprüngliche Aufgabe \"$task\". " +
                            "Schließe bestätigte Lücken, behebe Fehler und vervollständige fehlende Bedien- oder Fehlerzustände. Halte die Änderungen klein und prüfbar."
                    }
                    engine.execute(AutonomyEngine.Request(requestSettings, prompt, iteration, iterations, assets = dateien)) { event ->
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
                val pending = pendingAnalysisTarget
                pendingAnalysisTarget = null
                if (pending != null && settings.isValid()) {
                    sendTask(ProjectAnalysis.task, analysis = true)
                }
            }
        }
    }

    fun addAttachment(uri: Uri) {
        if (anhaengsel.size >= maxAnhaengsel) {
            push(false, "Höchstens $maxAnhaengsel Dateien je Auftrag.", isError = true)
            return
        }
        viewModelScope.launch {
            val kontext = getApplication<Application>()
            try {
                val name = withContext(Dispatchers.IO) {
                    kontext.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                        if (cursor.moveToFirst()) {
                            val spalte = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                            if (spalte >= 0) cursor.getString(spalte) else null
                        } else {
                            null
                        }
                    }
                } ?: uri.lastPathSegment ?: "datei"
                val bytes = withContext(Dispatchers.IO) {
                    kontext.contentResolver.openInputStream(uri)?.use { input ->
                        val output = ByteArrayOutputStream()
                        val buffer = ByteArray(8192)
                        var total = 0
                        while (true) {
                            val gelesen = input.read(buffer)
                            if (gelesen < 0) break
                            total += gelesen
                            if (total > maxAnhangBytes) throw AttachmentTooLargeException()
                            output.write(buffer, 0, gelesen)
                        }
                        output.toByteArray()
                    }
                }
                when {
                    bytes == null || bytes.isEmpty() ->
                        push(false, "Die Datei konnte nicht gelesen werden.", isError = true)
                    else -> {
                        val basis = name.substringAfterLast('/').ifBlank { "datei" }
                        val punkt = basis.lastIndexOf('.')
                        val stamm = if (punkt > 0) basis.substring(0, punkt) else basis
                        val endung = if (punkt > 0) basis.substring(punkt) else ""
                        var anzeige = basis
                        var index = 2
                        while (anhaengselDaten.containsKey(anzeige)) {
                            anzeige = "$stamm ($index)$endung"
                            index++
                        }
                        anhaengselDaten[anzeige] = bytes
                        anhaengsel.add(anzeige)
                        push(false, "Angehängt: $anzeige (${bytes.size / 1024} KB). Wird beim Senden ins Zielprojekt geladen.")
                    }
                }
            } catch (error: AttachmentTooLargeException) {
                push(false, "Datei zu groß. Erlaubt sind ${maxAnhangBytes / (1024 * 1024)} MB.", isError = true)
            } catch (error: Exception) {
                push(false, "Datei nicht übernommen: ${error.message ?: error::class.simpleName}", isError = true)
            }
        }
    }

    fun removeAttachment(name: String) {
        anhaengselDaten.remove(name)
        anhaengsel.remove(name)
    }

    /** Laedt die Anhaengsel ins Zielprojekt und gibt die Rohadressen zurueck. */
    private suspend fun ladeAnhaengselHoch(): List<String> {
        if (anhaengsel.isEmpty()) return emptyList()
        val projekt = Projects.findBySlug(settings.project)
        val repo = projekt?.let { "${settings.controlOwner}/${it.targetShort}" } ?: settings.targetRepo
        val api = GitHubApi { settings.token }
        val adressen = mutableListOf<String>()
        val erfolgreich = mutableListOf<String>()
        val stempel = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
        for (name in anhaengsel.toList()) {
            val bytes = anhaengselDaten[name] ?: continue
            val sicher = name.replace(Regex("[^A-Za-z0-9._-]"), "-").take(60).ifBlank { "datei" }
            val pfad = "docs/openhands/assets/$stempel-$sicher"
            try {
                statusText = "Datei wird hochgeladen: $name"
                val adresse = api.uploadAsset(repo, pfad, bytes, "anhang: $sicher")
                adressen.add(adresse)
                erfolgreich.add(name)
                push(false, "Datei abgelegt: $adresse")
            } catch (error: GitHubApi.ApiException) {
                push(false, "Datei $name nicht hochgeladen: ${error.message}", isError = true)
            }
        }
        // Nur erfolgreich hochgeladene Dateien entfernen. Fehlgeschlagene
        // Anhaenge bleiben fuer einen erneuten Versuch erhalten.
        erfolgreich.forEach { name ->
            anhaengselDaten.remove(name)
            anhaengsel.remove(name)
        }
        return adressen
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
