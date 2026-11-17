package dev.openhands.devbox.ui

import android.annotation.SuppressLint
import android.net.Uri
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.unit.dp

@SuppressLint("SetJavaScriptEnabled")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LivePreviewScreen(
    url: String,
    projectLabel: String,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val validUrl = remember(url) {
        runCatching {
            val uri = Uri.parse(url.trim())
            uri.scheme in setOf("http", "https") && !uri.host.isNullOrBlank()
        }.getOrDefault(false)
    }
    val webView = remember(url) {
        WebView(context).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.setSupportZoom(true)
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    val target = request.url
                    return target.scheme !in setOf("http", "https")
                }
            }
            if (validUrl) loadUrl(url.trim())
        }
    }
    DisposableEffect(webView) {
        onDispose { webView.stopLoading(); webView.destroy() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Live App · $projectLabel") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Zurück") } },
                actions = {
                    TextButton(onClick = { if (validUrl) webView.reload() }, enabled = validUrl) { Text("Aktualisieren") }
                },
            )
        },
    ) { padding ->
        if (validUrl) {
            AndroidView(
                factory = { webView },
                modifier = Modifier.fillMaxSize().padding(padding),
            )
        } else {
            Column(
                modifier = Modifier.fillMaxSize().padding(padding).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text("Keine Live-App konfiguriert", style = MaterialTheme.typography.headlineSmall)
                Text(
                    "Hinterlege in den Einstellungen eine vollständige http://- oder https://-Adresse. Die Vorschau bleibt leer, solange keine gültige URL gesetzt ist.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Zu den Einstellungen") }
                if (url.isNotBlank()) Text("Die aktuelle Adresse ist ungültig oder nicht unterstützt.", color = MaterialTheme.colorScheme.error)
            }
        }
    }
}
