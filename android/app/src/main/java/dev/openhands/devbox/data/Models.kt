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
