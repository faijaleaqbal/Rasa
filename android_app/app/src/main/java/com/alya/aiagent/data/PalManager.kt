package com.alya.aiagent.data

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

/**
 * PocketPal-style Persona (Pal) Manager for Alya AI.
 * Handles built-in personality presets and custom user-created AI personas.
 */
class PalManager private constructor(private val context: Context) {

    companion object {
        private const val PREFS_NAME = "AlyaPalPrefs"
        private const val KEY_ACTIVE_PAL_ID = "active_pal_id"
        private const val KEY_CUSTOM_PALS = "custom_pals_json"

        @Volatile
        private var INSTANCE: PalManager? = null

        fun getInstance(context: Context): PalManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: PalManager(context.applicationContext).also { INSTANCE = it }
            }
        }

        val PRESET_PALS = listOf(
            Pal(
                id = "alya_smart",
                name = "Alya Assistant",
                role = "Proactive AI Assistant",
                tagline = "Bilingual Hinglish intelligence with cloud & local tool routing",
                systemPrompt = "You are Alya, a highly capable, polite, and intelligent AI personal assistant. You communicate naturally in Hinglish (a balanced mix of Hindi and English) and English. Provide structured, accurate, and actionable answers. When solving user requests, be proactive, helpful, and clear.",
                avatarEmoji = "🤖",
                colorHex = "#8B5CF6",
                temperature = 0.7f,
                topP = 0.9f,
                isCustom = false
            ),
            Pal(
                id = "alya_buddy",
                name = "Alya Dost",
                role = "Conversational Best Friend",
                tagline = "Warm, witty & empathetic everyday buddy",
                systemPrompt = "You are Alya, the user's close and supportive best friend (Dost). You talk in very natural, warm, and lively Hinglish. Use friendly expressions, light humor, empathy, and relatable advice. Keep the conversation engaging and casual.",
                avatarEmoji = "☕",
                colorHex = "#EC4899",
                temperature = 0.85f,
                topP = 0.95f,
                isCustom = false
            ),
            Pal(
                id = "alya_coder",
                name = "Code & Tech Wizard",
                role = "Senior Systems Engineer",
                tagline = "Clean code, debugging, architecture & algorithms",
                systemPrompt = "You are an elite software architect and coding specialist. Write clean, production-grade, bug-free code in Kotlin, Python, JavaScript, C++, and Bash. Explain technical concepts with high precision, optimal time complexity, and standard best practices. Avoid conversational filler.",
                avatarEmoji = "💻",
                colorHex = "#10B981",
                temperature = 0.2f,
                topP = 0.8f,
                isCustom = false
            ),
            Pal(
                id = "alya_tutor",
                name = "Language & Grammar Tutor",
                role = "Bilingual Language Guide",
                tagline = "Master Hindi, English, grammar & translation",
                systemPrompt = "You are an expert bilingual English and Hindi language tutor. You help users improve their vocabulary, polish email drafts, correct grammatical errors, and translate nuanced phrases between English and Hindi with cultural context.",
                avatarEmoji = "📚",
                colorHex = "#3B82F6",
                temperature = 0.5f,
                topP = 0.85f,
                isCustom = false
            ),
            Pal(
                id = "alya_minimal",
                name = "Fast Solver",
                role = "Ultra-Concise Direct Bot",
                tagline = "Instant calculations, bullet points, zero fluff",
                systemPrompt = "You are an ultra-concise fact and logic engine. Answer in the fewest words possible. Give direct mathematical solutions, short bullet points, and straight facts with zero greeting, preamble, or filler.",
                avatarEmoji = "⚡",
                colorHex = "#F59E0B",
                temperature = 0.1f,
                topP = 0.7f,
                isCustom = false
            ),
            Pal(
                id = "alya_storyteller",
                name = "Roleplay & Storyteller",
                role = "Creative Narrative Master",
                tagline = "Imaginative world-building, dialogues & stories",
                systemPrompt = "You are a master creative storyteller and roleplay persona. Build rich, immersive worlds, detailed character dialogue, suspenseful plot twists, and vivid sensory descriptions.",
                avatarEmoji = "🎭",
                colorHex = "#6366F1",
                temperature = 0.95f,
                topP = 0.95f,
                isCustom = false
            )
        )
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getAllPals(): List<Pal> {
        val list = mutableListOf<Pal>()
        list.addAll(PRESET_PALS)
        list.addAll(getCustomPals())
        return list
    }

    fun getActivePal(): Pal {
        val activeId = prefs.getString(KEY_ACTIVE_PAL_ID, "alya_smart") ?: "alya_smart"
        return getAllPals().find { it.id == activeId } ?: PRESET_PALS.first()
    }

    fun setActivePal(palId: String) {
        prefs.edit().putString(KEY_ACTIVE_PAL_ID, palId).apply()
    }

    fun getCustomPals(): List<Pal> {
        val jsonStr = prefs.getString(KEY_CUSTOM_PALS, null) ?: return emptyList()
        val customList = mutableListOf<Pal>()
        try {
            val jsonArray = JSONArray(jsonStr)
            for (i in 0 until jsonArray.length()) {
                val obj = jsonArray.getJSONObject(i)
                customList.add(Pal.fromJson(obj))
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return customList
    }

    fun saveCustomPal(pal: Pal) {
        val current = getCustomPals().toMutableList()
        val index = current.indexOfFirst { it.id == pal.id }
        if (index >= 0) {
            current[index] = pal
        } else {
            current.add(pal)
        }
        saveCustomList(current)
    }

    fun deleteCustomPal(palId: String) {
        val current = getCustomPals().toMutableList()
        current.removeAll { it.id == palId }
        saveCustomList(current)
        if (getActivePal().id == palId) {
            setActivePal(PRESET_PALS.first().id)
        }
    }

    private fun saveCustomList(list: List<Pal>) {
        val jsonArray = JSONArray()
        for (pal in list) {
            jsonArray.put(pal.toJson())
        }
        prefs.edit().putString(KEY_CUSTOM_PALS, jsonArray.toString()).apply()
    }
}
