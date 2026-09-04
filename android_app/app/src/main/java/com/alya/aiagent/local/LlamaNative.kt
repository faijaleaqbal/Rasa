package com.alya.aiagent.local

import android.util.Log

/**
 * Low-level JNI bindings to llama.cpp C++ runtime.
 */
object LlamaNative {
    private const val TAG = "LlamaNative"
    private var isLoaded = false

    const val ERR_FILE_NOT_FOUND = -1L
    const val ERR_MODEL_TOO_LARGE = -2L
    const val ERR_CONTEXT_INIT_FAILED = -3L
    const val ERR_INSUFFICIENT_MEMORY = -4L
    const val ERR_UNSUPPORTED_BACKEND = -5L
    const val ERR_INVALID_MODEL = -6L

    init {
        try {
            System.loadLibrary("alya_llama")
            isLoaded = true
            Log.i(TAG, "libalya_llama.so successfully loaded")
        } catch (e: UnsatisfiedLinkError) {
            Log.w(TAG, "libalya_llama.so not yet loaded or not present in unit test environment: ${e.message}")
            isLoaded = false
        }
    }

    fun isNativeLoaded(): Boolean = isLoaded

    @JvmStatic
    external fun nativeInit(nativeLibDir: String?): Boolean

    @JvmStatic
    external fun nativeGetBackendDevices(): String

    @JvmStatic
    external fun nativeLoadModel(
        modelPath: String,
        nThreads: Int,
        nCtx: Int,
        nBatch: Int,
        nUBatch: Int,
        nGpuLayers: Int,
        useMmap: Boolean,
        useMlock: Boolean,
        flashAttn: Boolean,
        cacheTypeK: Int,
        cacheTypeV: Int,
        temp: Float,
        topP: Float,
        topK: Int,
        repeatPenalty: Float
    ): Long

    @JvmStatic
    external fun nativeProcessSystemPrompt(handle: Long, systemPrompt: String): Int

    @JvmStatic
    external fun nativeProcessUserPrompt(handle: Long, userPrompt: String, nPredict: Int): Int

    @JvmStatic
    external fun nativeGenerateNextToken(handle: Long): String?

    @JvmStatic
    external fun nativeCancel(handle: Long)

    @JvmStatic
    external fun nativeGetParamCount(handle: Long): Long

    @JvmStatic
    external fun nativeGetModelSize(handle: Long): Long

    @JvmStatic
    external fun nativeGetModelDesc(handle: Long): String

    @JvmStatic
    external fun nativeGetModelMetadata(handle: Long): String

    @JvmStatic
    external fun nativeGetGenerationTimings(handle: Long): String

    @JvmStatic
    external fun nativeUnloadModel(handle: Long)

    @JvmStatic
    external fun nativeShutdown()

    @JvmStatic
    external fun nativeSystemInfo(): String
}
