package com.alya.aiagent.local

import android.content.Context
import android.net.Uri
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

/**
 * PocketPal-style Model Manager for ALYA.
 * Discovers, imports, validates, and manages local GGUF models without arbitrary size limits.
 * Model viability is determined by comparing required RAM against available device RAM.
 */
class ModelManager private constructor(private val context: Context) {

    companion object {
        private const val TAG = "ModelManager"
        private const val PREFS_NAME = "AlyaModelPrefs"
        const val KEY_ACTIVE_MODEL_ID = "active_model_id"
        const val KEY_AUTO_RELEASE_MODEL = "auto_release_model"
        const val KEY_DEFAULT_BACKEND = "default_backend_selection"
        const val KEY_DEFAULT_THREADS = "default_threads"
        const val KEY_DEFAULT_CTX = "default_ctx_size"
        const val KEY_USE_MMAP = "default_use_mmap"

        @Volatile
        private var INSTANCE: ModelManager? = null

        fun getInstance(context: Context): ModelManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: ModelManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getModelsDirectory(): File {
        val dir = File(context.filesDir, "models")
        if (!dir.exists()) {
            dir.mkdirs()
        }
        return dir
    }

    fun getExternalModelsDirectory(): File? {
        val extDir = context.getExternalFilesDir(null) ?: return null
        val dir = File(extDir, "models")
        if (!dir.exists()) {
            dir.mkdirs()
        }
        return dir
    }

    fun isAutoReleaseEnabled(): Boolean = prefs.getBoolean(KEY_AUTO_RELEASE_MODEL, true)

    fun setAutoReleaseEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_AUTO_RELEASE_MODEL, enabled).apply()
    }

    fun getPreferredBackend(): String = prefs.getString(KEY_DEFAULT_BACKEND, "Auto") ?: "Auto"

    fun setPreferredBackend(backend: String) {
        prefs.edit().putString(KEY_DEFAULT_BACKEND, backend).apply()
    }

    fun getPreferredThreads(): Int = prefs.getInt(KEY_DEFAULT_THREADS, 4)

    fun setPreferredThreads(threads: Int) {
        prefs.edit().putInt(KEY_DEFAULT_THREADS, threads).apply()
    }

    fun getPreferredContextSize(): Int = prefs.getInt(KEY_DEFAULT_CTX, 2048)

    fun setPreferredContextSize(ctx: Int) {
        prefs.edit().putInt(KEY_DEFAULT_CTX, ctx).apply()
    }

    fun isMmapEnabled(): Boolean = prefs.getBoolean(KEY_USE_MMAP, true)

    fun setMmapEnabled(useMmap: Boolean) {
        prefs.edit().putBoolean(KEY_USE_MMAP, useMmap).apply()
    }

    suspend fun discoverModels(): List<ModelInfo> = withContext(Dispatchers.IO) {
        val models = mutableListOf<ModelInfo>()
        val externalBase = android.os.Environment.getExternalStorageDirectory()
        val downloadDir = android.os.Environment.getExternalStoragePublicDirectory(android.os.Environment.DIRECTORY_DOWNLOADS)
        val dirs = listOfNotNull(
            getModelsDirectory(),
            getExternalModelsDirectory(),
            File(context.filesDir, ""),
            context.getExternalFilesDir(null),
            File(downloadDir, "models"),
            downloadDir,
            File(externalBase, "Models"),
            File(externalBase, "models"),
            File("/sdcard/Android/data/${context.packageName}/files/models"),
            File("/sdcard/Android/data/${context.packageName}/files"),
            File("/sdcard/Download/models"),
            File("/sdcard/Download")
        )
        val seenPaths = mutableSetOf<String>()

        for (dir in dirs) {
            if (!dir.exists() || !dir.isDirectory) continue
            val files = dir.listFiles { f -> f.isFile && f.name.endsWith(".gguf", ignoreCase = true) } ?: continue

            for (file in files) {
                val canonical = try { file.canonicalPath } catch (_: Throwable) { file.absolutePath }
                if (seenPaths.contains(canonical)) continue
                seenPaths.add(canonical)

                try {
                    val metadata = GgufMetadataReader.readMetadata(file)
                    val estRam = GgufMetadataReader.estimateRequiredRamBytes(
                        fileSizeBytes = file.length(),
                        contextLength = metadata.contextLength,
                        layerCount = metadata.layerCount,
                        embeddingLength = metadata.embeddingLength,
                        headCount = metadata.headCount,
                        headCountKv = metadata.headCountKv
                    )

                    val model = ModelInfo(
                        id = file.name,
                        name = if (metadata.name.isNotBlank()) metadata.name else file.nameWithoutExtension,
                        filePath = file.absolutePath,
                        sizeBytes = file.length(),
                        parameterCount = metadata.parameterCount,
                        contextLength = metadata.contextLength,
                        quantization = metadata.quantization,
                        architecture = metadata.architecture,
                        embeddingLength = metadata.embeddingLength,
                        layerCount = metadata.layerCount,
                        headCount = metadata.headCount,
                        headCountKv = metadata.headCountKv,
                        estimatedRamBytes = estRam,
                        backendPreference = getPreferredBackend(),
                        isSupported = true,
                        validationMessage = null,
                        state = ModelState.READY
                    )
                    models.add(model)
                } catch (e: Throwable) {
                    Log.w(TAG, "Failed to parse metadata for ${file.name}: ${e.message}")
                    val fallbackEst = file.length() + (160 * 1024 * 1024L)
                    models.add(
                        ModelInfo(
                            id = file.name,
                            name = file.nameWithoutExtension,
                            filePath = file.absolutePath,
                            sizeBytes = file.length(),
                            parameterCount = (file.length() / 0.57).toLong(),
                            contextLength = 2048,
                            quantization = "Q4_K_M",
                            architecture = "llama",
                            estimatedRamBytes = fallbackEst,
                            backendPreference = getPreferredBackend(),
                            isSupported = true,
                            validationMessage = null,
                            state = ModelState.READY
                        )
                    )
                }
            }
        }

        val activeId = getActiveModelId()
        models.map { if (it.id == activeId) it.copy(isLoaded = true, state = ModelState.LOADED) else it }
    }

    suspend fun importModelFromUri(
        uri: Uri,
        customName: String? = null,
        onProgress: ((bytesRead: Long, totalBytes: Long) -> Unit)? = null
    ): Result<ModelInfo> = withContext(Dispatchers.IO) {
        try {
            val contentResolver = context.contentResolver
            val originalName = getFileNameFromUri(uri) ?: "imported_model.gguf"
            val safeName = if (originalName.endsWith(".gguf", ignoreCase = true)) originalName else "$originalName.gguf"

            val targetDir = getModelsDirectory()
            val targetFile = File(targetDir, safeName)

            // Validate GGUF header before copying
            contentResolver.openInputStream(uri)?.use { _ ->
                if (!GgufMetadataReader.isGgufUri(context, uri)) {
                    return@withContext Result.failure(
                        IllegalArgumentException("Selected file is not a valid GGUF binary format.")
                    )
                }
            }

            var totalBytes = -1L
            contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                val sizeIndex = cursor.getColumnIndex(android.provider.OpenableColumns.SIZE)
                if (sizeIndex != -1 && cursor.moveToFirst()) {
                    totalBytes = cursor.getLong(sizeIndex)
                }
            }

            contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(targetFile).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    var bytesRead: Int
                    var totalRead = 0L
                    while (input.read(buffer).also { bytesRead = it } != -1) {
                        output.write(buffer, 0, bytesRead)
                        totalRead += bytesRead
                        onProgress?.invoke(totalRead, totalBytes)
                    }
                    output.flush()
                }
            }

            val metadata = GgufMetadataReader.readMetadata(targetFile)
            val estRam = GgufMetadataReader.estimateRequiredRamBytes(
                fileSizeBytes = targetFile.length(),
                contextLength = metadata.contextLength,
                layerCount = metadata.layerCount,
                embeddingLength = metadata.embeddingLength,
                headCount = metadata.headCount,
                headCountKv = metadata.headCountKv
            )

            val modelInfo = ModelInfo(
                id = targetFile.name,
                name = customName ?: if (metadata.name.isNotBlank()) metadata.name else targetFile.nameWithoutExtension,
                filePath = targetFile.absolutePath,
                sizeBytes = targetFile.length(),
                parameterCount = metadata.parameterCount,
                contextLength = metadata.contextLength,
                quantization = metadata.quantization,
                architecture = metadata.architecture,
                embeddingLength = metadata.embeddingLength,
                layerCount = metadata.layerCount,
                headCount = metadata.headCount,
                headCountKv = metadata.headCountKv,
                estimatedRamBytes = estRam,
                backendPreference = getPreferredBackend(),
                isSupported = true,
                validationMessage = null,
                state = ModelState.READY
            )

            setActiveModelId(modelInfo.id)
            Result.success(modelInfo)
        } catch (e: Throwable) {
            Log.e(TAG, "Failed to import model from URI: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun importModelFromFile(
        sourceFile: File,
        customName: String? = null
    ): Result<ModelInfo> = withContext(Dispatchers.IO) {
        try {
            if (!sourceFile.exists() || !sourceFile.canRead()) {
                return@withContext Result.failure(IllegalArgumentException("Source file does not exist or cannot be read."))
            }

            if (!GgufMetadataReader.isGgufFile(sourceFile)) {
                return@withContext Result.failure(IllegalArgumentException("Source file is not a valid GGUF binary format."))
            }

            val metadata = GgufMetadataReader.readMetadata(sourceFile)
            val targetDir = getModelsDirectory()
            val targetFile = File(targetDir, sourceFile.name)
            if (sourceFile.absolutePath != targetFile.absolutePath) {
                sourceFile.copyTo(targetFile, overwrite = true)
            }

            val estRam = GgufMetadataReader.estimateRequiredRamBytes(
                fileSizeBytes = targetFile.length(),
                contextLength = metadata.contextLength,
                layerCount = metadata.layerCount,
                embeddingLength = metadata.embeddingLength,
                headCount = metadata.headCount,
                headCountKv = metadata.headCountKv
            )

            val modelInfo = ModelInfo(
                id = targetFile.name,
                name = customName ?: if (metadata.name.isNotBlank()) metadata.name else targetFile.nameWithoutExtension,
                filePath = targetFile.absolutePath,
                sizeBytes = targetFile.length(),
                parameterCount = metadata.parameterCount,
                contextLength = metadata.contextLength,
                quantization = metadata.quantization,
                architecture = metadata.architecture,
                embeddingLength = metadata.embeddingLength,
                layerCount = metadata.layerCount,
                headCount = metadata.headCount,
                headCountKv = metadata.headCountKv,
                estimatedRamBytes = estRam,
                backendPreference = getPreferredBackend(),
                isSupported = true,
                validationMessage = null,
                state = ModelState.READY
            )

            setActiveModelId(modelInfo.id)
            Result.success(modelInfo)
        } catch (e: Throwable) {
            Log.e(TAG, "Failed to import model from file: ${e.message}", e)
            Result.failure(e)
        }
    }

    fun deleteModel(model: ModelInfo): Boolean {
        val file = File(model.filePath)
        if (file.exists()) {
            val deleted = file.delete()
            if (deleted && getActiveModelId() == model.id) {
                setActiveModelId(null)
            }
            return deleted
        }
        return false
    }

    fun getActiveModelId(): String? = prefs.getString(KEY_ACTIVE_MODEL_ID, null)

    fun setActiveModelId(modelId: String?) {
        prefs.edit().putString(KEY_ACTIVE_MODEL_ID, modelId).apply()
    }

    private fun getFileNameFromUri(uri: Uri): String? {
        var result: String? = null
        if (uri.scheme == "content") {
            val cursor = context.contentResolver.query(uri, null, null, null, null)
            cursor?.use {
                if (it.moveToFirst()) {
                    val idx = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                    if (idx != -1) {
                        result = it.getString(idx)
                    }
                }
            }
        }
        if (result == null) {
            result = uri.path
            val cut = result?.lastIndexOf('/') ?: -1
            if (cut != -1) {
                result = result?.substring(cut + 1)
            }
        }
        return result
    }
}
