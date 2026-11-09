package dev.openhands.devbox.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Steuerdaten der App. Der Token wird verschlüsselt gespeichert und nie geloggt.
 */
data class Settings(
    val token: String = "",
    val controlOwner: String = "niknight1403",
    val controlRepo: String = "openhands-devbox",
    val workflowFile: String = "openhands-task.yml",
    val project: String = "",
    val targetRepo: String = "niknight1403/Agenten-Villa",
    val profile: String = "superagent",
    val model: String = "",
    val autoMerge: Boolean = false,
    val autoIterate: Boolean = false,
    val maxIterations: Int = 2,
) {
    val controlRepoFullName: String get() = "$controlOwner/$controlRepo"

    fun isValid(): Boolean =
        token.isNotBlank() &&
            GITHUB_OWNER.matches(controlOwner) &&
            GITHUB_REPO.matches(controlRepo) &&
            validWorkflowPath(workflowFile) &&
            validRepositoryFullName(targetRepo)

    private fun validRepositoryFullName(value: String): Boolean {
        val parts = value.split("/")
        return parts.size == 2 && GITHUB_OWNER.matches(parts[0]) && GITHUB_REPO.matches(parts[1])
    }

    private fun validWorkflowPath(value: String): Boolean {
        if (!value.endsWith(".yml", ignoreCase = true) && !value.endsWith(".yaml", ignoreCase = true)) {
            return false
        }
        val parts = value.split("/")
        return parts.isNotEmpty() && parts.all { part ->
            part.isNotBlank() && part != "." && part != ".." && WORKFLOW_SEGMENT.matches(part)
        }
    }

    private companion object {
        val GITHUB_OWNER = Regex("^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
        val GITHUB_REPO = Regex("^[A-Za-z0-9._-]{1,100}$")
        val WORKFLOW_SEGMENT = Regex("^[A-Za-z0-9._-]+$")
    }
}

class SettingsStore(context: Context) {

    private val prefs: SharedPreferences = runCatching {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "openhands_devbox_settings",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }.getOrElse {
        context.getSharedPreferences("openhands_devbox_settings_fallback", Context.MODE_PRIVATE)
    }

    fun load(): Settings = Settings(
        token = prefs.getString(KEY_TOKEN, "") ?: "",
        controlOwner = prefs.getString(KEY_CONTROL_OWNER, "niknight1403") ?: "niknight1403",
        controlRepo = prefs.getString(KEY_CONTROL_REPO, "openhands-devbox") ?: "openhands-devbox",
        workflowFile = prefs.getString(KEY_WORKFLOW, "openhands-task.yml") ?: "openhands-task.yml",
        project = prefs.getString(KEY_PROJECT, "") ?: "",
        targetRepo = prefs.getString(KEY_TARGET, "niknight1403/Agenten-Villa") ?: "niknight1403/Agenten-Villa",
        profile = prefs.getString(KEY_PROFILE, "superagent") ?: "superagent",
        model = prefs.getString(KEY_MODEL, "") ?: "",
        autoMerge = prefs.getBoolean(KEY_AUTO_MERGE, false),
        autoIterate = prefs.getBoolean(KEY_AUTO_ITERATE, false),
        maxIterations = prefs.getInt(KEY_MAX_ITERATIONS, 2),
    )

    fun save(settings: Settings) {
        prefs.edit()
            .putString(KEY_TOKEN, settings.token)
            .putString(KEY_CONTROL_OWNER, settings.controlOwner)
            .putString(KEY_CONTROL_REPO, settings.controlRepo)
            .putString(KEY_WORKFLOW, settings.workflowFile)
            .putString(KEY_PROJECT, settings.project)
            .putString(KEY_TARGET, settings.targetRepo)
            .putString(KEY_PROFILE, settings.profile)
            .putString(KEY_MODEL, settings.model)
            .putBoolean(KEY_AUTO_MERGE, settings.autoMerge)
            .putBoolean(KEY_AUTO_ITERATE, settings.autoIterate)
            .putInt(KEY_MAX_ITERATIONS, settings.maxIterations.coerceIn(1, 3))
            .apply()
    }

    private companion object {
        const val KEY_TOKEN = "token"
        const val KEY_CONTROL_OWNER = "control_owner"
        const val KEY_CONTROL_REPO = "control_repo"
        const val KEY_WORKFLOW = "workflow_file"
        const val KEY_PROJECT = "project"
        const val KEY_TARGET = "target_repo"
        const val KEY_PROFILE = "profile"
        const val KEY_MODEL = "model"
        const val KEY_AUTO_MERGE = "auto_merge"
        const val KEY_AUTO_ITERATE = "auto_iterate"
        const val KEY_MAX_ITERATIONS = "max_iterations"
    }
}
