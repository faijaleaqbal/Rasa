package com.alya.aiagent.local

import android.content.Context
import android.net.Uri
import java.io.File
import java.io.IOException
import java.io.InputStream

/**
 * PocketPal-style streaming GGUF header parser.
 * Reads metadata without loading model weights into memory.
 */
object GgufMetadataReader {

    private val GGUF_MAGIC = byteArrayOf(0x47, 0x47, 0x55, 0x46) // "GGUF"

    enum class ValueType(val code: Int) {
        UINT8(0), INT8(1), UINT16(2), INT16(3),
        UINT32(4), INT32(5), FLOAT32(6), BOOL(7),
        STRING(8), ARRAY(9), UINT64(10), INT64(11), FLOAT64(12);

        companion object {
            private val map = entries.associateBy(ValueType::code)
            fun fromCode(code: Int): ValueType = map[code]
                ?: throw IOException("Unknown GGUF value type: $code")
        }
    }

    private val FILE_TYPES = mapOf(
        0 to "ALL_F32",
        1 to "MOSTLY_F16",
        2 to "MOSTLY_Q4_0",
        3 to "MOSTLY_Q4_1",
        7 to "MOSTLY_Q8_0",
        8 to "MOSTLY_Q5_0",
        9 to "MOSTLY_Q5_1",
        10 to "MOSTLY_Q2_K",
        11 to "MOSTLY_Q3_K_S",
        12 to "MOSTLY_Q3_K_M",
        13 to "MOSTLY_Q3_K_L",
        14 to "MOSTLY_Q4_K_S",
        15 to "MOSTLY_Q4_K_M",
        16 to "MOSTLY_Q5_K_S",
        17 to "MOSTLY_Q5_K_M",
        18 to "MOSTLY_Q6_K",
        19 to "MOSTLY_IQ2_XXS",
        20 to "MOSTLY_IQ2_XS",
        21 to "MOSTLY_Q2_K_S",
        22 to "MOSTLY_IQ3_XS",
        23 to "MOSTLY_IQ3_XXS",
        24 to "MOSTLY_IQ1_S",
        25 to "MOSTLY_IQ4_NL",
        26 to "MOSTLY_IQ3_S",
        27 to "MOSTLY_IQ3_M",
        28 to "MOSTLY_IQ2_S",
        29 to "MOSTLY_IQ2_M",
        30 to "MOSTLY_IQ4_XS",
        31 to "MOSTLY_IQ1_M",
        32 to "MOSTLY_BF16"
    )

    fun isGgufFile(file: File): Boolean {
        if (!file.exists() || file.length() < 8) return false
        return try {
            file.inputStream().buffered().use { isValidMagic(it) }
        } catch (e: Exception) {
            false
        }
    }

    fun isGgufUri(context: Context, uri: Uri): Boolean {
        return try {
            context.contentResolver.openInputStream(uri)?.buffered()?.use { isValidMagic(it) } == true
        } catch (e: Exception) {
            false
        }
    }

    private fun isValidMagic(input: InputStream): Boolean {
        val magic = ByteArray(4)
        if (input.read(magic) != 4) return false
        return magic.contentEquals(GGUF_MAGIC)
    }

    @Throws(IOException::class)
    fun readMetadata(file: File): GgufMetadata {
        file.inputStream().buffered().use { stream ->
            return parseGguf(stream, file.name, file.length())
        }
    }

    @Throws(IOException::class)
    fun readMetadata(input: InputStream, fallbackName: String = "model.gguf", fileSizeBytes: Long = 0): GgufMetadata {
        return parseGguf(input, fallbackName, fileSizeBytes)
    }

    /**
     * PocketPal-style memory calculation:
     * Model Size + KV Cache (n_layers, n_ctx, heads, head_dim) + Compute Graph buffer + native overhead
     */
    fun estimateRequiredRamBytes(
        fileSizeBytes: Long,
        contextLength: Int = 2048,
        layerCount: Int = 24,
        embeddingLength: Int = 896,
        headCount: Int = 14,
        headCountKv: Int = 2
    ): Long {
        val effectiveLayers = if (layerCount > 0) layerCount else 24
        val effectiveCtx = minOf(if (contextLength > 0) contextLength else 2048, 4096)
        val effectiveEmbd = if (embeddingLength > 0) embeddingLength else 896
        val effectiveHeads = if (headCount > 0) headCount else 14
        val effectiveHeadsKv = if (headCountKv > 0) headCountKv else maxOf(1, effectiveHeads / 4)
        val headDim = maxOf(32, effectiveEmbd / maxOf(1, effectiveHeads))

        // KV Cache = 2 (K and V) * n_layers * n_ctx * n_heads_kv * head_dim * 2 (f16 bytes)
        val kvCacheBytes = 2L * effectiveLayers * effectiveCtx * effectiveHeadsKv * headDim * 2L

        // Compute / Graph scratch overhead: ~48 MB
        val computeBufferBytes = 48L * 1024L * 1024L

        // Native llama.cpp runtime overhead: ~32 MB
        val nativeOverheadBytes = 32L * 1024L * 1024L

        return fileSizeBytes + kvCacheBytes + computeBufferBytes + nativeOverheadBytes
    }

    private fun parseGguf(input: InputStream, fallbackName: String, fileSizeBytes: Long): GgufMetadata {
        if (!isValidMagic(input)) {
            throw IOException("Invalid GGUF magic header. Expected 'GGUF'")
        }

        val version = readLEInt32(input)
        val tensorCount = readLEInt64(input)
        val kvCount = readLEInt64(input)

        val metadataMap = mutableMapOf<String, Any>()
        val skipKeys = setOf(
            "tokenizer.ggml.tokens",
            "tokenizer.ggml.scores",
            "tokenizer.ggml.token_type",
            "tokenizer.ggml.merges"
        )

        val maxKv = minOf(kvCount, 2000L).toInt()
        for (i in 0 until maxKv) {
            val key = readString(input)
            val typeCode = readLEInt32(input)
            val valueType = ValueType.fromCode(typeCode)

            if (key in skipKeys) {
                skipValue(input, valueType)
            } else {
                val value = parseValue(input, valueType)
                if (value != null) {
                    metadataMap[key] = value
                }
            }
        }

        val architecture = (metadataMap["general.architecture"] as? String) ?: "llama"
        val name = (metadataMap["general.basename"] as? String)
            ?: (metadataMap["general.name"] as? String)
            ?: fallbackName.removeSuffix(".gguf")

        val contextLength = (metadataMap["$architecture.context_length"] as? Number)?.toInt()
            ?: (metadataMap["general.context_length"] as? Number)?.toInt()
            ?: 2048

        val embeddingLength = (metadataMap["$architecture.embedding_length"] as? Number)?.toInt()
            ?: (metadataMap["general.embedding_length"] as? Number)?.toInt()
            ?: 896

        val layerCount = (metadataMap["$architecture.block_count"] as? Number)?.toInt()
            ?: (metadataMap["$architecture.layer_count"] as? Number)?.toInt()
            ?: 24

        val headCount = (metadataMap["$architecture.attention.head_count"] as? Number)?.toInt()
            ?: 14

        val headCountKv = (metadataMap["$architecture.attention.head_count_kv"] as? Number)?.toInt()
            ?: 2

        val feedForwardLength = (metadataMap["$architecture.feed_forward_length"] as? Number)?.toInt()
            ?: 4864

        val vocabSize = (metadataMap["$architecture.vocab_size"] as? Number)?.toInt()
            ?: (metadataMap["general.vocab_size"] as? Number)?.toInt()
            ?: 151936

        val fileType = (metadataMap["general.file_type"] as? Number)?.toInt() ?: 15
        val rawQuant = FILE_TYPES[fileType] ?: "Q4_K_M"
        val quantization = rawQuant.removePrefix("MOSTLY_")

        val chatTemplate = (metadataMap["tokenizer.chat_template"] as? String)
            ?: (metadataMap["tokenizer.ggml.chat_template"] as? String)

        var paramCount = (metadataMap["general.parameter_count"] as? Number)?.toLong() ?: 0L
        if (paramCount <= 0L && fileSizeBytes > 0L) {
            paramCount = (fileSizeBytes / 0.57).toLong()
        }

        return GgufMetadata(
            version = version,
            tensorCount = tensorCount,
            kvCount = kvCount,
            architecture = architecture,
            name = name,
            contextLength = contextLength,
            parameterCount = paramCount,
            embeddingLength = embeddingLength,
            layerCount = layerCount,
            headCount = headCount,
            headCountKv = headCountKv,
            feedForwardLength = feedForwardLength,
            vocabSize = vocabSize,
            fileType = fileType,
            quantization = quantization,
            chatTemplate = chatTemplate,
            isSupported = true,
            validationError = null
        )
    }

    private fun parseValue(input: InputStream, type: ValueType): Any? {
        return when (type) {
            ValueType.UINT8 -> input.read().toUByte().toInt()
            ValueType.INT8 -> input.read().toByte().toInt()
            ValueType.UINT16 -> readLEUInt16(input)
            ValueType.INT16 -> readLEInt16(input)
            ValueType.UINT32 -> readLEUInt32(input)
            ValueType.INT32 -> readLEInt32(input)
            ValueType.FLOAT32 -> Float.fromBits(readLEInt32(input))
            ValueType.BOOL -> (input.read() != 0)
            ValueType.STRING -> readString(input)
            ValueType.ARRAY -> {
                val elemType = ValueType.fromCode(readLEInt32(input))
                val length = readLEInt64(input).toInt()
                if (length > 128) {
                    repeat(length) { skipValue(input, elemType) }
                    "Array(${elemType.name}, $length items)"
                } else {
                    val list = ArrayList<Any?>(length)
                    repeat(length) {
                        list.add(parseValue(input, elemType))
                    }
                    list
                }
            }
            ValueType.UINT64 -> readLEInt64(input)
            ValueType.INT64 -> readLEInt64(input)
            ValueType.FLOAT64 -> Double.fromBits(readLEInt64(input))
        }
    }

    private fun skipValue(input: InputStream, type: ValueType) {
        when (type) {
            ValueType.UINT8, ValueType.INT8, ValueType.BOOL -> input.skipFully(1)
            ValueType.UINT16, ValueType.INT16 -> input.skipFully(2)
            ValueType.UINT32, ValueType.INT32, ValueType.FLOAT32 -> input.skipFully(4)
            ValueType.UINT64, ValueType.INT64, ValueType.FLOAT64 -> input.skipFully(8)
            ValueType.STRING -> {
                val len = readLEInt64(input)
                input.skipFully(len)
            }
            ValueType.ARRAY -> {
                val elemType = ValueType.fromCode(readLEInt32(input))
                val length = readLEInt64(input).toInt()
                repeat(length) { skipValue(input, elemType) }
            }
        }
    }

    private fun readString(input: InputStream): String {
        val len = readLEInt64(input)
        if (len < 0 || len > 10 * 1024 * 1024) throw IOException("String length invalid: $len")
        val bytes = ByteArray(len.toInt())
        if (bytes.isNotEmpty()) input.readFully(bytes)
        return String(bytes, Charsets.UTF_8)
    }

    private fun readLEUInt16(input: InputStream): Int {
        val b0 = input.read(); val b1 = input.read()
        if (b1 == -1) throw IOException("Unexpected EOF")
        return (b1 and 0xFF shl 8) or (b0 and 0xFF)
    }

    private fun readLEInt16(input: InputStream): Short {
        return readLEUInt16(input).toShort()
    }

    private fun readLEUInt32(input: InputStream): Long {
        val b0 = input.read(); val b1 = input.read(); val b2 = input.read(); val b3 = input.read()
        if (b3 == -1) throw IOException("Unexpected EOF")
        return ((b3.toLong() and 0xFF) shl 24) or
               ((b1.toLong() and 0xFF) shl 8) or
               ((b2.toLong() and 0xFF) shl 16) or
               (b0.toLong() and 0xFF)
    }

    private fun readLEInt32(input: InputStream): Int {
        val b0 = input.read(); val b1 = input.read(); val b2 = input.read(); val b3 = input.read()
        if (b3 == -1) throw IOException("Unexpected EOF")
        return (b3 and 0xFF shl 24) or (b2 and 0xFF shl 16) or (b1 and 0xFF shl 8) or (b0 and 0xFF)
    }

    private fun readLEInt64(input: InputStream): Long {
        val bytes = ByteArray(8)
        input.readFully(bytes)
        return (bytes[7].toLong() and 0xFFL shl 56) or
               (bytes[6].toLong() and 0xFFL shl 48) or
               (bytes[5].toLong() and 0xFFL shl 40) or
               (bytes[4].toLong() and 0xFFL shl 32) or
               (bytes[3].toLong() and 0xFFL shl 24) or
               (bytes[2].toLong() and 0xFFL shl 16) or
               (bytes[1].toLong() and 0xFFL shl 8) or
               (bytes[0].toLong() and 0xFFL)
    }

    private fun InputStream.readFully(buf: ByteArray) {
        var off = 0
        while (off < buf.size) {
            val n = read(buf, off, buf.size - off)
            if (n == -1) throw IOException("Unexpected EOF while filling buffer")
            off += n
        }
    }

    private fun InputStream.skipFully(n: Long) {
        var remaining = n
        val scratch = ByteArray(4096)
        while (remaining > 0) {
            val skipped = skip(remaining)
            if (skipped > 0) {
                remaining -= skipped
            } else {
                val read = read(scratch, 0, minOf(remaining, scratch.size.toLong()).toInt())
                if (read == -1) throw IOException("Unexpected EOF while skipping bytes")
                remaining -= read
            }
        }
    }
}
