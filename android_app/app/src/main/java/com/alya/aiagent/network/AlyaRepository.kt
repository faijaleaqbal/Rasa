package com.alya.aiagent.network

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.alya.aiagent.data.SessionManager
import java.util.concurrent.Executors

class AlyaRepository(context: Context) {

    private val apiClient = AlyaApiClient()
    val sessionManager = SessionManager(context)
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    fun sendMessage(
        messageText: String,
        onResult: (NetworkResult<List<RasaMessage>>) -> Unit
    ) {
        val serverUrl = sessionManager.getServerUrl()
        val sessionId = sessionManager.getCurrentSessionId()

        executor.execute {
            val result = apiClient.sendMessage(serverUrl, sessionId, messageText)
            mainHandler.post {
                if (result is NetworkResult.Success && messageText.length > 2) {
                    val preview = if (messageText.length > 25) messageText.take(25) + "..." else messageText
                    sessionManager.saveSessionMetadata(sessionId, preview)
                }
                onResult(result)
            }
        }
    }

    fun checkHealth(onResult: (HealthStatus) -> Unit) {
        val serverUrl = sessionManager.getServerUrl()
        executor.execute {
            val status = apiClient.checkHealth(serverUrl)
            mainHandler.post {
                onResult(status)
            }
        }
    }

    fun validateAndSaveServerUrl(rawUrl: String): Pair<Boolean, String> {
        val (isValid, cleanOrError) = apiClient.validateUrl(rawUrl)
        if (isValid) {
            sessionManager.saveServerUrl(cleanOrError)
        }
        return Pair(isValid, cleanOrError)
    }

    fun startNewConversation(): String {
        return sessionManager.createNewSession("New Conversation")
    }

    fun getCurrentSessionId(): String {
        return sessionManager.getCurrentSessionId()
    }
}
