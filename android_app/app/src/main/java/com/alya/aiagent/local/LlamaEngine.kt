package com.alya.aiagent.local

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import android.os.Debug
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale

/**
 * High-level orchestration engine for on-device GGUF inference via llama.cpp.
 * Implements PocketPal-style local model management:
 * - Dynamic device-aware memory estimation (Model + KV Cache + Compute Graph + Runtime overhead)
 * - Configurable context parameters (n_ctx, n_batch, n_ubatch, n_threads, n_gpu_layers, mmap, flash_attn)
 * - Hardware backend detection (CPU / ARM NEON, GPU / OpenCL / Adreno, NPU) with graceful fallback
 * - Real-time streaming tokens with cancellation and PocketPal performance breakdown (TTFT, prompt t/s, gen t/s)
 * - Safe model unloading and model switching
 */
class LlamaEngine private constructor(private val context: Context) {

    companion object {
        private const val TAG = "LlamaEngine"

        @Volatile
        private var INSTANCE: LlamaEngine? = null

        fun getInstance(context: Context): LlamaEngine {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: LlamaEngine(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    data class ContextParams(
        val nCtx: Int = 2048,
        val nBatch: Int = 512,
        val nUBatch: Int = 512,
        val nThreads: Int = 4,
        val nGpuLayers: Int = 0,
        val useMmap: Boolean = true,
        val useMlock: Boolean = false,
        val flashAttn: Boolean = false,
        val cacheTypeK: Int = 0,
        val cacheTypeV: Int = 0,
        val temp: Float = 0.7f,
        val topP: Float = 0.9f,
        val topK: Int = 40,
        val repeatPenalty: Float = 1.1f,
        val backendPreference: String = "Auto"
    )

    data class BackendDevice(
        val type: String,
        val name: String,
        val description: String,
        val backend: String
    )

    data class MemoryEstimate(
        val requiredBytes: Long,
        val availableBytes: Long,
        val totalBytes: Long,
        val isSafeToLoad: Boolean,
        val message: String
    )

    data class InferenceChunk(
        val text: String,
        val isFirstToken: Boolean = false,
        val isComplete: Boolean = false,
        val isCancelled: Boolean = false,
        val tokenCount: Int = 0,
        val tokensPerSecond: Double = 0.0,
        val promptTimeMs: Long = 0,
        val genTimeMs: Long = 0,
        val ttftMs: Long = 0,
        val promptTps: Double = 0.0,
        val elapsedMs: Long = 0,
        val ramUsageMb: Long = 0,
        val backendName: String = "CPU"
    )

    data class LoadMetrics(
        val loadTimeMs: Long,
        val ramUsedMb: Long,
        val paramCount: Long,
        val modelDesc: String,
        val backendName: String,
        val contextSize: Int
    )

    private val mutex = Mutex()
    private val inferenceDispatcher = Dispatchers.IO.limitedParallelism(1)

    @Volatile
    private var activeModel: ModelInfo? = null

    @Volatile
    private var activeNativeHandle: Long = 0L

    @Volatile
    private var isGenerating = false

    @Volatile
    private var activeBackendName: String = "CPU"

    init {
        try {
            val nativeLibDir = context.applicationInfo.nativeLibraryDir
            LlamaNative.nativeInit(nativeLibDir)
            Log.i(TAG, "Llama engine initialized with native lib dir: $nativeLibDir")
        } catch (e: Throwable) {
            Log.w(TAG, "LlamaNative nativeInit deferred: ${e.message}")
        }
    }

    fun isModelLoaded(): Boolean = activeNativeHandle > 0L && activeModel != null

    fun getActiveModel(): ModelInfo? = activeModel

    fun getActiveBackendName(): String = activeBackendName

    fun getUsedMemoryMb(): Long {
        val runtime = Runtime.getRuntime()
        val heapUsed = (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024)
        val nativeHeap = Debug.getNativeHeapAllocatedSize() / (1024 * 1024)
        return heapUsed + nativeHeap
    }

    fun getAvailableBackends(): List<BackendDevice> {
        val backends = mutableListOf<BackendDevice>()
        try {
            val jsonStr = LlamaNative.nativeGetBackendDevices()
            if (!jsonStr.isNullOrBlank()) {
                val array = JSONArray(jsonStr)
                for (i in 0 until array.length()) {
                    val obj = array.getJSONObject(i)
                    backends.add(
                        BackendDevice(
                            type = obj.optString("type", "CPU"),
                            name = obj.optString("name", "CPU"),
                            description = obj.optString("description", ""),
                            backend = obj.optString("backend", "CPU")
                        )
                    )
                }
            }
        } catch (e: Throwable) {
            Log.w(TAG, "Failed to parse native backends: ${e.message}")
        }
        if (backends.isEmpty()) {
            backends.add(BackendDevice("CPU", "CPU (ARM NEON)", "ARM64 CPU Backend", "CPU"))
        }
        return backends
    }

    fun checkMemorySafety(model: ModelInfo, params: ContextParams): MemoryEstimate {
        val actManager = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
        val memInfo = ActivityManager.MemoryInfo()
        actManager?.getMemoryInfo(memInfo)

        val totalMem = if (memInfo.totalMem > 0) memInfo.totalMem else (6L * 1024 * 1024 * 1024L)
        val availMem = if (memInfo.availMem > 0) memInfo.availMem else (2L * 1024 * 1024 * 1024L)

        val requiredBytes = GgufMetadataReader.estimateRequiredRamBytes(
            fileSizeBytes = model.sizeBytes,
            contextLength = params.nCtx,
            layerCount = model.layerCount,
            embeddingLength = model.embeddingLength,
            headCount = model.headCount,
            headCountKv = model.headCountKv
        )

        // PocketPal memory guardrail: safe to load if available RAM can hold model weights
        val isSafe = (availMem >= model.sizeBytes) && !memInfo.lowMemory

        val reqMb = requiredBytes / (1024 * 1024)
        val availGb = String.format(Locale.US, "%.2f", availMem / (1024.0 * 1024.0 * 1024.0))

        val msg = if (isSafe) {
            "Memory OK (~$reqMb MB estimated, ~$availGb GB available)"
        } else {
            "Not enough memory for this model. Estimated: ~$reqMb MB, Available: ~$availGb GB"
        }

        return MemoryEstimate(
            requiredBytes = requiredBytes,
            availableBytes = availMem,
            totalBytes = totalMem,
            isSafeToLoad = isSafe,
            message = msg
        )
    }

    suspend fun loadModel(
        model: ModelInfo,
        params: ContextParams = ContextParams()
    ): Result<LoadMetrics> = withContext(inferenceDispatcher) {
        mutex.withLock {
            try {
                val modelFile = File(model.filePath)
                if (!modelFile.exists() || !modelFile.canRead()) {
                    return@withContext Result.failure(IllegalArgumentException("Model file unreadable or not found at: ${model.filePath}"))
                }

                // 1. Device-aware memory pre-flight validation
                val memCheck = checkMemorySafety(model, params)
                if (!memCheck.isSafeToLoad) {
                    Log.e(TAG, "Memory check failed: ${memCheck.message}")
                    return@withContext Result.failure(IllegalStateException(memCheck.message))
                }

                // 2. Unload existing model context safely
                if (activeNativeHandle > 0L) {
                    unloadModelInternal()
                }

                val startRam = getUsedMemoryMb()
                val startTime = SystemClock.elapsedRealtime()

                Log.i(TAG, "Loading GGUF model: ${model.name} (${model.filePath}) with backend preference: ${params.backendPreference}")

                var handle = LlamaNative.nativeLoadModel(
                    modelPath = model.filePath,
                    nThreads = params.nThreads,
                    nCtx = params.nCtx,
                    nBatch = params.nBatch,
                    nUBatch = params.nUBatch,
                    nGpuLayers = params.nGpuLayers,
                    useMmap = params.useMmap,
                    useMlock = params.useMlock,
                    flashAttn = params.flashAttn,
                    cacheTypeK = params.cacheTypeK,
                    cacheTypeV = params.cacheTypeV,
                    temp = params.temp,
                    topP = params.topP,
                    topK = params.topK,
                    repeatPenalty = params.repeatPenalty
                )

                // 3. Graceful fallback to CPU if GPU/OpenCL offload fails or is unsupported
                if (handle <= 0L && params.nGpuLayers > 0) {
                    Log.w(TAG, "GPU offload init failed (code=$handle). Falling back to CPU backend...")
                    handle = LlamaNative.nativeLoadModel(
                        modelPath = model.filePath,
                        nThreads = params.nThreads,
                        nCtx = params.nCtx,
                        nBatch = params.nBatch,
                        nUBatch = params.nUBatch,
                        nGpuLayers = 0,
                        useMmap = params.useMmap,
                        useMlock = params.useMlock,
                        flashAttn = false,
                        cacheTypeK = 0,
                        cacheTypeV = 0,
                        temp = params.temp,
                        topP = params.topP,
                        topK = params.topK,
                        repeatPenalty = params.repeatPenalty
                    )
                }

                if (handle == LlamaNative.ERR_CONTEXT_INIT_FAILED) {
                    return@withContext Result.failure(
                        IllegalStateException("Failed to allocate context buffer for model (${params.nCtx} context length).")
                    )
                } else if (handle <= 0L) {
                    return@withContext Result.failure(
                        IllegalStateException("Failed to load GGUF model into memory (native error code: $handle)")
                    )
                }

                val loadTime = SystemClock.elapsedRealtime() - startTime
                val endRam = getUsedMemoryMb()
                val ramUsed = maxOf(0L, endRam - startRam)

                var paramCount = model.parameterCount
                var modelDesc = model.name
                var backendName = if (params.nGpuLayers > 0) "GPU" else "CPU"

                try {
                    val metaJson = LlamaNative.nativeGetModelMetadata(handle)
                    if (metaJson.isNotBlank()) {
                        val obj = JSONObject(metaJson)
                        val p = obj.optLong("param_count", 0L)
                        if (p > 0) paramCount = p
                        modelDesc = obj.optString("desc", model.name)
                        backendName = obj.optString("backend", backendName)
                    }
                } catch (e: Throwable) {
                    Log.w(TAG, "Metadata JSON parsing exception (non-fatal): ${e.message}")
                }

                activeNativeHandle = handle
                activeBackendName = backendName
                activeModel = model.copy(
                    isLoaded = true,
                    state = ModelState.LOADED,
                    parameterCount = paramCount,
                    estimatedRamBytes = memCheck.requiredBytes
                )

                val metrics = LoadMetrics(
                    loadTimeMs = loadTime,
                    ramUsedMb = ramUsed,
                    paramCount = paramCount,
                    modelDesc = modelDesc,
                    backendName = backendName,
                    contextSize = params.nCtx
                )

                Log.i(TAG, "Model loaded in ${loadTime}ms. Backend: $backendName. RAM delta: ${ramUsed}MB. Desc: $modelDesc")
                Result.success(metrics)
            } catch (e: Throwable) {
                Log.e(TAG, "Exception while loading model", e)
                Result.failure(e)
            }
        }
    }

    suspend fun unloadModel(): Boolean = withContext(inferenceDispatcher) {
        mutex.withLock {
            unloadModelInternal()
        }
    }

    private fun unloadModelInternal(): Boolean {
        if (activeNativeHandle > 0L) {
            try {
                LlamaNative.nativeCancel(activeNativeHandle)
                LlamaNative.nativeUnloadModel(activeNativeHandle)
                Log.i(TAG, "Native model unloaded successfully")
            } catch (e: Throwable) {
                Log.e(TAG, "Error releasing native model handle", e)
            } finally {
                activeNativeHandle = 0L
                activeModel = null
                isGenerating = false
                activeBackendName = "CPU"
            }
            return true
        }
        return false
    }

    fun cancelGeneration() {
        val handle = activeNativeHandle
        if (handle > 0L) {
            LlamaNative.nativeCancel(handle)
            isGenerating = false
            Log.i(TAG, "Inference generation cancellation signal dispatched")
        }
    }

    fun generateStream(
        userPrompt: String,
        systemPrompt: String? = null,
        nPredict: Int = 1024
    ): Flow<InferenceChunk> = flow {
        val handle = activeNativeHandle
        if (handle <= 0L) {
            throw IllegalStateException("No GGUF model is currently loaded in memory.")
        }

        isGenerating = true
        val startTime = SystemClock.elapsedRealtime()
        var firstTokenTime = 0L
        var tokenCount = 0
        val fullResponse = StringBuilder()

        try {
            if (!systemPrompt.isNullOrBlank()) {
                val sysRes = LlamaNative.nativeProcessSystemPrompt(handle, systemPrompt)
                if (sysRes != 0) {
                    Log.w(TAG, "System prompt returned code: $sysRes")
                }
            }

            val promptStartTime = SystemClock.elapsedRealtime()
            val userRes = LlamaNative.nativeProcessUserPrompt(handle, userPrompt, nPredict)
            val promptElapsed = SystemClock.elapsedRealtime() - promptStartTime

            if (userRes != 0) {
                throw IllegalStateException("Failed to process prompt in native context (error $userRes)")
            }

            val genStartTime = SystemClock.elapsedRealtime()

            while (isGenerating) {
                val token = LlamaNative.nativeGenerateNextToken(handle)
                if (token == null) {
                    break
                }

                if (token.isEmpty()) {
                    continue
                }

                tokenCount++
                val now = SystemClock.elapsedRealtime()
                val genElapsed = now - genStartTime
                val totalElapsed = now - startTime

                val isFirst = if (firstTokenTime == 0L) {
                    firstTokenTime = now
                    true
                } else false

                val ttft = if (firstTokenTime > 0) firstTokenTime - startTime else promptElapsed
                val tps = if (genElapsed > 0) (tokenCount * 1000.0) / genElapsed else 0.0
                fullResponse.append(token)

                emit(
                    InferenceChunk(
                        text = token,
                        isFirstToken = isFirst,
                        isComplete = false,
                        isCancelled = false,
                        tokenCount = tokenCount,
                        tokensPerSecond = tps,
                        promptTimeMs = promptElapsed,
                        genTimeMs = genElapsed,
                        ttftMs = ttft,
                        promptTps = if (promptElapsed > 0) 1000.0 / promptElapsed else 0.0,
                        elapsedMs = totalElapsed,
                        ramUsageMb = getUsedMemoryMb(),
                        backendName = activeBackendName
                    )
                )
            }

            val totalElapsed = SystemClock.elapsedRealtime() - startTime
            val finalGenElapsed = SystemClock.elapsedRealtime() - genStartTime
            val finalTps = if (finalGenElapsed > 0) (tokenCount * 1000.0) / finalGenElapsed else 0.0
            val finalTtft = if (firstTokenTime > 0) firstTokenTime - startTime else promptElapsed

            emit(
                InferenceChunk(
                    text = "",
                    isFirstToken = false,
                    isComplete = true,
                    isCancelled = !isGenerating && tokenCount == 0,
                    tokenCount = tokenCount,
                    tokensPerSecond = finalTps,
                    promptTimeMs = promptElapsed,
                    genTimeMs = finalGenElapsed,
                    ttftMs = finalTtft,
                    promptTps = if (promptElapsed > 0) 1000.0 / promptElapsed else 0.0,
                    elapsedMs = totalElapsed,
                    ramUsageMb = getUsedMemoryMb(),
                    backendName = activeBackendName
                )
            )

            Log.i(TAG, "Inference finished: $tokenCount tokens in ${finalGenElapsed}ms (${String.format(Locale.US, "%.2f", finalTps)} tokens/sec)")
        } catch (e: CancellationException) {
            Log.i(TAG, "Inference flow cancelled by collector")
            cancelGeneration()
            throw e
        } catch (e: Throwable) {
            Log.e(TAG, "Error during streaming inference", e)
            throw e
        } finally {
            isGenerating = false
        }
    }.flowOn(inferenceDispatcher)
}
