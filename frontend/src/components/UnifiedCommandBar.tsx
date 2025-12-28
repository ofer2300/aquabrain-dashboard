'use client';

/**
 * UnifiedCommandBar Component v4.0 - Enhanced Operations Center
 * ==============================================================
 * Full transparency in the process - like WhatsApp status indicators
 *
 * Architecture:
 * - Gemini = Brain (Reasoning, Planning, UI Interface)
 * - Claude Code CLI = Hands (Execution, Code, Automation)
 *
 * V4.0 Features:
 * - Live Operations Log (חמ"ל) - NARROWER (50% width, right side)
 * - Repositioned chat input (center, more prominent)
 * - Screenshot capture capability
 * - Document upload for agent consultation
 * - Message status tracking: pending -> processing -> success/error
 * - Gemini Flash (Free) / Gemini Pro+ (Premium) toggle
 * - Claude Agent activation for real code execution
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, Paperclip, Terminal, Zap, Loader2, CheckCircle2, AlertCircle, Clock,
  Camera, FileText, X, ChevronRight, Upload, Eye, Trash2, Minimize2, Maximize2
} from 'lucide-react';
import { useLocalBridge } from '@/hooks/useLocalBridge';

interface LogMessage {
  id: string;
  text: string;
  sender: 'user' | 'agent' | 'system';
  status: 'pending' | 'processing' | 'success' | 'error';
  timestamp: string;
  attachments?: AttachedFile[];
}

interface AttachedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  preview?: string; // base64 for images
  content?: string; // base64 for documents
}

export const UnifiedCommandBar: React.FC = () => {
  const [input, setInput] = useState('');
  const [isPremium, setIsPremium] = useState(false);
  const [useClaudeAgent, setUseClaudeAgent] = useState(false);
  const [history, setHistory] = useState<LogMessage[]>([]);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [isLogsExpanded, setIsLogsExpanded] = useState(true);
  const [isLogsMinimized, setIsLogsMinimized] = useState(false);
  const [isBarCollapsed, setIsBarCollapsed] = useState(false);

  const { runCommand, logs, isConnected, status: bridgeStatus } = useLocalBridge();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const documentInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, logs]);

  // Listen to logs from server and update status in real-time
  useEffect(() => {
    if (logs.length > 0) {
      const latestLog = logs[logs.length - 1];

      setHistory(prev => {
        const newHistory = [...prev];
        const lastAgentMsgIndex = newHistory.findLastIndex(msg =>
          (msg.sender === 'agent' || msg.sender === 'system') &&
          (msg.status === 'pending' || msg.status === 'processing')
        );

        if (lastAgentMsgIndex !== -1) {
          newHistory[lastAgentMsgIndex].text = latestLog.content;

          if (latestLog.type === 'success') {
            newHistory[lastAgentMsgIndex].status = 'success';
          } else if (latestLog.type === 'error') {
            newHistory[lastAgentMsgIndex].status = 'error';
          } else {
            newHistory[lastAgentMsgIndex].status = 'processing';
          }
        } else {
          newHistory.push({
            id: Date.now().toString(),
            text: latestLog.content,
            sender: 'system',
            status: latestLog.type === 'error' ? 'error' : 'success',
            timestamp: new Date().toLocaleTimeString('he-IL')
          });
        }
        return [...newHistory];
      });
    }
  }, [logs]);

  // Update status when bridge completes
  useEffect(() => {
    if (bridgeStatus === 'idle' && history.length > 0) {
      setHistory(prev => {
        const newHistory = [...prev];
        const lastAgentMsg = newHistory.filter(m =>
          (m.sender === 'agent' || m.sender === 'system') && m.status === 'processing'
        ).pop();
        if (lastAgentMsg) {
          lastAgentMsg.status = 'success';
        }
        return [...newHistory];
      });
    }
  }, [bridgeStatus]);

  // Screenshot capture
  const captureScreenshot = useCallback(async () => {
    try {
      // Request screen capture
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { mediaSource: 'screen' } as any
      });

      const video = document.createElement('video');
      video.srcObject = stream;
      await video.play();

      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx?.drawImage(video, 0, 0);

      // Stop the stream
      stream.getTracks().forEach(track => track.stop());

      // Get base64
      const dataUrl = canvas.toDataURL('image/png');
      const base64 = dataUrl.split(',')[1];

      const screenshotFile: AttachedFile = {
        id: Date.now().toString(),
        name: `screenshot_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`,
        type: 'image/png',
        size: Math.round(base64.length * 0.75),
        preview: dataUrl,
        content: base64
      };

      setAttachedFiles(prev => [...prev, screenshotFile]);
    } catch (error) {
      console.error('Screenshot capture failed:', error);
    }
  }, []);

  // Handle file uploads (documents for consultation)
  const handleDocumentUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        const preview = file.type.startsWith('image/') ? reader.result as string : undefined;

        const attachedFile: AttachedFile = {
          id: Date.now().toString() + Math.random(),
          name: file.name,
          type: file.type,
          size: file.size,
          preview,
          content: base64
        };

        setAttachedFiles(prev => [...prev, attachedFile]);
      };
      reader.readAsDataURL(file);
    });

    // Reset input
    e.target.value = '';
  }, []);

  const removeAttachment = (id: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== id));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleSend = async () => {
    if (!input.trim() && attachedFiles.length === 0) return;

    // 1. Add user message to log immediately (transparency)
    const userMsg: LogMessage = {
      id: Date.now().toString(),
      text: input || (attachedFiles.length > 0 ? `[${attachedFiles.length} קבצים מצורפים]` : ''),
      sender: 'user',
      status: 'success',
      timestamp: new Date().toLocaleTimeString('he-IL'),
      attachments: attachedFiles.length > 0 ? [...attachedFiles] : undefined
    };

    // 2. Add "waiting" message from agent
    const agentMsg: LogMessage = {
      id: (Date.now() + 1).toString(),
      text: useClaudeAgent ? "מעביר משימה ל-Claude Agent..." : "מעבד בקשה עם Gemini...",
      sender: 'agent',
      status: 'pending',
      timestamp: new Date().toLocaleTimeString('he-IL')
    };

    setHistory(prev => [...prev, userMsg, agentMsg]);
    const currentInput = input;
    const currentAttachments = [...attachedFiles];
    setInput('');
    setAttachedFiles([]);

    // 3. Update to processing status
    setTimeout(() => {
      setHistory(prev => prev.map(msg =>
        msg.id === agentMsg.id ? { ...msg, status: 'processing' as const } : msg
      ));
    }, 300);

    // 4. Send to server
    try {
      if (useClaudeAgent) {
        // Build prompt with attachments info
        let fullPrompt = currentInput;
        if (currentAttachments.length > 0) {
          fullPrompt += '\n\n[קבצים מצורפים לייעוץ:]\n';
          currentAttachments.forEach(f => {
            fullPrompt += `- ${f.name} (${f.type}, ${formatFileSize(f.size)})\n`;
          });
        }
        runCommand(fullPrompt, 'claude_agent');
      } else {
        // Gemini API call with attachments
        const response = await fetch('http://localhost:8000/api/chat/interact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: currentInput,
            model: isPremium ? 'gemini-pro' : 'gemini-2.5-flash',
            session_id: 'unified-command-bar',
            attachments: currentAttachments.map(f => ({
              name: f.name,
              type: f.type,
              content: f.content
            }))
          }),
        });

        if (!response.ok) {
          throw new Error(`שגיאת API: ${response.statusText}`);
        }

        const data = await response.json();
        const responseText = data.response || data.message || 'לא התקבלה תשובה';

        setHistory(prev => prev.map(msg =>
          msg.id === agentMsg.id
            ? { ...msg, text: responseText, status: 'success' as const }
            : msg
        ));
      }
    } catch (error: any) {
      setHistory(prev => prev.map(msg =>
        msg.id === agentMsg.id
          ? { ...msg, text: `שגיאה: ${error.message}`, status: 'error' as const }
          : msg
      ));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Status icon component
  const StatusIcon = ({ status }: { status: LogMessage['status'] }) => {
    switch (status) {
      case 'pending':
        return <Clock size={10} className="text-slate-500 animate-pulse" />;
      case 'processing':
        return <Loader2 size={10} className="animate-spin text-purple-400" />;
      case 'success':
        return <CheckCircle2 size={10} className="text-green-500" />;
      case 'error':
        return <AlertCircle size={10} className="text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: LogMessage['status']): string => {
    switch (status) {
      case 'pending': return 'ממתין...';
      case 'processing': return 'מעבד...';
      case 'success': return 'הושלם';
      case 'error': return 'שגיאה';
      default: return '';
    }
  };

  // Collapsed view - small floating button
  if (isBarCollapsed) {
    return (
      <div className="fixed bottom-4 left-4 z-50" dir="rtl">
        <button
          onClick={() => setIsBarCollapsed(false)}
          className="pointer-events-auto bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white rounded-full p-4 shadow-2xl flex items-center gap-2 transition-all hover:scale-105"
        >
          <Terminal size={20} />
          <span className="text-sm font-medium">AI</span>
          {history.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {history.length}
            </span>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 pointer-events-none" dir="rtl">
      <div className="flex items-end gap-4 p-4">

        {/* ============================================ */}
        {/* COMMAND INPUT BAR (CENTER - MAIN FOCUS)     */}
        {/* ============================================ */}
        <div className="flex-1 max-w-2xl mx-auto pointer-events-auto">
          <div className="bg-slate-950/95 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">

            {/* Attached Files Preview */}
            {attachedFiles.length > 0 && (
              <div className="px-4 py-2 border-b border-slate-800 flex flex-wrap gap-2">
                {attachedFiles.map(file => (
                  <div
                    key={file.id}
                    className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-1.5 text-xs"
                  >
                    {file.preview ? (
                      <img src={file.preview} alt={file.name} className="w-6 h-6 object-cover rounded" />
                    ) : (
                      <FileText size={14} className="text-slate-400" />
                    )}
                    <span className="max-w-[100px] truncate">{file.name}</span>
                    <span className="text-slate-500">{formatFileSize(file.size)}</span>
                    <button
                      onClick={() => removeAttachment(file.id)}
                      className="p-0.5 hover:bg-white/10 rounded"
                    >
                      <X size={12} className="text-slate-400" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Control buttons */}
            <div className="flex justify-between items-center px-4 py-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPremium(!isPremium)}
                  className={`px-3 py-1 rounded-full text-xs font-bold flex gap-1 transition ${
                    isPremium
                      ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {isPremium && <Zap size={12} fill="currentColor" />}
                  {isPremium ? 'Gemini Pro+' : 'Gemini Flash'}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setUseClaudeAgent(!useClaudeAgent)}
                  className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold border transition-all ${
                    useClaudeAgent
                      ? 'bg-purple-900/60 border-purple-500 text-purple-200 shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                      : 'bg-slate-900 border-slate-700 text-slate-500 hover:border-slate-600'
                  }`}
                >
                  <Terminal size={14} />
                  {useClaudeAgent ? 'Claude Agent: ON' : 'Claude Agent: OFF'}
                </button>

                {/* Minimize entire bar button */}
                <button
                  onClick={() => setIsBarCollapsed(true)}
                  title="מזער את חלון הצ'אט"
                  className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-700 rounded-lg transition"
                >
                  <Minimize2 size={14} />
                </button>
              </div>
            </div>

            {/* Input row */}
            <div className={`flex items-end gap-2 p-3 transition-all ${
              useClaudeAgent ? 'bg-purple-950/30' : ''
            }`}>
              {/* Attachment buttons */}
              <div className="flex flex-col gap-1">
                <button
                  onClick={captureScreenshot}
                  title="צילום מסך"
                  className="p-2 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded-lg transition"
                >
                  <Camera size={18} />
                </button>
                <button
                  onClick={() => documentInputRef.current?.click()}
                  title="העלה מסמך לייעוץ"
                  className="p-2 text-slate-400 hover:text-purple-400 hover:bg-slate-800 rounded-lg transition"
                >
                  <Upload size={18} />
                </button>
                <input
                  type="file"
                  ref={documentInputRef}
                  className="hidden"
                  multiple
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt"
                  onChange={handleDocumentUpload}
                />
              </div>

              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={useClaudeAgent
                  ? "תן פקודה ל-Claude (למשל: צור סקריפט Python לסריקת קבצים)..."
                  : "שוחח עם Gemini..."
                }
                className="flex-1 bg-transparent text-white placeholder-slate-500 text-sm p-3 focus:outline-none resize-none h-12 max-h-32"
              />

              <button
                onClick={handleSend}
                disabled={!input.trim() && attachedFiles.length === 0}
                className={`p-3 rounded-xl transition-all ${
                  (input.trim() || attachedFiles.length > 0)
                    ? (useClaudeAgent
                        ? 'bg-purple-600 hover:bg-purple-500 text-white'
                        : 'bg-blue-600 hover:bg-blue-500 text-white'
                      )
                    : 'bg-slate-800 text-slate-600 cursor-not-allowed'
                }`}
              >
                {useClaudeAgent ? <Terminal size={20} /> : <Send size={20} />}
              </button>
            </div>

            {/* Hint */}
            <div className="text-center text-[10px] text-slate-600 py-1 border-t border-slate-800">
              <Camera size={10} className="inline mr-1" /> צילום מסך
              <span className="mx-2">|</span>
              <Upload size={10} className="inline mr-1" /> העלה מסמך
              <span className="mx-2">|</span>
              <kbd className="px-1 bg-slate-800 rounded">Enter</kbd> לשליחה
            </div>
          </div>
        </div>

        {/* ============================================ */}
        {/* LIVE OPERATIONS LOG (RIGHT SIDE - NARROW)   */}
        {/* ============================================ */}
        {history.length > 0 && !isLogsMinimized && (
          <div className="w-80 pointer-events-auto">
            <div className="bg-slate-950/90 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[350px]">

              {/* Header */}
              <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex justify-between items-center">
                <span className="text-xs text-slate-400 font-mono flex items-center gap-2">
                  <Terminal size={12} />
                  Live Operations
                  {bridgeStatus === 'running' && (
                    <Loader2 size={10} className="animate-spin text-purple-400" />
                  )}
                </span>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                  <button
                    onClick={() => setHistory([])}
                    className="text-xs text-slate-500 hover:text-white transition"
                  >
                    נקה
                  </button>
                  <button
                    onClick={() => setIsLogsMinimized(true)}
                    className="p-1 hover:bg-white/10 rounded"
                  >
                    <Minimize2 size={12} className="text-slate-400" />
                  </button>
                </div>
              </div>

              {/* Operation Logs */}
              <div className="flex-1 overflow-y-auto p-2 space-y-2 text-xs font-mono">
                {history.slice(-15).map((msg) => (
                  <div
                    key={msg.id}
                    className={`p-2 rounded-lg ${
                      msg.sender === 'user'
                        ? 'bg-blue-900/30 border-r-2 border-blue-500'
                        : msg.status === 'error'
                          ? 'bg-red-900/30 border-r-2 border-red-500'
                          : 'bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <StatusIcon status={msg.status} />
                      <div className="flex-1 min-w-0">
                        <p className={`truncate ${
                          msg.status === 'error' ? 'text-red-400' :
                          msg.sender === 'user' ? 'text-blue-300' : 'text-green-400'
                        }`}>
                          {msg.text.length > 60 ? msg.text.slice(0, 60) + '...' : msg.text}
                        </p>
                        {msg.attachments && msg.attachments.length > 0 && (
                          <div className="flex gap-1 mt-1">
                            {msg.attachments.map(a => (
                              <span key={a.id} className="text-[10px] text-slate-500 bg-slate-700 px-1 rounded">
                                {a.name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-600 whitespace-nowrap">{msg.timestamp}</span>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </div>
        )}

        {/* Minimized Logs Button */}
        {isLogsMinimized && history.length > 0 && (
          <button
            onClick={() => setIsLogsMinimized(false)}
            className="pointer-events-auto bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 flex items-center gap-2 text-xs hover:bg-slate-800 transition"
          >
            <Terminal size={14} />
            <span className="text-slate-400">לוגים ({history.length})</span>
            <Maximize2 size={12} />
          </button>
        )}
      </div>
    </div>
  );
};

export default UnifiedCommandBar;
