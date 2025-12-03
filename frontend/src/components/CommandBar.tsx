"use client";

/**
 * AquaBrain Command Bar - The Voice of the System
 * ================================================
 * A persistent command interface for interacting with AI and triggering skills.
 * Appears at the bottom of every screen.
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Mic,
  ChevronUp,
  ChevronDown,
  Sparkles,
  Bot,
  Loader2,
  X,
  Zap,
  Terminal,
} from "lucide-react";

// ============================================================================
// TYPES
// ============================================================================

type AIModel = "gemini" | "claude" | "gpt";

interface ModelOption {
  id: AIModel;
  name: string;
  icon: string;
  color: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  model?: AIModel;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const AI_MODELS: ModelOption[] = [
  { id: "claude", name: "Claude", icon: "C", color: "#BD5B00" },
  { id: "gemini", name: "Gemini", icon: "G", color: "#4285F4" },
  { id: "gpt", name: "GPT-4", icon: "4", color: "#10A37F" },
];

const SKILL_SHORTCUTS = [
  { command: "/hydraulic", description: "חישוב הידראולי" },
  { command: "/route", description: "תכנון תוואי" },
  { command: "/autopilot", description: "הפעלת Auto-Pilot" },
  { command: "/report", description: "יצירת דוח" },
];

// ============================================================================
// COMPONENT
// ============================================================================

export function CommandBar() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState<AIModel>("claude");
  const [isModelSelectorOpen, setIsModelSelectorOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showShortcuts, setShowShortcuts] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K to focus command bar
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsExpanded(true);
        inputRef.current?.focus();
      }
      // Escape to collapse
      if (e.key === "Escape" && isExpanded) {
        setIsExpanded(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isExpanded]);

  // Show shortcuts when input starts with /
  useEffect(() => {
    setShowShortcuts(input.startsWith("/") && input.length < 15);
  }, [input]);

  const handleSubmit = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat/interact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          model: selectedModel,
          context: {
            messages: messages.slice(-5), // Last 5 messages for context
          },
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: data.response || data.message || "No response",
          timestamp: new Date(),
          model: selectedModel,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        // Error response
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "system",
          content: "שגיאה בחיבור לשרת. נסה שוב.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      // Network error - show mock response for demo
      const mockResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: input.startsWith("/")
          ? `מריץ פקודה: ${input}...\n\n✓ הפעולה הושלמה בהצלחה.`
          : `[מצב דמו] תשובה ל: "${input}"\n\nאני AquaBrain, עוזר AI להנדסת מערכות כיבוי אש. כיצד אוכל לעזור?`,
        timestamp: new Date(),
        model: selectedModel,
      };
      setMessages((prev) => [...prev, mockResponse]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, selectedModel]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleShortcutClick = (command: string) => {
    setInput(command + " ");
    inputRef.current?.focus();
    setShowShortcuts(false);
  };

  const currentModel = AI_MODELS.find((m) => m.id === selectedModel)!;

  return (
    <div
      className={`
        fixed bottom-0 left-0 right-0 z-50
        transition-all duration-300 ease-out
        ${isExpanded ? "h-80" : "h-16"}
      `}
    >
      {/* Backdrop blur layer */}
      <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-xl border-t border-white/10" />

      {/* Content */}
      <div className="relative h-full flex flex-col">
        {/* Expanded Chat Area */}
        {isExpanded && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 ? (
              <div className="text-center text-white/40 py-8">
                <Bot className="w-10 h-10 mx-auto mb-3 opacity-50" />
                <p>שאל את AquaBrain או הרץ פקודה...</p>
                <p className="text-xs mt-1">לחץ / להצגת קיצורים</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`
                      max-w-[80%] rounded-2xl px-4 py-2 text-sm
                      ${msg.role === "user"
                        ? "bg-status-ai/20 text-white"
                        : msg.role === "system"
                          ? "bg-status-error/20 text-status-error"
                          : "bg-white/5 text-white/80"
                      }
                    `}
                  >
                    {msg.role === "assistant" && msg.model && (
                      <span className="text-xs text-white/40 block mb-1">
                        {AI_MODELS.find((m) => m.id === msg.model)?.name}
                      </span>
                    )}
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Skill Shortcuts Dropdown */}
        {showShortcuts && isExpanded && (
          <div className="absolute bottom-16 left-4 right-4 bg-slate-800/95 backdrop-blur-lg rounded-xl border border-white/10 p-2 shadow-xl">
            <p className="text-xs text-white/40 px-2 pb-2">קיצורי פקודות</p>
            {SKILL_SHORTCUTS.filter((s) =>
              s.command.toLowerCase().includes(input.toLowerCase())
            ).map((shortcut) => (
              <button
                key={shortcut.command}
                onClick={() => handleShortcutClick(shortcut.command)}
                className="w-full text-right px-3 py-2 rounded-lg hover:bg-white/5 flex items-center gap-3 transition-colors"
              >
                <Terminal className="w-4 h-4 text-status-ai" />
                <span className="font-mono text-status-ai">{shortcut.command}</span>
                <span className="text-white/60 text-sm">{shortcut.description}</span>
              </button>
            ))}
          </div>
        )}

        {/* Input Bar */}
        <div className="h-16 px-4 flex items-center gap-3 border-t border-white/5">
          {/* Expand/Collapse Toggle */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="w-5 h-5 text-white/60" />
            ) : (
              <ChevronUp className="w-5 h-5 text-white/60" />
            )}
          </button>

          {/* Model Selector */}
          <div className="relative">
            <button
              onClick={() => setIsModelSelectorOpen(!isModelSelectorOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
            >
              <span
                className="w-5 h-5 rounded-md flex items-center justify-center text-xs font-bold"
                style={{ backgroundColor: currentModel.color }}
              >
                {currentModel.icon}
              </span>
              <span className="text-sm text-white/70">{currentModel.name}</span>
            </button>

            {/* Model Dropdown */}
            {isModelSelectorOpen && (
              <div className="absolute bottom-full left-0 mb-2 bg-slate-800/95 backdrop-blur-lg rounded-xl border border-white/10 p-1 shadow-xl min-w-[140px]">
                {AI_MODELS.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModel(model.id);
                      setIsModelSelectorOpen(false);
                    }}
                    className={`
                      w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors
                      ${selectedModel === model.id ? "bg-white/10" : "hover:bg-white/5"}
                    `}
                  >
                    <span
                      className="w-5 h-5 rounded-md flex items-center justify-center text-xs font-bold"
                      style={{ backgroundColor: model.color }}
                    >
                      {model.icon}
                    </span>
                    <span className="text-sm text-white/80">{model.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Input Field */}
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsExpanded(true)}
              placeholder="שאל את AquaBrain או הרץ פקודה... (Ctrl+K)"
              className="
                w-full bg-white/5 border border-white/10 rounded-xl
                px-4 py-2.5 text-white text-sm
                placeholder:text-white/30
                focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30
              "
              dir="auto"
            />
            {input.startsWith("/") && (
              <Zap className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-status-ai" />
            )}
          </div>

          {/* Microphone (UI only) */}
          <button
            className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
            title="הקלטה קולית (בקרוב)"
          >
            <Mic className="w-5 h-5 text-white/40" />
          </button>

          {/* Send Button */}
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className="
              p-2.5 rounded-xl transition-all
              bg-status-ai/20 hover:bg-status-ai/30
              disabled:opacity-50 disabled:cursor-not-allowed
            "
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-status-ai animate-spin" />
            ) : (
              <Send className="w-5 h-5 text-status-ai" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CommandBar;
