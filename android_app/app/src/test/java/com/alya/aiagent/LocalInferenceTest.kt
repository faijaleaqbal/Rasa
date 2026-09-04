package com.alya.aiagent

import com.alya.aiagent.local.GgufMetadataReader
import com.alya.aiagent.local.ModelInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class LocalInferenceTest {

    @Test
    fun test3BParameterLimit_under3B() {
        val model05B = ModelInfo(
            id = "qwen2.5-0.5b",
            name = "Qwen 2.5 0.5B Instruct",
            filePath = "/path/to/qwen.gguf",
            sizeBytes = 491_400_032L,
            parameterCount = 490_000_000L,
            contextLength = 4096,
            quantization = "Q4_K_M",
            architecture = "qwen2",
            isSupported = true
        )
        assertTrue(model05B.isSupported)
        assertEquals("490M params", model05B.formattedParams)
        assertEquals("468.64 MB", model05B.formattedSize)

        val model3BExact = ModelInfo(
            id = "exact-3b",
            name = "Exact 3.0B Model",
            filePath = "/path/to/exact3b.gguf",
            sizeBytes = 1_800_000_000L,
            parameterCount = ModelInfo.MAX_SUPPORTED_PARAMS,
            contextLength = 4096,
            quantization = "Q4_K_M",
            architecture = "llama",
            isSupported = true
        )
        assertTrue(model3BExact.isSupported)
        assertEquals("3B params", model3BExact.formattedParams)
        assertTrue(model3BExact.parameterCount <= ModelInfo.MAX_SUPPORTED_PARAMS)
    }

    @Test
    fun test3BParameterLimit_exceeds3B() {
        val model7B = ModelInfo(
            id = "mistral-7b",
            name = "Mistral 7B Instruct",
            filePath = "/path/to/mistral.gguf",
            sizeBytes = 4_300_000_000L,
            parameterCount = 7_240_000_000L,
            contextLength = 32768,
            quantization = "Q4_K_M",
            architecture = "mistral",
            isSupported = false,
            validationMessage = "Model exceeds 3B parameter limit"
        )
        assertFalse(model7B.isSupported)
        assertEquals("7.24B params", model7B.formattedParams)
        assertTrue(model7B.formattedSize.startsWith("4"))
        assertNotNull(model7B.validationMessage)
    }

    @Test
    fun testSyntheticGgufHeaderParsing() {
        // Build minimal valid GGUF header
        val buffer = ByteBuffer.allocate(1024).order(ByteOrder.LITTLE_ENDIAN)
        // 1. Magic 'GGUF'
        buffer.put(0x47.toByte())
        buffer.put(0x47.toByte())
        buffer.put(0x55.toByte())
        buffer.put(0x46.toByte())
        // 2. Version: 3
        buffer.putInt(3)
        // 3. Tensor count: 10
        buffer.putLong(10L)
        // 4. KV count: 3
        buffer.putLong(3L)

        // KV 1: general.architecture (String = "llama")
        val key1 = "general.architecture".toByteArray(Charsets.UTF_8)
        buffer.putLong(key1.size.toLong())
        buffer.put(key1)
        buffer.putInt(GgufMetadataReader.ValueType.STRING.code)
        val val1 = "llama".toByteArray(Charsets.UTF_8)
        buffer.putLong(val1.size.toLong())
        buffer.put(val1)

        // KV 2: llama.context_length (UInt32 = 4096)
        val key2 = "llama.context_length".toByteArray(Charsets.UTF_8)
        buffer.putLong(key2.size.toLong())
        buffer.put(key2)
        buffer.putInt(GgufMetadataReader.ValueType.UINT32.code)
        buffer.putInt(4096)

        // KV 3: general.parameter_count (UInt64 = 1_500_000_000L)
        val key3 = "general.parameter_count".toByteArray(Charsets.UTF_8)
        buffer.putLong(key3.size.toLong())
        buffer.put(key3)
        buffer.putInt(GgufMetadataReader.ValueType.UINT64.code)
        buffer.putLong(1_500_000_000L)

        val bytes = buffer.array().copyOf(buffer.position())
        val input = ByteArrayInputStream(bytes)

        val metadata = GgufMetadataReader.readMetadata(input, fallbackName = "synthetic.gguf", fileSizeBytes = 1024)
        assertEquals(3, metadata.version)
        assertEquals(10L, metadata.tensorCount)
        assertEquals(3L, metadata.kvCount)
        assertEquals("llama", metadata.architecture)
        assertEquals(4096, metadata.contextLength)
        assertEquals(1_500_000_000L, metadata.parameterCount)
        assertTrue(metadata.isSupported)
        assertNull(metadata.validationError)
    }

    @Test
    fun testRealQwenGgufHeaderIfPresent() {
        val file = File("/home/ubuntu/alya/android_app/test_models/qwen2.5-0.5b-instruct-q4_k_m.gguf")
        if (file.exists()) {
            val metadata = GgufMetadataReader.readMetadata(file)
            assertEquals("qwen2", metadata.architecture)
            assertTrue(metadata.isSupported)
            assertTrue(metadata.parameterCount <= ModelInfo.MAX_SUPPORTED_PARAMS)
            assertTrue(metadata.contextLength > 0)
            assertNotNull(metadata.quantization)
        }
    }
}
