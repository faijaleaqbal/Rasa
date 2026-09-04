package com.alya.aiagent.local

import android.content.Context
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

enum class DownloadState {
    IDLE,
    DOWNLOADING,
    COMPLETED,
    FAILED,
    CANCELLED
}

data class DownloadProgress(
    val filename: String,
    val state: DownloadState,
    val downloadedBytes: Long = 0L,
    val totalBytes: Long = 0L,
    val percent: Int = 0,
    val speedMBps: Double = 0.0,
    val errorMessage: String? = null
)

/**
 * PocketPal-style Background Download Manager for GGUF models.
 */
class ModelDownloadManager private constructor(private val context: Context) {

    companion object {
        private const val TAG = "ModelDownloadManager"

        @Volatile
        private var INSTANCE: ModelDownloadManager? = null

        fun getInstance(context: Context): ModelDownloadManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: ModelDownloadManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    private val scope = CoroutineScope(Dispatchers.IO)
    private var downloadJob: Job? = null
    private val hfClient = HuggingFaceClient(context)

    private val _progressFlow = MutableStateFlow(
        DownloadProgress(filename = "", state = DownloadState.IDLE)
    )
    val progressFlow: StateFlow<DownloadProgress> = _progressFlow.asStateFlow()

    fun isDownloading(): Boolean = _progressFlow.value.state == DownloadState.DOWNLOADING

    fun startDownload(
        downloadUrl: String,
        targetFilename: String,
        onComplete: ((File) -> Unit)? = null
    ) {
        if (isDownloading()) {
            Log.w(TAG, "Download already in progress")
            return
        }

        downloadJob = scope.launch {
            val safeName = if (targetFilename.endsWith(".gguf", ignoreCase = true)) targetFilename else "$targetFilename.gguf"
            val targetDir = ModelManager.getInstance(context).getModelsDirectory()
            val finalFile = File(targetDir, safeName)
            val partFile = File(targetDir, "$safeName.part")

            _progressFlow.value = DownloadProgress(
                filename = safeName,
                state = DownloadState.DOWNLOADING,
                downloadedBytes = 0L,
                totalBytes = -1L,
                percent = 0,
                speedMBps = 0.0
            )

            var conn: HttpURLConnection? = null
            var input: InputStream? = null
            var output: FileOutputStream? = null

            try {
                var currentUrl = downloadUrl
                var redirects = 0
                while (redirects < 5) {
                    val url = URL(currentUrl)
                    conn = url.openConnection() as HttpURLConnection
                    conn.instanceFollowRedirects = true
                    conn.connectTimeout = 15000
                    conn.readTimeout = 30000
                    conn.setRequestProperty("User-Agent", "Alya-AI-PocketPal/2.0")

                    val token = hfClient.getHfToken()
                    if (!token.isNullOrBlank()) {
                        conn.setRequestProperty("Authorization", "Bearer $token")
                    }

                    val code = conn.responseCode
                    if (code == HttpURLConnection.HTTP_MOVED_TEMP || code == HttpURLConnection.HTTP_MOVED_PERM || code == 307 || code == 308) {
                        val newUrl = conn.getHeaderField("Location")
                        if (newUrl != null) {
                            currentUrl = newUrl
                            conn.disconnect()
                            redirects++
                            continue
                        }
                    }
                    break
                }

                val totalLength = conn?.contentLengthLong ?: -1L
                input = conn?.inputStream
                output = FileOutputStream(partFile, false)

                val buffer = ByteArray(64 * 1024)
                var bytesRead: Int
                var totalDownloaded = 0L
                var lastTime = SystemClock.elapsedRealtime()
                var lastBytes = 0L

                while (input?.read(buffer).also { bytesRead = it ?: -1 } != -1 && bytesRead > 0) {
                    output.write(buffer, 0, bytesRead)
                    totalDownloaded += bytesRead

                    val now = SystemClock.elapsedRealtime()
                    val timeDiff = now - lastTime
                    if (timeDiff >= 500) {
                        val bytesDiff = totalDownloaded - lastBytes
                        val speedMBps = if (timeDiff > 0) (bytesDiff / 1024.0 / 1024.0) / (timeDiff / 1000.0) else 0.0
                        val percent = if (totalLength > 0) ((totalDownloaded * 100) / totalLength).toInt() else 0

                        _progressFlow.value = DownloadProgress(
                            filename = safeName,
                            state = DownloadState.DOWNLOADING,
                            downloadedBytes = totalDownloaded,
                            totalBytes = totalLength,
                            percent = percent,
                            speedMBps = speedMBps
                        )

                        lastTime = now
                        lastBytes = totalDownloaded
                    }
                }
                output.flush()

                if (partFile.exists()) {
                    if (finalFile.exists()) finalFile.delete()
                    partFile.renameTo(finalFile)
                }

                _progressFlow.value = DownloadProgress(
                    filename = safeName,
                    state = DownloadState.COMPLETED,
                    downloadedBytes = totalDownloaded,
                    totalBytes = totalDownloaded,
                    percent = 100,
                    speedMBps = 0.0
                )

                withContext(Dispatchers.Main) {
                    onComplete?.invoke(finalFile)
                }
            } catch (e: Throwable) {
                Log.e(TAG, "Download failed: ${e.message}", e)
                if (partFile.exists()) partFile.delete()
                _progressFlow.value = DownloadProgress(
                    filename = safeName,
                    state = DownloadState.FAILED,
                    errorMessage = e.message ?: "Download failed"
                )
            } finally {
                try { input?.close() } catch (_: Throwable) {}
                try { output?.close() } catch (_: Throwable) {}
                try { conn?.disconnect() } catch (_: Throwable) {}
            }
        }
    }

    fun cancelDownload() {
        downloadJob?.cancel()
        val current = _progressFlow.value
        _progressFlow.value = current.copy(state = DownloadState.CANCELLED)
    }
}
