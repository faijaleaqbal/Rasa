package com.alya.aiagent.local

/**
 * Parsed header metadata from a GGUF format file.
 */
data class GgufMetadata(
    val version: Int,
    val tensorCount: Long,
    val kvCount: Long,
    val architecture: String,
    val name: String,
    val contextLength: Int,
    val parameterCount: Long,
    val embeddingLength: Int,
    val layerCount: Int,
    val headCount: Int,
    val headCountKv: Int,
    val feedForwardLength: Int,
    val vocabSize: Int,
    val fileType: Int,
    val quantization: String,
    val chatTemplate: String?,
    val isSupported: Boolean,
    val validationError: String? = null
)
