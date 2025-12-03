"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Paperclip, Mic, Search, User, MoreVertical, Phone, Bot, Loader2 } from 'lucide-react';
import { sendChatMessage } from '@/services/api';

interface Message {
  id: string;
  sender: 'user' | 'ai' | 'them';
  text: string;
  time: string;
  confidence?: number;
}

interface Chat {
  id: number;
  name: string;
  status: 'online' | 'offline' | 'ai';
  lastMsg: string;
  time: string;
  unread: number;
}

const INITIAL_CHATS: Chat[] = [
  { id: 1, name: 'יועץ אינסטלציה (PLUM)', status: 'online', lastMsg: 'האם אשרת את השינוי בקומה 14?', time: '10:42', unread: 2 },
  { id: 2, name: 'מנהל פרויקט (Roni)', status: 'offline', lastMsg: 'שלחתי את הפרוגרמה המעודכנת.', time: '09:15', unread: 0 },
  { id: 3, name: 'AquaBrain AI Agent', status: 'ai', lastMsg: 'מוכן לעזור עם ניתוח התנגשויות', time: 'עכשיו', unread: 0 },
];

const INITIAL_MESSAGES: Message[] = [
  { id: '1', sender: 'ai', text: 'שלום! אני AquaBrain AI Agent. איך אוכל לעזור לך היום?', time: getTimeString() },
];

function getTimeString(): string {
  return new Date().toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

export function CommunicationHub() {
  const [activeChat, setActiveChat] = useState(3); // Start with AI chat
  const [chats, setChats] = useState<Chat[]>(INITIAL_CHATS);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      sender: 'user',
      text: input.trim(),
      time: getTimeString(),
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Send to backend and get AI response
      const response = await sendChatMessage(input.trim());

      const aiMessage: Message = {
        id: generateId(),
        sender: 'ai',
        text: response.message,
        time: getTimeString(),
        confidence: response.confidence,
      };

      setMessages(prev => [...prev, aiMessage]);

      // Update chat list with last message
      setChats(prev => prev.map(chat =>
        chat.id === 3 ? { ...chat, lastMsg: response.message.substring(0, 40) + '...', time: getTimeString() } : chat
      ));
    } catch (error) {
      const errorMessage: Message = {
        id: generateId(),
        sender: 'ai',
        text: 'מצטער, יש בעיית תקשורת עם השרת. נסה שוב.',
        time: getTimeString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeContact = chats.find(c => c.id === activeChat);

  return (
    <div className="flex h-full gap-6">
      {/* Sidebar - Contact List */}
      <div className="w-1/3 glass-heavy rounded-2xl overflow-hidden flex flex-col">
        <div className="p-4 border-b border-white/10">
          <div className="relative">
            <Search className="absolute right-3 top-2.5 text-white/40 w-4 h-4" />
            <input
              type="text"
              placeholder="חפש אנשי קשר..."
              className="w-full bg-white/5 border border-white/10 rounded-lg py-2 pr-10 pl-4 text-sm text-white focus:outline-none focus:border-[var(--status-ai)]/50 transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => setActiveChat(chat.id)}
              className={`p-3 rounded-xl cursor-pointer transition-all flex items-center gap-3 ${
                activeChat === chat.id ? 'bg-white/10 border border-white/10' : 'hover:bg-white/5 border border-transparent'
              }`}
            >
              <div className="relative">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  chat.status === 'ai' ? 'bg-[var(--status-ai)]/20 text-[var(--status-ai)]' : 'bg-white/10'
                }`}>
                  {chat.status === 'ai' ? <Bot size={20} /> : <User size={18} />}
                </div>
                {chat.status === 'online' && (
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-[var(--status-success)] rounded-full border-2 border-[#030305]"></div>
                )}
                {chat.status === 'ai' && (
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-[var(--status-ai)] rounded-full border-2 border-[#030305] animate-pulse"></div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-baseline mb-1">
                  <span className="font-bold text-sm truncate">{chat.name}</span>
                  <span className="text-xs text-white/40">{chat.time}</span>
                </div>
                <p className="text-xs text-white/60 truncate">{chat.lastMsg}</p>
              </div>

              {chat.unread > 0 && (
                <div className="w-5 h-5 bg-[var(--status-ai)] rounded-full flex items-center justify-center text-[10px] font-bold">
                  {chat.unread}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 glass-heavy rounded-2xl flex flex-col overflow-hidden relative">
        {/* Chat Header */}
        <div className="p-4 border-b border-white/10 flex justify-between items-center bg-white/5 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              activeContact?.status === 'ai' ? 'bg-[var(--status-ai)]/20 text-[var(--status-ai)]' : 'bg-white/10'
            }`}>
              {activeContact?.status === 'ai' ? <Bot size={20} /> : <User size={20} />}
            </div>
            <div>
              <h3 className="font-bold">{activeContact?.name}</h3>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full animate-pulse ${
                  activeContact?.status === 'ai' ? 'bg-[var(--status-ai)]' :
                  activeContact?.status === 'online' ? 'bg-[var(--status-success)]' : 'bg-white/30'
                }`}></span>
                <span className="text-xs text-white/60">
                  {activeContact?.status === 'ai' ? 'AI Engine READY' :
                   activeContact?.status === 'online' ? 'מחובר כעת' : 'לא מחובר'}
                </span>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="p-2 hover:bg-white/10 rounded-lg transition-colors"><Phone size={18} /></button>
            <button className="p-2 hover:bg-white/10 rounded-lg transition-colors"><MoreVertical size={18} /></button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.map((msg) => (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={msg.id}
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[70%] p-3 rounded-2xl ${
                msg.sender === 'user'
                  ? 'bg-[var(--status-ai)]/20 border border-[var(--status-ai)]/30 text-white rounded-bl-none'
                  : 'bg-white/10 border border-white/5 text-white/90 rounded-br-none'
              }`}>
                <p className="text-sm">{msg.text}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-white/40">{msg.time}</span>
                  {msg.confidence && (
                    <span className="text-[10px] text-[var(--status-ai)]">
                      ({Math.round(msg.confidence * 100)}% confidence)
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start"
            >
              <div className="bg-white/10 border border-white/5 rounded-2xl rounded-br-none p-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-[var(--status-ai)]" />
                <span className="text-sm text-white/60">AI מעבד את הבקשה...</span>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white/5 border-t border-white/10">
          <div className="flex gap-2 items-end">
            <button className="p-3 bg-white/5 hover:bg-white/10 rounded-xl text-white/60 transition-all">
              <Paperclip size={20} />
            </button>
            <div className="flex-1 bg-white/5 border border-white/10 rounded-xl flex items-center p-2 focus-within:border-[var(--status-ai)]/50 focus-within:bg-white/10 transition-all">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className="flex-1 bg-transparent border-none focus:outline-none text-sm px-2 h-10 disabled:opacity-50"
                placeholder={isLoading ? "ממתין לתגובה..." : "הקלד הודעה..."}
              />
              <button className="p-2 text-white/40 hover:text-white transition-colors">
                <Mic size={18} />
              </button>
            </div>
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !input.trim()}
              className="p-3 bg-[var(--status-ai)] hover:bg-[var(--status-ai)]/80 rounded-xl text-white glow-purple transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
