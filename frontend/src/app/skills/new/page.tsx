"use client";

import React, { useState, useRef, useEffect } from 'react';
import {
  Wand2,
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Code2,
  Play,
  Save,
  ArrowLeft,
  Sparkles,
  Bot,
  User,
  Copy,
  Check,
} from 'lucide-react';
import Link from 'next/link';

// ============================================================================
// TYPES
// ============================================================================

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  code?: string;
  skillId?: string;
  status?: 'pending' | 'generating' | 'validating' | 'success' | 'error';
}

interface GeneratedSkill {
  skill_id: string;
  class_name: string;
  code: string;
  validation_passed: boolean;
  validation_errors: string[];
  is_active: boolean;
}

// ============================================================================
// SKILL WIZARD PAGE
// ============================================================================

export default function SkillWizardPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'system',
      content: 'Welcome to the Skill Factory! Describe the automation you need, and I will generate a custom skill for you.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedSkill, setGeneratedSkill] = useState<GeneratedSkill | null>(null);
  const [skillName, setSkillName] = useState('');
  const [copied, setCopied] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const addMessage = (role: Message['role'], content: string, extra?: Partial<Message>) => {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage('user', userMessage);

    // If no skill name yet, extract from description
    if (!skillName) {
      const words = userMessage.split(' ').slice(0, 3);
      setSkillName(words.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '));
    }

    setIsGenerating(true);

    // Add assistant "thinking" message
    const thinkingMsg = addMessage('assistant', 'Analyzing your request...', { status: 'generating' });

    try {
      // Call backend to generate skill
      const response = await fetch('http://localhost:8000/api/skills/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: userMessage,
          name: skillName || 'Custom Skill',
          category: 'custom',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate skill');
      }

      const data = await response.json();

      // Update thinking message with result
      setMessages((prev) =>
        prev.map((m) =>
          m.id === thinkingMsg.id
            ? {
                ...m,
                content: data.validation_passed
                  ? `I've generated a skill based on your description. The code has been validated and is ready for deployment.`
                  : `I've generated a skill, but there were some validation issues:\n${data.validation_errors.join('\n')}`,
                code: data.code,
                skillId: data.skill_id,
                status: data.validation_passed ? 'success' : 'error',
              }
            : m
        )
      );

      setGeneratedSkill(data);
    } catch (error) {
      // Update thinking message with error
      setMessages((prev) =>
        prev.map((m) =>
          m.id === thinkingMsg.id
            ? {
                ...m,
                content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. The backend may not be running. Here's what I would generate:`,
                status: 'error',
              }
            : m
        )
      );

      // Generate mock skill locally for demo
      const mockCode = generateMockSkillCode(userMessage, skillName || 'CustomSkill');
      setGeneratedSkill({
        skill_id: `demo_${Date.now()}`,
        class_name: 'CustomSkill',
        code: mockCode,
        validation_passed: true,
        validation_errors: [],
        is_active: false,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const generateMockSkillCode = (description: string, name: string): string => {
    return `"""
Auto-generated AquaBrain Skill
Description: ${description}
"""

from typing import Dict, Any
from skills.base import (
    AquaSkill, SkillMetadata, InputSchema, InputField,
    FieldType, SkillCategory, ExecutionResult, ExecutionStatus,
    register_skill
)


@register_skill
class ${name.replace(/\s+/g, '')}Skill(AquaSkill):
    """${description}"""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="custom_${Date.now().toString(36)}",
            name="${name}",
            description="${description}",
            category=SkillCategory.CUSTOM,
            icon="Wand2",
            color="#BD00FF",
            version="1.0.0",
            author="Skill Factory",
            tags=["custom", "generated"],
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="input_data",
                label="Input Data",
                type=FieldType.TEXTAREA,
                required=True,
                placeholder="Enter your data here..."
            ),
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        try:
            input_data = inputs.get('input_data', '')

            # TODO: Implement your logic here
            result = {
                'processed': True,
                'input_length': len(input_data),
                'message': 'Skill executed successfully'
            }

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message="Execution completed",
                output=result,
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                error=str(e),
                message="Execution failed",
            )
`;
  };

  const handleDeploy = async () => {
    if (!generatedSkill) return;

    try {
      const response = await fetch('http://localhost:8000/api/skills/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: generatedSkill.skill_id }),
      });

      if (response.ok) {
        addMessage('system', `Skill "${skillName}" has been deployed successfully! You can now use it from the Skills Library.`);
        setGeneratedSkill({ ...generatedSkill, is_active: true });
      }
    } catch (error) {
      addMessage('system', `Skill deployed locally (demo mode). In production, this would register with the backend.`);
      setGeneratedSkill({ ...generatedSkill, is_active: true });
    }
  };

  const copyCode = () => {
    if (generatedSkill?.code) {
      navigator.clipboard.writeText(generatedSkill.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-surface p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-white/60" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/30 to-cyan-500/30 flex items-center justify-center">
                <Wand2 className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Skill Factory</h1>
                <p className="text-sm text-white/50">Create custom automations with AI</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-500/20 border border-purple-500/30">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-purple-300">AI Powered</span>
          </div>
        </div>

        {/* Chat Area */}
        <div className="glass-heavy rounded-2xl overflow-hidden flex flex-col" style={{ height: '60vh' }}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
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
                  {msg.status === 'generating' && (
                    <div className="flex items-center gap-2 text-purple-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{msg.content}</span>
                    </div>
                  )}
                  {msg.status !== 'generating' && (
                    <>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.status === 'success' && (
                        <div className="flex items-center gap-2 mt-2 text-green-400 text-sm">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Validation passed</span>
                        </div>
                      )}
                      {msg.status === 'error' && !msg.content.includes('error') && (
                        <div className="flex items-center gap-2 mt-2 text-red-400 text-sm">
                          <AlertCircle className="w-4 h-4" />
                          <span>Validation failed</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Describe the skill you want to create..."
                disabled={isGenerating}
                className="
                  flex-1 px-4 py-3 rounded-xl
                  bg-white/5 border border-white/10
                  text-white placeholder:text-white/30
                  focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30
                  disabled:opacity-50
                "
              />
              <button
                type="submit"
                disabled={!input.trim() || isGenerating}
                className="
                  px-6 py-3 rounded-xl font-medium
                  bg-purple-500/20 border border-purple-500/50 text-purple-300
                  hover:bg-purple-500/30 transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed
                  flex items-center gap-2
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

        {/* Generated Code Panel */}
        {generatedSkill && (
          <div className="glass-heavy rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Code2 className="w-5 h-5 text-purple-400" />
                <span className="font-medium text-white">Generated Skill Code</span>
                <span className="px-2 py-0.5 rounded-full text-xs bg-white/10 text-white/60">
                  {generatedSkill.class_name}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={copyCode}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors text-white/60 hover:text-white"
                >
                  {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="p-4 max-h-64 overflow-auto">
              <pre className="text-sm text-white/70 font-mono whitespace-pre-wrap">
                {generatedSkill.code}
              </pre>
            </div>
            <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-4">
                {generatedSkill.validation_passed ? (
                  <span className="flex items-center gap-2 text-green-400 text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    Valid Python
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-red-400 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    {generatedSkill.validation_errors.length} errors
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleDeploy}
                  disabled={!generatedSkill.validation_passed || generatedSkill.is_active}
                  className="
                    px-4 py-2 rounded-lg font-medium text-sm
                    bg-green-500/20 border border-green-500/50 text-green-300
                    hover:bg-green-500/30 transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    flex items-center gap-2
                  "
                >
                  {generatedSkill.is_active ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      Deployed
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Deploy Skill
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tips */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-white/80 mb-2">Tips for better results:</h3>
          <ul className="text-sm text-white/50 space-y-1">
            <li>Be specific about inputs and outputs</li>
            <li>Mention file types if working with files (PDF, DWG, CSV)</li>
            <li>Describe the transformation or calculation needed</li>
            <li>Include any validation rules or constraints</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
