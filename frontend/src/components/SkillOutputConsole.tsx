"use client";

/**
 * SkillOutputConsole Component
 * =============================
 * Displays Python skill execution results with JSON formatting and streaming output.
 * Part of the Neural Link architecture connecting Next.js to Python engineering core.
 */

import { useState, useEffect, useRef } from 'react';
import { Terminal, CheckCircle2, XCircle, Loader2, Code2, Table, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import type { BridgeLog, SkillResult } from '@/hooks/useLocalBridge';

interface SkillOutputConsoleProps {
  logs: BridgeLog[];
  skillResults: SkillResult[];
  currentSkill: string | null;
  status: 'idle' | 'connecting' | 'running' | 'error';
  onClear?: () => void;
}

type ViewMode = 'stream' | 'json' | 'table';

export function SkillOutputConsole({
  logs,
  skillResults,
  currentSkill,
  status,
  onClear,
}: SkillOutputConsoleProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('stream');
  const [isExpanded, setIsExpanded] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current && status === 'running') {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, status]);

  // Filter skill-related logs
  const skillLogs = logs.filter(log =>
    log.type === 'skill' ||
    log.skill ||
    log.content.includes('Skill')
  );

  // Get latest result
  const latestResult = skillResults[skillResults.length - 1];

  return (
    <div className="glass-heavy rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
            status === 'running' ? 'bg-purple-500/30' :
            status === 'error' ? 'bg-red-500/30' :
            'bg-emerald-500/30'
          }`}>
            {status === 'running' ? (
              <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
            ) : status === 'error' ? (
              <XCircle className="w-5 h-5 text-red-400" />
            ) : (
              <Terminal className="w-5 h-5 text-emerald-400" />
            )}
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Python Skill Output</h3>
            <p className="text-xs text-white/50">
              {currentSkill ? `Running: ${currentSkill}` :
               latestResult ? `Last: ${latestResult.skill}` :
               'No skill executed yet'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex bg-white/5 rounded-lg p-1">
            <button
              onClick={() => setViewMode('stream')}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                viewMode === 'stream'
                  ? 'bg-purple-500/30 text-purple-300'
                  : 'text-white/50 hover:text-white'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('json')}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                viewMode === 'json'
                  ? 'bg-purple-500/30 text-purple-300'
                  : 'text-white/50 hover:text-white'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                viewMode === 'table'
                  ? 'bg-purple-500/30 text-purple-300'
                  : 'text-white/50 hover:text-white'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Clear Button */}
          {onClear && (
            <button
              onClick={onClear}
              className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-all"
              title="Clear output"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          {/* Expand/Collapse */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-all"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div
          ref={scrollRef}
          className="p-4 max-h-[400px] overflow-y-auto font-mono text-sm"
        >
          {viewMode === 'stream' && (
            <StreamView logs={skillLogs} status={status} />
          )}
          {viewMode === 'json' && (
            <JsonView result={latestResult} />
          )}
          {viewMode === 'table' && (
            <TableView results={skillResults} />
          )}
        </div>
      )}

      {/* Status Bar */}
      {latestResult && (
        <div className={`px-4 py-2 border-t border-white/10 flex items-center justify-between text-xs ${
          latestResult.success ? 'bg-emerald-500/10' : 'bg-red-500/10'
        }`}>
          <div className="flex items-center gap-2">
            {latestResult.success ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-red-400" />
            )}
            <span className={latestResult.success ? 'text-emerald-300' : 'text-red-300'}>
              Exit code: {latestResult.exitCode}
            </span>
          </div>
          <span className="text-white/40">
            {new Date(latestResult.timestamp).toLocaleTimeString()}
          </span>
        </div>
      )}
    </div>
  );
}

// Stream View - Real-time output
function StreamView({ logs, status }: { logs: BridgeLog[]; status: string }) {
  if (logs.length === 0) {
    return (
      <div className="text-center text-white/30 py-8">
        <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No output yet. Execute a skill to see results.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {logs.map((log, index) => (
        <div
          key={log.id || index}
          className={`py-1 px-2 rounded ${
            log.type === 'error' ? 'bg-red-500/10 text-red-300' :
            log.type === 'success' ? 'bg-emerald-500/10 text-emerald-300' :
            log.type === 'skill' ? 'text-cyan-300' :
            'text-white/70'
          }`}
        >
          <span className="text-white/30 mr-2">
            {log.timestamp.toLocaleTimeString()}
          </span>
          <span className="whitespace-pre-wrap">{log.content}</span>
        </div>
      ))}
      {status === 'running' && (
        <div className="flex items-center gap-2 text-purple-300 py-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Processing...</span>
        </div>
      )}
    </div>
  );
}

// JSON View - Formatted result
function JsonView({ result }: { result?: SkillResult }) {
  if (!result) {
    return (
      <div className="text-center text-white/30 py-8">
        <Code2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No result to display. Execute a skill first.</p>
      </div>
    );
  }

  const jsonData = typeof result.result === 'object'
    ? result.result
    : { output: result.result };

  return (
    <pre className="text-cyan-300 whitespace-pre-wrap overflow-x-auto">
      {JSON.stringify(jsonData, null, 2)}
    </pre>
  );
}

// Table View - Results history
function TableView({ results }: { results: SkillResult[] }) {
  if (results.length === 0) {
    return (
      <div className="text-center text-white/30 py-8">
        <Table className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No execution history yet.</p>
      </div>
    );
  }

  return (
    <table className="w-full text-left">
      <thead>
        <tr className="text-white/50 text-xs border-b border-white/10">
          <th className="py-2 px-2">Skill</th>
          <th className="py-2 px-2">Status</th>
          <th className="py-2 px-2">Exit</th>
          <th className="py-2 px-2">Time</th>
        </tr>
      </thead>
      <tbody>
        {results.slice().reverse().map((result, index) => (
          <tr
            key={result.processId || index}
            className="border-b border-white/5 hover:bg-white/5"
          >
            <td className="py-2 px-2 text-cyan-300">{result.skill}</td>
            <td className="py-2 px-2">
              {result.success ? (
                <span className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> OK
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-400">
                  <XCircle className="w-3.5 h-3.5" /> Fail
                </span>
              )}
            </td>
            <td className="py-2 px-2 text-white/60">{result.exitCode}</td>
            <td className="py-2 px-2 text-white/40">
              {new Date(result.timestamp).toLocaleTimeString()}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default SkillOutputConsole;
