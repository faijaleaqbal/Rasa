package com.alya.aiagent

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var tvStatus: TextView
    private lateinit var tvResponse: TextView
    private lateinit var btnMic: Button
    private lateinit var etServerUrl: EditText
    private lateinit var btnSaveServer: Button

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private val executor = Executors.newSingleThreadExecutor()

    private val PERMISSION_REQUEST_CODE = 101

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Simple Dynamic Programmatic Layout (No XML inflate required for clean compilation)
        val layout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(48, 80, 48, 48)
            gravity = android.view.Gravity.CENTER_HORIZONTAL
            setBackgroundColor(android.graphics.Color.parseColor("#0F172A"))
        }

        val tvTitle = TextView(this).apply {
            text = "🤖 Alya AI Voice Assistant"
            textSize = 24f
            setTextColor(android.graphics.Color.WHITE)
            setTypeface(null, android.graphics.Typeface.BOLD)
            gravity = android.view.Gravity.CENTER
        }
        layout.addView(tvTitle)

        val tvSubtitle = TextView(this).apply {
            text = "Gemini-style Autonomous Mobile Agent"
            textSize = 14f
            setTextColor(android.graphics.Color.parseColor("#94A3B8"))
            gravity = android.view.Gravity.CENTER
            setPadding(0, 10, 0, 40)
        }
        layout.addView(tvSubtitle)

        etServerUrl = EditText(this).apply {
            hint = "EC2 Server URL (e.g. http://127.0.0.1:5005)"
            setText(getSharedPreferences("AlyaPrefs", Context.MODE_PRIVATE).getString("server_url", "http://127.0.0.1:5005"))
            setTextColor(android.graphics.Color.WHITE)
            setHintTextColor(android.graphics.Color.GRAY)
            setBackgroundColor(android.graphics.Color.parseColor("#1E293B"))
            setPadding(30, 30, 30, 30)
        }
        layout.addView(etServerUrl)

        btnSaveServer = Button(this).apply {
            text = "Save Server IP"
            setBackgroundColor(android.graphics.Color.parseColor("#3B82F6"))
            setTextColor(android.graphics.Color.WHITE)
            setOnClickListener {
                val url = etServerUrl.text.toString().trim()
                getSharedPreferences("AlyaPrefs", Context.MODE_PRIVATE).edit().putString("server_url", url).apply()
                Toast.makeText(this@MainActivity, "Server URL Saved: $url", Toast.LENGTH_SHORT).show()
            }
        }
        layout.addView(btnSaveServer)

        tvStatus = TextView(this).apply {
            text = "Tap the button below and speak to Alya"
            textSize = 16f
            setTextColor(android.graphics.Color.parseColor("#38BDF8"))
            gravity = android.view.Gravity.CENTER
            setPadding(0, 50, 0, 30)
        }
        layout.addView(tvStatus)

        btnMic = Button(this).apply {
            text = "🎙️ TAP TO SPEAK (HEY ALYA)"
            textSize = 18f
            setTypeface(null, android.graphics.Typeface.BOLD)
            setBackgroundColor(android.graphics.Color.parseColor("#10B981"))
            setTextColor(android.graphics.Color.WHITE)
            setPadding(40, 50, 40, 50)
            setOnClickListener {
                startVoiceRecognition()
            }
        }
        layout.addView(btnMic)

        tvResponse = TextView(this).apply {
            text = "Alya replies will appear here..."
            textSize = 15f
            setTextColor(android.graphics.Color.parseColor("#E2E8F0"))
            setPadding(20, 40, 20, 20)
        }
        layout.addView(tvResponse)

        setContentView(layout)

        tts = TextToSpeech(this, this)
        checkAndRequestPermissions()
        initSpeechRecognizer()
    }

    private fun checkAndRequestPermissions() {
        val permissions = arrayOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.CALL_PHONE,
            Manifest.permission.SEND_SMS,
            Manifest.permission.READ_SMS,
            Manifest.permission.READ_CONTACTS
        )

        val needed = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), PERMISSION_REQUEST_CODE)
        }
    }

    private fun initSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                runOnUiThread { tvStatus.text = "🎙️ Listening to you... (Speak now)" }
            }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {
                runOnUiThread { tvStatus.text = "⏳ Processing command with Alya AI..." }
            }
            override fun onError(error: Int) {
                runOnUiThread { tvStatus.text = "⚠️ Mic error or timeout. Tap button to retry." }
            }

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    val query = matches[0]
                    runOnUiThread { tvStatus.text = "🗣️ You said: \"$query\"" }
                    sendToAlyaServer(query)
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
    }

    private fun startVoiceRecognition() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to Alya...")
        }
        speechRecognizer?.startListening(intent)
    }

    private fun sendToAlyaServer(message: String) {
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
                    put("message", message)
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
                    runOnUiThread {
                        tvResponse.text = finalReply
                        tvStatus.text = "✅ Task completed!"
                    }

                    speakOut(finalReply)
                    handleIntentTriggers(finalReply)
                }
            } catch (e: Exception) {
                runOnUiThread {
                    tvResponse.text = "Connection Error: ${e.message}\nPlease check Server URL."
                }
            }
        }
    }

    private fun speakOut(text: String) {
        val cleanSpeech = text.replace("*", "").replace("#", "").replace("`", "")
        tts?.speak(cleanSpeech, TextToSpeech.QUEUE_FLUSH, null, "AlyaVoiceId")
    }

    private fun handleIntentTriggers(text: String) {
        // Direct Phone Call
        if (text.contains("tel:")) {
            val phone = text.substringAfter("tel:").substringBefore(")")
            val callIntent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$phone"))
            startActivity(callIntent)
        }

        // WhatsApp Direct Link
        if (text.contains("https://wa.me/")) {
            val waUrl = text.substringAfter("https://wa.me/").substringBefore(")")
            val waIntent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/$waUrl"))
            startActivity(waIntent)
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("hi", "IN")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer?.destroy()
        tts?.stop()
        tts?.shutdown()
    }
}
