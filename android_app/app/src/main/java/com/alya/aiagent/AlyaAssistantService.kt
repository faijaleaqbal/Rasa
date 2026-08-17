package com.alya.aiagent

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Log
import androidx.core.app.NotificationCompat
import java.util.Locale

class AlyaAssistantService : Service(), TextToSpeech.OnInitListener {

    companion object {
        const val TAG = "AlyaAssistantService"
        const val CHANNEL_ID = "AlyaVoiceAssistantChannel"
        const val NOTIFICATION_ID = 1001
        var isServiceRunning = false
    }

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    private var isListening = false
    private var isDestroyed = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        isServiceRunning = true
        isDestroyed = false
        
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildForegroundNotification("Listening for \"Hey Alya\"..."))
        
        tts = TextToSpeech(this, this)
        initSpeechRecognizerOnMain()
        Log.i(TAG, "Alya Continuous Wake-Word Voice Service Started.")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isListening && !isDestroyed) {
            startWakeWordListening()
        }
        return START_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Alya Voice Assistant",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Background 'Hey Alya' Wake Word & Voice Assistant"
                setShowBadge(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildForegroundNotification(statusText: String): Notification {
        val tapIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, tapIntent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT else PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("🤖 Alya AI Assistant")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
        manager?.notify(NOTIFICATION_ID, buildForegroundNotification(text))
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("hi", "IN")
        }
    }

    private fun initSpeechRecognizerOnMain() {
        mainHandler.post {
            try {
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {
                        Log.d(TAG, "SpeechRecognizer ready for wake word")
                    }
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}

                    override fun onError(error: Int) {
                        Log.d(TAG, "Wake word recognizer error: $error. Scheduling restart...")
                        isListening = false
                        scheduleRestart(400)
                    }

                    override fun onResults(results: Bundle?) {
                        isListening = false
                        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if (!matches.isNullOrEmpty()) {
                            val speech = matches[0].lowercase(Locale.ROOT).trim()
                            Log.i(TAG, "Heard background phrase: $speech")

                            if (isWakeWordMatch(speech)) {
                                Log.i(TAG, "Wake word DETECTED! Launching Alya Popup...")
                                triggerAlyaPopup()
                                return
                            }
                        }
                        scheduleRestart(300)
                    }

                    override fun onPartialResults(partialResults: Bundle?) {
                        val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if (!matches.isNullOrEmpty()) {
                            val speech = matches[0].lowercase(Locale.ROOT).trim()
                            if (isWakeWordMatch(speech)) {
                                Log.i(TAG, "Wake word detected in partial stream: $speech")
                                isListening = false
                                try {
                                    speechRecognizer?.stopListening()
                                } catch (e: Exception) {}
                                triggerAlyaPopup()
                            }
                        }
                    }

                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
                startWakeWordListening()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize SpeechRecognizer: ${e.message}")
                scheduleRestart(2000)
            }
        }
    }

    private fun isWakeWordMatch(speech: String): Boolean {
        val triggers = listOf(
            "hey alya", "hey alia", "hey aleya", "hey aalya",
            "ok alya", "ok alia", "hi alya", "hi alia",
            "alya", "alia", "aalya", "sun alya", "hai alya",
            "hello alya", "oye alya", "sun aaliya", "aalia"
        )
        return triggers.any { speech.contains(it) }
    }

    private fun triggerAlyaPopup() {
        // 1. Haptic Feedback
        try {
            val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(120, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                vibrator?.vibrate(120)
            }
        } catch (e: Exception) {}

        // 2. Launch MainActivity as full assistant popup
        try {
            val popupIntent = Intent(applicationContext, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("EXTRA_START_LISTENING", true)
                putExtra("EXTRA_TRIGGER_SOURCE", "WAKE_WORD")
            }
            startActivity(popupIntent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start activity from service: ${e.message}")
        }

        updateNotification("Wake word detected! Alya is active.")

        // Brief delay before re-enabling background wake word listening
        scheduleRestart(5000)
    }

    private fun startWakeWordListening() {
        if (isDestroyed) return
        mainHandler.post {
            try {
                if (speechRecognizer == null) {
                    initSpeechRecognizerOnMain()
                    return@post
                }
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
                }
                speechRecognizer?.startListening(intent)
                isListening = true
            } catch (e: Exception) {
                Log.w(TAG, "Error starting wake word listener: ${e.message}")
                isListening = false
                scheduleRestart(1000)
            }
        }
    }

    private fun scheduleRestart(delayMs: Long) {
        if (isDestroyed) return
        mainHandler.removeCallbacksAndMessages(null)
        mainHandler.postDelayed({
            if (!isDestroyed && !isListening) {
                startWakeWordListening()
            }
        }, delayMs)
    }

    override fun onDestroy() {
        super.onDestroy()
        isDestroyed = true
        isListening = false
        isServiceRunning = false
        mainHandler.removeCallbacksAndMessages(null)
        try {
            speechRecognizer?.cancel()
            speechRecognizer?.destroy()
        } catch (e: Exception) {}
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (e: Exception) {}
        Log.i(TAG, "AlyaAssistantService destroyed.")
    }
}
