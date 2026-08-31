package com.alya.aiagent

import com.alya.aiagent.network.AlyaApiClient
import com.alya.aiagent.network.NetworkResult
import com.alya.aiagent.network.RasaButton
import com.alya.aiagent.network.RasaMessage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class NetworkTest {

    private lateinit var apiClient: AlyaApiClient

    @Before
    fun setup() {
        apiClient = AlyaApiClient()
    }

    @Test
    fun testUrlValidation_validHttp() {
        val (isValid, cleanUrl) = apiClient.validateUrl("http://3.90.20.247:5005")
        assertTrue(isValid)
        assertEquals("http://3.90.20.247:5005", cleanUrl)
    }

    @Test
    fun testUrlValidation_validHttps() {
        val (isValid, cleanUrl) = apiClient.validateUrl("https://api.alya.ai/")
        assertTrue(isValid)
        assertEquals("https://api.alya.ai", cleanUrl)
    }

    @Test
    fun testUrlValidation_missingProtocol() {
        val (isValid, cleanUrl) = apiClient.validateUrl("127.0.0.1:5005")
        assertTrue(isValid)
        assertEquals("http://127.0.0.1:5005", cleanUrl)
    }

    @Test
    fun testUrlValidation_rejectCredentials() {
        val (isValid, error) = apiClient.validateUrl("http://admin:secret@3.90.20.247:5005")
        assertFalse(isValid)
        assertTrue(error.contains("credentials", ignoreCase = true))
    }

    @Test
    fun testUrlValidation_emptyUrl() {
        val (isValid, error) = apiClient.validateUrl("   ")
        assertFalse(isValid)
        assertTrue(error.contains("empty", ignoreCase = true))
    }

    @Test
    fun testRasaMessageModel() {
        val buttons = listOf(RasaButton("Check Status", "/status"))
        val msg = RasaMessage(
            recipientId = "test_user",
            text = "Hello from Rasa",
            buttons = buttons
        )
        assertEquals("test_user", msg.recipientId)
        assertEquals("Hello from Rasa", msg.text)
        assertEquals(1, msg.buttons?.size)
        assertEquals("/status", msg.buttons?.first()?.payload)
    }

    @Test
    fun testNetworkResultTypes() {
        val success = NetworkResult.Success("data")
        assertTrue(success is NetworkResult.Success)
        assertEquals("data", success.data)

        val offline = NetworkResult.Offline("No network")
        assertTrue(offline is NetworkResult.Offline)

        val timeout = NetworkResult.Timeout("Timed out")
        assertTrue(timeout is NetworkResult.Timeout)

        val error = NetworkResult.Error(500, "Internal error")
        assertEquals(500, error.code)
    }
}
