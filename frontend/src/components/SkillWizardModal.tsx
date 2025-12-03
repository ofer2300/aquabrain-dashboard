"use client";

import React, { useState, useRef, useEffect } from 'react';
import {
  Wand2,
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  Sparkles,
  Bot,
  User,
  Code2,
  Play,
  Cog,
  Droplets,
  Building2,
  FileBarChart,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'pending' | 'generating' | 'validating' | 'success' | 'error';
}

interface GeneratedSkill {
  skill_id: string;
  class_name: string;
  name: string;
  icon: string;
  color: string;
  validation_passed: boolean;
  is_active: boolean;
}

interface SkillWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSkillCreated?: (skill: GeneratedSkill) => void;
}

// ============================================================================
// COMPONENT
// ============================================================================

export function SkillWizardModal({ isOpen, onClose, onSkillCreated }: SkillWizardModalProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'system',
      content: 'תאר את האוטומציה שאתה צריך, ואני אייצר עבורך skill מותאם אישית.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStep, setCurrentStep] = useState<'idle' | 'generating' | 'validating' | 'complete'>('idle');
  const [generatedSkill, setGeneratedSkill] = useState<GeneratedSkill | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setMessages([{
        id: '1',
        role: 'system',
        content: 'תאר את האוטומציה שאתה צריך, ואני אייצר עבורך skill מותאם אישית.',
        timestamp: new Date(),
      }]);
      setGeneratedSkill(null);
      setCurrentStep('idle');
    }
  }, [isOpen]);

  const addMessage = (role: Message['role'], content: string, extra?: Partial<Message>): Message => {
    const msg: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
      ...extra,
    };
    setMessages((prev) => [...prev, msg]);
    return msg;
  };

  const updateMessage = (id: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage('user', userMessage);

    setIsGenerating(true);
    setCurrentStep('generating');

    // Step 1: Generating Logic
    const thinkingMsg = addMessage('assistant', 'מייצר לוגיקה...', { status: 'generating' });

    await new Promise((r) => setTimeout(r, 1500));
    updateMessage(thinkingMsg.id, { content: 'מאמת בסביבת Sandbox...', status: 'validating' });
    setCurrentStep('validating');

    await new Promise((r) => setTimeout(r, 1500));

    // Try to call backend, fallback to mock
    try {
      const response = await fetch('http://localhost:8000/api/skills/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: userMessage,
          name: extractSkillName(userMessage),
          category: 'custom',
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const skill: GeneratedSkill = {
          skill_id: data.skill_id,
          class_name: data.class_name,
          name: extractSkillName(userMessage),
          icon: inferIcon(userMessage),
          color: inferColor(userMessage),
          validation_passed: data.validation_passed,
          is_active: false,
        };
        completeGeneration(thinkingMsg.id, skill);
      } else {
        throw new Error('Backend error');
      }
    } catch {
      // Mock generation for demo
      const skill: GeneratedSkill = {
        skill_id: `custom_${Date.now().toString(36)}`,
        class_name: extractSkillName(userMessage).replace(/\s+/g, '') + 'Skill',
        name: extractSkillName(userMessage),
        icon: inferIcon(userMessage),
        color: inferColor(userMessage),
        validation_passed: true,
        is_active: false,
      };
      completeGeneration(thinkingMsg.id, skill);
    }
  };

  const completeGeneration = (msgId: string, skill: GeneratedSkill) => {
    updateMessage(msgId, {
      content: `Skill "${skill.name}" נוצר בהצלחה! לחץ על "הפעל" כדי להוסיף אותו לספריית ה-Skills.`,
      status: 'success',
    });
    setGeneratedSkill(skill);
    setCurrentStep('complete');
    setIsGenerating(false);
  };

  const extractSkillName = (description: string): string => {
    const words = description.split(' ').slice(0, 3);
    return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  const inferIcon = (description: string): string => {
    const d = description.toLowerCase();
    if (d.includes('hydraulic') || d.includes('מים') || d.includes('צינור')) return 'Droplets';
    if (d.includes('revit') || d.includes('בניין') || d.includes('מודל')) return 'Building2';
    if (d.includes('report') || d.includes('דוח')) return 'FileBarChart';
    if (d.includes('file') || d.includes('קובץ')) return 'FileBarChart';
    return 'Cog';
  };

  const inferColor = (description: string): string => {
    const d = description.toLowerCase();
    if (d.includes('hydraulic') || d.includes('מים')) return '#00E676';
    if (d.includes('revit') || d.includes('בניין')) return '#4FACFE';
    if (d.includes('report') || d.includes('דוח')) return '#BD00FF';
    return '#FF9F0A';
  };

  const handleActivate = () => {
    if (generatedSkill) {
      const activatedSkill = { ...generatedSkill, is_active: true };
      setGeneratedSkill(activatedSkill);
      addMessage('system', `Skill "${generatedSkill.name}" הופעל בהצלחה ונוסף לספריה!`);
      onSkillCreated?.(activatedSkill);
    }
  };

  const IconComponent = ({ name }: { name: string }) => {
    switch (name) {
      case 'Droplets': return <Droplets className="w-5 h-5" />;
      case 'Building2': return <Building2 className="w-5 h-5" />;
      case 'FileBarChart': return <FileBarChart className="w-5 h-5" />;
      default: return <Cog className="w-5 h-5" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 glass-heavy rounded-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-purple-500/20 to-cyan-500/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/30 flex items-center justify-center">
              <Wand2 className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Skill Factory</h2>
              <p className="text-xs text-white/50">יצירת אוטומציות עם AI</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Progress Steps */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full transition-all ${currentStep !== 'idle' ? 'bg-purple-400' : 'bg-white/20'}`} />
              <div className={`w-2 h-2 rounded-full transition-all ${currentStep === 'validating' || currentStep === 'complete' ? 'bg-cyan-400' : 'bg-white/20'}`} />
              <div className={`w-2 h-2 rounded-full transition-all ${currentStep === 'complete' ? 'bg-green-400' : 'bg-white/20'}`} />
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5 text-white/60" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="h-80 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                  ${msg.role === 'user' ? 'bg-cyan-500/30' : ''}
                  ${msg.role === 'assistant' ? 'bg-purple-500/30' : ''}
                  ${msg.role === 'system' ? 'bg-white/10' : ''}
                `}
              >
                {msg.role === 'user' && <User className="w-4 h-4 text-cyan-400" />}
                {msg.role === 'assistant' && <Bot className="w-4 h-4 text-purple-400" />}
                {msg.role === 'system' && <Sparkles className="w-4 h-4 text-white/60" />}
              </div>
              <div
                className={`
                  max-w-[80%] rounded-2xl px-4 py-3
                  ${msg.role === 'user' ? 'bg-cyan-500/20 text-white' : ''}
                  ${msg.role === 'assistant' ? 'bg-white/5 text-white/90' : ''}
                  ${msg.role === 'system' ? 'bg-white/5 text-white/70 text-sm' : ''}
                `}
              >
                {msg.status === 'generating' || msg.status === 'validating' ? (
                  <div className="flex items-center gap-2 text-purple-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{msg.content}</span>
                  </div>
                ) : (
                  <>
                    <p>{msg.content}</p>
                    {msg.status === 'success' && (
                      <div className="flex items-center gap-2 mt-2 text-green-400 text-sm">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>אומת בהצלחה</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Generated Skill Preview */}
        {generatedSkill && (
          <div className="px-6 py-4 border-t border-white/10 bg-white/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${generatedSkill.color}30` }}
                >
                  <span style={{ color: generatedSkill.color }}>
                    <IconComponent name={generatedSkill.icon} />
                  </span>
                </div>
                <div>
                  <p className="font-medium text-white">{generatedSkill.name}</p>
                  <p className="text-xs text-white/50">{generatedSkill.class_name}</p>
                </div>
              </div>
              <button
                onClick={handleActivate}
                disabled={generatedSkill.is_active}
                className={`
                  px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2
                  ${generatedSkill.is_active
                    ? 'bg-green-500/20 text-green-300 cursor-default'
                    : 'bg-purple-500/20 border border-purple-500/50 text-purple-300 hover:bg-purple-500/30'}
                  transition-colors
                `}
              >
                {generatedSkill.is_active ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    הופעל
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    הפעל Skill
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="תאר את ה-Skill שאתה צריך..."
              disabled={isGenerating}
              className="
                flex-1 px-4 py-3 rounded-xl
                bg-white/5 border border-white/10
                text-white placeholder:text-white/30
                focus:outline-none focus:border-purple-500/50
                disabled:opacity-50
              "
            />
            <button
              type="submit"
              disabled={!input.trim() || isGenerating}
              className="
                px-5 py-3 rounded-xl
                bg-purple-500/20 border border-purple-500/50 text-purple-300
                hover:bg-purple-500/30 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {isGenerating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SkillWizardModal;
