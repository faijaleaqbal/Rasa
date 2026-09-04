package com.alya.aiagent.cloud

import org.json.JSONArray
import org.json.JSONObject

enum class ProviderType(val displayName: String, val defaultBaseUrl: String, val icon: String) {
    ALYA_RASA("Alya Cloud Brain", "http://3.90.20.247:5005", "⚡"),
    GROQ("Groq (Ultra-Fast)", "https://api.groq.com/openai/v1", "⚡"),
    OPENAI("OpenAI", "https://api.openai.com/v1", "✨"),
    DEEPSEEK("DeepSeek", "https://api.deepseek.com/v1", "🐋"),
    ANTHROPIC("Anthropic Claude", "https://api.anthropic.com/v1", "🧠"),
    CUSTOM("Custom OpenAI-Compatible", "http://localhost:1337/v1", "🔌")
}

data class CloudModel(
    val id: String,
    val name: String,
    val provider: ProviderType,
    val contextWindow: String,
    val description: String,
    val isReasoningModel: Boolean = false
) {
    companion object {
        val DEFAULT_MODELS = listOf(
            // Alya Cloud
            CloudModel(
                id = "alya_cloud_rasa",
                name = "Alya Cloud Brain (100+ Skills)",
                provider = ProviderType.ALYA_RASA,
                contextWindow = "32K",
                description = "Enterprise assistant with real-time weather, crypto, stocks, train status, search & productivity skills."
            ),
            // Groq Models
            CloudModel(
                id = "llama-3.3-70b-versatile",
                name = "Llama 3.3 70B Versatile",
                provider = ProviderType.GROQ,
                contextWindow = "128K",
                description = "Meta's flagship open-weights model running at 300+ tokens/sec on Groq LPUs."
            ),
            CloudModel(
                id = "qwen-2.5-32b",
                name = "Qwen 2.5 32B Instruct",
                provider = ProviderType.GROQ,
                contextWindow = "128K",
                description = "Top-tier multilingual, reasoning, and coding model."
            ),
            CloudModel(
                id = "deepseek-r1-distill-llama-70b",
                name = "DeepSeek R1 Distill 70B",
                provider = ProviderType.GROQ,
                contextWindow = "128K",
                description = "Advanced chain-of-thought reasoning with full step-by-step thinking.",
                isReasoningModel = true
            ),
            CloudModel(
                id = "gemma2-9b-it",
                name = "Gemma 2 9B Instruct",
                provider = ProviderType.GROQ,
                contextWindow = "8K",
                description = "Google's fast, highly coherent model for general tasks."
            ),
            // DeepSeek API
            CloudModel(
                id = "deepseek-chat",
                name = "DeepSeek-V3",
                provider = ProviderType.DEEPSEEK,
                contextWindow = "64K",
                description = "Frontier model with state-of-the-art general knowledge, coding, and chat fluency."
            ),
            CloudModel(
                id = "deepseek-reasoner",
                name = "DeepSeek-R1 (Reasoning)",
                provider = ProviderType.DEEPSEEK,
                contextWindow = "64K",
                description = "Full DeepSeek R1 reasoning model with deep thought processes.",
                isReasoningModel = true
            ),
            // OpenAI Models
            CloudModel(
                id = "gpt-4o",
                name = "GPT-4o",
                provider = ProviderType.OPENAI,
                contextWindow = "128K",
                description = "OpenAI's flagship multimodal intelligence engine."
            ),
            CloudModel(
                id = "gpt-4o-mini",
                name = "GPT-4o Mini",
                provider = ProviderType.OPENAI,
                contextWindow = "128K",
                description = "Fast, lightweight, highly affordable model for everyday conversation."
            )
        )
    }
}
