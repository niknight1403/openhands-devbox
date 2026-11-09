package dev.openhands.devbox.data

import kotlinx.coroutines.delay
import java.util.concurrent.atomic.AtomicInteger

/**
 * Führt einen Auftrag vollständig durch: Workflow starten, Lauf verfolgen,
 * Draft-PR finden, optional als bereit markieren und mergen, dann optional
 * einen Folgeauftrag starten.
 *
 * Der Agent selbst läuft in GitHub Actions; die App ist die Steuer- und
 * Kontrollfläche und zeigt ausschließlich echte Pipeline-Zustände an.
 */
class AutonomyEngine(private val api: GitHubApi) {

    sealed class Event {
        data class Info(val text: String) : Event()
        data class StepUpdate(val step: String, val state: String, val runUrl: String?) : Event()
        data class PullFound(val number: Int, val url: String, val changedFiles: Int?) : Event()
        data class Merged(val text: String) : Event()
        data class Failure(val text: String, val runUrl: String? = null) : Event()
        data object Finished : Event()
    }

    data class Request(
        val settings: Settings,
        val task: String,
        val iteration: Int,
        val iterations: Int,
        /** Rohadressen mitgegebener Dateien, Fotos und Videos. */
        val assets: List<String> = emptyList(),
    )

    private val pollMillis = 15_000L
    private val maxTicks = 320 // etwa 80 Minuten je Durchlauf

    suspend fun execute(request: Request, emit: suspend (Event) -> Unit) {
        val settings = request.settings
        val slug = System.currentTimeMillis().toString()
        val branch = "agent/app-$slug"

        emit(Event.Info("Auftrag angenommen. Durchlauf ${request.iteration} von ${request.iterations}."))
        val gewaehltesProjekt = Projects.findBySlug(settings.project)
        val targetRepo = gewaehltesProjekt?.let { "${settings.controlOwner}/${it.targetShort}" } ?: settings.targetRepo
        if (gewaehltesProjekt != null) {
            emit(
                Event.Info(
                    "Projekt: ${gewaehltesProjekt.label} (${gewaehltesProjekt.slug}). " +
                        "Ziel: ${gewaehltesProjekt.targetShort}. Profil: ${settings.profile}.",
                ),
            )
        } else {
            emit(Event.Info("Zielprojekt: ${settings.targetRepo}. Profil: ${settings.profile}."))
        }

        val inputs = buildMap {
            put("task", request.task)
            put("profile", settings.profile)
            put("model", settings.model)
            // Der Workflow akzeptiert nur freigegebene Kurznamen, die API braucht owner/repo.
            // Ein Projekt bestimmt sein Zielrepository selbst; der Kurzname kommt aus der Liste.
            put("target", gewaehltesProjekt?.targetShort ?: settings.targetRepo.substringAfterLast('/'))
            put("client_run", slug)
            if (gewaehltesProjekt != null) {
                put("project", gewaehltesProjekt.slug)
            }
            if (request.assets.isNotEmpty()) {
                put("assets", request.assets.joinToString("\n"))
            }
        }

        val dispatchedAt = System.currentTimeMillis()
        try {
            api.dispatch(settings.controlRepoFullName, settings.workflowFile, "main", inputs)
        } catch (error: GitHubApi.ApiException) {
            emit(Event.Failure("Start fehlgeschlagen: ${error.message}"))
            return
        }

        emit(Event.Info("Workflow gestartet. Ich warte auf den Lauf."))

        val run = awaitRun(settings, dispatchedAt) ?: run {
            emit(Event.Failure("Kein Lauf gefunden. Prüfen Sie, ob der Workflow workflow_dispatch erlaubt und die Eingaben akzeptiert."))
            return
        }

        emit(Event.Info("Lauf ${run.id} läuft. Branch: $branch. Die Agentenphasen dauern typischerweise 20 bis 60 Minuten."))

        val lastStep = AtomicInteger(-1)
        var tick = 0
        var conclusion: String? = null
        var runUrl: String? = run.htmlUrl

        while (tick < maxTicks) {
            delay(pollMillis)
            tick++
            val current = try {
                api.run(settings.controlRepoFullName, run.id)
            } catch (error: GitHubApi.ApiException) {
                emit(Event.Failure("Statusabfrage fehlgeschlagen: ${error.message}", runUrl))
                return
            }
            runUrl = current.htmlUrl ?: runUrl
            if (current.status != "completed") {
                reportStep(settings, run.id, lastStep, runUrl, emit)
                continue
            }
            conclusion = current.conclusion
            break
        }

        if (conclusion == null) {
            emit(Event.Failure("Zeitlimit erreicht. Der Lauf läuft weiter, die App verfolgt ihn nicht mehr.", runUrl))
            return
        }

        if (conclusion != "success") {
            emit(
                Event.Failure(
                    "Lauf mit Ergebnis '$conclusion' beendet. Die Action-Logs nennen den Grund; sensible Rohlogs bleiben dort.",
                    runUrl,
                ),
            )
            return
        }

        emit(Event.Info("Lauf erfolgreich beendet. Ich suche den Draft-PR."))
        val pull = awaitPull(targetRepo, branch)
        if (pull == null) {
            emit(Event.Info("Kein offener Pull Request gefunden. Möglicherweise waren keine Änderungen nötig."))
            return
        }

        emit(Event.PullFound(pull.number, pull.htmlUrl.orEmpty(), pull.changedFiles))

        if (!settings.autoMerge) {
            emit(Event.Info("Autonomer Merge ist aus. PR ${pull.number} wartet auf Ihre Prüfung."))
            return
        }

        api.markReadyForReview(targetRepo, pull.number)
        emit(Event.Info("PR ${pull.number} als bereit markiert. Prüfe Mergebarkeit."))

        val mergeable = awaitMergeable(targetRepo, pull.number)
        if (mergeable != true) {
            emit(Event.Failure("PR ${pull.number} ist noch nicht mergebar (Status: ${mergeable ?: "unbekannt"}). Bitte Checks im PR prüfen.", pull.htmlUrl))
            return
        }

        val result = try {
            api.mergePullRequest(targetRepo, pull.number)
        } catch (error: GitHubApi.ApiException) {
            emit(Event.Failure("Merge abgelehnt: ${error.message}", pull.htmlUrl))
            return
        }
        emit(Event.Merged("PR ${pull.number}: $result"))
    }

    private suspend fun awaitRun(settings: Settings, dispatchedAt: Long): WorkflowRun? {
        repeat(6) {
            delay(10_000)
            val run = runCatching {
                api.findRunAfter(settings.controlRepoFullName, settings.workflowFile, dispatchedAt)
            }.getOrNull()
            if (run != null) return run
        }
        return null
    }

    private suspend fun awaitPull(targetRepo: String, branch: String): PullRequest? {
        repeat(8) {
            val pull = runCatching { api.findPullRequest(targetRepo, branch) }.getOrNull()
            if (pull != null) return pull
            delay(7_500)
        }
        return null
    }

    private suspend fun awaitMergeable(targetRepo: String, number: Int): Boolean? {
        repeat(8) {
            val pull = runCatching { api.pullRequest(targetRepo, number) }.getOrNull()
            if (pull?.mergeable != null) return pull.mergeable
            delay(7_500)
        }
        return null
    }

    private suspend fun reportStep(
        settings: Settings,
        runId: Long,
        lastIndex: AtomicInteger,
        runUrl: String?,
        emit: suspend (Event) -> Unit,
    ) {
        val jobs = runCatching { api.runJobs(settings.controlRepoFullName, runId) }.getOrNull() ?: return
        val step = jobs.asSequence()
            .flatMap { it.steps.asSequence() }
            .lastOrNull { it.status == "in_progress" }
            ?: jobs.asSequence().flatMap { it.steps.asSequence() }.lastOrNull { it.conclusion == "success" }
            ?: return
        if (step.number == lastIndex.get()) return
        lastIndex.set(step.number)
        emit(Event.StepUpdate(step.name, step.conclusion ?: step.status ?: "läuft", runUrl))
    }
}
