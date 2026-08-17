import React, { useState, useRef, useEffect } from "react";
import {
  Menu,
  Smile,
  Paperclip,
  Mic,
  Send,
  X,
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
  CloudSun,
  Newspaper,
  DollarSign,
  Search,
  Sparkles,
  CheckCircle2,
  Trash2
} from "lucide-react";

/**
 * Categorized Telegram Bot Commands for the bottom sheet menu
 */
const BOT_COMMANDS = [
  {
    category: "🌤️ Real-Time Free APIs",
    items: [
      { cmd: "/weather", desc: "Live weather forecast", icon: "🌤️", example: "/weather Mumbai" },
      { cmd: "/news", desc: "Top headlines & news digest", icon: "🗞️", example: "/news tech" },
      { cmd: "/currency", desc: "Real-time currency exchange", icon: "💱", example: "/currency 100 USD INR" },
      { cmd: "/crypto", desc: "Live crypto prices & gas fees", icon: "🪙", example: "/crypto btc,eth" },
      { cmd: "/wiki", desc: "Wikipedia encyclopedia search", icon: "📚", example: "/wiki AI" },
      { cmd: "/movie", desc: "IMDb ratings, directors & plot", icon: "🎬", example: "/movie Interstellar" },
      { cmd: "/holiday", desc: "Public holidays & festivals", icon: "🎉", example: "/holiday IN" },
      { cmd: "/image", desc: "Search high-res stock photos", icon: "🖼️", example: "/image nature" },
      { cmd: "/breach", desc: "Email & password leak check", icon: "🚨", example: "/breach test@example.com" },
      { cmd: "/math", desc: "WolframAlpha & calculus solver", icon: "🔢", example: "/math solve 2x+5=15" },
    ],
  },
  {
    category: "📋 Utilities & Tools",
    items: [
      { cmd: "/remind", desc: "Set time-based reminder", icon: "⏰", example: "/remind in 10 mins Call client" },
      { cmd: "/todo", desc: "Add task to to-do list", icon: "✅", example: "/todo Buy groceries" },
      { cmd: "/expense", desc: "Log expense & category", icon: "💰", example: "/expense 500 food Lunch" },
      { cmd: "/traffic", desc: "Commute ETA & live distance", icon: "🚗", example: "/traffic Mumbai to Pune" },
      { cmd: "/ride", desc: "Uber & Ola cab fare estimates", icon: "🚖", example: "/ride Mumbai to Pune" },
      { cmd: "/serverstatus", desc: "EC2 CPU, RAM & Disk health", icon: "🖥️", example: "/serverstatus" },
    ],
  },
  {
    category: "📁 Documents & Productivity",
    items: [
      { cmd: "/pdf", desc: "Generate styled PDF document", icon: "📄", example: "/pdf Weekly Report" },
      { cmd: "/excel", desc: "Generate styled Excel sheet", icon: "📊", example: "/excel Budget 2026" },
      { cmd: "/doc", desc: "Generate Word document (.docx)", icon: "📝", example: "/doc Meeting Notes" },
      { cmd: "/gmail", desc: "Read latest Gmail messages", icon: "📬", example: "/gmail" },
      { cmd: "/outlook", desc: "Read recent Outlook emails", icon: "📧", example: "/outlook" },
      { cmd: "/github", desc: "GitHub repos, issues & PRs", icon: "🐙", example: "/github" },
      { cmd: "/code", desc: "OpenCode AI coding delegation", icon: "💻", example: "/code Build uptime checker" },
    ],
  },
];

const POPULAR_EMOJIS = [
  "😀", "😂", "🔥", "👍", "❤️", "🎉", "✨", "🚀", "💡", "🤖",
  "🌤️", "🚗", "💰", "📊", "📄", "⚡", "💯", "👏", "✅", "🙌"
];

/**
 * Reusable Telegram Dark Theme Chat Input Bar
 *
 * @param {Object} props
 * @param {Function} props.onSendMessage - Callback when text is sent: (text: string) => void
 * @param {Function} props.onSendCommand - Callback when a command is selected from the menu: (cmd: string) => void
 * @param {Function} props.onAttachFile - Callback when attachment is selected: (type: string, file?: File) => void
 * @param {Function} props.onVoiceRecord - Callback when voice recording is completed: (blob: Blob) => void
 * @param {boolean} [props.disabled=false] - Whether input is disabled
 * @param {string} [props.placeholder="Message"] - Input placeholder text
 */
export default function TelegramChatInput({
  onSendMessage,
  onSendCommand,
  onAttachFile,
  onVoiceRecord,
  disabled = false,
  placeholder = "Message",
}) {
  const [message, setMessage] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isEmojiOpen, setIsEmojiOpen] = useState(false);
  const [isAttachOpen, setIsAttachOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const [searchFilter, setSearchFilter] = useState("");

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const recordingTimerRef = useRef(null);

  // Trigger Telegram WebApp Haptic Feedback if running inside Telegram Mini App
  const triggerHaptic = (style = "light") => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred(style);
    }
  };

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  // Voice recording timer
  useEffect(() => {
    if (isRecording) {
      recordingTimerRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      setRecordDuration(0);
    }
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    };
  }, [isRecording]);

  const handleSend = () => {
    if (!message.trim() || disabled) return;
    triggerHaptic("medium");
    if (onSendMessage) onSendMessage(message.trim());
    setMessage("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCommandSelect = (cmdExample) => {
    triggerHaptic("selection");
    setIsMenuOpen(false);
    if (onSendCommand) {
      onSendCommand(cmdExample);
    } else {
      setMessage(cmdExample);
      if (textareaRef.current) textareaRef.current.focus();
    }
  };

  const handleEmojiClick = (emoji) => {
    triggerHaptic("light");
    setMessage((prev) => prev + emoji);
    if (textareaRef.current) textareaRef.current.focus();
  };

  const handleMicPress = () => {
    triggerHaptic("heavy");
    if (!isRecording) {
      setIsRecording(true);
    } else {
      setIsRecording(false);
      if (onVoiceRecord) onVoiceRecord(null);
    }
  };

  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins}:${s < 10 ? "0" : ""}${s}`;
  };

  return (
    <div className="relative w-full font-sans select-none">
      {/* ------------------------------------------------------------- */}
      {/* 1. BOTTOM SHEET COMMANDS DRAWER (Telegram Menu)               */}
      {/* ------------------------------------------------------------- */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/60 backdrop-blur-sm transition-opacity">
          <div className="relative max-h-[80vh] w-full rounded-t-3xl border-t border-[#2c3848] bg-[#17212b] p-4 text-white shadow-2xl animate-in slide-in-from-bottom duration-200">
            {/* Sheet Handle */}
            <div className="mx-auto mb-3 h-1.5 w-12 rounded-full bg-[#415264]" />

            {/* Header with Search */}
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#5b6eea]/20 text-[#5b6eea]">
                  <Sparkles size={18} />
                </div>
                <h3 className="text-lg font-semibold text-white">Bot Commands</h3>
              </div>
              <button
                onClick={() => setIsMenuOpen(false)}
                className="rounded-full p-1.5 text-gray-400 hover:bg-[#232e3c] hover:text-white"
              >
                <X size={20} />
              </button>
            </div>

            {/* Search Input */}
            <div className="relative mb-3">
              <Search className="absolute left-3 top-2.5 text-gray-400" size={16} />
              <input
                type="text"
                placeholder="Search commands (e.g. weather, pdf, remind)..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full rounded-xl bg-[#0e1621] py-2 pl-9 pr-3 text-sm text-white placeholder-gray-500 outline-none focus:ring-1 focus:ring-[#5b6eea]"
              />
            </div>

            {/* Commands List Scrollable Container */}
            <div className="max-h-[50vh] space-y-4 overflow-y-auto pr-1">
              {BOT_COMMANDS.map((cat, idx) => {
                const filtered = cat.items.filter(
                  (i) =>
                    i.cmd.toLowerCase().includes(searchFilter.toLowerCase()) ||
                    i.desc.toLowerCase().includes(searchFilter.toLowerCase())
                );
                if (filtered.length === 0) return null;

                return (
                  <div key={idx} className="space-y-1.5">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                      {cat.category}
                    </div>
                    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                      {filtered.map((item, cIdx) => (
                        <button
                          key={cIdx}
                          onClick={() => handleCommandSelect(item.example)}
                          className="flex items-center justify-between rounded-xl bg-[#202b36] p-2.5 text-left transition hover:bg-[#2b394a] active:scale-[0.98]"
                        >
                          <div className="flex items-center gap-2.5">
                            <span className="text-xl">{item.icon}</span>
                            <div>
                              <div className="font-mono text-sm font-semibold text-[#6ab2f2]">
                                {item.cmd}
                              </div>
                              <div className="text-xs text-gray-300">{item.desc}</div>
                            </div>
                          </div>
                          <span className="text-[11px] font-medium text-gray-400">
                            {item.example}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 2. EMOJI PICKER POPUP                                         */}
      {/* ------------------------------------------------------------- */}
      {isEmojiOpen && (
        <div className="absolute bottom-16 left-12 z-40 w-72 rounded-2xl border border-[#2c3848] bg-[#17212b] p-3 shadow-2xl animate-in zoom-in-95 duration-150">
          <div className="mb-2 flex items-center justify-between border-b border-[#242f3d] pb-1.5 text-xs font-medium text-gray-400">
            <span>Quick Reactions & Emojis</span>
            <button onClick={() => setIsEmojiOpen(false)} className="text-gray-400 hover:text-white">
              <X size={14} />
            </button>
          </div>
          <div className="grid grid-cols-5 gap-2 text-2xl">
            {POPULAR_EMOJIS.map((emoji, i) => (
              <button
                key={i}
                onClick={() => handleEmojiClick(emoji)}
                className="flex h-10 w-10 items-center justify-center rounded-lg transition hover:bg-[#2b394a] active:scale-125"
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. ATTACHMENT POPUP OPTIONS                                   */}
      {/* ------------------------------------------------------------- */}
      {isAttachOpen && (
        <div className="absolute bottom-16 right-12 z-40 w-56 rounded-2xl border border-[#2c3848] bg-[#17212b] p-2 shadow-2xl animate-in zoom-in-95 duration-150">
          <button
            onClick={() => {
              setIsAttachOpen(false);
              fileInputRef.current?.click();
            }}
            className="flex w-full items-center gap-3 rounded-xl p-2.5 text-sm text-gray-200 hover:bg-[#2b394a]"
          >
            <ImageIcon size={18} className="text-blue-400" />
            <span>Photo / Image</span>
          </button>
          <button
            onClick={() => {
              setIsAttachOpen(false);
              fileInputRef.current?.click();
            }}
            className="flex w-full items-center gap-3 rounded-xl p-2.5 text-sm text-gray-200 hover:bg-[#2b394a]"
          >
            <FileText size={18} className="text-amber-400" />
            <span>Document (PDF/Doc)</span>
          </button>
          <button
            onClick={() => {
              setIsAttachOpen(false);
              fileInputRef.current?.click();
            }}
            className="flex w-full items-center gap-3 rounded-xl p-2.5 text-sm text-gray-200 hover:bg-[#2b394a]"
          >
            <FileSpreadsheet size={18} className="text-emerald-400" />
            <span>Excel Spreadsheet</span>
          </button>
        </div>
      )}

      {/* Hidden File Input Trigger */}
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.[0] && onAttachFile) {
            onAttachFile("file", e.target.files[0]);
          }
        }}
      />

      {/* ------------------------------------------------------------- */}
      {/* 4. MAIN TELEGRAM CHAT INPUT BAR CONTAINER                     */}
      {/* ------------------------------------------------------------- */}
      <div className="flex w-full flex-col items-center bg-[#0e1621] px-2 pt-2 pb-1.5 border-t border-[#1b2633]">
        {/* Floating Input Pill Bar */}
        <div className="flex w-full max-w-4xl items-center gap-1.5 rounded-3xl bg-[#17212b] px-2 py-1.5 shadow-md border border-[#232e3c]/50">
          
          {/* VOICE RECORDING STATE VIEW */}
          {isRecording ? (
            <div className="flex flex-1 items-center justify-between px-3 py-1 text-white animate-pulse">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-red-500 animate-ping" />
                <span className="text-sm font-semibold text-red-400">Recording Audio...</span>
                <span className="font-mono text-sm text-gray-300">({formatTime(recordDuration)})</span>
              </div>
              <button
                onClick={() => setIsRecording(false)}
                className="flex items-center gap-1 rounded-lg bg-red-500/20 px-2.5 py-1 text-xs text-red-300 hover:bg-red-500/30"
              >
                <Trash2 size={14} /> Cancel
              </button>
            </div>
          ) : (
            <>
              {/* Left Pill "Menu" Button */}
              <button
                type="button"
                onClick={() => {
                  triggerHaptic("medium");
                  setIsMenuOpen(true);
                }}
                className="flex shrink-0 items-center gap-1.5 rounded-full bg-[#5b6eea] px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#6c7ff2] active:scale-95"
                title="Bot Commands Menu"
              >
                <Menu size={15} strokeWidth={2.5} />
                <span>Menu</span>
              </button>

              {/* Emoji Button */}
              <button
                type="button"
                onClick={() => {
                  triggerHaptic("light");
                  setIsEmojiOpen(!isEmojiOpen);
                  setIsAttachOpen(false);
                }}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-gray-400 transition hover:bg-[#242f3d] hover:text-gray-200 active:scale-95"
                title="Emojis"
              >
                <Smile size={20} strokeWidth={1.8} />
              </button>

              {/* Center Text Input Area */}
              <div className="flex flex-1 items-center">
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={placeholder}
                  disabled={disabled}
                  className="w-full resize-none bg-transparent px-2 py-1.5 text-sm text-white placeholder-gray-400 outline-none leading-relaxed overflow-y-auto max-h-28"
                  style={{ minHeight: "24px" }}
                />
              </div>

              {/* Paperclip / Attachment Button */}
              <button
                type="button"
                onClick={() => {
                  triggerHaptic("light");
                  setIsAttachOpen(!isAttachOpen);
                  setIsEmojiOpen(false);
                }}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-gray-400 transition hover:bg-[#242f3d] hover:text-gray-200 active:scale-95"
                title="Attach Document or Media"
              >
                <Paperclip size={20} strokeWidth={1.8} />
              </button>
            </>
          )}

          {/* Right Action Button (Mic <-> Send dynamic toggle) */}
          {message.trim().length > 0 ? (
            <button
              type="button"
              onClick={handleSend}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#5b6eea] text-white shadow-md transition hover:bg-[#6c7ff2] hover:scale-105 active:scale-95 animate-in zoom-in-75 duration-100"
              title="Send Message"
            >
              <Send size={16} className="ml-0.5" strokeWidth={2.2} />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleMicPress}
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition shadow-md ${
                isRecording
                  ? "bg-red-500 text-white animate-bounce"
                  : "bg-[#5b6eea] text-white hover:bg-[#6c7ff2] active:scale-95"
              }`}
              title="Record Voice Message"
            >
              <Mic size={18} strokeWidth={2.2} />
            </button>
          )}
        </div>

        {/* ------------------------------------------------------------- */}
        {/* 5. BOTTOM MOBILE HOME GESTURE INDICATOR                       */}
        {/* ------------------------------------------------------------- */}
        <div className="mt-1.5 mb-0.5 h-1 w-32 rounded-full bg-gray-600/50" />
      </div>
    </div>
  );
}
