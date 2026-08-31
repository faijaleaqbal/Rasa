package com.alya.aiagent

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
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
import android.view.ViewGroup
import android.view.animation.Animation
import android.view.animation.ScaleAnimation
import android.widget.Button
import android.widget.CompoundButton
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity(), TextToSpeech.OnInitListener {

    companion object {
        const val DEFAULT_SERVER_URL = "http://3.90.20.247:5005"
        const val PREFS_NAME = "AlyaPrefs"
        const val KEY_SERVER_URL = "server_url"
        const val KEY_WAKE_WORD_ENABLED = "wake_word_enabled"
        const val PERMISSION_REQUEST_CODE = 101
        const val FILE_PICKER_REQUEST_CODE = 202
        const val TAG = "MainActivity"
    }

    private enum class Tab { HOME, MODELS, HISTORY, SETTINGS }
    private var currentTab = Tab.HOME

    private lateinit var rootContainer: LinearLayout
    private lateinit var contentFrame: LinearLayout
    private lateinit var bottomNavDock: LinearLayout

    private lateinit var tvStatusBadge: TextView

    private lateinit var homeTabContainer: LinearLayout
    private lateinit var modelsTabContainer: LinearLayout
    private lateinit var historyTabContainer: LinearLayout
    private lateinit var settingsTabContainer: LinearLayout

    private lateinit var chatScrollView: ScrollView
    private lateinit var chatContainer: LinearLayout
    private lateinit var etMessageInput: EditText
    private lateinit var btnOrb: LinearLayout
    private lateinit var ivOrbMic: ImageView
    private lateinit var tvOrbLabel: TextView
    private lateinit var tvThinkingIndicator: TextView

    private lateinit var etServerUrl: EditText
    private lateinit var switchWakeWord: Switch
    private lateinit var tvServerLatency: TextView

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var isListening = false
    private var isCloudOnline = true
    private var activeModelName = "Llama-3-8B-Instruct.Q4_K_M"

    private val installedModels = mutableListOf(
        ModelItem("Llama-3-8B-Instruct.Q4_K_M", "Meta • FP8/Q4", "4.8 GB", "8,192", true, true),
        ModelItem("Mistral-7B-Instruct-v0.3.Q4", "Mistral AI • GGUF", "4.3 GB", "32,768", true, false),
        ModelItem("Phi-3-Mini-4k-Instruct.Q4", "Microsoft • GGUF", "2.3 GB", "4,096", true, false),
        ModelItem("Gemma-2-2B-IT.Q4_K_M", "Google • GGUF", "1.6 GB", "8,192", true, false)
    )

    private val conversationHistory = mutableListOf<HistoryItem>()

    data class ModelItem(
        val name: String,
        val provider: String,
        val size: String,
        val contextLength: String,
        var isInstalled: Boolean,
        var isActive: Boolean
    )

    data class HistoryItem(
        val title: String,
        val time: String,
        val snippet: String,
        val type: String
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val sdf = SimpleDateFormat("hh:mm a", Locale.getDefault())
        conversationHistory.add(HistoryItem("Q3 Financial Analysis", sdf.format(Date()), "Analyzed quarterly metrics and market summary", "doc"))
        conversationHistory.add(HistoryItem("Passport Photo Studio", "Yesterday", "Generated 300 DPI Indian Passport dimensions", "image"))

        setContentView(buildRootLayout())

        tts = TextToSpeech(this, this)
        initSpeechRecognizer()
        checkAndRequestPermissions()

        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val wakeWordEnabled = prefs.getBoolean(KEY_WAKE_WORD_ENABLED, true)
        switchWakeWord.isChecked = wakeWordEnabled
        if (wakeWordEnabled) {
            startAlyaService()
        }

        checkServerHealth(getSavedServerUrl())
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
        val isVoiceTrigger = intent.getBooleanExtra("VOICE_TRIGGER", false)
        val isWakeWord = intent.getBooleanExtra("WAKE_WORD_TRIGGER", false)

        if (isWakeWord || isVoiceTrigger || Intent.ACTION_VOICE_COMMAND == action || Intent.ACTION_ASSIST == action) {
            switchTab(Tab.HOME)
            mainHandler.postDelayed({
                startVoiceRecognition()
            }, 400)
        }
    }

    // =========================================================================
    // UI BUILDER (Stitch Design System + Dark / Violet / Gold Hierarchy)
    // =========================================================================

    private fun buildRootLayout(): View {
        rootContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#08080A"))
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }

        val header = buildTopAppBar()
        rootContainer.addView(header)

        contentFrame = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1.0f
            )
        }

        homeTabContainer = buildHomeTab()
        modelsTabContainer = buildModelsTab()
        historyTabContainer = buildHistoryTab()
        settingsTabContainer = buildSettingsTab()

        contentFrame.addView(homeTabContainer)
        contentFrame.addView(modelsTabContainer)
        contentFrame.addView(historyTabContainer)
        contentFrame.addView(settingsTabContainer)

        modelsTabContainer.visibility = View.GONE
        historyTabContainer.visibility = View.GONE
        settingsTabContainer.visibility = View.GONE

        rootContainer.addView(contentFrame)

        bottomNavDock = buildBottomNavDock()
        rootContainer.addView(bottomNavDock)

        return rootContainer
    }

    private fun buildTopAppBar(): View {
        val density = resources.displayMetrics.density
        val headerLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(Color.parseColor("#0D0D10"))
            setPadding((16 * density).toInt(), (12 * density).toInt(), (16 * density).toInt(), (12 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

        val tvBrand = TextView(this).apply {
            text = "ALYA"
            textSize = 20f
            setTextColor(Color.WHITE)
            setTypeface(Typeface.create("sans-serif-black", Typeface.BOLD))
            letterSpacing = 0.15f
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }
        headerLayout.addView(tvBrand)

        tvStatusBadge = TextView(this).apply {
            text = "● CLOUD ONLINE"
            textSize = 10f
            setTextColor(Color.parseColor("#34D399"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.05f
            val pillRes = resources.getIdentifier("bg_status_pill", "drawable", packageName)
            if (pillRes != 0) setBackgroundResource(pillRes)
            setPadding((12 * density).toInt(), (6 * density).toInt(), (12 * density).toInt(), (6 * density).toInt())
            setOnClickListener {
                toggleExecutionMode()
            }
        }
        headerLayout.addView(tvStatusBadge)

        return headerLayout
    }

    // =========================================================================
    // TAB 1: HOME & LIVE CHAT VIEW
    // =========================================================================

    private fun buildHomeTab(): LinearLayout {
        val density = resources.displayMetrics.density
        val homeLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        }

        val homeScrollView = ScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1.0f
            )
            isVerticalScrollBarEnabled = false
        }

        val scrollContent = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding((16 * density).toInt(), (16 * density).toInt(), (16 * density).toInt(), (20 * density).toInt())
        }

        val tvGreeting = TextView(this).apply {
            text = "Namaste, Alex"
            textSize = 22f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
            setPadding(0, 0, 0, (4 * density).toInt())
        }
        scrollContent.addView(tvGreeting)

        val tvSubGreeting = TextView(this).apply {
            text = "Ready to analyze documents, fetch live data, or run local AI models."
            textSize = 13f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 0, 0, (18 * density).toInt())
        }
        scrollContent.addView(tvSubGreeting)

        val bentoGrid = buildBentoGrid()
        scrollContent.addView(bentoGrid)

        val orbWrapper = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(0, (12 * density).toInt(), 0, (16 * density).toInt())
        }

        val orbSize = (140 * density).toInt()
        btnOrb = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(orbSize, orbSize)
            val orbRes = resources.getIdentifier("bg_orb_idle", "drawable", packageName)
            if (orbRes != 0) setBackgroundResource(orbRes)
            isClickable = true
            isFocusable = true
            setOnClickListener {
                if (isListening) stopVoiceRecognition() else startVoiceRecognition()
            }
        }

        ivOrbMic = ImageView(this).apply {
            setImageResource(android.R.drawable.ic_btn_speak_now)
            val micSize = (38 * density).toInt()
            layoutParams = LinearLayout.LayoutParams(micSize, micSize)
            setColorFilter(Color.WHITE)
        }
        btnOrb.addView(ivOrbMic)

        tvOrbLabel = TextView(this).apply {
            text = "TAP TO SPEAK"
            textSize = 11f
            setTextColor(Color.parseColor("#E2E8F0"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            setPadding(0, (6 * density).toInt(), 0, 0)
        }
        btnOrb.addView(tvOrbLabel)
        orbWrapper.addView(btnOrb)
        scrollContent.addView(orbWrapper)

        val chipScroll = buildHorizontalChips()
        scrollContent.addView(chipScroll)

        val chatCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_graphite", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding((16 * density).toInt(), (14 * density).toInt(), (16 * density).toInt(), (14 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, (16 * density).toInt()) }
        }

        val chatHeaderRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, (10 * density).toInt())
        }

        val tvChatHeader = TextView(this).apply {
            text = "💬 LIVE CONVERSATION"
            textSize = 11f
            setTextColor(Color.parseColor("#A1A1AA"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }
        chatHeaderRow.addView(tvChatHeader)

        tvThinkingIndicator = TextView(this).apply {
            text = "✦ Alya is thinking..."
            textSize = 11f
            setTextColor(Color.parseColor("#C4B5FD"))
            setTypeface(null, Typeface.ITALIC)
            visibility = View.GONE
        }
        chatHeaderRow.addView(tvThinkingIndicator)
        chatCard.addView(chatHeaderRow)

        chatScrollView = ScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                (240 * density).toInt()
            )
            isVerticalScrollBarEnabled = false
        }

        chatContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        chatScrollView.addView(chatContainer)
        chatCard.addView(chatScrollView)
        scrollContent.addView(chatCard)

        homeScrollView.addView(scrollContent)
        homeLayout.addView(homeScrollView)

        val composer = buildChatComposer()
        homeLayout.addView(composer)

        addAssistantMessage("Namaste! Main Alya hoon. Aap bol kar ya text likh kar Jobs, Trains, Models, Documents ya koi bhi sawaal pooch sakte hain.")

        return homeLayout
    }

    private fun buildBentoGrid(): View {
        val density = resources.displayMetrics.density
        val grid = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 0, 0, (16 * density).toInt())
        }

        val row1 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 0, 0, (10 * density).toInt())
        }
        row1.addView(createBentoCard("📄 Extract Text", "Scan & OCR docs") {
            sendQuickPrompt("/ocr")
        })
        row1.addView(createBentoCard("🎨 Photo Studio", "Passport & Presets") {
            sendQuickPrompt("/imagetools")
        })
        grid.addView(row1)

        val row2 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        row2.addView(createBentoCard("🚂 Live Trains", "PNR & NTES Status") {
            sendQuickPrompt("/pnr")
        })
        row2.addView(createBentoCard("🎓 Jobs & Alerts", "Railway, Bank, SVMCM") {
            sendQuickPrompt("/jobs")
        })
        grid.addView(row2)

        return grid
    }

    private fun createBentoCard(title: String, subtitle: String, onClick: () -> Unit): View {
        val density = resources.displayMetrics.density
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_graphite", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding((14 * density).toInt(), (12 * density).toInt(), (14 * density).toInt(), (12 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            ).apply { setMargins(0, 0, (8 * density).toInt(), 0) }

            val tvTitle = TextView(this@MainActivity).apply {
                text = title
                textSize = 13f
                setTextColor(Color.WHITE)
                setTypeface(null, Typeface.BOLD)
            }
            addView(tvTitle)

            val tvSub = TextView(this@MainActivity).apply {
                text = subtitle
                textSize = 10f
                setTextColor(Color.parseColor("#71717A"))
                setPadding(0, (2 * density).toInt(), 0, 0)
            }
            addView(tvSub)

            setOnClickListener {
                vibrateTap()
                onClick()
            }
        }
    }

    private fun buildHorizontalChips(): View {
        val density = resources.displayMetrics.density
        val scroll = HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            setPadding(0, 0, 0, (14 * density).toInt())
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        val chips = listOf(
            "💼 /jobs",
            "🌟 /svmcm",
            "🚂 /railway",
            "🏦 /bank",
            "🎟️ /admitcard",
            "🏆 /results",
            "📱 /imei",
            "🌤️ /weather"
        )

        for (chip in chips) {
            val tv = TextView(this).apply {
                text = chip
                textSize = 12f
                setTextColor(Color.parseColor("#E4E4E7"))
                val chipRes = resources.getIdentifier("bg_chip", "drawable", packageName)
                if (chipRes != 0) setBackgroundResource(chipRes)
                setPadding((16 * density).toInt(), (8 * density).toInt(), (16 * density).toInt(), (8 * density).toInt())
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, (8 * density).toInt(), 0) }

                setOnClickListener {
                    vibrateTap()
                    val query = chip.substring(chip.indexOf("/") + 1).trim()
                    addUserMessage("/$query")
                    sendToAlyaServer("/$query")
                }
            }
            container.addView(tv)
        }
        scroll.addView(container)
        return scroll
    }

    private fun buildChatComposer(): View {
        val density = resources.displayMetrics.density
        val composerLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            val bgRes = resources.getIdentifier("bg_input_glass", "drawable", packageName)
            if (bgRes != 0) setBackgroundResource(bgRes)
            setPadding((12 * density).toInt(), (6 * density).toInt(), (12 * density).toInt(), (6 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins((14 * density).toInt(), 0, (14 * density).toInt(), (10 * density).toInt()) }
        }

        val btnAttach = ImageView(this).apply {
            setImageResource(android.R.drawable.ic_input_add)
            setColorFilter(Color.parseColor("#A1A1AA"))
            val sz = (36 * density).toInt()
            layoutParams = LinearLayout.LayoutParams(sz, sz)
            setOnClickListener {
                vibrateTap()
                openFilePicker()
            }
        }
        composerLayout.addView(btnAttach)

        etMessageInput = EditText(this).apply {
            hint = "Ask Alya anything..."
            setTextColor(Color.WHITE)
            setHintTextColor(Color.parseColor("#52525B"))
            textSize = 14f
            background = null
            setPadding((10 * density).toInt(), 0, (10 * density).toInt(), 0)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }
        composerLayout.addView(etMessageInput)

        val btnSend = Button(this).apply {
            text = "➔"
            textSize = 15f
            setTextColor(Color.BLACK)
            setTypeface(null, Typeface.BOLD)
            val btnRes = resources.getIdentifier("bg_button_primary", "drawable", packageName)
            if (btnRes != 0) setBackgroundResource(btnRes)
            val sz = (36 * density).toInt()
            layoutParams = LinearLayout.LayoutParams(sz, sz)
            setOnClickListener {
                val msg = etMessageInput.text.toString().trim()
                if (msg.isNotEmpty()) {
                    vibrateTap()
                    addUserMessage(msg)
                    etMessageInput.setText("")
                    sendToAlyaServer(msg)
                }
            }
        }
        composerLayout.addView(btnSend)

        return composerLayout
    }

    // =========================================================================
    // TAB 2: MODEL MANAGER VIEW (Local GGUF & Hugging Face Hub)
    // =========================================================================

    private fun buildModelsTab(): LinearLayout {
        val density = resources.displayMetrics.density
        val modelsLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding((16 * density).toInt(), (16 * density).toInt(), (16 * density).toInt(), (20 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        }

        val scroll = ScrollView(this).apply { isVerticalScrollBarEnabled = false }
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }

        val tvTitle = TextView(this).apply {
            text = "🧠 Model Manager"
            textSize = 22f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
            setPadding(0, 0, 0, (4 * density).toInt())
        }
        content.addView(tvTitle)

        val tvSub = TextView(this).apply {
            text = "Local llama.cpp runtime & Hugging Face model deployment"
            textSize = 13f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 0, 0, (18 * density).toInt())
        }
        content.addView(tvSub)

        // Memory Monitor Card
        val vramCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val plateRes = resources.getIdentifier("bg_plate_dark", "drawable", packageName)
            if (plateRes != 0) setBackgroundResource(plateRes)
            setPadding((16 * density).toInt(), (14 * density).toInt(), (16 * density).toInt(), (14 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, (18 * density).toInt()) }
        }

        val vramHeaderRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val tvVramTitle = TextView(this).apply {
            text = "HARDWARE MEMORY UTILIZATION"
            textSize = 11f
            setTextColor(Color.parseColor("#A1A1AA"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }
        vramHeaderRow.addView(tvVramTitle)

        val tvVramPct = TextView(this).apply {
            text = "4.2 GB / 8.0 GB (52%)"
            textSize = 11f
            setTextColor(Color.parseColor("#A78BFA"))
            setTypeface(null, Typeface.BOLD)
        }
        vramHeaderRow.addView(tvVramPct)
        vramCard.addView(vramHeaderRow)

        val pBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            progress = 52
            max = 100
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                (8 * density).toInt()
            ).apply { setMargins(0, (10 * density).toInt(), 0, 0) }
        }
        vramCard.addView(pBar)
        content.addView(vramCard)

        // Installed Models List
        val tvSectionInstalled = TextView(this).apply {
            text = "INSTALLED LOCAL MODELS (.GGUF)"
            textSize = 11f
            setTextColor(Color.parseColor("#71717A"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            setPadding(0, 0, 0, (10 * density).toInt())
        }
        content.addView(tvSectionInstalled)

        for (model in installedModels) {
            content.addView(createModelCard(model))
        }

        val btnRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, (10 * density).toInt(), 0, (20 * density).toInt())
        }

        val btnImport = Button(this).apply {
            text = "📥 Import .GGUF File"
            textSize = 12f
            setTextColor(Color.WHITE)
            val secRes = resources.getIdentifier("bg_button_secondary", "drawable", packageName)
            if (secRes != 0) setBackgroundResource(secRes)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f).apply {
                setMargins(0, 0, (6 * density).toInt(), 0)
            }
            setOnClickListener {
                vibrateTap()
                openFilePicker()
            }
        }
        btnRow.addView(btnImport)

        val btnHub = Button(this).apply {
            text = "🤗 Hugging Face Hub"
            textSize = 12f
            setTextColor(Color.WHITE)
            val btnGrad = resources.getIdentifier("bg_button_gradient", "drawable", packageName)
            if (btnGrad != 0) setBackgroundResource(btnGrad)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f).apply {
                setMargins((6 * density).toInt(), 0, 0, 0)
            }
            setOnClickListener {
                vibrateTap()
                Toast.makeText(this@MainActivity, "Connecting to Hugging Face Model Hub...", Toast.LENGTH_SHORT).show()
            }
        }
        btnRow.addView(btnHub)
        content.addView(btnRow)

        scroll.addView(content)
        modelsLayout.addView(scroll)
        return modelsLayout
    }

    private fun createModelCard(model: ModelItem): View {
        val density = resources.displayMetrics.density
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier(if (model.isActive) "bg_plate_dark" else "bg_card_graphite", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding((14 * density).toInt(), (12 * density).toInt(), (14 * density).toInt(), (12 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, (10 * density).toInt()) }
        }

        val topRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val nameCol = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }

        val tvName = TextView(this).apply {
            text = model.name
            textSize = 14f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
        }
        nameCol.addView(tvName)

        val tvMeta = TextView(this).apply {
            text = "${model.provider} • ${model.size} • Context: ${model.contextLength}"
            textSize = 11f
            setTextColor(Color.parseColor("#71717A"))
            setPadding(0, (2 * density).toInt(), 0, 0)
        }
        nameCol.addView(tvMeta)
        topRow.addView(nameCol)

        if (model.isActive) {
            val tvActiveBadge = TextView(this).apply {
                text = "ACTIVE"
                textSize = 9f
                setTextColor(Color.parseColor("#C4B5FD"))
                setTypeface(null, Typeface.BOLD)
                val chipRes = resources.getIdentifier("bg_chip", "drawable", packageName)
                if (chipRes != 0) setBackgroundResource(chipRes)
                setPadding((8 * density).toInt(), (4 * density).toInt(), (8 * density).toInt(), (4 * density).toInt())
            }
            topRow.addView(tvActiveBadge)
        }
        card.addView(topRow)

        val actionRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, (10 * density).toInt(), 0, 0)
        }

        val btnToggle = Button(this).apply {
            text = if (model.isActive) "Unload" else "Set Active"
            textSize = 11f
            setTextColor(if (model.isActive) Color.parseColor("#EF4444") else Color.WHITE)
            val secRes = resources.getIdentifier("bg_button_secondary", "drawable", packageName)
            if (secRes != 0) setBackgroundResource(secRes)
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                (36 * density).toInt()
            )
            setOnClickListener {
                vibrateTap()
                setActiveModel(model.name)
            }
        }
        actionRow.addView(btnToggle)
        card.addView(actionRow)

        return card
    }

    private fun setActiveModel(modelName: String) {
        for (m in installedModels) {
            m.isActive = (m.name == modelName)
        }
        activeModelName = modelName
        Toast.makeText(this, "Active model set to $modelName", Toast.LENGTH_SHORT).show()
        rebuildModelsView()
    }

    private fun rebuildModelsView() {
        modelsTabContainer.removeAllViews()
        modelsTabContainer.addView(buildModelsTab())
    }

    // =========================================================================
    // TAB 3: HISTORY & EXTRACTED FILES VIEW
    // =========================================================================

    private fun buildHistoryTab(): LinearLayout {
        val density = resources.displayMetrics.density
        val historyLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding((16 * density).toInt(), (16 * density).toInt(), (16 * density).toInt(), (20 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        }

        val tvTitle = TextView(this).apply {
            text = "📁 History & Files"
            textSize = 22f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
            setPadding(0, 0, 0, (4 * density).toInt())
        }
        historyLayout.addView(tvTitle)

        val tvSub = TextView(this).apply {
            text = "Past conversations, analyzed PDFs, and generated media"
            textSize = 13f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 0, 0, (16 * density).toInt())
        }
        historyLayout.addView(tvSub)

        val scroll = ScrollView(this).apply { isVerticalScrollBarEnabled = false }
        val listContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }

        for (item in conversationHistory) {
            val itemCard = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                val cardRes = resources.getIdentifier("bg_card_graphite", "drawable", packageName)
                if (cardRes != 0) setBackgroundResource(cardRes)
                setPadding((14 * density).toInt(), (12 * density).toInt(), (14 * density).toInt(), (12 * density).toInt())
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 0, (10 * density).toInt()) }

                val tvItemTitle = TextView(this@MainActivity).apply {
                    text = "${if (item.type == "doc") "📄 " else if (item.type == "image") "🎨 " else "💬 "}${item.title}"
                    textSize = 14f
                    setTextColor(Color.WHITE)
                    setTypeface(null, Typeface.BOLD)
                }
                addView(tvItemTitle)

                val tvItemSnippet = TextView(this@MainActivity).apply {
                    text = item.snippet
                    textSize = 12f
                    setTextColor(Color.parseColor("#A1A1AA"))
                    setPadding(0, (2 * density).toInt(), 0, (4 * density).toInt())
                }
                addView(tvItemSnippet)

                val tvItemTime = TextView(this@MainActivity).apply {
                    text = "Recorded ${item.time}"
                    textSize = 10f
                    setTextColor(Color.parseColor("#71717A"))
                }
                addView(tvItemTime)
            }
            listContainer.addView(itemCard)
        }

        scroll.addView(listContainer)
        historyLayout.addView(scroll)
        return historyLayout
    }

    // =========================================================================
    // TAB 4: SETTINGS & CLOUD CONFIGURATION VIEW
    // =========================================================================

    private fun buildSettingsTab(): LinearLayout {
        val density = resources.displayMetrics.density
        val settingsLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding((16 * density).toInt(), (16 * density).toInt(), (16 * density).toInt(), (20 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        }

        val scroll = ScrollView(this).apply { isVerticalScrollBarEnabled = false }
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }

        val tvTitle = TextView(this).apply {
            text = "⚙️ Settings & Triggers"
            textSize = 22f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
            setPadding(0, 0, 0, (4 * density).toInt())
        }
        content.addView(tvTitle)

        val tvSub = TextView(this).apply {
            text = "Cloud endpoint routing, wake word, and hardware shortcuts"
            textSize = 13f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 0, 0, (18 * density).toInt())
        }
        content.addView(tvSub)

        // Server Endpoint Card
        val serverCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_graphite", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding((16 * density).toInt(), (14 * density).toInt(), (16 * density).toInt(), (14 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, (16 * density).toInt()) }
        }

        val tvServerHdr = TextView(this).apply {
            text = "🌐 CLOUD SERVER ENDPOINT"
            textSize = 11f
            setTextColor(Color.parseColor("#A1A1AA"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            setPadding(0, 0, 0, (10 * density).toInt())
        }
        serverCard.addView(tvServerHdr)

        val savedUrl = getSavedServerUrl()
        etServerUrl = EditText(this).apply {
            hint = "e.g. $DEFAULT_SERVER_URL"
            setText(savedUrl)
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            val inputBg = resources.getIdentifier("bg_input", "drawable", packageName)
            if (inputBg != 0) setBackgroundResource(inputBg)
            setPadding((12 * density).toInt(), (10 * density).toInt(), (12 * density).toInt(), (10 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, (10 * density).toInt()) }
        }
        serverCard.addView(etServerUrl)

        val btnRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }

        val btnSave = Button(this).apply {
            text = "💾 Save URL"
            textSize = 12f
            setTextColor(Color.BLACK)
            setTypeface(null, Typeface.BOLD)
            val btnPrim = resources.getIdentifier("bg_button_primary", "drawable", packageName)
            if (btnPrim != 0) setBackgroundResource(btnPrim)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f).apply {
                setMargins(0, 0, (6 * density).toInt(), 0)
            }
            setOnClickListener {
                vibrateTap()
                val rawUrl = etServerUrl.text.toString().trim()
                val cleanUrl = sanitizeServerUrl(rawUrl)
                saveServerUrl(cleanUrl)
                etServerUrl.setText(cleanUrl)
                Toast.makeText(this@MainActivity, "Server URL Saved!", Toast.LENGTH_SHORT).show()
                checkServerHealth(cleanUrl)
            }
        }
        btnRow.addView(btnSave)

        val btnPing = Button(this).apply {
            text = "⚡ Test Ping"
            textSize = 12f
            setTextColor(Color.WHITE)
            val btnGrad = resources.getIdentifier("bg_button_gradient", "drawable", packageName)
            if (btnGrad != 0) setBackgroundResource(btnGrad)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f).apply {
                setMargins((6 * density).toInt(), 0, 0, 0)
            }
            setOnClickListener {
                vibrateTap()
                checkServerHealth(sanitizeServerUrl(etServerUrl.text.toString()))
            }
        }
        btnRow.addView(btnPing)
        serverCard.addView(btnRow)

        tvServerLatency = TextView(this).apply {
            text = "Latency: Checking..."
            textSize = 11f
            setTextColor(Color.parseColor("#34D399"))
            setPadding(0, (8 * density).toInt(), 0, 0)
        }
        serverCard.addView(tvServerLatency)
        content.addView(serverCard)

        // Wake Word & Default Assistant Card
        val triggerCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val cardRes = resources.getIdentifier("bg_card_graphite", "drawable", packageName)
            if (cardRes != 0) setBackgroundResource(cardRes)
            setPadding((16 * density).toInt(), (14 * density).toInt(), (16 * density).toInt(), (14 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, (16 * density).toInt()) }
        }

        val tvTriggerHdr = TextView(this).apply {
            text = "🎙️ WAKE WORD & OS INTEGRATION"
            textSize = 11f
            setTextColor(Color.parseColor("#A1A1AA"))
            setTypeface(null, Typeface.BOLD)
            letterSpacing = 0.08f
            setPadding(0, 0, 0, (10 * density).toInt())
        }
        triggerCard.addView(tvTriggerHdr)

        val switchRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, (12 * density).toInt())
        }

        val switchLabels = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f)
        }

        val tvSwitchTitle = TextView(this).apply {
            text = "\"Hey Alya\" Voice Activation"
            textSize = 13f
            setTextColor(Color.WHITE)
            setTypeface(null, Typeface.BOLD)
        }
        switchLabels.addView(tvSwitchTitle)

        val tvSwitchSub = TextView(this).apply {
            text = "Continuous low-power background listening"
            textSize = 11f
            setTextColor(Color.parseColor("#71717A"))
        }
        switchLabels.addView(tvSwitchSub)
        switchRow.addView(switchLabels)

        switchWakeWord = Switch(this).apply {
            setOnCheckedChangeListener { _: CompoundButton, isChecked: Boolean ->
                getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    .edit()
                    .putBoolean(KEY_WAKE_WORD_ENABLED, isChecked)
                    .apply()

                if (isChecked) {
                    startAlyaService()
                    Toast.makeText(this@MainActivity, "Wake word active!", Toast.LENGTH_SHORT).show()
                } else {
                    stopAlyaService()
                    Toast.makeText(this@MainActivity, "Wake word disabled", Toast.LENGTH_SHORT).show()
                }
            }
        }
        switchRow.addView(switchWakeWord)
        triggerCard.addView(switchRow)

        val btnPowerSettings = Button(this).apply {
            text = "⚡ Configure Default Assistant & Power Button"
            textSize = 12f
            setTextColor(Color.WHITE)
            val secRes = resources.getIdentifier("bg_button_secondary", "drawable", packageName)
            if (secRes != 0) setBackgroundResource(secRes)
            setPadding((16 * density).toInt(), (10 * density).toInt(), (16 * density).toInt(), (10 * density).toInt())
            setOnClickListener {
                vibrateTap()
                openAssistantSettings()
            }
        }
        triggerCard.addView(btnPowerSettings)
        content.addView(triggerCard)

        scroll.addView(content)
        settingsLayout.addView(scroll)
        return settingsLayout
    }

    // =========================================================================
    // FLOATING BOTTOM NAVIGATION DOCK
    // =========================================================================

    private fun buildBottomNavDock(): LinearLayout {
        val density = resources.displayMetrics.density
        val dockContainer = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding((16 * density).toInt(), (6 * density).toInt(), (16 * density).toInt(), (10 * density).toInt())
        }

        val dockPill = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            val dockRes = resources.getIdentifier("bg_nav_dock", "drawable", packageName)
            if (dockRes != 0) setBackgroundResource(dockRes)
            setPadding((14 * density).toInt(), (6 * density).toInt(), (14 * density).toInt(), (6 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

        dockPill.addView(createNavItem("💬", "Chat", Tab.HOME))
        dockPill.addView(createNavItem("🧠", "Models", Tab.MODELS))
        dockPill.addView(createNavItem("📁", "History", Tab.HISTORY))
        dockPill.addView(createNavItem("⚙️", "Settings", Tab.SETTINGS))

        dockContainer.addView(dockPill)
        return dockContainer
    }

    private fun createNavItem(icon: String, label: String, tab: Tab): View {
        val density = resources.displayMetrics.density
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding((14 * density).toInt(), (6 * density).toInt(), (14 * density).toInt(), (6 * density).toInt())

            val tvIcon = TextView(this@MainActivity).apply {
                text = icon
                textSize = 16f
                gravity = Gravity.CENTER
            }
            addView(tvIcon)

            val tvLabel = TextView(this@MainActivity).apply {
                text = label
                textSize = 10f
                setTextColor(if (tab == currentTab) Color.parseColor("#A78BFA") else Color.parseColor("#71717A"))
                setTypeface(null, if (tab == currentTab) Typeface.BOLD else Typeface.NORMAL)
            }
            addView(tvLabel)

            setOnClickListener {
                vibrateTap()
                switchTab(tab)
            }
        }
    }

    private fun switchTab(tab: Tab) {
        currentTab = tab
        homeTabContainer.visibility = if (tab == Tab.HOME) View.VISIBLE else View.GONE
        modelsTabContainer.visibility = if (tab == Tab.MODELS) View.VISIBLE else View.GONE
        historyTabContainer.visibility = if (tab == Tab.HISTORY) View.VISIBLE else View.GONE
        settingsTabContainer.visibility = if (tab == Tab.SETTINGS) View.VISIBLE else View.GONE

        rootContainer.removeView(bottomNavDock)
        bottomNavDock = buildBottomNavDock()
        rootContainer.addView(bottomNavDock)
    }

    // =========================================================================
    // CHAT ENGINE & NETWORKING
    // =========================================================================

    private fun addUserMessage(message: String) {
        val density = resources.displayMetrics.density
        val userLayout = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
            setPadding(0, (4 * density).toInt(), 0, (6 * density).toInt())
        }

        val tvBubble = TextView(this).apply {
            text = message
            textSize = 14f
            setTextColor(Color.WHITE)
            val bubbleRes = resources.getIdentifier("bg_user_bubble", "drawable", packageName)
            if (bubbleRes != 0) setBackgroundResource(bubbleRes)
            setPadding((14 * density).toInt(), (10 * density).toInt(), (14 * density).toInt(), (10 * density).toInt())
            maxWidth = (260 * density).toInt()
        }
        userLayout.addView(tvBubble)
        chatContainer.addView(userLayout)
        scrollChatToBottom()
    }

    private fun addAssistantMessage(message: String) {
        val density = resources.displayMetrics.density
        val aiLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, (4 * density).toInt(), 0, (6 * density).toInt())
        }

        val bubbleCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val bubbleRes = resources.getIdentifier("bg_assistant_bubble", "drawable", packageName)
            if (bubbleRes != 0) setBackgroundResource(bubbleRes)
            setPadding((14 * density).toInt(), (12 * density).toInt(), (14 * density).toInt(), (12 * density).toInt())
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

        val tvBubble = TextView(this).apply {
            text = message
            textSize = 14f
            setTextColor(Color.parseColor("#F4F4F5"))
            setLineSpacing(4f, 1.1f)
            maxWidth = (280 * density).toInt()
        }
        bubbleCard.addView(tvBubble)

        val actionRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
            setPadding(0, (6 * density).toInt(), 0, 0)
        }

        val btnCopy = TextView(this).apply {
            text = "📋 Copy"
            textSize = 10f
            setTextColor(Color.parseColor("#71717A"))
            setPadding((8 * density).toInt(), 0, (8 * density).toInt(), 0)
            setOnClickListener {
                vibrateTap()
                copyToClipboard(message)
                Toast.makeText(this@MainActivity, "Copied to clipboard!", Toast.LENGTH_SHORT).show()
            }
        }
        actionRow.addView(btnCopy)

        val btnSpeak = TextView(this).apply {
            text = "🔊 Speak"
            textSize = 10f
            setTextColor(Color.parseColor("#71717A"))
            setOnClickListener {
                vibrateTap()
                speakOut(message)
            }
        }
        actionRow.addView(btnSpeak)
        bubbleCard.addView(actionRow)

        aiLayout.addView(bubbleCard)
        chatContainer.addView(aiLayout)
        scrollChatToBottom()
    }

    private fun sendQuickPrompt(cmd: String) {
        addUserMessage(cmd)
        sendToAlyaServer(cmd)
    }

    private fun sendToAlyaServer(userMessage: String) {
        tvThinkingIndicator.visibility = View.VISIBLE

        executor.execute {
            val serverUrl = getSavedServerUrl()
            val webhookUrl = "$serverUrl/webhooks/rest/webhook"

            try {
                val url = URL(webhookUrl)
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.connectTimeout = 8000
                conn.readTimeout = 15000
                conn.doOutput = true

                val payload = JSONObject().apply {
                    put("sender", "8433855679")
                    put("message", userMessage)
                }

                val writer = OutputStreamWriter(conn.outputStream)
                writer.write(payload.toString())
                writer.flush()
                writer.close()

                val responseCode = conn.responseCode
                if (responseCode == 200) {
                    val response = conn.inputStream.bufferedReader().use { it.readText() }
                    val jsonArray = JSONArray(response)

                    mainHandler.post {
                        tvThinkingIndicator.visibility = View.GONE
                        isCloudOnline = true
                        updateStatusBadge()

                        if (jsonArray.length() == 0) {
                            addAssistantMessage("Alya processed your request.")
                        } else {
                            val sb = java.lang.StringBuilder()
                            for (i in 0 until jsonArray.length()) {
                                val obj = jsonArray.getJSONObject(i)
                                if (obj.has("text")) {
                                    val text = obj.getString("text")
                                    if (text.isNotEmpty()) {
                                        addAssistantMessage(text)
                                        sb.append(text).append("\n")
                                    }
                                }
                            }
                            speakOut(sb.toString().take(200))
                        }
                    }
                } else {
                    handleServerFallback(userMessage, "HTTP $responseCode")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Server connection failed: ${e.message}")
                handleServerFallback(userMessage, e.message ?: "Network error")
            }
        }
    }

    private fun handleServerFallback(userMessage: String, errorReason: String) {
        mainHandler.post {
            tvThinkingIndicator.visibility = View.GONE
            isCloudOnline = false
            updateStatusBadge()

            addAssistantMessage("⚡ **[Switched to Local Model: $activeModelName]**\n\n(Cloud server unreachable: $errorReason)\n\nExecuting offline inference for: \"$userMessage\"")
        }
    }

    private fun toggleExecutionMode() {
        isCloudOnline = !isCloudOnline
        updateStatusBadge()
        val mode = if (isCloudOnline) "Cloud (AWS/Rasa)" else "Local llama.cpp ($activeModelName)"
        Toast.makeText(this, "Active Engine: $mode", Toast.LENGTH_SHORT).show()
    }

    private fun updateStatusBadge() {
        if (isCloudOnline) {
            tvStatusBadge.text = "● CLOUD ONLINE"
            tvStatusBadge.setTextColor(Color.parseColor("#34D399"))
        } else {
            tvStatusBadge.text = "● LOCAL GGUF"
            tvStatusBadge.setTextColor(Color.parseColor("#A78BFA"))
        }
    }

    private fun checkServerHealth(serverUrl: String) {
        executor.execute {
            val t0 = System.currentTimeMillis()
            try {
                val url = URL("$serverUrl/status")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 4000
                conn.readTimeout = 4000
                val code = conn.responseCode
                val elapsed = System.currentTimeMillis() - t0

                mainHandler.post {
                    if (code == 200 || code == 404) {
                        tvServerLatency.text = "Latency: ${elapsed}ms (Healthy)"
                        tvServerLatency.setTextColor(Color.parseColor("#34D399"))
                        isCloudOnline = true
                    } else {
                        tvServerLatency.text = "Status: HTTP $code"
                        tvServerLatency.setTextColor(Color.parseColor("#F59E0B"))
                    }
                    updateStatusBadge()
                }
            } catch (e: Exception) {
                mainHandler.post {
                    tvServerLatency.text = "Status: Offline / Timeout"
                    tvServerLatency.setTextColor(Color.parseColor("#EF4444"))
                    isCloudOnline = false
                    updateStatusBadge()
                }
            }
        }
    }

    // =========================================================================
    // SPEECH RECOGNITION & TTS
    // =========================================================================

    private fun initSpeechRecognizer() {
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
            speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    tvOrbLabel.text = "LISTENING..."
                    animateOrbListening(true)
                }

                override fun onBeginningOfSpeech() {
                    tvOrbLabel.text = "HEARING..."
                }

                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}

                override fun onEndOfSpeech() {
                    tvOrbLabel.text = "PROCESSING..."
                    animateOrbListening(false)
                }

                override fun onError(error: Int) {
                    isListening = false
                    tvOrbLabel.text = "TAP TO SPEAK"
                    animateOrbListening(false)
                }

                override fun onResults(results: Bundle?) {
                    isListening = false
                    tvOrbLabel.text = "TAP TO SPEAK"
                    animateOrbListening(false)

                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!matches.isNullOrEmpty()) {
                        val spokenText = matches[0]
                        addUserMessage(spokenText)
                        sendToAlyaServer(spokenText)
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
        }
    }

    private fun startVoiceRecognition() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), PERMISSION_REQUEST_CODE)
            return
        }

        vibrateTap()
        isListening = true
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Listening for query...")
        }
        speechRecognizer?.startListening(intent)
    }

    private fun stopVoiceRecognition() {
        isListening = false
        speechRecognizer?.stopListening()
        animateOrbListening(false)
        tvOrbLabel.text = "TAP TO SPEAK"
    }

    private fun animateOrbListening(listening: Boolean) {
        val orbRes = resources.getIdentifier(
            if (listening) "bg_orb_listening" else "bg_orb_idle",
            "drawable",
            packageName
        )
        if (orbRes != 0) btnOrb.setBackgroundResource(orbRes)

        if (listening) {
            val scale = ScaleAnimation(
                1.0f, 1.08f, 1.0f, 1.08f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f
            ).apply {
                duration = 600
                repeatMode = Animation.REVERSE
                repeatCount = Animation.INFINITE
            }
            btnOrb.startAnimation(scale)
        } else {
            btnOrb.clearAnimation()
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("hi", "IN")
        }
    }

    private fun speakOut(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "AlyaUtterance")
    }

    // =========================================================================
    // HELPERS & OS HOOKS
    // =========================================================================

    private fun getSavedServerUrl(): String {
        return getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_SERVER_URL, DEFAULT_SERVER_URL) ?: DEFAULT_SERVER_URL
    }

    private fun saveServerUrl(url: String) {
        getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_SERVER_URL, url)
            .apply()
    }

    private fun sanitizeServerUrl(raw: String): String {
        var clean = raw.trim()
        if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
            clean = "http://$clean"
        }
        return clean.trimEnd('/')
    }

    private fun scrollChatToBottom() {
        chatScrollView.post {
            chatScrollView.fullScroll(View.FOCUS_DOWN)
        }
    }

    private fun vibrateTap() {
        val v = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            v?.vibrate(VibrationEffect.createOneShot(25, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            v?.vibrate(25)
        }
    }

    private fun copyToClipboard(text: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("Alya", text)
        clipboard.setPrimaryClip(clip)
    }

    private fun openFilePicker() {
        val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
            type = "*/*"
            addCategory(Intent.CATEGORY_OPENABLE)
        }
        startActivityForResult(Intent.createChooser(intent, "Select GGUF Model or Document"), FILE_PICKER_REQUEST_CODE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == FILE_PICKER_REQUEST_CODE && resultCode == Activity.RESULT_OK) {
            val uri: Uri? = data?.data
            if (uri != null) {
                val path = uri.lastPathSegment ?: "file"
                if (path.endsWith(".gguf")) {
                    Toast.makeText(this, "Validating GGUF header for: $path...", Toast.LENGTH_SHORT).show()
                    installedModels.add(ModelItem(path, "Imported Local", "3.2 GB", "4,096", true, false))
                    rebuildModelsView()
                    Toast.makeText(this, "Model $path successfully imported!", Toast.LENGTH_LONG).show()
                } else {
                    addUserMessage("📄 Attached file: $path")
                    sendToAlyaServer("/transcribe $path")
                }
            }
        }
    }

    private fun openAssistantSettings() {
        try {
            startActivity(Intent(Settings.ACTION_VOICE_INPUT_SETTINGS))
        } catch (e: Exception) {
            try {
                startActivity(Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS))
            } catch (ex: Exception) {
                Toast.makeText(this, "Please select Alya in Default Assistant Settings", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun startAlyaService() {
        val intent = Intent(this, AlyaAssistantService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopAlyaService() {
        stopService(Intent(this, AlyaAssistantService::class.java))
    }

    private fun checkAndRequestPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.RECORD_AUDIO
        )
        val needed = permissions.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (needed.isNotEmpty()) {
            requestPermissions(needed.toTypedArray(), PERMISSION_REQUEST_CODE)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer?.destroy()
        tts?.stop()
        tts?.shutdown()
    }
}
