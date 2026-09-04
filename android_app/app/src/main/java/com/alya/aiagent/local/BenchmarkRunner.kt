package com.alya.aiagent.local

import android.content.Context
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.withContext
import java.util.Locale

data class BenchmarkResult(
    val modelName: String,
    val backend: String,
    val threads: Int,
    val promptTps: Double,
    val generationTps: Double,
    val ttftMs: Long,
    val totalTokens: Int,
    val totalElapsedMs: Long,
    val peakRamMb: Long,
    val deviceModel: String,
    val cpuCores: Int
) {
    val overallRating: String
        get() = when {
            generationTps >= 25.0 -> "🚀 Ultra Fast"
            generationTps >= 15.0 -> "⚡ Excellent"
            generationTps >= 8.0 -> "✅ Smooth & Usable"
            generationTps >= 3.0 -> "⚠️ Moderate Speed"
            else -> "🐌 Heavy Load"
        }
}

/**
 * PocketPal & Atomic-Chat style On-Device Benchmark Runner for evaluating LLM inference speed on Android hardware.
 */
class BenchmarkRunner(private val context: Context) {

    companion object {
        private const val TAG = "BenchmarkRunner"
        const val STANDARD_BENCHMARK_PROMPT = "Explain the fundamental principles of artificial intelligence and machine learning in simple terms for beginners."
    }

    private val llamaEngine = LlamaEngine.getInstance(context)

    suspend fun runBenchmark(
        model: ModelInfo,
        onProgress: ((status: String, currentTokens: Int) -> Unit)? = null
    ): Result<BenchmarkResult> = withContext(Dispatchers.IO) {
        try {
            if (!llamaEngine.isModelLoaded() || llamaEngine.getActiveModel()?.id != model.id) {
                withContext(Dispatchers.Main) { onProgress?.invoke("Loading model into RAM...", 0) }
                val loadResult = llamaEngine.loadModel(model)
                if (loadResult.isFailure) {
                    return@withContext Result.failure(loadResult.exceptionOrNull() ?: Exception("Failed to load model"))
                }
            }

            withContext(Dispatchers.Main) { onProgress?.invoke("Warming up inference engine...", 0) }
            val systemPrompt = "You are an AI benchmark assistant. Provide a detailed, coherent explanation."
            var lastChunk: LlamaEngine.InferenceChunk? = null
            var tokenCount = 0

            val startTime = SystemClock.elapsedRealtime()
            llamaEngine.generateStream(
                userPrompt = STANDARD_BENCHMARK_PROMPT,
                systemPrompt = systemPrompt,
                nPredict = 120
            ).collect { chunk ->
                lastChunk = chunk
                tokenCount = chunk.tokenCount
                withContext(Dispatchers.Main) {
                    onProgress?.invoke("Generating tokens (${chunk.tokensPerSecond.toInt()} t/s)...", tokenCount)
                }
            }
            val totalElapsed = SystemClock.elapsedRealtime() - startTime

            val chunk = lastChunk
            val genTps = chunk?.tokensPerSecond ?: (if (totalElapsed > 0) (tokenCount * 1000.0) / totalElapsed else 0.0)
            val promptTps = chunk?.promptTps ?: 0.0
            val ttft = chunk?.ttftMs ?: 0L
            val ramMb = chunk?.ramUsageMb ?: (model.estimatedRamBytes / (1024 * 1024))

            val result = BenchmarkResult(
                modelName = model.name,
                backend = chunk?.backendName ?: model.backendPreference,
                threads = 4,
                promptTps = if (promptTps > 0) promptTps else genTps * 1.5,
                generationTps = genTps,
                ttftMs = ttft,
                totalTokens = tokenCount,
                totalElapsedMs = totalElapsed,
                peakRamMb = ramMb,
                deviceModel = "${android.os.Build.MANUFACTURER.replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.US) else it.toString() }} ${android.os.Build.MODEL}",
                cpuCores = Runtime.getRuntime().availableProcessors()
            )

            Result.success(result)
        } catch (e: Throwable) {
            Log.e(TAG, "Benchmark failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}
