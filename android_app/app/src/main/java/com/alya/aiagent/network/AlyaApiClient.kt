package com.alya.aiagent.network

import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException

class AlyaApiClient {

    companion object {
        private const val TAG = "AlyaApiClient"
        private const val CONNECT_TIMEOUT_MS = 8000
        private const val READ_TIMEOUT_MS = 25000
    }

    fun sendMessage(baseUrl: String, senderId: String, messageText: String): NetworkResult<List<RasaMessage>> {
        val cleanUrl = sanitizeBaseUrl(baseUrl)
        val webhookUrl = "$cleanUrl/webhooks/rest/webhook"

        var conn: HttpURLConnection? = null
        try {
            val url = URL(webhookUrl)
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Accept", "application/json")
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                doOutput = true
            }

            val payload = JSONObject().apply {
                put("sender", senderId)
                put("message", messageText)
            }

            OutputStreamWriter(conn.outputStream, "UTF-8").use { writer ->
                writer.write(payload.toString())
                writer.flush()
            }

            val responseCode = conn.responseCode
            if (responseCode in 200..299) {
                val responseBody = conn.inputStream.bufferedReader().use { it.readText() }
                val messages = parseRasaResponse(responseBody)
                return NetworkResult.Success(messages)
            } else {
                val errorBody = try {
                    conn.errorStream?.bufferedReader()?.use { it.readText() } ?: "HTTP $responseCode"
                } catch (e: Exception) {
                    "HTTP $responseCode"
                }
                return NetworkResult.Error(responseCode, "Server returned: $errorBody")
            }
        } catch (e: SocketTimeoutException) {
            Log.e(TAG, "Request timeout: ${e.message}")
            return NetworkResult.Timeout("Request timed out after ${READ_TIMEOUT_MS / 1000}s. Please retry.")
        } catch (e: UnknownHostException) {
            Log.e(TAG, "No network / host unreachable: ${e.message}")
            return NetworkResult.Offline("Alya server unreachable. Please check your network or server URL.")
        } catch (e: Exception) {
            Log.e(TAG, "Network exception: ${e.message}", e)
            val msg = e.localizedMessage ?: "Network connection failure"
            return if (msg.contains("failed to connect", ignoreCase = true) || msg.contains("ENETUNREACH", ignoreCase = true)) {
                NetworkResult.Offline("Unable to connect to server ($msg)")
            } else {
                NetworkResult.Error(-1, msg)
            }
        } finally {
            conn?.disconnect()
        }
    }

    fun checkHealth(baseUrl: String): HealthStatus {
        val cleanUrl = sanitizeBaseUrl(baseUrl)
        val startTime = System.currentTimeMillis()

        var conn: HttpURLConnection? = null
        try {
            val url = URL("$cleanUrl/status")
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 4000
                readTimeout = 4000
            }

            val code = conn.responseCode
            val latency = System.currentTimeMillis() - startTime

            if (code == 200) {
                val body = conn.inputStream.bufferedReader().use { it.readText() }
                val json = JSONObject(body)
                val modelId = json.optString("model_id", "active")
                return HealthStatus(
                    isHealthy = true,
                    latencyMs = latency,
                    modelId = modelId,
                    message = "Connected (${latency}ms)"
                )
            } else if (code == 404) {
                // Fallback to /version endpoint
                return checkVersionEndpoint(cleanUrl, startTime)
            } else {
                return HealthStatus(
                    isHealthy = false,
                    latencyMs = latency,
                    message = "Server returned HTTP $code"
                )
            }
        } catch (e: Exception) {
            val latency = System.currentTimeMillis() - startTime
            return HealthStatus(
                isHealthy = false,
                latencyMs = latency,
                message = "Server unreachable (${e.localizedMessage ?: "Offline"})"
            )
        } finally {
            conn?.disconnect()
        }
    }

    private fun checkVersionEndpoint(cleanUrl: String, startTime: Long): HealthStatus {
        var conn: HttpURLConnection? = null
        try {
            val url = URL("$cleanUrl/version")
            conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 4000
                readTimeout = 4000
            }

            val code = conn.responseCode
            val latency = System.currentTimeMillis() - startTime
            if (code == 200) {
                val body = conn.inputStream.bufferedReader().use { it.readText() }
                val json = JSONObject(body)
                val version = json.optString("version", "3.x")
                return HealthStatus(
                    isHealthy = true,
                    latencyMs = latency,
                    version = version,
                    message = "Connected (${latency}ms) v$version"
                )
            } else {
                return HealthStatus(
                    isHealthy = false,
                    latencyMs = latency,
                    message = "Server error HTTP $code"
                )
            }
        } catch (e: Exception) {
            return HealthStatus(
                isHealthy = false,
                latencyMs = System.currentTimeMillis() - startTime,
                message = "Version check failed"
            )
        } finally {
            conn?.disconnect()
        }
    }

    fun validateUrl(rawUrl: String): Pair<Boolean, String> {
        val trimmed = rawUrl.trim()
        if (trimmed.isEmpty()) {
            return Pair(false, "URL cannot be empty")
        }
        if (trimmed.contains("@")) {
            return Pair(false, "URL must not contain credentials")
        }
        return try {
            val url = URL(sanitizeBaseUrl(trimmed))
            val protocol = url.protocol.lowercase()
            if (protocol != "http" && protocol != "https") {
                Pair(false, "Only HTTP and HTTPS protocols are supported")
            } else {
                Pair(true, sanitizeBaseUrl(trimmed))
            }
        } catch (e: Exception) {
            Pair(false, "Invalid URL format: ${e.message}")
        }
    }

    private fun sanitizeBaseUrl(rawUrl: String): String {
        var clean = rawUrl.trim()
        if (!clean.startsWith("http://", ignoreCase = true) && !clean.startsWith("https://", ignoreCase = true)) {
            clean = "http://$clean"
        }
        return clean.trimEnd('/')
    }

    private fun parseRasaResponse(jsonString: String): List<RasaMessage> {
        val list = mutableListOf<RasaMessage>()
        try {
            val array = JSONArray(jsonString)
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                val recipientId = obj.optString("recipient_id", "")
                val text = if (obj.has("text")) obj.getString("text") else null
                val image = if (obj.has("image")) obj.getString("image") else null

                val buttonsList = mutableListOf<RasaButton>()
                if (obj.has("buttons")) {
                    val buttonsArray = obj.getJSONArray("buttons")
                    for (b in 0 until buttonsArray.length()) {
                        val btnObj = buttonsArray.getJSONObject(b)
                        buttonsList.add(
                            RasaButton(
                                title = btnObj.optString("title", ""),
                                payload = btnObj.optString("payload", "")
                            )
                        )
                    }
                }

                list.add(
                    RasaMessage(
                        recipientId = recipientId,
                        text = text,
                        image = image,
                        buttons = if (buttonsList.isNotEmpty()) buttonsList else null
                    )
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse Rasa JSON response: $jsonString", e)
        }
        return list
    }
}
