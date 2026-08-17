# 📱 Telegram Dark Theme Chat Input Component

Pixel-perfect Telegram dark theme chat input bar built with **React** + **Tailwind CSS** + **Lucide Icons**, compatible with standard web apps and **Telegram WebApp / Mini Apps**.

---

## 🎨 Visual Design Breakdown
- **Dark Theme Background**: Floating container with `#17212b` & `#0e1621` Telegram Dark palette.
- **Pill-shaped Menu Button**: `#5b6eea` indigo background, white hamburger icon `☰` + `Menu` label.
- **Emoji Picker Drawer**: Interactive popup with popular reactions & emojis.
- **Seamless Auto-resizing Input**: Multi-line expand with `Message` placeholder and no borders.
- **Attachment Picker**: Instant options for Photos, Documents (PDF/Word), and Excel spreadsheets.
- **Dynamic Action Button**: Smooth transition between **Voice Mic** (when empty) and **Paper Plane Send** (when typing).
- **Mobile Home Indicator**: Bottom gesture bar for iOS / Android mobile viewports.
- **Telegram WebApp Haptics**: Auto-triggers `window.Telegram.WebApp.HapticFeedback` on mobile devices.

---

## 🚀 Installation

Install icons if you haven't already:
```bash
npm install lucide-react
```

---

## 💻 Example Usage

```jsx
import React, { useState } from "react";
import TelegramChatInput from "./components/TelegramChatInput";

export default function ChatScreen() {
  const [messages, setMessages] = useState([]);

  const handleSendMessage = (text) => {
    console.log("Sent text:", text);
    setMessages((prev) => [...prev, { sender: "user", text }]);
  };

  const handleSendCommand = (cmd) => {
    console.log("Selected command:", cmd);
    // Directly dispatch slash command to Rasa or backend
    handleSendMessage(cmd);
  };

  const handleAttachFile = (type, file) => {
    console.log("Attached file:", type, file?.name);
  };

  const handleVoiceRecord = (blob) => {
    console.log("Recorded voice note");
  };

  return (
    <div className="flex h-screen flex-col bg-[#0e1621] text-white">
      {/* Chat Messages List */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <div key={i} className="my-2 rounded-xl bg-[#17212b] p-3 max-w-md">
            {m.text}
          </div>
        ))}
      </div>

      {/* Telegram Chat Input Bar */}
      <TelegramChatInput
        onSendMessage={handleSendMessage}
        onSendCommand={handleSendCommand}
        onAttachFile={handleAttachFile}
        onVoiceRecord={handleVoiceRecord}
        placeholder="Message"
      />
    </div>
  );
}
```
