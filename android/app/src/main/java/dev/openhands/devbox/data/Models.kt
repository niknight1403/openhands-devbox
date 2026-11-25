package dev.openhands.devbox.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class WorkflowRun(
    val id: Long = 0,
    val name: String? = null,
    val status: String? = null,
    val conclusion: String? = null,
    @SerialName("html_url") val htmlUrl: String? = null,
    @SerialName("head_branch") val headBranch: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("run_started_at") val runStartedAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("workflow_id") val workflowId: Long? = null,
)

@Serializable
data class WorkflowRunsResponse(
    @SerialName("total_count") val totalCount: Int = 0,
    @SerialName("workflow_runs") val workflowRuns: List<WorkflowRun> = emptyList(),
)

@Serializable
data class Step(
    val name: String = "",
    val status: String? = null,
    val conclusion: String? = null,
    val number: Int = 0,
)

@Serializable
data class Job(
    val id: Long = 0,
    val name: String? = null,
    val status: String? = null,
    val conclusion: String? = null,
    val steps: List<Step> = emptyList(),
)

@Serializable
data class JobsResponse(val jobs: List<Job> = emptyList())

@Serializable
data class AutopilotStatus(
    @SerialName("generated_at") val generatedAt: String? = null,
    val mode: String? = null,
    val packs: List<AutopilotPack> = emptyList(),
    val routes: List<AutopilotRoute> = emptyList(),
    val best: AutopilotRoute? = null,
    @SerialName("tool_probe") val toolProbe: Boolean? = null,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class AutopilotRoute(
    val provider: String? = null,
    val model: String? = null,
    @SerialName("chat_ok") val chatOk: Boolean = false,
    @SerialName("tools_ok") val toolsOk: Boolean = false,
    @SerialName("latency_ms") val latencyMs: Int? = null,
)

@Serializable
data class AutopilotPack(
    val name: String = "",
    val ok: Boolean = false,
    val reason: String? = null,
    val installed: Int = 0,
    val skills: List<AutopilotSkill> = emptyList(),
)

@Serializable
data class AutopilotSkill(
    val name: String = "",
    val ok: Boolean = false,
    val reason: String? = null,
)

@Serializable
data class PullHead(val ref: String = "", val sha: String? = null)

@Serializable
data class PullRequest(
    val number: Int = 0,
    val title: String? = null,
    val draft: Boolean = false,
    val state: String? = null,
    @SerialName("html_url") val htmlUrl: String? = null,
    val mergeable: Boolean? = null,
    @SerialName("mergeable_state") val mergeableState: String? = null,
    @SerialName("changed_files") val changedFiles: Int? = null,
    val head: PullHead? = null,
)

@Serializable
data class GitHubUser(val login: String = "")

@Serializable
data class ContentUpload(
    val path: String? = null,
    @SerialName("download_url") val downloadUrl: String? = null,
)
