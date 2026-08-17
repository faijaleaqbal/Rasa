import React, { useState, useRef, useEffect } from "react";
import { BorderBeam } from "./border-beam";
import { AtSign, ChevronDown, ArrowUp, Mic, MicOff, Sparkles, Terminal, Bot } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (text: string, mode?: string) => void;
  isLoading: boolean;
}

const CHIP_STYLE: React.CSSProperties = {
  borderRadius: 36,
  background: "rgba(255, 255, 255, 0.05)",
  boxShadow: "inset 0 0 0 1px rgba(255, 255, 255, 0.06), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)",
};

export function GlowingChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [inputText, setInputText] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("Alya Agent");
  const [isListening, setIsListening] = useState(false);
  const [showAgentMenu, setShowAgentMenu] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Web Speech API Voice Recognition
  const toggleVoiceInput = () => {
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please use Chrome/Edge.");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "hi-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      const speechToText = event.results[0][0].transcript;
      setInputText(speechToText);
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const handleSend = () => {
    if (inputText.trim() && !isLoading) {
      onSendMessage(inputText.trim(), selectedAgent);
      setInputText("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative w-full max-w-[540px] mx-auto group">
      <BorderBeam size="md" colorVariant="colorful">
        <div
          className="w-full rounded-[22px] bg-[#16161a] overflow-hidden relative font-sans transition-all"
          style={{
            boxShadow: "inset 0 0 0 1px rgba(255, 255, 255, 0.08), inset 0 0 40px 0 rgba(255, 255, 255, 0.02)",
          }}
        >
          <div className="p-3 flex flex-col min-h-[128px]">
            {/* Top Toolbar */}
            <div className="flex items-center justify-between">
              <div
                style={CHIP_STYLE}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition-colors"
                onClick={() => setInputText((prev) => (prev ? prev : "@alya "))}
              >
                <AtSign className="w-3.5 h-3.5 text-sky-400" />
                <span>alya</span>
              </div>

              {/* Live Status indicator */}
              <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Rasa Brain Active</span>
              </div>
            </div>

            {/* Main Input Text Box */}
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder={isListening ? "🎙️ Listening to you... (Speak now)" : "Ask Alya, run MCP tool, build anything..."}
              className="w-full bg-transparent border-none outline-none text-slate-100 placeholder:text-slate-500 text-[14px] px-1 py-3 focus:ring-0"
            />

            {/* Bottom Action Bar */}
            <div className="flex items-center gap-2 mt-auto pt-2 border-t border-white/[0.04]">
              {/* Agent Selection Pill */}
              <div className="relative">
                <button
                  type="button"
                  style={CHIP_STYLE}
                  onClick={() => setShowAgentMenu(!showAgentMenu)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-300 hover:text-white transition-colors"
                >
                  <Bot className="w-3.5 h-3.5 text-sky-400" />
                  <span>{selectedAgent}</span>
                  <ChevronDown className="w-3 h-3 text-slate-400" />
                </button>

                {showAgentMenu && (
                  <div className="absolute bottom-8 left-0 z-50 w-44 rounded-xl bg-[#1e1e24] border border-white/10 shadow-2xl p-1.5 space-y-1">
                    {["Alya Agent", "Market & Transit", "Document Builder", "Developer & MCP"].map((agent) => (
                      <div
                        key={agent}
                        onClick={() => {
                          setSelectedAgent(agent);
                          setShowAgentMenu(false);
                        }}
                        className="px-2.5 py-1.5 rounded-lg text-xs text-slate-300 hover:bg-white/10 hover:text-white cursor-pointer transition-colors"
                      >
                        {agent}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Auto Mode Pill */}
              <div
                style={CHIP_STYLE}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-400 cursor-default"
              >
                <Sparkles className="w-3 h-3 text-purple-400" />
                <span>Auto-Route</span>
              </div>

              {/* Voice Mic Button */}
              <button
                type="button"
                onClick={toggleVoiceInput}
                style={CHIP_STYLE}
                className={`ml-auto inline-flex items-center justify-center w-8 h-8 rounded-full transition-all ${
                  isListening ? "bg-red-500/20 text-red-400 ring-2 ring-red-500 animate-pulse" : "text-slate-400 hover:text-white hover:bg-white/10"
                }`}
                title="Voice Input (Speech-to-Text)"
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Send Arrow Button */}
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputText.trim() || isLoading}
                style={CHIP_STYLE}
                className={`inline-flex items-center justify-center w-8 h-8 rounded-full transition-all ${
                  inputText.trim() && !isLoading
                    ? "bg-sky-500 text-white hover:bg-sky-400 cursor-pointer shadow-lg shadow-sky-500/20"
                    : "text-slate-600 opacity-50 cursor-not-allowed"
                }`}
                title="Send Message (Enter)"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </BorderBeam>
    </div>
  );
}
