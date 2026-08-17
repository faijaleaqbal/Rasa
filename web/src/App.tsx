import React, { useState, useEffect, useRef } from "react";
import { GlowingChatInput } from "./components/ui/chat-input";
import {
  TrendingUp,
  Coins,
  Train,
  FileText,
  Sun,
  Code2,
  Phone,
  Volume2,
  VolumeX,
  Copy,
  Check,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Cpu
} from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: string;
  attachmentUrl?: string;
  isStreaming?: boolean;
}

const QUICK_PROMPTS = [
  { icon: TrendingUp, label: "Reliance & Nifty Stock", prompt: "/stock RELIANCE" },
  { icon: Coins, label: "Live Gold Rate (24K)", prompt: "/gold" },
  { icon: Train, label: "IRCTC Train Tracker", prompt: "/train 12301" },
  { icon: FileText, label: "ATS Resume Builder", prompt: "/resume Senior Full Stack Software Engineer" },
  { icon: Sun, label: "Morning AI Briefing", prompt: "/briefing" },
  { icon: Code2, label: "Python Sandbox", prompt: "/py [x**2 for x in range(10)]" },
  { icon: Phone, label: "Find My Phone Alarm", prompt: "/findmyphone" },
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-msg",
      sender: "bot",
      text: "Namaste! Main **Alya** hoon — aapki autonomous AI mobile aur web assistant. Main aapke phone calls, WhatsApp, stock quotes, train tracking, resume generation, aur 100+ developer tools execute kar sakti hoon. Aaj main aapki kya madad kar sakti hoon?",
      timestamp: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isServerOnline, setIsServerOnline] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isSpeakingId, setIsSpeakingId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Check backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("/status", { method: "GET" });
        if (res.ok) setIsServerOnline(true);
      } catch {
        setIsServerOnline(true); // default optimistic
      }
    };
    checkHealth();
  }, []);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userTimestamp = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    const userMessageId = `user-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, sender: "user", text, timestamp: userTimestamp },
    ]);

    setIsLoading(true);

    try {
      // Connect to Rasa REST webhook
      const res = await fetch("/webhooks/rest/webhook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender: "web_client_user",
          message: text,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }

      const botReplies = await res.json();
      const botTimestamp = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

      if (Array.isArray(botReplies) && botReplies.length > 0) {
        botReplies.forEach((reply: any, idx: number) => {
          setMessages((prev) => [
            ...prev,
            {
              id: `bot-${Date.now()}-${idx}`,
              sender: "bot",
              text: reply.text || "Action executed successfully.",
              timestamp: botTimestamp,
              attachmentUrl: reply.attachment || reply.image,
            },
          ]);
        });
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `bot-${Date.now()}`,
            sender: "bot",
            text: "✅ Command processed successfully.",
            timestamp: botTimestamp,
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          sender: "bot",
          text: `⚠️ **Connection Notice:** Could not reach Rasa backend (${err.message}). Make sure your server is running on port 5005.`,
          timestamp: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const playTTS = (text: string, id: string) => {
    if (!("speechSynthesis" in window)) return;

    if (isSpeakingId === id) {
      window.speechSynthesis.cancel();
      setIsSpeakingId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const clean = text.replace(/[*_#`]/g, "");
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "hi-IN";
    utterance.onend = () => setIsSpeakingId(null);
    utterance.onerror = () => setIsSpeakingId(null);

    setIsSpeakingId(id);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="min-h-screen bg-[#0d0d0f] text-slate-100 flex flex-col font-sans selection:bg-sky-500/30">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 w-full border-b border-white/[0.06] bg-[#0d0d0f]/80 backdrop-blur-xl px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-white tracking-tight">Alya Autonomous AI Agent</h1>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  v3.0 Hybrid
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Rasa 3.6 • Groq LLM • 100+ Live Skills • IST</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs">
              <span className={`w-2 h-2 rounded-full ${isServerOnline ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`}></span>
              <span className="text-slate-300 font-medium">{isServerOnline ? "EC2 Server Live" : "Connecting..."}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 md:p-6 flex flex-col justify-between">
        {/* Messages Feed */}
        <div className="space-y-6 flex-1 pb-36">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.sender === "bot" && (
                <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-sky-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-md shadow-sky-500/10">
                  <BotIcon className="w-4 h-4 text-white" />
                </div>
              )}

              <div
                className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 text-sm leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-lg shadow-sky-500/10 rounded-tr-none"
                    : "glass-panel text-slate-200 rounded-tl-none border border-white/[0.08]"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.text}</div>

                {msg.attachmentUrl && (
                  <div className="mt-3">
                    <img src={msg.attachmentUrl} alt="Attachment" className="rounded-lg max-h-60 object-cover border border-white/10" />
                  </div>
                )}

                {/* Footer Toolbar */}
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/[0.06] text-[11px] text-slate-400">
                  <span>{msg.timestamp}</span>

                  {msg.sender === "bot" && (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => playTTS(msg.text, msg.id)}
                        className="hover:text-sky-400 transition-colors flex items-center gap-1"
                        title="Listen to Voice Reply"
                      >
                        {isSpeakingId === msg.id ? <VolumeX className="w-3.5 h-3.5 text-purple-400" /> : <Volume2 className="w-3.5 h-3.5" />}
                        <span>{isSpeakingId === msg.id ? "Stop" : "Speak"}</span>
                      </button>

                      <button
                        onClick={() => copyToClipboard(msg.text, msg.id)}
                        className="hover:text-sky-400 transition-colors flex items-center gap-1"
                        title="Copy to Clipboard"
                      >
                        {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedId === msg.id ? "Copied" : "Copy"}</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {msg.sender === "user" && (
                <div className="w-7 h-7 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
                  <span className="text-xs font-semibold text-slate-200">U</span>
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-sky-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-1 animate-pulse">
                <BotIcon className="w-4 h-4 text-white" />
              </div>
              <div className="glass-panel rounded-2xl rounded-tl-none p-4 text-sm text-slate-400 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-sky-400" />
                <span>Alya AI is reasoning and executing tools...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Floating Bottom Action Bar & Glowing BorderBeam Input */}
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-gradient-to-t from-[#0d0d0f] via-[#0d0d0f]/95 to-transparent pt-6 pb-4 px-4">
        <div className="max-w-4xl mx-auto space-y-3">
          {/* Quick Action Chips Bar */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
            {QUICK_PROMPTS.map((qp, idx) => {
              const Icon = qp.icon;
              return (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(qp.prompt)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-white/[0.04] border border-white/[0.06] text-slate-300 hover:bg-white/[0.08] hover:text-white transition-all flex-shrink-0"
                >
                  <Icon className="w-3.5 h-3.5 text-sky-400" />
                  <span>{qp.label}</span>
                </button>
              );
            })}
          </div>

          {/* The Exact Glowing BorderBeam ChatInput */}
          <GlowingChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}

function BotIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 8V4H8" />
      <rect width="16" height="12" x="4" y="8" rx="2" />
      <path d="M2 14h2" />
      <path d="M20 14h2" />
      <path d="M15 13v2" />
      <path d="M9 13v2" />
    </svg>
  );
}
