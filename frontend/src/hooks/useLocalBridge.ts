/**
 * useLocalBridge Hook
 * ====================
 * React hook for connecting to the AquaBrain Local Bridge Server
 * Provides real-time command execution with streaming output
 *
 * Features:
 * - WebSocket connection management with auto-reconnect
 * - PowerShell and Bash command execution
 * - pyRevit integration
 * - File operations
 * - Process management
 *
 * Usage:
 * const { runCommand, runPyRevit, logs, status, isConnected } = useLocalBridge();
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// Types
export interface BridgeLog {
  id: string;
  type: 'stdout' | 'stderr' | 'info' | 'error' | 'success' | 'skill';
  content: string;
  timestamp: Date;
  processId?: string;
  skill?: string;
  parsed?: any;
}

export interface SkillResult {
  processId: string;
  skill: string;
  success: boolean;
  exitCode: number;
  result: any;
  fullOutput: string;
  errors: string;
  timestamp: number;
}

export interface PythonCoreInfo {
  connected: boolean;
  path: string | null;
  error?: string;
}

export interface SystemInfo {
  platform: string;
  arch: string;
  hostname: string;
  cpus: number;
  totalMemory: number;
  freeMemory: number;
  uptime: number;
  nodeVersion: string;
  activeProcesses: number;
}

export interface BridgeState {
  isConnected: boolean;
  status: 'idle' | 'connecting' | 'running' | 'error';
  logs: BridgeLog[];
  systemInfo: SystemInfo | null;
  currentProcessId: string | null;
  capabilities: string[];
  pythonCore: PythonCoreInfo | null;
  skillResults: SkillResult[];
  currentSkill: string | null;
}

export interface UseBridgeReturn extends BridgeState {
  // Command execution
  runCommand: (command: string, type?: 'powershell' | 'bash' | 'claude_agent') => void;
  runClaudeAgent: (prompt: string, workingDirectory?: string) => void;
  runPython: (script: string, args?: string[]) => void;
  runPyRevit: (pyrevitAction: string, script?: string, revitVersion?: string) => void;

  // =============================================================
  // NEURAL LINK: Python Skill Execution
  // =============================================================
  runSkill: (skillName: string, params?: Record<string, any>) => void;
  listSkills: () => void;
  clearSkillResults: () => void;

  // File operations
  readFile: (path: string) => Promise<string>;
  writeFile: (path: string, content: string) => Promise<void>;
  listFiles: (path: string) => Promise<Array<{ name: string; isDirectory: boolean; path: string }>>;

  // Process management
  killProcess: (processId: string) => void;
  listProcesses: () => void;

  // Utilities
  clearLogs: () => void;
  getSystemInfo: () => void;
  reconnect: () => void;
}

// Dynamic Bridge URL - uses current hostname for WSL2 compatibility
// NOTE: Bridge runs on 8085 (Airflow uses 8080)
const getBridgeUrl = () => {
  if (typeof window !== 'undefined') {
    // Use the same host as the page, but on port 8085
    const host = window.location.hostname;
    return `ws://${host}:8085`;
  }
  return 'ws://localhost:8085';
};

const BRIDGE_URL = getBridgeUrl();
const MAX_LOGS = 500;
const RECONNECT_DELAY = 3000;

export const useLocalBridge = (): UseBridgeReturn => {
  const [state, setState] = useState<BridgeState>({
    isConnected: false,
    status: 'idle',
    logs: [],
    systemInfo: null,
    currentProcessId: null,
    capabilities: [],
    pythonCore: null,
    skillResults: [],
    currentSkill: null,
  });

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const filePromises = useRef<Map<string, { resolve: Function; reject: Function }>>(new Map());

  // Add log entry
  const addLog = useCallback((log: Omit<BridgeLog, 'id' | 'timestamp'>) => {
    setState(prev => ({
      ...prev,
      logs: [
        ...prev.logs.slice(-MAX_LOGS + 1),
        {
          ...log,
          id: `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
        },
      ],
    }));
  }, []);

  // Connect to bridge
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    setState(prev => ({ ...prev, status: 'connecting' }));

    try {
      ws.current = new WebSocket(BRIDGE_URL);

      ws.current.onopen = () => {
        console.log('🔌 Connected to Local Bridge');
        setState(prev => ({
          ...prev,
          isConnected: true,
          status: 'idle',
        }));
        addLog({ type: 'success', content: '✅ Connected to AquaBrain Local Bridge' });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };

      ws.current.onclose = () => {
        console.log('🔌 Disconnected from Local Bridge');
        setState(prev => ({
          ...prev,
          isConnected: false,
          status: 'idle',
        }));
        addLog({ type: 'error', content: '❌ Disconnected from bridge. Reconnecting...' });

        // Auto-reconnect
        if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ ...prev, status: 'error' }));
        addLog({ type: 'error', content: '❌ Connection error. Is the bridge server running?' });
      };
    } catch (error) {
      console.error('Failed to connect:', error);
      setState(prev => ({ ...prev, status: 'error' }));
    }
  }, [addLog]);

  // Handle incoming messages
  const handleMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'connected':
        setState(prev => ({
          ...prev,
          capabilities: data.capabilities || [],
          pythonCore: data.pythonCore || null,
        }));
        addLog({ type: 'info', content: `🖥️ Platform: ${data.platform} | Host: ${data.hostname}` });
        if (data.pythonCore?.connected) {
          addLog({ type: 'success', content: `🐍 Python Core connected: ${data.pythonCore.path}` });
        } else if (data.pythonCore?.error) {
          addLog({ type: 'error', content: `🐍 Python Core error: ${data.pythonCore.error}` });
        }
        break;

      case 'stdout':
        addLog({
          type: 'stdout',
          content: data.output,
          processId: data.processId,
        });
        break;

      case 'stderr':
        addLog({
          type: 'stderr',
          content: data.output,
          processId: data.processId,
        });
        break;

      case 'process-started':
        setState(prev => ({
          ...prev,
          status: 'running',
          currentProcessId: data.processId,
        }));
        addLog({
          type: 'info',
          content: `▶️ Started: ${data.command}... (${data.shell})`,
          processId: data.processId,
        });
        break;

      case 'process-completed':
        setState(prev => ({
          ...prev,
          status: 'idle',
          currentProcessId: null,
        }));
        addLog({
          type: data.success ? 'success' : 'error',
          content: `${data.success ? '✅' : '❌'} Process completed (exit code: ${data.exitCode})`,
          processId: data.processId,
        });
        break;

      case 'process-error':
        setState(prev => ({
          ...prev,
          status: 'error',
          currentProcessId: null,
        }));
        addLog({
          type: 'error',
          content: `❌ Process error: ${data.error}`,
          processId: data.processId,
        });
        break;

      // Claude Agent specific messages
      case 'claude-agent-started':
        setState(prev => ({
          ...prev,
          status: 'running',
          currentProcessId: data.processId,
        }));
        addLog({
          type: 'info',
          content: `🤖 Claude Agent started: ${data.prompt}...`,
          processId: data.processId,
        });
        break;

      case 'claude-stdout':
        addLog({
          type: 'stdout',
          content: data.output,
          processId: data.processId,
        });
        break;

      case 'claude-stderr':
        addLog({
          type: 'stderr',
          content: data.output,
          processId: data.processId,
        });
        break;

      case 'claude-agent-completed':
        setState(prev => ({
          ...prev,
          status: 'idle',
          currentProcessId: null,
        }));
        addLog({
          type: data.success ? 'success' : 'error',
          content: `🤖 Claude Agent ${data.success ? 'completed successfully' : 'failed'} (exit code: ${data.exitCode})`,
          processId: data.processId,
        });
        break;

      case 'claude-agent-error':
        setState(prev => ({
          ...prev,
          status: 'error',
          currentProcessId: null,
        }));
        addLog({
          type: 'error',
          content: `🤖 Claude Agent error: ${data.error}\n💡 ${data.hint || ''}`,
          processId: data.processId,
        });
        break;

      // =============================================================
      // NEURAL LINK: Python Skill Messages
      // =============================================================
      case 'SKILL_STARTED':
        setState(prev => ({
          ...prev,
          status: 'running',
          currentProcessId: data.processId,
          currentSkill: data.skill,
        }));
        addLog({
          type: 'info',
          content: `🐍 Skill started: ${data.skill}`,
          processId: data.processId,
          skill: data.skill,
        });
        break;

      case 'SKILL_OUTPUT':
        addLog({
          type: 'skill',
          content: data.output,
          processId: data.processId,
          skill: data.skill,
          parsed: data.parsed,
        });
        break;

      case 'SKILL_COMPLETED':
        setState(prev => ({
          ...prev,
          status: 'idle',
          currentProcessId: null,
          currentSkill: null,
          skillResults: [
            ...prev.skillResults.slice(-9), // Keep last 10 results
            {
              processId: data.processId,
              skill: data.skill,
              success: data.success,
              exitCode: data.exitCode,
              result: data.result,
              fullOutput: data.fullOutput,
              errors: data.errors,
              timestamp: data.timestamp,
            },
          ],
        }));
        addLog({
          type: data.success ? 'success' : 'error',
          content: `🐍 Skill ${data.skill} ${data.success ? 'completed successfully' : 'failed'} (exit code: ${data.exitCode})`,
          processId: data.processId,
          skill: data.skill,
        });
        break;

      case 'SKILL_ERROR':
        setState(prev => ({
          ...prev,
          status: 'error',
          currentProcessId: null,
          currentSkill: null,
        }));
        addLog({
          type: 'error',
          content: `🐍 Skill error: ${data.error}\n💡 ${data.hint || ''}`,
          processId: data.processId,
          skill: data.skill,
        });
        break;

      case 'skills-list':
        addLog({
          type: 'info',
          content: `🐍 Available skills: ${data.skills?.map((s: any) => s.name).join(', ') || 'none'}`,
        });
        break;

      case 'system-info':
        setState(prev => ({ ...prev, systemInfo: data }));
        break;

      case 'file-content':
        const readPromise = filePromises.current.get(`read:${data.path}`);
        if (readPromise) {
          readPromise.resolve(data.content);
          filePromises.current.delete(`read:${data.path}`);
        }
        break;

      case 'file-written':
        const writePromise = filePromises.current.get(`write:${data.path}`);
        if (writePromise) {
          writePromise.resolve();
          filePromises.current.delete(`write:${data.path}`);
        }
        addLog({ type: 'success', content: `📁 File written: ${data.path}` });
        break;

      case 'file-list':
        const listPromise = filePromises.current.get(`list:${data.path}`);
        if (listPromise) {
          listPromise.resolve(data.files);
          filePromises.current.delete(`list:${data.path}`);
        }
        break;

      case 'error':
        addLog({ type: 'error', content: `❌ ${data.error}` });
        // Reject any pending file promises
        for (const [key, promise] of filePromises.current.entries()) {
          promise.reject(new Error(data.error));
        }
        filePromises.current.clear();
        break;

      case 'pong':
        // Heartbeat response
        break;

      default:
        console.log('Unknown message type:', data.type, data);
    }
  }, [addLog]);

  // Send message to bridge
  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      addLog({ type: 'error', content: '❌ Not connected to bridge' });
    }
  }, [addLog]);

  // Command execution
  const runCommand = useCallback((command: string, type: 'powershell' | 'bash' | 'claude_agent' = 'powershell') => {
    if (type === 'claude_agent') {
      send({ action: 'claude_agent', command });
    } else {
      send({ action: 'execute', command, type });
    }
  }, [send]);

  // Claude Agent - The "Hands" of AquaBrain
  const runClaudeAgent = useCallback((prompt: string, workingDirectory?: string) => {
    send({ action: 'claude_agent', command: prompt, workingDirectory });
  }, [send]);

  const runPython = useCallback((script: string, args: string[] = []) => {
    send({ action: 'python', script, args });
  }, [send]);

  const runPyRevit = useCallback((pyrevitAction: string, script?: string, revitVersion: string = '2025') => {
    send({ action: 'pyrevit', pyrevitAction, script, revitVersion });
  }, [send]);

  // =============================================================
  // NEURAL LINK: Python Skill Execution
  // =============================================================
  const runSkill = useCallback((skillName: string, params: Record<string, any> = {}) => {
    send({ type: 'EXECUTE_SKILL', skill: skillName, params });
  }, [send]);

  const listSkills = useCallback(() => {
    send({ type: 'list-skills' });
  }, [send]);

  const clearSkillResults = useCallback(() => {
    setState(prev => ({ ...prev, skillResults: [] }));
  }, []);

  // File operations
  const readFile = useCallback((path: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      filePromises.current.set(`read:${path}`, { resolve, reject });
      send({ action: 'file-read', path });

      // Timeout after 10 seconds
      setTimeout(() => {
        if (filePromises.current.has(`read:${path}`)) {
          filePromises.current.delete(`read:${path}`);
          reject(new Error('File read timeout'));
        }
      }, 10000);
    });
  }, [send]);

  const writeFile = useCallback((path: string, content: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      filePromises.current.set(`write:${path}`, { resolve, reject });
      send({ action: 'file-write', path, content });

      setTimeout(() => {
        if (filePromises.current.has(`write:${path}`)) {
          filePromises.current.delete(`write:${path}`);
          reject(new Error('File write timeout'));
        }
      }, 10000);
    });
  }, [send]);

  const listFiles = useCallback((path: string): Promise<Array<{ name: string; isDirectory: boolean; path: string }>> => {
    return new Promise((resolve, reject) => {
      filePromises.current.set(`list:${path}`, { resolve, reject });
      send({ action: 'file-list', path });

      setTimeout(() => {
        if (filePromises.current.has(`list:${path}`)) {
          filePromises.current.delete(`list:${path}`);
          reject(new Error('File list timeout'));
        }
      }, 10000);
    });
  }, [send]);

  // Process management
  const killProcess = useCallback((processId: string) => {
    send({ action: 'process-kill', processId });
  }, [send]);

  const listProcesses = useCallback(() => {
    send({ action: 'process-list' });
  }, [send]);

  // Utilities
  const clearLogs = useCallback(() => {
    setState(prev => ({ ...prev, logs: [] }));
  }, []);

  const getSystemInfo = useCallback(() => {
    send({ action: 'system-info' });
  }, [send]);

  const reconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
    }
    connect();
  }, [connect]);

  // Initialize connection on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  // Heartbeat to keep connection alive
  useEffect(() => {
    const interval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        send({ action: 'ping' });
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [send]);

  return {
    ...state,
    runCommand,
    runClaudeAgent,
    runPython,
    runPyRevit,
    // NEURAL LINK
    runSkill,
    listSkills,
    clearSkillResults,
    // File operations
    readFile,
    writeFile,
    listFiles,
    killProcess,
    listProcesses,
    clearLogs,
    getSystemInfo,
    reconnect,
  };
};

export default useLocalBridge;
