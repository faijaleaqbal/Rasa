package com.alya.aiagent.talents

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.AlarmClock
import android.util.Log
import com.alya.aiagent.network.AlyaRepository
import com.alya.aiagent.network.NetworkResult
import com.alya.aiagent.network.RasaMessage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.coroutines.resume

data class TalentTool(
    val name: String,
    val description: String,
    val parametersJsonSchema: String
)

data class TalentExecutionResult(
    val toolName: String,
    val success: Boolean,
    val output: String
)

/**
 * PocketPal & Atomic-Chat style AgentRunner & Talents Engine.
 * Supports tool calling for math, datetime, device actions, and cloud Rasa skills bridge.
 */
class TalentEngine(private val context: Context) {

    companion object {
        private const val TAG = "TalentEngine"

        val AVAILABLE_TOOLS = listOf(
            TalentTool(
                name = "calculate",
                description = "Perform mathematical and arithmetic evaluations",
                parametersJsonSchema = "{\"type\":\"object\",\"properties\":{\"expression\":{\"type\":\"string\",\"description\":\"Math formula like 45 * 12 + 10\"}},\"required\":[\"expression\"]}"
            ),
            TalentTool(
                name = "datetime",
                description = "Get the current exact local date, time, and day of week",
                parametersJsonSchema = "{\"type\":\"object\",\"properties\":{},\"required\":[]}"
            ),
            TalentTool(
                name = "device_action",
                description = "Trigger native Android device actions such as phone calling, sending SMS, setting alarms or timers",
                parametersJsonSchema = "{\"type\":\"object\",\"properties\":{\"action\":{\"type\":\"string\",\"enum\":[\"call\",\"sms\",\"alarm\",\"timer\"]},\"target\":{\"type\":\"string\"},\"value\":{\"type\":\"string\"}},\"required\":[\"action\"]}"
            ),
            TalentTool(
                name = "cloud_bridge",
                description = "Query Alya Cloud Brain (Rasa + Groq) for real-time live info (weather, crypto, news, wiki, stocks, train status)",
                parametersJsonSchema = "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\",\"description\":\"User's real-time query\"}},\"required\":[\"query\"]}"
            )
        )
    }

    private val repository = AlyaRepository(context)

    fun detectAndExtractToolCall(text: String): Pair<String, String>? {
        val funcRegex = Regex("""<tool>(\w+):\s*(.*?)</tool>""", RegexOption.DOT_MATCHES_ALL)
        val funcMatch = funcRegex.find(text)
        if (funcMatch != null) {
            val name = funcMatch.groupValues[1].trim()
            val arg = funcMatch.groupValues[2].trim()
            return Pair(name, arg)
        }

        val jsonToolRegex = Regex("""```json\s*\{\s*"tool":\s*"(\w+)",\s*"argument":\s*"([^"]+)"\s*\}\s*```""")
        val jsonMatch = jsonToolRegex.find(text)
        if (jsonMatch != null) {
            val name = jsonMatch.groupValues[1].trim()
            val arg = jsonMatch.groupValues[2].trim()
            return Pair(name, arg)
        }

        return null
    }

    suspend fun executeTalent(toolName: String, argument: String): TalentExecutionResult = withContext(Dispatchers.IO) {
        try {
            when (toolName.lowercase()) {
                "calculate", "math" -> {
                    val result = evaluateMathExpression(argument)
                    TalentExecutionResult(toolName, true, "Result: $result")
                }
                "datetime", "time", "date" -> {
                    val now = Date()
                    val sdf = SimpleDateFormat("EEEE, dd MMMM yyyy, hh:mm:ss a (z)", Locale.getDefault())
                    TalentExecutionResult(toolName, true, "Current Time: ${sdf.format(now)}")
                }
                "device_action" -> {
                    val res = executeDeviceAction(argument)
                    TalentExecutionResult(toolName, true, res)
                }
                "cloud_bridge", "cloud", "rasa" -> {
                    val cloudReplies = queryCloud(argument)
                    TalentExecutionResult(toolName, true, cloudReplies)
                }
                else -> {
                    TalentExecutionResult(toolName, false, "Unknown talent tool: $toolName")
                }
            }
        } catch (e: Throwable) {
            Log.e(TAG, "Tool execution failed: ${e.message}", e)
            TalentExecutionResult(toolName, false, "Error executing talent: ${e.message}")
        }
    }

    private suspend fun queryCloud(query: String): String = suspendCancellableCoroutine { continuation ->
        repository.sendMessage(query) { result ->
            when (result) {
                is NetworkResult.Success -> {
                    val replies = result.data.joinToString("\n") { it.text ?: "" }
                    continuation.resume(replies.ifBlank { "Cloud answered without text." })
                }
                is NetworkResult.Error -> {
                    continuation.resume("Cloud Error: ${result.message}")
                }
                is NetworkResult.Offline -> {
                    continuation.resume("Offline: ${result.message}")
                }
                is NetworkResult.Timeout -> {
                    continuation.resume("Timeout: ${result.message}")
                }
            }
        }
    }

    private fun evaluateMathExpression(expr: String): String {
        return try {
            val clean = expr.replace("x", "*").replace("X", "*").replace(" ", "")
            val parsed = evalSimpleMath(clean)
            if (parsed == parsed.toLong().toDouble()) {
                parsed.toLong().toString()
            } else {
                String.format(Locale.US, "%.4f", parsed).trimEnd('0').trimEnd('.')
            }
        } catch (e: Exception) {
            "Could not calculate: $expr"
        }
    }

    private fun evalSimpleMath(str: String): Double {
        return object : Any() {
            var pos = -1
            var ch = 0

            fun nextChar() {
                ch = if (++pos < str.length) str[pos].code else -1
            }

            fun eat(charToEat: Int): Boolean {
                while (ch == ' '.code) nextChar()
                if (ch == charToEat) {
                    nextChar()
                    return true
                }
                return false
            }

            fun parse(): Double {
                nextChar()
                val x = parseExpression()
                if (pos < str.length) throw RuntimeException("Unexpected: " + ch.toChar())
                return x
            }

            fun parseExpression(): Double {
                var x = parseTerm()
                while (true) {
                    if (eat('+'.code)) x += parseTerm()
                    else if (eat('-'.code)) x -= parseTerm()
                    else return x
                }
            }

            fun parseTerm(): Double {
                var x = parseFactor()
                while (true) {
                    if (eat('*'.code)) x *= parseFactor()
                    else if (eat('/'.code)) x /= parseFactor()
                    else return x
                }
            }

            fun parseFactor(): Double {
                if (eat('+'.code)) return parseFactor()
                if (eat('-'.code)) return -parseFactor()
                var x: Double
                val startPos = pos
                if (eat('('.code)) {
                    x = parseExpression()
                    eat(')'.code)
                } else if ((ch in '0'.code..'9'.code) || ch == '.'.code) {
                    while ((ch in '0'.code..'9'.code) || ch == '.'.code) nextChar()
                    x = str.substring(startPos, pos).toDouble()
                } else {
                    throw RuntimeException("Unexpected: " + ch.toChar())
                }
                return x
            }
        }.parse()
    }

    private suspend fun executeDeviceAction(actionString: String): String = withContext(Dispatchers.Main) {
        try {
            val lower = actionString.lowercase()
            when {
                lower.startsWith("call:") || lower.startsWith("dial:") -> {
                    val phone = actionString.substringAfter(":").trim()
                    val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone")).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(intent)
                    "Opening phone dialer for: $phone"
                }
                lower.startsWith("alarm:") -> {
                    val parts = actionString.substringAfter(":").trim().split(":")
                    val hour = parts.getOrNull(0)?.toIntOrNull() ?: 7
                    val min = parts.getOrNull(1)?.toIntOrNull() ?: 0
                    val intent = Intent(AlarmClock.ACTION_SET_ALARM).apply {
                        putExtra(AlarmClock.EXTRA_HOUR, hour)
                        putExtra(AlarmClock.EXTRA_MINUTES, min)
                        putExtra(AlarmClock.EXTRA_MESSAGE, "Alya Alarm")
                        putExtra(AlarmClock.EXTRA_SKIP_UI, false)
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(intent)
                    "Setting alarm for %02d:%02d".format(hour, min)
                }
                lower.startsWith("timer:") -> {
                    val seconds = actionString.substringAfter(":").trim().toIntOrNull() ?: 60
                    val intent = Intent(AlarmClock.ACTION_SET_TIMER).apply {
                        putExtra(AlarmClock.EXTRA_LENGTH, seconds)
                        putExtra(AlarmClock.EXTRA_MESSAGE, "Alya Timer")
                        putExtra(AlarmClock.EXTRA_SKIP_UI, false)
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    }
                    context.startActivity(intent)
                    "Setting timer for $seconds seconds"
                }
                else -> {
                    "Executed device action: $actionString"
                }
            }
        } catch (e: Exception) {
            "Device action error: ${e.message}"
        }
    }
}
