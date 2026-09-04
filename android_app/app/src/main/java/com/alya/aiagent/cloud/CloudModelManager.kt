package com.alya.aiagent.cloud

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * Atomic-Chat style Multi-Provider Cloud Model Manager for ALYA.
 * Supports Groq (Ultra-Fast), OpenAI, DeepSeek, Anthropic, Custom OpenAI Endpoints, and Alya Rasa Server.
 */
class CloudModelManager private constructor(private val context: Context) {

    companion object {
        private const val TAG = "CloudModelManager"
        private const val PREFS_NAME = "AlyaCloudPrefs"
        const val KEY_ACTIVE_MODEL_ID = "active_cloud_model_id"
        const val KEY_GROQ_KEY = "api_key_groq"
        const val KEY_OPENAI_KEY = "api_key_openai"
        const val KEY_DEEPSEEK_KEY = "api_key_deepseek"
        const val KEY_ANTHROPIC_KEY = "api_key_anthropic"
        const val KEY_CUSTOM_BASE_URL = "custom_base_url"
        const val KEY_CUSTOM_KEY = "api_key_custom"

        // Default Groq key (configured via preferences or environment)
        const val DEFAULT_GROQ_KEY = ""

        @Volatile
        private var INSTANCE: CloudModelManager? = null

        fun getInstance(context: Context): CloudModelManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: CloudModelManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getAllCloudModels(): List<CloudModel> = CloudModel.DEFAULT_MODELS

    fun getActiveCloudModel(): CloudModel {
        val activeId = prefs.getString(KEY_ACTIVE_MODEL_ID, "llama-3.3-70b-versatile") ?: "llama-3.3-70b-versatile"
        return getAllCloudModels().find { it.id == activeId } ?: CloudModel.DEFAULT_MODELS.find { it.id == "llama-3.3-70b-versatile" } ?: CloudModel.DEFAULT_MODELS.first()
    }

    fun setActiveCloudModel(modelId: String) {
        prefs.edit().putString(KEY_ACTIVE_MODEL_ID, modelId).apply()
    }

    fun getApiKey(provider: ProviderType): String? {
        return when (provider) {
            ProviderType.GROQ -> prefs.getString(KEY_GROQ_KEY, DEFAULT_GROQ_KEY) ?: DEFAULT_GROQ_KEY
            ProviderType.OPENAI -> prefs.getString(KEY_OPENAI_KEY, null)
            ProviderType.DEEPSEEK -> prefs.getString(KEY_DEEPSEEK_KEY, null)
            ProviderType.ANTHROPIC -> prefs.getString(KEY_ANTHROPIC_KEY, null)
            ProviderType.CUSTOM -> prefs.getString(KEY_CUSTOM_KEY, null)
            ProviderType.ALYA_RASA -> null
        }
    }

    fun setApiKey(provider: ProviderType, key: String?) {
        val prefKey = when (provider) {
            ProviderType.GROQ -> KEY_GROQ_KEY
            ProviderType.OPENAI -> KEY_OPENAI_KEY
            ProviderType.DEEPSEEK -> KEY_DEEPSEEK_KEY
            ProviderType.ANTHROPIC -> KEY_ANTHROPIC_KEY
            ProviderType.CUSTOM -> KEY_CUSTOM_KEY
            ProviderType.ALYA_RASA -> return
        }
        if (key.isNullOrBlank()) {
            prefs.edit().remove(prefKey).apply()
        } else {
            prefs.edit().putString(prefKey, key.trim()).apply()
        }
    }

    fun getCustomBaseUrl(): String {
        return prefs.getString(KEY_CUSTOM_BASE_URL, "http://localhost:1337/v1") ?: "http://localhost:1337/v1"
    }

    fun setCustomBaseUrl(url: String) {
        prefs.edit().putString(KEY_CUSTOM_BASE_URL, url.trim()).apply()
    }

    fun streamCloudCompletion(
        userPrompt: String,
        systemPrompt: String? = null,
        temperature: Float = 0.7f,
        topP: Float = 0.9f
    ): Flow<String> = flow {
        val model = getActiveCloudModel()
        if (model.provider == ProviderType.ALYA_RASA) {
            return@flow
        }

        val apiKey = getApiKey(model.provider)
        val baseUrl = if (model.provider == ProviderType.CUSTOM) getCustomBaseUrl() else model.provider.defaultBaseUrl
        val endpoint = if (baseUrl.endsWith("/")) "${baseUrl}chat/completions" else "$baseUrl/chat/completions"

        var conn: HttpURLConnection? = null
        try {
            val url = URL(endpoint)
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.connectTimeout = 12000
            conn.readTimeout = 45000
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Accept", "text/event-stream")
            conn.setRequestProperty("User-Agent", "Alya-Atomic-Chat/2.0")

            if (!apiKey.isNullOrBlank()) {
                conn.setRequestProperty("Authorization", "Bearer $apiKey")
            }

            val messagesArray = JSONArray()
            if (!systemPrompt.isNullOrBlank()) {
                messagesArray.put(JSONObject().apply {
                    put("role", "system")
                    put("content", systemPrompt)
                })
            }
            messagesArray.put(JSONObject().apply {
                put("role", "user")
                put("content", userPrompt)
            })

            val payload = JSONObject().apply {
                put("model", model.id)
                put("messages", messagesArray)
                put("temperature", temperature.toDouble())
                put("top_p", topP.toDouble())
                put("stream", true)
            }

            OutputStreamWriter(conn.outputStream, "UTF-8").use { writer ->
                writer.write(payload.toString())
                writer.flush()
            }

            val responseCode = conn.responseCode
            if (responseCode in 200..299) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream, "UTF-8"))
                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    val l = line?.trim() ?: continue
                    if (l.startsWith("data: ")) {
                        val dataStr = l.substring(6).trim()
                        if (dataStr == "[DONE]") break

                        try {
                            val json = JSONObject(dataStr)
                            val choices = json.optJSONArray("choices")
                            if (choices != null && choices.length() > 0) {
                                val delta = choices.getJSONObject(0).optJSONObject("delta")
                                val content = delta?.optString("content", "") ?: ""
                                val reasoning = delta?.optString("reasoning_content", "") ?: ""

                                if (reasoning.isNotEmpty()) {
                                    emit(reasoning)
                                } else if (content.isNotEmpty()) {
                                    emit(content)
                                }
                            }
                        } catch (je: Throwable) {
                            // ignore partial JSON parse chunk
                        }
                    }
                }
                reader.close()
            } else {
                val errReader = BufferedReader(InputStreamReader(conn.errorStream ?: conn.inputStream, "UTF-8"))
                val errSb = StringBuilder()
                var eline: String?
                while (errReader.readLine().also { eline = it } != null) {
                    errSb.append(eline)
                }
                errReader.close()
                emit("❌ ${model.provider.displayName} Error ($responseCode): $errSb\n(Please check your API Key in Settings)")
            }
        } catch (e: Throwable) {
            Log.e(TAG, "Cloud completion error: ${e.message}", e)
            emit("❌ Connection Failed: ${e.message}\n(Tip: You can switch to a local offline GGUF model in the Models tab!)")
        } finally {
            conn?.disconnect()
        }
    }.flowOn(Dispatchers.IO)
}
