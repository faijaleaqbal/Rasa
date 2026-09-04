package com.alya.aiagent.local

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * PocketPal-style Hugging Face Hub API Client for discovering & exploring GGUF models.
 */
class HuggingFaceClient(private val context: Context) {

    companion object {
        private const val TAG = "HuggingFaceClient"
        private const val HF_API_BASE = "https://huggingface.co/api"
        private const val PREFS_NAME = "AlyaHfPrefs"
        const val KEY_HF_TOKEN = "hf_access_token"
    }

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getHfToken(): String? = prefs.getString(KEY_HF_TOKEN, null)

    fun setHfToken(token: String?) {
        if (token.isNullOrBlank()) {
            prefs.edit().remove(KEY_HF_TOKEN).apply()
        } else {
            prefs.edit().putString(KEY_HF_TOKEN, token.trim()).apply()
        }
    }

    suspend fun searchGgufModels(query: String, limit: Int = 15): List<HfModelCard> = withContext(Dispatchers.IO) {
        val results = mutableListOf<HfModelCard>()
        try {
            val encodedQuery = URLEncoder.encode(query, "UTF-8")
            val urlString = "$HF_API_BASE/models?search=$encodedQuery&filter=gguf&sort=downloads&direction=-1&limit=$limit"
            val jsonArray = fetchJsonArray(urlString) ?: return@withContext results

            for (i in 0 until jsonArray.length()) {
                val obj = jsonArray.getJSONObject(i)
                val id = obj.optString("id", "")
                if (id.isBlank()) continue

                val parts = id.split("/")
                val author = if (parts.size > 1) parts[0] else "Unknown"
                val name = if (parts.size > 1) parts[1] else id
                val downloads = obj.optLong("downloads", 0L)
                val likes = obj.optLong("likes", 0L)
                val description = "Hugging Face Hub model: $id"

                results.add(
                    HfModelCard(
                        repoId = id,
                        name = name,
                        author = author,
                        description = description,
                        downloads = downloads,
                        likes = likes,
                        parameterSize = extractParamSize(name),
                        isCurated = false
                    )
                )
            }
        } catch (e: Throwable) {
            Log.e(TAG, "Failed to search models: ${e.message}", e)
        }
        results
    }

    suspend fun fetchModelQuantFiles(repoId: String): List<HfQuantFile> = withContext(Dispatchers.IO) {
        val files = mutableListOf<HfQuantFile>()
        try {
            val urlString = "$HF_API_BASE/models/$repoId/tree/main"
            val jsonArray = fetchJsonArray(urlString) ?: return@withContext files

            for (i in 0 until jsonArray.length()) {
                val obj = jsonArray.getJSONObject(i)
                val path = obj.optString("path", "")
                val type = obj.optString("type", "")

                if (type == "file" && path.endsWith(".gguf", ignoreCase = true)) {
                    val size = obj.optLong("size", 0L)
                    val quantType = extractQuantType(path)
                    val downloadUrl = "https://huggingface.co/$repoId/resolve/main/$path"

                    files.add(
                        HfQuantFile(
                            filename = path,
                            quantType = quantType,
                            sizeBytes = size,
                            downloadUrl = downloadUrl
                        )
                    )
                }
            }
        } catch (e: Throwable) {
            Log.e(TAG, "Failed to fetch model quant files for $repoId: ${e.message}", e)
        }
        files
    }

    private fun extractParamSize(name: String): String {
        val lower = name.lowercase()
        val regex = Regex("([0-9]+(\\.[0-9]+)?b)")
        val match = regex.find(lower)
        return match?.value?.uppercase() ?: ""
    }

    private fun extractQuantType(filename: String): String {
        val upper = filename.uppercase()
        val quants = listOf(
            "Q4_K_M", "Q4_K_S", "Q4_0", "Q4_1",
            "Q5_K_M", "Q5_K_S", "Q5_0", "Q5_1",
            "Q8_0", "Q6_K", "Q3_K_M", "Q3_K_S", "Q2_K",
            "IQ4_XS", "IQ4_NL", "IQ3_M", "IQ2_XS", "F16", "BF16"
        )
        for (q in quants) {
            if (upper.contains(q)) return q
        }
        return "GGUF"
    }

    private fun fetchJsonArray(urlString: String): JSONArray? {
        var conn: HttpURLConnection? = null
        return try {
            val url = URL(urlString)
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.connectTimeout = 10000
            conn.readTimeout = 15000
            conn.setRequestProperty("User-Agent", "Alya-AI-PocketPal/2.0")

            val token = getHfToken()
            if (!token.isNullOrBlank()) {
                conn.setRequestProperty("Authorization", "Bearer $token")
            }

            if (conn.responseCode in 200..299) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream))
                val sb = StringBuilder()
                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    sb.append(line)
                }
                reader.close()
                JSONArray(sb.toString())
            } else {
                Log.w(TAG, "HTTP error ${conn.responseCode} for $urlString")
                null
            }
        } catch (e: Throwable) {
            Log.e(TAG, "Network error: ${e.message}")
            null
        } finally {
            conn?.disconnect()
        }
    }
}
