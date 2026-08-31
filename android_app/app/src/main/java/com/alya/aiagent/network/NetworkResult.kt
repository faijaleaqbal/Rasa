package com.alya.aiagent.network

sealed class NetworkResult<out T> {
    data class Success<out T>(val data: T) : NetworkResult<T>()
    data class Error(val code: Int, val message: String, val canRetry: Boolean = true) : NetworkResult<Nothing>()
    data class Offline(val message: String = "You're offline. Please check your internet connection.") : NetworkResult<Nothing>()
    data class Timeout(val message: String = "Request timed out. Please try again.") : NetworkResult<Nothing>()
}

data class RasaMessage(
    val recipientId: String,
    val text: String?,
    val image: String? = null,
    val buttons: List<RasaButton>? = null
)

data class RasaButton(
    val title: String,
    val payload: String
)

data class HealthStatus(
    val isHealthy: Boolean,
    val latencyMs: Long,
    val version: String? = null,
    val modelId: String? = null,
    val message: String
)
