package com.alya.aiagent

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.animation.Animation
import android.view.animation.ScaleAnimation
import android.widget.Button
import android.widget.CompoundButton
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity(), TextToSpeech.OnInitListener {

    companion object {
        const val DEFAULT_SERVER_URL = "http://3.90.20.247:5005"
        const val PREFS_NAME = "AlyaPrefs"
        const val KEY_SERVER_URL = "server_url"
        const val KEY_WAKE_WORD_ENABLED = "wake_word_enabled"
        const val PERMISSION_REQUEST_CODE = 101
        const val TAG = "MainActivity"
    }

    private lateinit var tvStatus: TextView
    private lateinit var tvPulseHint: TextView
    private lateinit var btnOrb: LinearLayout
    private lateinit var ivOrbMic: ImageView
    private lateinit var tvOrbLabel: TextView
    private lateinit var chatContainer: LinearLayout
    private lateinit var chatScrollView: ScrollView
    private lateinit var switchWakeWord: Switch
    private lateinit var etServerUrl: EditText
    private lateinit var serverConfigCard: LinearLayout

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var isListening = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContentView(buildModernUi())

        tts = TextToSpeech(this, this)
        initSpeechRecognizer()
        checkAndRequestPermissions()

        // Check if wake word service should be running
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val wakeWordEnabled = prefs.getBoolean(KEY_WAKE_WORD_ENABLED, true)
        switchWakeWord.isChecked = wakeWordEnabled
        if (wakeWordEnabled) {
            startAlyaService()
        }

        // Handle Launch from Wake-Word, Assist Button, or Power Button
        handleTriggerIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleTriggerIntent(intent)
    }

    private fun handleTriggerIntent(intent: Intent?) {
        if (intent == null) return

        val action = intent.action
        val isFromWakeWord = intent.getBooleanExtra("EXTRA_START_LISTENING", false)
        val isAssistAction = (action == Intent.ACTION_ASSIST || 
                              action == Intent.ACTION_VOICE_COMMAND ||
                              action == "android.intent.action.VOICE_ASSIST" || 
                              action == "android.intent.action.SEARCH_LONG_PRESS")

        if (isFromWakeWord || isAssistAction) {
            mainHandler.postDelayed({
                vibratePhone(100)
                addSystemNotice("⚡ Alya activated via ${if (isFromWakeWord) "Wake Word ('Hey Alya')" else "Power / Assist Button"}")
                startVoiceRecognition()
            }, 300)
        }
    }

    private fun buildModernUi(): View {
        val rootScrollView = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#0B0F19"))
            isFillViewport = true
        }

        val mainLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 50, 40, 60)
            gravity = Gravity.CENTER_HORIZONTAL
        }

        // Top Header Bar
        val headerLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 10, 0, 30)
        }

        val ivLogo = ImageView(this).apply {
            val logoResId = resources.getIdentifier("alya_logo", "drawable", packageName)
            if (logoResId != 0) {
                setImageResource(logoResId)
            }
            val size = (48 * resources.displayMetrics.density).toInt()
            layoutParams = LinearLayout.LayoutParams(size, size).apply {
                setMargins(0, 0, 24, 0)
            }
        }
        headerLayout.addView(ivLogo)

        val headerTextLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }

        val tvHeaderTitle = TextView(this).apply {
            text = "ALYA AI ASSISTANT"
            textSize = 19f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.05f
        }
        headerTextLayout.addView(tvHeaderTitle)

        val tvHeaderSub = TextView(this).apply {
            text = "Autonomous Voice & Phone Controller"
            textSize = 12f
            setTextColor(Color.parseColor("#38BDF8"))
        }
        headerTextLayout.addView(tvHeaderSub)

        headerLayout.addView(headerTextLayout)
        mainLayout.addView(headerLayout)

        // Status Pill Badge
        val statusPillLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(32, 14, 32, 14)
            val pillResId = resources.getIdentifier("bg_status_pill", "drawable", packageName)
            if (pillResId != 0) setBackgroundResource(pillResId)
        }

        tvStatus = TextView(this).apply {
            text = "🟢 Ready • Tap Orb or say 'Hey Alya'"
            textSize = 13f
            setTextColor(Color.parseColor("#38BDF8"))
            gravity = Gravity.CENTER
            setTypeface(null, Typeface.BOLD)
        }
        statusPillLayout.addView(tvStatus)
        mainLayout.addView(statusPillLayout)

        // Center Hero Orb
        val orbContainer = LinearLayout(this).apply {
            gravity = Gravity.CENTER
            setPadding(0, 40, 0, 30)
        }

        val orbSize = (160 * resources.displayMetrics.density).toInt()
        btnOrb = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(orbSize, orbSize)
            val orbResId = resources.getIdentifier("bg_orb_idle", "drawable", packageName)
            if (orbResId != 0) setBackgroundResource(orbResId)
            isClickable = true
            isFocusable = true
            setOnClickListener {
                if (isListening) {
                    stopVoiceRecognition()
                } else {
                    startVoiceRecognition()
                }
            }
        }

        ivOrbMic = ImageView(this).apply {
            setImageResource(android.R.drawable.ic_btn_speak_now)
            val micSize = (48 * resources.displayMetrics.density).toInt()
            layoutParams = LinearLayout.LayoutParams(micSize, micSize)
            setColorFilter(Color.WHITE)
        }
        btnOrb.addView(ivOrbMic)

        tvOrbLabel = TextView(this).apply {
            text = "TAP TO SPEAK"
            textSize = 12f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            setPadding(0, 8, 0, 0)
        }
        btnOrb.addView(tvOrbLabel)

        orbContainer.addView(btnOrb)
        mainLayout.addView(orbContainer)

        tvPulseHint = TextView(this).apply {
            text = "Say \"Hey Alya\" anytime or press power button"
            textSize = 12f
            setTextColor(Color.parseColor("#64748B"))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, 24)
        }
        mainLayout.addView(tvPulseHint)

        // Quick Suggestions Horizontal Chips
        val chipScroll = HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            setPadding(0, 0, 0, 24)
        }
        val chipContainer = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        val chips = listOf(
            "📞 Call Mom",
            "💬 Send WhatsApp",
            "⏰ Set Alarm 7 AM",
            "🌤️ Weather Update",
            "🤖 EC2 Test Ping"
        )

        for (chip in chips) {
            val tvChip = TextView(this).apply {
                text = chip
                textSize = 12f
                setTextColor(Color.parseColor("#93C5FD"))
                val chipBg = resources.getIdentifier("bg_chip", "drawable", packageName)
                if (chipBg != 0) setBackgroundResource(chipBg)
                setPadding(30, 16, 30, 16)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 16, 0) }
                layoutParams = params
                setOnClickListener {
                    val promptText = chip.substring(chip.indexOf(" ") + 1)
                    if (chip.contains("EC2 Test")) {
                        testServerConnection(sanitizeServerUrl(etServerUrl.text.toString()))
                    } else {
                        addUserMessage(promptText)
                        sendToAlyaServer(promptText)
                    }
                }
            }
            chipContainer.addView(tvChip)
        }
        chipScroll.addView(chipContainer)
        mainLayout.addView(chipScroll)

        // Live Chat / Interaction Container Card
        val chatCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_dark", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding(32, 28, 32, 28)
            val cardParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 24) }
            layoutParams = cardParams
        }

        val tvChatHeader = TextView(this).apply {
            text = "💬 LIVE CONVERSATION & ACTIONS"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.05f
            setPadding(0, 0, 0, 16)
        }
        chatCard.addView(tvChatHeader)

        chatScrollView = ScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                (220 * resources.displayMetrics.density).toInt()
            )
        }

        chatContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        chatScrollView.addView(chatContainer)
        chatCard.addView(chatScrollView)
        mainLayout.addView(chatCard)

        // Add Initial Welcome Message
        addAssistantMessage("Namaste! Main Alya hoon. Aap mujhse bol kar call, WhatsApp, alarm ya koi bhi sawaal pooch sakte hain.")

        // System Integrations Card (Wake Word & Assistant Trigger)
        val systemCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_dark", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding(32, 24, 32, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 24) }
            layoutParams = params
        }

        val tvSystemHeader = TextView(this).apply {
            text = "⚡ SMART TRIGGERS & INTEGRATIONS"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.05f
            setPadding(0, 0, 0, 16)
        }
        systemCard.addView(tvSystemHeader)

        // 1. Wake Word Switch Row
        val switchRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 8, 0, 16)
        }

        val switchLabelLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }

        val tvSwitchTitle = TextView(this).apply {
            text = "🎙️ 'Hey Alya' Wake Word"
            textSize = 14f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
        }
        switchLabelLayout.addView(tvSwitchTitle)

        val tvSwitchSub = TextView(this).apply {
            text = "Background continuous listening"
            textSize = 11f
            setTextColor(Color.parseColor("#64748B"))
        }
        switchLabelLayout.addView(tvSwitchSub)
        switchRow.addView(switchLabelLayout)

        switchWakeWord = Switch(this).apply {
            setOnCheckedChangeListener { _: CompoundButton, isChecked: Boolean ->
                getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    .edit()
                    .putBoolean(KEY_WAKE_WORD_ENABLED, isChecked)
                    .apply()

                if (isChecked) {
                    startAlyaService()
                    Toast.makeText(this@MainActivity, "'Hey Alya' Wake Word Activated!", Toast.LENGTH_SHORT).show()
                } else {
                    stopAlyaService()
                    Toast.makeText(this@MainActivity, "Wake Word Deactivated", Toast.LENGTH_SHORT).show()
                }
            }
        }
        switchRow.addView(switchWakeWord)
        systemCard.addView(switchRow)

        // 2. Set Default Assistant Button (Power Button Trigger)
        val btnDefaultAssistant = Button(this).apply {
            text = "⚙️ Set Power Button / Default Assistant"
            textSize = 13f
            setTextColor(Color.WHITE)
            val btnGrad = resources.getIdentifier("bg_button_gradient", "drawable", packageName)
            if (btnGrad != 0) setBackgroundResource(btnGrad)
            setPadding(24, 20, 24, 20)
            setOnClickListener {
                openAssistantSettings()
            }
        }
        systemCard.addView(btnDefaultAssistant)

        mainLayout.addView(systemCard)

        // Cloud Server Configuration Card
        serverConfigCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_dark", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding(32, 24, 32, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 30) }
            layoutParams = params
        }

        val tvServerHeading = TextView(this).apply {
            text = "🌐 EC2 / RASA SERVER SETTINGS"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.05f
            setPadding(0, 0, 0, 12)
        }
        serverConfigCard.addView(tvServerHeading)

        val savedUrl = getSavedServerUrl()
        etServerUrl = EditText(this).apply {
            hint = "e.g. $DEFAULT_SERVER_URL"
            setText(savedUrl)
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            val inputBg = resources.getIdentifier("bg_input", "drawable", packageName)
            if (inputBg != 0) setBackgroundResource(inputBg)
            setPadding(30, 24, 30, 24)
            textSize = 13f
        }
        serverConfigCard.addView(etServerUrl)

        val btnServerRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 16, 0, 0)
        }

        val btnSaveUrl = Button(this).apply {
            text = "💾 Save URL"
            textSize = 12f
            setTextColor(Color.WHITE)
            val btnDark = resources.getIdentifier("bg_button_dark", "drawable", packageName)
            if (btnDark != 0) setBackgroundResource(btnDark)
            setOnClickListener {
                val cleaned = sanitizeServerUrl(etServerUrl.text.toString())
                etServerUrl.setText(cleaned)
                saveServerUrl(cleaned)
                Toast.makeText(this@MainActivity, "Server URL Saved!", Toast.LENGTH_SHORT).show()
            }
        }
        val saveParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f).apply {
            setMargins(0, 0, 12, 0)
        }
        btnServerRow.addView(btnSaveUrl, saveParams)

        val btnTestUrl = Button(this).apply {
            text = "⚡ Test Connect"
            textSize = 12f
            setTextColor(Color.WHITE)
            val btnGrad = resources.getIdentifier("bg_button_gradient", "drawable", packageName)
            if (btnGrad != 0) setBackgroundResource(btnGrad)
            setOnClickListener {
                val cleaned = sanitizeServerUrl(etServerUrl.text.toString())
                testServerConnection(cleaned)
            }
        }
        val testParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f).apply {
            setMargins(12, 0, 0, 0)
        }
        btnServerRow.addView(btnTestUrl, testParams)

        serverConfigCard.addView(btnServerRow)
        mainLayout.addView(serverConfigCard)

        rootScrollView.addView(mainLayout)
        return rootScrollView
    }

    private fun openAssistantSettings() {
        Toast.makeText(this, "Select 'Alya AI' as your Default Digital Assistant App", Toast.LENGTH_LONG).show()
        try {
            val intent = Intent(Settings.ACTION_VOICE_INPUT_SETTINGS)
            startActivity(intent)
        } catch (e: Exception) {
            try {
                val intent = Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)
                startActivity(intent)
            } catch (e2: Exception) {
                val intent = Intent(Settings.ACTION_SETTINGS)
                startActivity(intent)
            }
        }
    }

    private fun startAlyaService() {
        try {
            val serviceIntent = Intent(this, AlyaAssistantService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error starting service: ${e.message}")
        }
    }

    private fun stopAlyaService() {
        try {
            val serviceIntent = Intent(this, AlyaAssistantService::class.java)
            stopService(serviceIntent)
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping service: ${e.message}")
        }
    }

    private fun setOrbListeningState(listening: Boolean) {
        isListening = listening
        runOnUiThread {
            if (listening) {
                val orbRes = resources.getIdentifier("bg_orb_listening", "drawable", packageName)
                if (orbRes != 0) btnOrb.setBackgroundResource(orbRes)
                tvOrbLabel.text = "LISTENING..."
                tvStatus.text = "🎙️ Listening... (Speak now)"
                startOrbPulseAnimation()
            } else {
                btnOrb.clearAnimation()
                val orbRes = resources.getIdentifier("bg_orb_idle", "drawable", packageName)
                if (orbRes != 0) btnOrb.setBackgroundResource(orbRes)
                tvOrbLabel.text = "TAP TO SPEAK"
                tvStatus.text = "🟢 Ready • Tap Orb or say 'Hey Alya'"
            }
        }
    }

    private fun startOrbPulseAnimation() {
        val anim = ScaleAnimation(
            1.0f, 1.08f, 1.0f, 1.08f,
            Animation.RELATIVE_TO_SELF, 0.5f,
            Animation.RELATIVE_TO_SELF, 0.5f
        ).apply {
            duration = 450
            repeatMode = Animation.REVERSE
            repeatCount = Animation.INFINITE
        }
        btnOrb.startAnimation(anim)
    }

    private fun initSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                setOrbListeningState(true)
            }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {
                runOnUiThread {
                    tvStatus.text = "🧠 Thinking with Alya AI..."
                    tvOrbLabel.text = "THINKING..."
                }
            }
            override fun onError(error: Int) {
                setOrbListeningState(false)
                runOnUiThread {
                    tvStatus.text = "⚠️ Mic timeout. Tap orb to speak."
                }
            }

            override fun onResults(results: Bundle?) {
                setOrbListeningState(false)
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    val query = matches[0]
                    addUserMessage(query)
                    sendToAlyaServer(query)
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
    }

    private fun startVoiceRecognition() {
        vibratePhone(60)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to Alya...")
        }
        try {
            speechRecognizer?.startListening(intent)
            setOrbListeningState(true)
        } catch (e: Exception) {
            Toast.makeText(this, "Mic error: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun stopVoiceRecognition() {
        try {
            speechRecognizer?.stopListening()
        } catch (e: Exception) {}
        setOrbListeningState(false)
    }

    private fun addUserMessage(text: String) {
        runOnUiThread {
            val bubble = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                val bubbleRes = resources.getIdentifier("bg_user_bubble", "drawable", packageName)
                if (bubbleRes != 0) setBackgroundResource(bubbleRes)
                setPadding(28, 20, 28, 20)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    gravity = Gravity.END
                    setMargins(60, 10, 0, 10)
                }
                layoutParams = params
            }

            val tv = TextView(this).apply {
                this.text = "🗣️  $text"
                textSize = 14f
                setTextColor(Color.WHITE)
            }
            bubble.addView(tv)
            chatContainer.addView(bubble)
            scrollChatToBottom()
        }
    }

    private fun addAssistantMessage(text: String) {
        runOnUiThread {
            val bubble = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                val bubbleRes = resources.getIdentifier("bg_assistant_bubble", "drawable", packageName)
                if (bubbleRes != 0) setBackgroundResource(bubbleRes)
                setPadding(28, 20, 28, 20)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    gravity = Gravity.START
                    setMargins(0, 10, 60, 10)
                }
                layoutParams = params
            }

            val tv = TextView(this).apply {
                this.text = "🤖  $text"
                textSize = 14f
                setTextColor(Color.parseColor("#E2E8F0"))
                setLineSpacing(4f, 1f)
            }
            bubble.addView(tv)
            chatContainer.addView(bubble)
            scrollChatToBottom()
        }
    }

    private fun addSystemNotice(text: String) {
        runOnUiThread {
            val tv = TextView(this).apply {
                this.text = text
                textSize = 11f
                setTextColor(Color.parseColor("#38BDF8"))
                gravity = Gravity.CENTER
                setPadding(0, 6, 0, 6)
            }
            chatContainer.addView(tv)
            scrollChatToBottom()
        }
    }

    private fun scrollChatToBottom() {
        mainHandler.postDelayed({
            chatScrollView.fullScroll(ScrollView.FOCUS_DOWN)
        }, 100)
    }

    private fun sanitizeServerUrl(rawUrl: String): String {
        var clean = rawUrl.trim()
        if (clean.isEmpty()) return DEFAULT_SERVER_URL
        if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
            clean = "http://$clean"
        }
        if (clean.endsWith("/")) {
            clean = clean.dropLast(1)
        }
        return clean
    }

    private fun getSavedServerUrl(): String {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL) ?: DEFAULT_SERVER_URL
    }

    private fun saveServerUrl(url: String) {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_SERVER_URL, url).apply()
    }

    private fun testServerConnection(serverBase: String) {
        runOnUiThread {
            tvStatus.text = "🔄 Testing connection to EC2 Server..."
            addSystemNotice("🔄 Testing connection to $serverBase...")
        }

        executor.execute {
            try {
                val versionUrl = URL("$serverBase/version")
                val conn = versionUrl.openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 8000
                conn.readTimeout = 8000
                val code = conn.responseCode

                if (code == 200) {
                    val response = conn.inputStream.bufferedReader().use { it.readText() }
                    runOnUiThread {
                        tvStatus.text = "🟢 EC2 Server Online ($serverBase)"
                        addSystemNotice("🟢 EC2 Rasa Online! Response: $response")
                        Toast.makeText(this@MainActivity, "Connected to EC2 Rasa Server!", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    runOnUiThread {
                        tvStatus.text = "⚠️ Server responded with HTTP $code"
                        addSystemNotice("⚠️ Server HTTP $code")
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    tvStatus.text = "🔴 Connection Failed (${e.message})"
                    addSystemNotice("🔴 Connection Failed: ${e.message}\nEnsure EC2 Port 5005 Security Group is open.")
                }
            }
        }
    }

    private fun sendToAlyaServer(message: String) {
        val serverBase = sanitizeServerUrl(getSavedServerUrl())
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

                    val finalReply = if (combinedText.isNotEmpty()) combinedText.toString().trim() else "Kripya dobara kahiye."
                    addAssistantMessage(finalReply)
                    speakOut(finalReply)
                    handleIntentTriggers(finalReply)
                } else {
                    addAssistantMessage("HTTP Error ${conn.responseCode} from EC2 server.")
                }
            } catch (e: Exception) {
                addAssistantMessage("Connection Error: ${e.message}\nKripya EC2 Security Group port 5005 check karein.")
            }
        }
    }

    private fun speakOut(text: String) {
        val cleanSpeech = text.replace("*", "").replace("#", "").replace("`", "")
        tts?.speak(cleanSpeech, TextToSpeech.QUEUE_FLUSH, null, "AlyaVoiceId")
    }

    private fun handleIntentTriggers(text: String) {
        if (text.contains("tel:")) {
            val phone = text.substringAfter("tel:").substringBefore(")")
            val callIntent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$phone"))
            startActivity(callIntent)
        }

        if (text.contains("https://wa.me/")) {
            val waUrl = text.substringAfter("https://wa.me/").substringBefore(")")
            val waIntent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/$waUrl"))
            startActivity(waIntent)
        }
    }

    private fun vibratePhone(durationMs: Long) {
        try {
            val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                vibrator?.vibrate(durationMs)
            }
        } catch (e: Exception) {}
    }

    private fun checkAndRequestPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val permissions = arrayOf(
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.CALL_PHONE,
                Manifest.permission.SEND_SMS,
                Manifest.permission.READ_SMS,
                Manifest.permission.READ_CONTACTS
            )

            val needed = permissions.filter {
                checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
            }

            if (needed.isNotEmpty()) {
                requestPermissions(needed.toTypedArray(), PERMISSION_REQUEST_CODE)
            }

            // Request Battery Optimization Exemption so Android doesn't kill Wake Word
            val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
            if (powerManager != null && !powerManager.isIgnoringBatteryOptimizations(packageName)) {
                try {
                    val batteryIntent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                        data = Uri.parse("package:$packageName")
                    }
                    startActivity(batteryIntent)
                } catch (e: Exception) {}
            }

            // Check Overlay Permission for background popup
            if (!Settings.canDrawOverlays(this)) {
                try {
                    val overlayIntent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                    startActivity(overlayIntent)
                } catch (e: Exception) {}
            }
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
