package com.alya.aiagent.local

import java.text.DecimalFormat

enum class ModelState {
    DISCOVERED,
    DOWNLOADING,
    READY,
    LOADING,
    LOADED,
    GENERATING,
    UNLOADING,
    ERROR
}

/**
 * PocketPal-style Model data structure for local GGUF models.
 * Model viability is determined dynamically by comparing estimated required RAM
 * against actual available device memory, rather than arbitrary hardcoded parameter limits.
 */
data class ModelInfo(
    val id: String,
    val name: String,
    val filePath: String,
    val sizeBytes: Long,
    val parameterCount: Long,
    val contextLength: Int,
    val quantization: String,
    val architecture: String,
    val embeddingLength: Int = 896,
    val layerCount: Int = 24,
    val headCount: Int = 14,
    val headCountKv: Int = 2,
    val estimatedRamBytes: Long = 0L,
    val backendPreference: String = "Auto",
    val isSupported: Boolean = true,
    val validationMessage: String? = null,
    val state: ModelState = ModelState.READY,
    val isLoaded: Boolean = false
) {
    val formattedSize: String
        get() {
            val df = DecimalFormat("0.##")
            val mb = sizeBytes.toDouble() / (1024.0 * 1024.0)
            return if (mb >= 1024.0) {
                "${df.format(mb / 1024.0)} GB"
            } else {
                "${df.format(mb)} MB"
            }
        }

    val formattedEstimatedRam: String
        get() {
            val bytes = if (estimatedRamBytes > 0) estimatedRamBytes else (sizeBytes + 150 * 1024 * 1024L)
            val mb = bytes / (1024 * 1024)
            return if (mb >= 1024) {
                String.format(java.util.Locale.US, "~%.2f GB", mb / 1024.0)
            } else {
                "~$mb MB"
            }
        }

    val formattedParams: String
        get() {
            val df = DecimalFormat("0.##")
            val billions = parameterCount.toDouble() / 1_000_000_000.0
            return if (billions >= 1.0) {
                "${df.format(billions)}B params"
            } else {
                val millions = parameterCount.toDouble() / 1_000_000.0
                "${df.format(millions)}M params"
            }
        }
}
