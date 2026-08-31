package com.alya.aiagent.data

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class SessionManager(context: Context) {

    companion object {
        private const val PREFS_NAME = "AlyaSessionPrefs"
        private const val KEY_CURRENT_SESSION_ID = "current_session_id"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_SESSIONS_METADATA = "sessions_metadata"
        const val DEFAULT_SERVER_URL = "http://3.90.20.247:5005"
        const val FALLBACK_USER_ID = "8433855679"
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getCurrentSessionId(): String {
        var sessionId = prefs.getString(KEY_CURRENT_SESSION_ID, null)
        if (sessionId.isNullOrEmpty()) {
            sessionId = createNewSession("New Conversation")
        }
        return sessionId
    }

    fun createNewSession(title: String = "New Conversation"): String {
        val newSessionId = "alya_${UUID.randomUUID().toString().take(12)}"
        prefs.edit().putString(KEY_CURRENT_SESSION_ID, newSessionId).apply()
        saveSessionMetadata(newSessionId, title)
        return newSessionId
    }

    fun getServerUrl(): String {
        return prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL) ?: DEFAULT_SERVER_URL
    }

    fun saveServerUrl(url: String) {
        prefs.edit().putString(KEY_SERVER_URL, url).apply()
    }

    fun saveSessionMetadata(sessionId: String, title: String) {
        val sessions = getSessionsMetadata()
        val updated = mutableListOf<SessionMeta>()
        var found = false

        for (s in sessions) {
            if (s.id == sessionId) {
                updated.add(s.copy(title = title, lastUpdated = System.currentTimeMillis()))
                found = true
            } else {
                updated.add(s)
            }
        }
        if (!found) {
            updated.add(0, SessionMeta(id = sessionId, title = title, createdAt = System.currentTimeMillis(), lastUpdated = System.currentTimeMillis()))
        }

        val jsonArray = JSONArray()
        for (item in updated.take(50)) { // Keep last 50 sessions
            jsonArray.put(JSONObject().apply {
                put("id", item.id)
                put("title", item.title)
                put("createdAt", item.createdAt)
                put("lastUpdated", item.lastUpdated)
            })
        }
        prefs.edit().putString(KEY_SESSIONS_METADATA, jsonArray.toString()).apply()
    }

    fun getSessionsMetadata(): List<SessionMeta> {
        val list = mutableListOf<SessionMeta>()
        val raw = prefs.getString(KEY_SESSIONS_METADATA, null) ?: return list
        try {
            val array = JSONArray(raw)
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                list.add(
                    SessionMeta(
                        id = obj.getString("id"),
                        title = obj.getString("title"),
                        createdAt = obj.getLong("createdAt"),
                        lastUpdated = obj.getLong("lastUpdated")
                    )
                )
            }
        } catch (e: Exception) {
            // Ignore parse errors
        }
        return list
    }
}

data class SessionMeta(
    val id: String,
    val title: String,
    val createdAt: Long,
    val lastUpdated: Long
)
