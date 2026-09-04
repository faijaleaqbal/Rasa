package com.alya.aiagent.data

import org.json.JSONObject

data class Pal(
    val id: String,
    val name: String,
    val role: String,
    val tagline: String,
    val systemPrompt: String,
    val avatarEmoji: String,
    val colorHex: String,
    val temperature: Float = 0.7f,
    val topP: Float = 0.9f,
    val isCustom: Boolean = false
) {
    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("id", id)
            put("name", name)
            put("role", role)
            put("tagline", tagline)
            put("systemPrompt", systemPrompt)
            put("avatarEmoji", avatarEmoji)
            put("colorHex", colorHex)
            put("temperature", temperature.toDouble())
            put("topP", topP.toDouble())
            put("isCustom", isCustom)
        }
    }

    companion object {
        fun fromJson(json: JSONObject): Pal {
            return Pal(
                id = json.optString("id", "alya_default"),
                name = json.optString("name", "Alya Assistant"),
                role = json.optString("role", "Smart Assistant"),
                tagline = json.optString("tagline", "Helpful, intelligent AI assistant"),
                systemPrompt = json.optString("systemPrompt", ""),
                avatarEmoji = json.optString("avatarEmoji", "🤖"),
                colorHex = json.optString("colorHex", "#8B5CF6"),
                temperature = json.optDouble("temperature", 0.7).toFloat(),
                topP = json.optDouble("topP", 0.9).toFloat(),
                isCustom = json.optBoolean("isCustom", false)
            )
        }
    }
}
