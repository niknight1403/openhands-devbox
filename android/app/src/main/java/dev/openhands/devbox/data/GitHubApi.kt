package dev.openhands.devbox.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.TimeUnit

/**
 * Schmaler GitHub-REST-Client. Der Token wird nur im Authorization-Header verwendet
 * und taucht in keiner Meldung, keinem Log und keiner Ausnahme auf.
 */
class GitHubApi(private val tokenProvider: () -> String) {

    class ApiException(val code: Int, override val message: String) : Exception(message)

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .callTimeout(60, TimeUnit.SECONDS)
        .build()

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    private fun request(path: String, method: String = "GET", body: JsonObject? = null): Request {
        val token = tokenProvider()
        if (token.isBlank()) throw ApiException(401, "Kein GitHub-Token hinterlegt.")
        val builder = Request.Builder()
            .url("https://api.github.com$path")
            .header("Authorization", "Bearer $token")
            .header("Accept", "application/vnd.github+json")
            .header("X-GitHub-Api-Version", "2022-11-28")
        val payload = body?.let { json.encodeToString(JsonObject.serializer(), it) }
        val requestBody = payload?.toRequestBody(jsonMedia)
        when (method) {
            "GET" -> builder.get()
            "POST" -> builder.post(requestBody ?: "".toRequestBody(jsonMedia))
            "PUT" -> builder.put(requestBody ?: "".toRequestBody(jsonMedia))
            "PATCH" -> builder.patch(requestBody ?: "".toRequestBody(jsonMedia))
            else -> throw ApiException(400, "Nicht unterstützte Methode $method")
        }
        return builder.build()
    }

    private suspend fun call(request: Request): String = withContext(Dispatchers.IO) {
        client.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw ApiException(response.code, describeError(response.code, text))
            }
            text
        }
    }

    private fun describeError(code: Int, body: String): String {
        val message = runCatching {
            val element = json.parseToJsonElement(body)
            (element as? JsonObject)?.get("message")?.toString()?.trim('"').orEmpty()
        }.getOrDefault("")
        val hint = when (code) {
            401 -> "Token ungültig oder abgelaufen."
            403 -> "Keine Berechtigung. Benötigt wird ein Fine-grained Token mit Actions- und Pull-Request-Rechten."
            404 -> "Repository oder Workflow nicht gefunden. Prüfen Sie Owner, Repo und Workflow-Dateinamen."
            422 -> "GitHub hat die Anfrage abgelehnt (Eingaben oder Merge-Bedingungen)."
            else -> ""
        }
        return buildString {
            append("HTTP ").append(code)
            if (message.isNotBlank()) append(": ").append(message)
            if (hint.isNotBlank()) append(" – ").append(hint)
        }
    }

    suspend fun currentUser(): String =
        json.decodeFromString(GitHubUser.serializer(), call(request("/user"))).login

    /** Startet den OpenHands-Workflow. GitHub antwortet mit 204 ohne Run-ID. */
    suspend fun dispatch(
        controlRepo: String,
        workflowFile: String,
        ref: String,
        inputs: Map<String, String>,
    ) {
        val body = buildJsonObject {
            put("ref", ref)
            putJsonObject("inputs") { inputs.forEach { (key, value) -> put(key, value) } }
        }
        call(request("/repos/$controlRepo/actions/workflows/$workflowFile/dispatches", "POST", body))
    }

    /**
     * Legt eine Datei im Zielprojekt ab (Inhalts-API, Zweig main) und gibt die
     * Rohadresse zurueck. Der Workflow laedt sie von dort als Auftragsdatei.
     */
    suspend fun uploadAsset(targetRepo: String, path: String, bytes: ByteArray, message: String): String {
        val body = buildJsonObject {
            put("message", message)
            put("content", android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP))
            put("branch", "main")
        }
        val antwort = call(request("/repos/$targetRepo/contents/$path", "PUT", body))
        val daten = json.decodeFromString(ContentUpload.serializer(), antwort)
        return daten.downloadUrl ?: "https://raw.githubusercontent.com/$targetRepo/main/$path"
    }

    /** Sucht den Run, der nach dem Absenden entstanden ist. */
    suspend fun findRunAfter(controlRepo: String, workflowFile: String, dispatchedAtMillis: Long): WorkflowRun? {
        val runs = json.decodeFromString(
            WorkflowRunsResponse.serializer(),
            call(request("/repos/$controlRepo/actions/workflows/$workflowFile/runs?event=workflow_dispatch&per_page=10")),
        ).workflowRuns
        // Never attach the UI to an unrelated older run when the dispatch
        // has not appeared yet. If several runs start in the same window,
        // prefer the newest candidate instead of the earliest stale one.
        return runs
            .mapNotNull { run -> parseIso(run.createdAt)?.let { run to it } }
            .filter { (_, created) -> created >= dispatchedAtMillis - 15_000 }
            .maxByOrNull { (_, created) -> created }
            ?.first
    }

    suspend fun run(controlRepo: String, runId: Long): WorkflowRun =
        json.decodeFromString(WorkflowRun.serializer(), call(request("/repos/$controlRepo/actions/runs/$runId")))

    suspend fun runJobs(controlRepo: String, runId: Long): List<Job> =
        json.decodeFromString(
            JobsResponse.serializer(),
            call(request("/repos/$controlRepo/actions/runs/$runId/jobs?per_page=5")),
        ).jobs

    suspend fun cancelRun(controlRepo: String, runId: Long) {
        runCatching { call(request("/repos/$controlRepo/actions/runs/$runId/force-cancel", "POST")) }
    }

    suspend fun findPullRequest(targetRepo: String, branch: String): PullRequest? {
        val pulls = json.decodeFromString(
            ListSerializerHolder.pulls,
            call(request("/repos/$targetRepo/pulls?state=all&sort=created&direction=desc&per_page=30")),
        )
        return pulls.firstOrNull { it.head?.ref == branch }
    }

    suspend fun pullRequest(targetRepo: String, number: Int): PullRequest =
        json.decodeFromString(PullRequest.serializer(), call(request("/repos/$targetRepo/pulls/$number")))

    suspend fun markReadyForReview(targetRepo: String, number: Int) {
        val body = buildJsonObject { put("draft", false) }
        runCatching { call(request("/repos/$targetRepo/pulls/$number", "PATCH", body)) }
    }

    suspend fun mergePullRequest(targetRepo: String, number: Int, method: String = "squash"): String {
        val body = buildJsonObject { put("merge_method", method) }
        val response = call(request("/repos/$targetRepo/pulls/$number/merge", "PUT", body))
        val merged = runCatching {
            val element = json.parseToJsonElement(response) as JsonObject
            element["merged"]?.toString()?.toBoolean() ?: false
        }.getOrDefault(false)
        return if (merged) "squash-Merge ausgeführt" else "GitHub hat den Merge nicht bestätigt"
    }

    private fun parseIso(value: String?): Long? {
        if (value.isNullOrBlank()) return null
        return runCatching {
            val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
            format.timeZone = TimeZone.getTimeZone("UTC")
            format.parse(value)?.time
        }.getOrNull()
    }

    companion object {
        fun currentIsoUtc(): String {
            val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
            format.timeZone = TimeZone.getTimeZone("UTC")
            return format.format(Date())
        }
    }
}

private object ListSerializerHolder {
    val pulls = kotlinx.serialization.builtins.ListSerializer(PullRequest.serializer())
}
