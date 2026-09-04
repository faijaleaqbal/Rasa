package com.alya.aiagent.local

data class HfQuantFile(
    val filename: String,
    val quantType: String,
    val sizeBytes: Long,
    val downloadUrl: String
) {
    val sizeFormatted: String
        get() {
            if (sizeBytes <= 0) return "Unknown size"
            val mb = sizeBytes / (1024.0 * 1024.0)
            return if (mb >= 1024) {
                String.format(java.util.Locale.US, "%.2f GB", mb / 1024.0)
            } else {
                String.format(java.util.Locale.US, "%.1f MB", mb)
            }
        }
}

data class HfModelCard(
    val repoId: String,
    val name: String,
    val author: String,
    val description: String,
    val downloads: Long = 0,
    val likes: Long = 0,
    val parameterSize: String = "",
    val isCurated: Boolean = false,
    val quantFiles: List<HfQuantFile> = emptyList()
) {
    companion object {
        val CURATED_MODELS = listOf(
            HfModelCard(
                repoId = "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                name = "Qwen 2.5 (0.5B Instruct)",
                author = "Qwen",
                description = "Ultra-fast, featherlight model. Perfect for all low-RAM Android phones with instant token generation.",
                downloads = 250000,
                likes = 1200,
                parameterSize = "0.5B",
                isCurated = true,
                quantFiles = listOf(
                    HfQuantFile(
                        filename = "qwen2.5-0.5b-instruct-q4_k_m.gguf",
                        quantType = "Q4_K_M (Recommended)",
                        sizeBytes = 398000000L,
                        downloadUrl = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
                    ),
                    HfQuantFile(
                        filename = "qwen2.5-0.5b-instruct-q8_0.gguf",
                        quantType = "Q8_0 (High Precision)",
                        sizeBytes = 550000000L,
                        downloadUrl = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q8_0.gguf"
                    )
                )
            ),
            HfModelCard(
                repoId = "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
                name = "SmolLM2 (1.7B Instruct)",
                author = "HuggingFace",
                description = "Exceptional reasoning and language balance for mobile devices. Highly efficient on 4GB+ RAM.",
                downloads = 180000,
                likes = 950,
                parameterSize = "1.7B",
                isCurated = true,
                quantFiles = listOf(
                    HfQuantFile(
                        filename = "smollm2-1.7b-instruct-q4_k_m.gguf",
                        quantType = "Q4_K_M (Recommended)",
                        sizeBytes = 1060000000L,
                        downloadUrl = "https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF/resolve/main/smollm2-1.7b-instruct-q4_k_m.gguf"
                    ),
                    HfQuantFile(
                        filename = "smollm2-1.7b-instruct-q5_k_m.gguf",
                        quantType = "Q5_K_M (Higher Quality)",
                        sizeBytes = 1250000000L,
                        downloadUrl = "https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF/resolve/main/smollm2-1.7b-instruct-q5_k_m.gguf"
                    )
                )
            ),
            HfModelCard(
                repoId = "bartowski/Llama-3.2-1B-Instruct-GGUF",
                name = "Llama 3.2 (1B Instruct)",
                author = "Meta / Bartowski",
                description = "Meta's lightweight powerhouse. Outstanding multilingual instructions and conversational fluency.",
                downloads = 420000,
                likes = 2100,
                parameterSize = "1.2B",
                isCurated = true,
                quantFiles = listOf(
                    HfQuantFile(
                        filename = "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
                        quantType = "Q4_K_M (Recommended)",
                        sizeBytes = 804000000L,
                        downloadUrl = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
                    ),
                    HfQuantFile(
                        filename = "Llama-3.2-1B-Instruct-Q8_0.gguf",
                        quantType = "Q8_0 (Full Precision)",
                        sizeBytes = 1320000000L,
                        downloadUrl = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q8_0.gguf"
                    )
                )
            ),
            HfModelCard(
                repoId = "bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
                name = "DeepSeek R1 Distill (1.5B)",
                author = "DeepSeek / Bartowski",
                description = "Chain-of-Thought reasoning model. Explains step-by-step thinking before answering.",
                downloads = 680000,
                likes = 3400,
                parameterSize = "1.5B",
                isCurated = true,
                quantFiles = listOf(
                    HfQuantFile(
                        filename = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
                        quantType = "Q4_K_M (Recommended)",
                        sizeBytes = 1120000000L,
                        downloadUrl = "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
                    )
                )
            ),
            HfModelCard(
                repoId = "bartowski/gemma-2-2b-it-GGUF",
                name = "Gemma 2 (2B Instruct)",
                author = "Google / Bartowski",
                description = "Google's high-efficiency lightweight architecture. Excellent general knowledge & coding.",
                downloads = 310000,
                likes = 1750,
                parameterSize = "2.6B",
                isCurated = true,
                quantFiles = listOf(
                    HfQuantFile(
                        filename = "gemma-2-2b-it-Q4_K_M.gguf",
                        quantType = "Q4_K_M (Recommended)",
                        sizeBytes = 1710000000L,
                        downloadUrl = "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf"
                    )
                )
            ),
            HfModelCard(
                repoId = "bartowski/Llama-3.2-3B-Instruct-GGUF",
                name = "Llama 3.2 (3B Instruct)",
                author = "Meta / Bartowski",
                description = "Top-tier intelligence for devices with 6GB+ RAM. Superb reasoning, tool use, and writing.",
                downloads = 510000,
                likes = 2900,
                parameterSize = "3.2B",
                isCurated = true,
                quantFiles = listOf(
                    HfQuantFile(
                        filename = "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
                        quantType = "Q4_K_M (Recommended)",
                        sizeBytes = 2020000000L,
                        downloadUrl = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
                    )
                )
            )
        )
    }
}
