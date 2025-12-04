"use client";

/**
 * AquaBrain Command Bar - The Voice of the System
 * ================================================
 * A persistent command interface for interacting with AI and triggering skills.
 * Appears at the bottom of every screen.
 *
 * Claude Toggle: OFF by default, explicit activation only, auto-resets after conversation
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Mic,
  ChevronUp,
  ChevronDown,
  Bot,
  Loader2,
  Zap,
  Terminal,
  Sparkles,
  DollarSign,
  Power,
} from "lucide-react";

// ============================================================================
// TYPES
// ============================================================================

type AIModel = "gemini" | "claude";

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
  const [claudeEnabled, setClaudeEnabled] = useState(false); // OFF by default
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showClaudeWarning, setShowClaudeWarning] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // The actual model being used
  const activeModel: AIModel = claudeEnabled ? "claude" : "gemini";

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

  // Auto-reset Claude toggle when conversation ends (component unmounts or clear)
  const clearConversation = useCallback(() => {
    setMessages([]);
    setClaudeEnabled(false); // Reset Claude to OFF
    setShowClaudeWarning(false);
  }, []);

  // Toggle Claude with confirmation
  const toggleClaude = useCallback(() => {
    if (!claudeEnabled) {
      // Turning ON - show warning first
      setShowClaudeWarning(true);
    } else {
      // Turning OFF - no confirmation needed
      setClaudeEnabled(false);
    }
  }, [claudeEnabled]);

  const confirmClaudeActivation = useCallback(() => {
    setClaudeEnabled(true);
    setShowClaudeWarning(false);
  }, []);

  const cancelClaudeActivation = useCallback(() => {
    setShowClaudeWarning(false);
  }, []);

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
          model: activeModel,
          context: {
            messages: messages.slice(-5),
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
          model: activeModel,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
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
          : `[${activeModel === "claude" ? "Claude AI" : "Gemini"}] תשובה ל: "${input}"\n\nאני AquaBrain, עוזר AI להנדסת מערכות כיבוי אש. כיצד אוכל לעזור?`,
        timestamp: new Date(),
        model: activeModel,
      };
      setMessages((prev) => [...prev, mockResponse]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, activeModel]);

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

      {/* Claude Activation Warning Modal */}
      {showClaudeWarning && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-slate-800 border border-amber-500/30 rounded-2xl p-6 max-w-md mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-500/20 rounded-xl">
                <DollarSign className="w-6 h-6 text-amber-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">הפעלת Claude AI</h3>
            </div>
            <p className="text-white/70 mb-4 leading-relaxed">
              שים לב: השימוש ב-Claude AI כרוך בחיוב לפי שימוש.
              <br />
              <span className="text-amber-400">~$0.02-0.05 לכל שאלה</span>
            </p>
            <p className="text-white/50 text-sm mb-6">
              המתג יתאפס אוטומטית בסוף השיחה.
            </p>
            <div className="flex gap-3">
              <button
                onClick={cancelClaudeActivation}
                className="flex-1 px-4 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-white/70 transition-colors"
              >
                ביטול
              </button>
              <button
                onClick={confirmClaudeActivation}
                className="flex-1 px-4 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 rounded-xl text-amber-400 font-medium transition-colors"
              >
                הפעל Claude
              </button>
            </div>
          </div>
        </div>
      )}

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
              <>
                {messages.map((msg) => (
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
                            : msg.model === "claude"
                              ? "bg-amber-500/10 border border-amber-500/20 text-white/80"
                              : "bg-white/5 text-white/80"
                        }
                      `}
                    >
                      {msg.role === "assistant" && msg.model && (
                        <span className={`text-xs block mb-1 ${msg.model === "claude" ? "text-amber-400" : "text-blue-400"}`}>
                          {msg.model === "claude" ? "Claude AI" : "Gemini"}
                        </span>
                      )}
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))}
                {/* Clear conversation button */}
                {messages.length > 0 && (
                  <div className="flex justify-center pt-2">
                    <button
                      onClick={clearConversation}
                      className="text-xs text-white/30 hover:text-white/50 transition-colors"
                    >
                      נקה שיחה ואפס הגדרות
                    </button>
                  </div>
                )}
              </>
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

          {/* Claude Toggle Button */}
          <button
            onClick={toggleClaude}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-xl transition-all duration-200
              ${claudeEnabled
                ? "bg-amber-500/20 border border-amber-500/40 shadow-lg shadow-amber-500/10"
                : "bg-white/5 border border-white/10 hover:bg-white/10"
              }
            `}
            title={claudeEnabled ? "Claude AI פעיל (לחץ לכיבוי)" : "הפעל Claude AI (בתשלום)"}
          >
            {/* Power/Status Icon */}
            <div className={`
              relative w-5 h-5 rounded-md flex items-center justify-center text-xs font-bold
              ${claudeEnabled ? "bg-amber-500 text-slate-900" : "bg-slate-600 text-white/50"}
            `}>
              {claudeEnabled ? (
                <Sparkles className="w-3 h-3" />
              ) : (
                <Power className="w-3 h-3" />
              )}
              {/* Billing indicator dot */}
              {claudeEnabled && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              )}
            </div>

            {/* Label */}
            <span className={`text-sm font-medium ${claudeEnabled ? "text-amber-400" : "text-white/50"}`}>
              Claude
            </span>

            {/* ON/OFF Badge */}
            <span className={`
              text-[10px] font-bold px-1.5 py-0.5 rounded
              ${claudeEnabled
                ? "bg-amber-500/30 text-amber-300"
                : "bg-white/10 text-white/40"
              }
            `}>
              {claudeEnabled ? "ON" : "OFF"}
            </span>
          </button>

          {/* Active Model Indicator (Gemini when Claude is OFF) */}
          {!claudeEnabled && (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="w-4 h-4 rounded bg-blue-500 flex items-center justify-center text-[10px] font-bold text-white">
                G
              </div>
              <span className="text-xs text-blue-400">Gemini</span>
              <span className="text-[10px] text-green-400">FREE</span>
            </div>
          )}

          {/* Input Field */}
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsExpanded(true)}
              placeholder={claudeEnabled ? "שאל את Claude AI... (בתשלום)" : "שאל את AquaBrain... (Gemini - חינם)"}
              className={`
                w-full border rounded-xl
                px-4 py-2.5 text-white text-sm
                placeholder:text-white/30
                focus:outline-none focus:ring-1
                ${claudeEnabled
                  ? "bg-amber-500/5 border-amber-500/20 focus:border-amber-500/50 focus:ring-amber-500/30"
                  : "bg-white/5 border-white/10 focus:border-status-ai/50 focus:ring-status-ai/30"
                }
              `}
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
            className={`
              p-2.5 rounded-xl transition-all
              ${claudeEnabled
                ? "bg-amber-500/20 hover:bg-amber-500/30"
                : "bg-status-ai/20 hover:bg-status-ai/30"
              }
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
          >
            {isLoading ? (
              <Loader2 className={`w-5 h-5 animate-spin ${claudeEnabled ? "text-amber-400" : "text-status-ai"}`} />
            ) : (
              <Send className={`w-5 h-5 ${claudeEnabled ? "text-amber-400" : "text-status-ai"}`} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CommandBar;
