'use client';

/**
 * AutoPilotTerminal Component
 * ===========================
 * Full-featured terminal interface with glassmorphism design
 * Connects to Local Bridge for real-time command execution
 *
 * Features:
 * - Real-time streaming output
 * - PowerShell & Bash execution
 * - pyRevit integration
 * - Traffic Light status
 * - Quick actions for common tasks
 */

import React, { useState, useEffect, useRef } from 'react';
import { useLocalBridge, BridgeLog } from '@/hooks/useLocalBridge';

// Quick action presets
const QUICK_ACTIONS = {
  systemDiagnostics: {
    label: 'System Diagnostics',
    icon: '🔍',
    command: 'Get-ComputerInfo | Select-Object WindowsProductName, OsHardwareAbstractionLayer, CsProcessors, CsTotalPhysicalMemory',
    type: 'powershell' as const,
  },
  topProcesses: {
    label: 'Top Processes',
    icon: '📊',
    command: 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name, CPU, WorkingSet64',
    type: 'powershell' as const,
  },
  pyRevitEnv: {
    label: 'pyRevit Environment',
    icon: '🔧',
    command: 'pyrevit env',
    type: 'powershell' as const,
  },
  pyRevitRoutes: {
    label: 'pyRevit Routes',
    icon: '🌐',
    command: 'pyrevit configs routes',
    type: 'powershell' as const,
  },
  revitProcesses: {
    label: 'Revit Instances',
    icon: '🏗️',
    command: 'Get-Process Revit* -ErrorAction SilentlyContinue | Format-Table Name, Id, StartTime',
    type: 'powershell' as const,
  },
  autocadProcesses: {
    label: 'AutoCAD Instances',
    icon: '📐',
    command: 'Get-Process acad* -ErrorAction SilentlyContinue | Format-Table Name, Id, StartTime',
    type: 'powershell' as const,
  },
  networkStatus: {
    label: 'Network Status',
    icon: '🌍',
    command: 'Get-NetAdapter | Where-Object Status -eq "Up" | Select-Object Name, InterfaceDescription, LinkSpeed',
    type: 'powershell' as const,
  },
  diskSpace: {
    label: 'Disk Space',
    icon: '💾',
    command: 'Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{n="Used(GB)";e={[math]::Round($_.Used/1GB,2)}}, @{n="Free(GB)";e={[math]::Round($_.Free/1GB,2)}}',
    type: 'powershell' as const,
  },
};

// Glassmorphism styles
const glassStyle = {
  background: 'rgba(15, 23, 42, 0.8)',
  backdropFilter: 'blur(12px)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
};

interface AutoPilotTerminalProps {
  className?: string;
}

export const AutoPilotTerminal: React.FC<AutoPilotTerminalProps> = ({ className = '' }) => {
  const {
    isConnected,
    status,
    logs,
    systemInfo,
    capabilities,
    runCommand,
    runPyRevit,
    clearLogs,
    getSystemInfo,
    reconnect,
    currentProcessId,
    killProcess,
  } = useLocalBridge();

  const [commandInput, setCommandInput] = useState('');
  const [shellType, setShellType] = useState<'powershell' | 'bash'>('powershell');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Focus input on click
  const handleTerminalClick = () => {
    inputRef.current?.focus();
  };

  // Execute command
  const handleExecute = () => {
    if (!commandInput.trim()) return;

    // Add to history
    setCommandHistory(prev => [...prev, commandInput]);
    setHistoryIndex(-1);

    // Execute
    runCommand(commandInput, shellType);
    setCommandInput('');
  };

  // Handle key events
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleExecute();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIndex);
        setCommandInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommandInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      } else {
        setHistoryIndex(-1);
        setCommandInput('');
      }
    } else if (e.key === 'c' && e.ctrlKey && currentProcessId) {
      e.preventDefault();
      killProcess(currentProcessId);
    }
  };

  // Run quick action
  const handleQuickAction = (action: typeof QUICK_ACTIONS[keyof typeof QUICK_ACTIONS]) => {
    runCommand(action.command, action.type);
  };

  // Get status color
  const getStatusColor = () => {
    if (!isConnected) return 'bg-red-500';
    if (status === 'running') return 'bg-yellow-500 animate-pulse';
    if (status === 'error') return 'bg-red-500';
    return 'bg-green-500';
  };

  // Get log color
  const getLogColor = (log: BridgeLog) => {
    switch (log.type) {
      case 'stdout': return 'text-gray-200';
      case 'stderr': return 'text-red-400';
      case 'error': return 'text-red-500';
      case 'success': return 'text-green-400';
      case 'info': return 'text-blue-400';
      default: return 'text-gray-300';
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 rounded-t-xl"
        style={glassStyle}
      >
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <h2 className="text-lg font-bold text-white">Auto-Pilot Terminal</h2>
          <span className="text-xs text-gray-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Shell selector */}
          <select
            value={shellType}
            onChange={(e) => setShellType(e.target.value as 'powershell' | 'bash')}
            className="bg-slate-700 text-white text-sm rounded px-2 py-1 border border-slate-600"
          >
            <option value="powershell">PowerShell</option>
            <option value="bash">Bash (WSL)</option>
          </select>

          {/* Action buttons */}
          <button
            onClick={getSystemInfo}
            className="p-2 rounded hover:bg-slate-700 text-gray-400 hover:text-white transition-colors"
            title="System Info"
          >
            ℹ️
          </button>
          <button
            onClick={clearLogs}
            className="p-2 rounded hover:bg-slate-700 text-gray-400 hover:text-white transition-colors"
            title="Clear Logs"
          >
            🗑️
          </button>
          {!isConnected && (
            <button
              onClick={reconnect}
              className="p-2 rounded hover:bg-slate-700 text-gray-400 hover:text-white transition-colors"
              title="Reconnect"
            >
              🔄
            </button>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div
        className="flex flex-wrap gap-2 p-3 border-x"
        style={{ ...glassStyle, borderTop: 'none', borderBottom: 'none' }}
      >
        {Object.entries(QUICK_ACTIONS).map(([key, action]) => (
          <button
            key={key}
            onClick={() => handleQuickAction(action)}
            disabled={status === 'running'}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium
                       bg-gradient-to-r from-purple-600/50 to-blue-600/50
                       hover:from-purple-500/60 hover:to-blue-500/60
                       disabled:opacity-50 disabled:cursor-not-allowed
                       text-white transition-all duration-200 border border-white/10"
          >
            <span>{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {/* Terminal Output */}
      <div
        ref={terminalRef}
        onClick={handleTerminalClick}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm cursor-text"
        style={{
          ...glassStyle,
          background: 'rgba(0, 0, 0, 0.9)',
          minHeight: '300px',
        }}
      >
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            <div className="text-4xl mb-2">🚀</div>
            <p>Ready for commands</p>
            <p className="text-xs mt-2">
              {isConnected
                ? 'Type a command or use quick actions above'
                : 'Waiting for bridge connection...'}
            </p>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className={`whitespace-pre-wrap break-all ${getLogColor(log)}`}>
              <span className="text-gray-600 text-xs mr-2">
                [{log.timestamp.toLocaleTimeString()}]
              </span>
              {log.content}
            </div>
          ))
        )}

        {/* Running indicator */}
        {status === 'running' && (
          <div className="flex items-center gap-2 text-yellow-400 mt-2">
            <span className="animate-spin">⚙️</span>
            <span>Executing... (Ctrl+C to stop)</span>
          </div>
        )}
      </div>

      {/* Command Input */}
      <div
        className="flex items-center gap-2 p-3 rounded-b-xl"
        style={glassStyle}
      >
        <span className="text-green-400 font-mono">
          {shellType === 'powershell' ? 'PS >' : '$'}
        </span>
        <input
          ref={inputRef}
          type="text"
          value={commandInput}
          onChange={(e) => setCommandInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isConnected}
          placeholder={isConnected ? 'Enter command...' : 'Waiting for connection...'}
          className="flex-1 bg-transparent text-white font-mono outline-none placeholder-gray-500"
        />
        <button
          onClick={handleExecute}
          disabled={!isConnected || !commandInput.trim() || status === 'running'}
          className="px-4 py-2 rounded-lg font-bold
                     bg-gradient-to-r from-green-600 to-emerald-600
                     hover:from-green-500 hover:to-emerald-500
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white transition-all duration-200"
        >
          {status === 'running' ? '⏳' : '▶️'} Run
        </button>
      </div>

      {/* System Info Bar */}
      {systemInfo && (
        <div
          className="flex items-center justify-between px-4 py-2 text-xs text-gray-400 border-t border-white/10"
          style={glassStyle}
        >
          <span>🖥️ {systemInfo.hostname} | {systemInfo.platform} ({systemInfo.arch})</span>
          <span>
            💾 {Math.round(systemInfo.freeMemory / 1024 / 1024 / 1024)}GB free |
            ⚙️ {systemInfo.cpus} cores |
            📊 {systemInfo.activeProcesses} active
          </span>
        </div>
      )}
    </div>
  );
};

export default AutoPilotTerminal;
