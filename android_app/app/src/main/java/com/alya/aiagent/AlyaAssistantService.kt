package com.alya.aiagent

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Log
import androidx.core.app.NotificationCompat
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.Executors

class AlyaAssistantService : Service(), TextToSpeech.OnInitListener {

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private val executor = Executors.newSingleThreadExecutor()
    private val TAG = "AlyaAssistantService"
    private val CHANNEL_ID = "AlyaVoiceAssistantChannel"

    private var isListeningForWakeWord = true
    private var isAwaitingUserCommand = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(1001, buildForegroundNotification("Alya Voice Assistant Active (Listening for 'Hey Alya')"))
        
        tts = TextToSpeech(this, this)
        initSpeechRecognizer()
        startContinuousWakeWordListening()
        Log.i(TAG, "Alya Continuous Wake-Word Voice Service Started.")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Alya Voice Assistant Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildForegroundNotification(statusText: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("🤖 Alya AI Mobile Agent")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("hi", "IN")
        }
    }

    private fun initSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: android.os.Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            
            override fun onError(error: Int) {
                // Auto-restart continuous listening on timeout
                if (isListeningForWakeWord) {
                    startContinuousWakeWordListening()
                }
            }

            override fun onResults(results: android.os.Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    val speech = matches[0].lowercase().trim()
                    Log.i(TAG, "Heard speech: $speech")

                    // 1. Wake Word Detection Trigger ("Hey Alya", "Alya", "Ok Alya")
                    if (isListeningForWakeWord && (speech.contains("hey alya") || speech.contains("alya") || speech.contains("ok alya") || speech.contains("hai alya"))) {
                        isListeningForWakeWord = false
                        isAwaitingUserCommand = true
                        speakOut("Haan, boliye main sun rahi hoon.")
                        startCommandListening()
                    }
                    // 2. Active Command Processing
                    else if (isAwaitingUserCommand) {
                        isAwaitingUserCommand = false
                        processCommandWithAlya(matches[0])
                    }
                    // Continue listening for wake-word
                    else {
                        startContinuousWakeWordListening()
                    }
                } else {
                    startContinuousWakeWordListening()
                }
            }

            override fun onPartialResults(partialResults: android.os.Bundle?) {}
            override fun onEvent(eventType: Int, params: android.os.Bundle?) {}
        })
    }

    fun startContinuousWakeWordListening() {
        isListeningForWakeWord = true
        isAwaitingUserCommand = false
        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
            }
            speechRecognizer?.startListening(intent)
        } catch (e: Exception) {
            Log.w(TAG, "Error restarting wake-word: ${e.message}")
        }
    }

    fun startCommandListening() {
        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
                putExtra(RecognizerIntent.EXTRA_PROMPT, "Alya is listening to your command...")
            }
            speechRecognizer?.startListening(intent)
        } catch (e: Exception) {
            Log.w(TAG, "Error starting command listening: ${e.message}")
        }
    }

    private fun processCommandWithAlya(userMessage: String) {
        val serverBase = getSharedPreferences("AlyaPrefs", Context.MODE_PRIVATE).getString("server_url", "http://127.0.0.1:5005")
        val endpoint = "$serverBase/webhooks/rest/webhook"

        executor.execute {
            try {
                val url = URL(endpoint)
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                conn.doOutput = true
                conn.connectTimeout = 15000
                conn.readTimeout = 15000

                val payload = JSONObject().apply {
                    put("sender", "android_voice_user")
                    put("message", userMessage)
                }

                val wr = OutputStreamWriter(conn.outputStream)
                wr.write(payload.toString())
                wr.flush()

                if (conn.responseCode == 200) {
                    val responseText = conn.inputStream.bufferedReader().use { it.readText() }
                    val replies = JSONArray(responseText)
                    val combinedText = StringBuilder()

                    for (i in 0 until replies.length()) {
                        val reply = replies.getJSONObject(i)
                        val text = reply.optString("text")
                        if (text.isNotEmpty()) {
                            combinedText.append(text).append("\n\n")
                        }
                    }

                    val finalReply = combinedText.toString().trim()
                    speakOut(finalReply)

                    // If security verification was asked, listen for user's "Haan Confirm" or "Cancel" reply
                    if (finalReply.contains("Security Verification Required")) {
                        Thread.sleep(1500)
                        isAwaitingUserCommand = true
                        startCommandListening()
                        return@execute
                    }
                }
            } catch (e: Exception) {
                speakOut("Server se connection me issue aaya. Kripya URL check karein.")
            } finally {
                // Resume background wake-word detection
                if (!isAwaitingUserCommand) {
                    startContinuousWakeWordListening()
                }
            }
        }
    }

    private fun speakOut(text: String) {
        val cleanSpeech = text.replace("*", "").replace("#", "").replace("`", "")
        tts?.speak(cleanSpeech, TextToSpeech.QUEUE_FLUSH, null, "AlyaVoiceId")
    }

    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer?.destroy()
        tts?.stop()
        tts?.shutdown()
    }
}
