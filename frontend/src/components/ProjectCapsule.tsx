"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Rocket,
  Brain,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  FileSearch,
  Box,
  Route,
  Droplets,
  Hammer,
  Clock,
  History,
  ChevronDown,
  Cpu,
  CloudOff,
  CloudCheck,
  Database
} from 'lucide-react';
import { useProjectContext, type RevitVersion as ContextRevitVersion } from '@/hooks/useProjectContext';

// Process stages for the Auto-Pilot
type ProcessStage =
  | 'idle'
  | 'queued'           // ממתין בתור
  | 'initializing'     // מאתחל
  | 'extracting'       // שואב תוכניות מ-Revit
  | 'voxelizing'       // ממיר לרשת ווקסלים
  | 'routing'          // מתכנן תוואי צנרת
  | 'calculating'      // מחשב הידראוליקה
  | 'validating'       // בודק תאימות
  | 'generating'       // מייצר LOD 500
  | 'signaling'        // קובע סטטוס רמזור
  | 'completed'
  | 'failed';

// Traffic Light status
type TrafficLight = 'GREEN' | 'YELLOW' | 'RED' | null;

// V3.0: Revit Version Support
type RevitVersion = 'auto' | '2024' | '2025' | '2026';

interface RevitVersionOption {
  value: RevitVersion;
  label: string;
  labelHe: string;
  description: string;
}

const REVIT_VERSIONS: RevitVersionOption[] = [
  { value: 'auto', label: 'Auto-Detect', labelHe: 'זיהוי אוטומטי', description: 'Recommended - tries 2026 → 2025 → 2024' },
  { value: '2026', label: 'Revit 2026', labelHe: 'רוויט 2026', description: 'Latest version' },
  { value: '2025', label: 'Revit 2025', labelHe: 'רוויט 2025', description: 'Stable release' },
  { value: '2024', label: 'Revit 2024', labelHe: 'רוויט 2024', description: 'Legacy support' },
];

// API Response Types (V2.0 - Async Architecture)
interface TrafficLightMetrics {
  maxVelocity: number;
  pressureLoss: number;
  clashCount: number;
  nfpaCompliant: boolean;
}

interface TrafficLightResult {
  status: TrafficLight;
  message: string;
  details: string[];
  action_required: string | null;
  confidence: number;
  metrics: TrafficLightMetrics;
}

interface RoutingSummary {
  total_segments: number;
  total_length_m: number;
  total_sprinklers: number;
  branch_count: number;
}

interface HydraulicSummary {
  main_line: {
    pressure_loss_psi: number;
    velocity_fps: number;
    actual_diameter: number;
    compliant: boolean;
  };
  totals: {
    total_pressure_loss_psi: number;
    max_velocity_fps: number;
    all_compliant: boolean;
  };
}

// Async Job Submission Response
interface AsyncJobResponse {
  run_id: string;
  status: string;
  message: string;
}

// Status Polling Response
interface RunStatusResponse {
  id: string;
  project_id: string;
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  current_stage: string;
  progress_percent: number;
  hazard_class: string;
  notes: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number;
  error_message: string | null;
  metrics: TrafficLightMetrics;
  traffic_light: TrafficLightResult;
  geometry_summary: { floors: number; total_area_sqm: number; obstruction_count: number; clash_count: number };
  routing_summary: RoutingSummary;
  hydraulic_summary: HydraulicSummary;
}

const STAGE_CONFIG: Record<ProcessStage, { label: string; labelHe: string; icon: React.ElementType }> = {
  idle: { label: 'Ready', labelHe: 'מוכן', icon: Rocket },
  queued: { label: 'Queued', labelHe: 'ממתין בתור...', icon: Clock },
  initializing: { label: 'Initializing', labelHe: 'מאתחל...', icon: Brain },
  extracting: { label: 'Extracting Plans', labelHe: 'שואב תוכניות...', icon: FileSearch },
  voxelizing: { label: 'Voxelizing Geometry', labelHe: 'מנתח גיאומטריה...', icon: Box },
  routing: { label: 'Planning Routes', labelHe: 'מתכנן תוואי צנרת...', icon: Route },
  calculating: { label: 'Hydraulic Calculation', labelHe: 'מבצע חישוב הידראולי...', icon: Droplets },
  validating: { label: 'Validating NFPA 13', labelHe: 'מאמת תקן NFPA 13...', icon: CheckCircle2 },
  generating: { label: 'Generating LOD 500', labelHe: 'מייצר מודל LOD 500...', icon: Hammer },
  signaling: { label: 'Traffic Light', labelHe: 'קובע סטטוס רמזור...', icon: AlertTriangle },
  completed: { label: 'Completed', labelHe: 'הושלם', icon: CheckCircle2 },
  failed: { label: 'Failed', labelHe: 'נכשל', icon: AlertCircle },
};

// Map backend stage names to frontend
const mapBackendStage = (stage: string): ProcessStage => {
  const stageMap: Record<string, ProcessStage> = {
    'queued': 'queued',
    'initializing': 'initializing',
    'extracting': 'extracting',
    'voxelizing': 'voxelizing',
    'routing': 'routing',
    'calculating': 'calculating',
    'validating': 'validating',
    'generating': 'generating',
    'signaling': 'signaling',
    'completed': 'completed',
    'failed': 'failed',
  };
  return stageMap[stage] || 'idle';
};

interface ProjectCapsuleProps {
  projectId?: string;
  projectName?: string;
}

export function ProjectCapsule({ projectId: initialProjectId = '', projectName: initialProjectName = '' }: ProjectCapsuleProps) {
  // V3.1: Use persistent context for project state (survives page navigation)
  const {
    projectId,
    setProjectId,
    projectName,
    setProjectName,
    notes,
    setNotes,
    revitVersion,
    setRevitVersion,
    lastRunId,
    setLastRunId,
    isHydrated,
  } = useProjectContext();

  // Local UI state (doesn't need persistence)
  const [stage, setStage] = useState<ProcessStage>('idle');
  const [result, setResult] = useState<RunStatusResponse | null>(null);
  const [progress, setProgress] = useState(0);
  const [runId, setRunId] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const [versionDropdownOpen, setVersionDropdownOpen] = useState(false);

  // Initialize from props if context is empty (first load)
  useEffect(() => {
    if (isHydrated && !projectId && initialProjectId) {
      setProjectId(initialProjectId);
    }
    if (isHydrated && !projectName && initialProjectName) {
      setProjectName(initialProjectName);
    }
  }, [isHydrated, projectId, projectName, initialProjectId, initialProjectName, setProjectId, setProjectName]);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isProcessing = !['idle', 'completed', 'failed'].includes(stage);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Poll for status updates
  const pollStatus = useCallback(async (id: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/engineering/status/${id}`);

      if (!response.ok) {
        throw new Error('Failed to get status');
      }

      const data: RunStatusResponse = await response.json();

      // Update UI state from backend
      setProgress(data.progress_percent);
      setStage(mapBackendStage(data.current_stage));
      setPollCount(prev => prev + 1);

      // Check if processing is complete
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        // Stop polling
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        // Update final result
        setResult(data);
        setStage(data.status === 'COMPLETED' ? 'completed' : 'failed');
      }

    } catch (error) {
      console.error('Polling error:', error);
      // Don't stop polling on transient errors, just log
    }
  }, []);

  // Start polling when we have a runId
  useEffect(() => {
    if (runId && isProcessing) {
      // Start polling every 1 second
      pollIntervalRef.current = setInterval(() => {
        pollStatus(runId);
      }, 1000);

      // Initial poll
      pollStatus(runId);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [runId, pollStatus]);

  const startProcess = async () => {
    setStage('queued');
    setProgress(0);
    setResult(null);
    setRunId(null);
    setPollCount(0);

    try {
      // Submit async job
      const response = await fetch('http://localhost:8000/api/engineering/start-process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          notes: notes,
          hazard_class: 'ordinary_1',
          async_mode: true,  // Use async mode
          revit_version: revitVersion,  // V3.0: Multi-version support
        })
      });

      if (!response.ok) {
        throw new Error('Failed to queue job');
      }

      const data: AsyncJobResponse = await response.json();

      // Store run ID and start polling
      setRunId(data.run_id);
      setStage('queued');

    } catch (error) {
      console.error('Process error:', error);
      setStage('failed');
      setResult({
        id: '',
        project_id: projectId,
        status: 'FAILED',
        current_stage: 'failed',
        progress_percent: 0,
        hazard_class: 'light',
        notes: '',
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        duration_seconds: 0,
        error_message: error instanceof Error ? error.message : 'Unknown error',
        metrics: { maxVelocity: 0, pressureLoss: 0, clashCount: 0, nfpaCompliant: false },
        traffic_light: {
          status: 'RED',
          message: 'שגיאה בתהליך',
          details: [error instanceof Error ? error.message : 'Unknown error'],
          action_required: 'בדוק חיבור לשרת',
          confidence: 0,
          metrics: { maxVelocity: 0, pressureLoss: 0, clashCount: 0, nfpaCompliant: false }
        },
        geometry_summary: { floors: 0, total_area_sqm: 0, obstruction_count: 0, clash_count: 0 },
        routing_summary: { total_segments: 0, total_length_m: 0, total_sprinklers: 0, branch_count: 0 },
        hydraulic_summary: {
          main_line: { pressure_loss_psi: 0, velocity_fps: 0, actual_diameter: 0, compliant: false },
          totals: { total_pressure_loss_psi: 0, max_velocity_fps: 0, all_compliant: false }
        },
      });
    }
  };

  const getTrafficLightColor = (status: TrafficLight) => {
    switch (status) {
      case 'GREEN': return 'bg-status-success';
      case 'YELLOW': return 'bg-status-warning';
      case 'RED': return 'bg-status-error';
      default: return 'bg-white/20';
    }
  };

  const StageIcon = STAGE_CONFIG[stage].icon;

  return (
    <div className="glass-heavy rounded-2xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-status-ai/20 flex items-center justify-center glow-ai">
            <Brain className="w-8 h-8 text-status-ai" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">התנעת תכנון אוטומטי</h2>
            <p className="text-text-secondary text-sm">Auto-Pilot V3.1 | Total Memory</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Memory Indicator - Shows sync status */}
          <div className={`
            flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all
            ${isHydrated
              ? 'bg-status-success/10 border border-status-success/30'
              : 'bg-status-warning/10 border border-status-warning/30'}
          `}>
            {isHydrated ? (
              <>
                <Database className="w-4 h-4 text-status-success animate-pulse" />
                <span className="text-xs text-status-success font-medium">זיכרון פעיל</span>
              </>
            ) : (
              <>
                <CloudOff className="w-4 h-4 text-status-warning" />
                <span className="text-xs text-status-warning font-medium">טוען...</span>
              </>
            )}
          </div>

          {/* Traffic Light */}
          <div className="flex gap-2">
            <div className={`w-6 h-6 rounded-full transition-all ${result?.traffic_light?.status === 'RED' ? 'bg-status-error glow-error' : 'bg-white/10'}`} />
            <div className={`w-6 h-6 rounded-full transition-all ${result?.traffic_light?.status === 'YELLOW' ? 'bg-status-warning glow-warning' : 'bg-white/10'}`} />
            <div className={`w-6 h-6 rounded-full transition-all ${result?.traffic_light?.status === 'GREEN' ? 'bg-status-success glow-success' : 'bg-white/10'}`} />
          </div>
        </div>
      </div>

      {/* Project Info - Editable */}
      <div className="glass rounded-xl p-4 space-y-3">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-text-secondary block mb-1">שם הפרויקט</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={isProcessing}
              placeholder="לדוגמה: מגדל המאירי"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white
                       placeholder:text-white/30 text-sm
                       focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30
                       disabled:opacity-50"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">מזהה פרויקט</label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              disabled={isProcessing}
              placeholder="לדוגמה: HAMEIRI-TOWER-01"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-status-ai font-mono
                       placeholder:text-white/30 text-sm
                       focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30
                       disabled:opacity-50"
            />
          </div>
        </div>
      </div>

      {/* Run ID Badge */}
      {runId && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-status-ai/10 border border-status-ai/30">
          <History className="w-4 h-4 text-status-ai" />
          <span className="text-xs text-text-secondary">Run ID:</span>
          <span className="font-mono text-xs text-status-ai">{runId}</span>
          {isProcessing && (
            <span className="text-xs text-white/50 ml-auto">Poll #{pollCount}</span>
          )}
        </div>
      )}

      {/* V3.0: Revit Version Selector */}
      <div className="space-y-2">
        <label className="text-sm text-text-secondary flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          גרסת Revit
        </label>
        <div className="relative">
          <button
            onClick={() => setVersionDropdownOpen(!versionDropdownOpen)}
            disabled={isProcessing}
            className={`
              w-full px-4 py-3 rounded-xl text-right
              bg-white/5 border border-white/10
              hover:border-status-ai/30 hover:bg-white/10
              focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30
              transition-all flex items-center justify-between
              disabled:opacity-50 disabled:cursor-not-allowed
              ${versionDropdownOpen ? 'border-status-ai/50 ring-1 ring-status-ai/30' : ''}
            `}
          >
            <ChevronDown className={`w-5 h-5 text-white/50 transition-transform ${versionDropdownOpen ? 'rotate-180' : ''}`} />
            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-white font-medium">
                  {REVIT_VERSIONS.find(v => v.value === revitVersion)?.labelHe}
                </span>
                <span className="text-xs text-white/50 block">
                  {REVIT_VERSIONS.find(v => v.value === revitVersion)?.description}
                </span>
              </div>
              <div className={`
                w-10 h-10 rounded-lg flex items-center justify-center
                ${revitVersion === 'auto' ? 'bg-status-ai/20 text-status-ai' : 'bg-cyan-500/20 text-cyan-400'}
              `}>
                <Cpu className="w-5 h-5" />
              </div>
            </div>
          </button>

          {/* Dropdown Options */}
          {versionDropdownOpen && (
            <div className="absolute z-50 w-full mt-2 rounded-xl bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
              {REVIT_VERSIONS.map((version) => (
                <button
                  key={version.value}
                  onClick={() => {
                    setRevitVersion(version.value);
                    setVersionDropdownOpen(false);
                  }}
                  className={`
                    w-full px-4 py-3 flex items-center justify-between text-right
                    hover:bg-white/10 transition-all
                    ${revitVersion === version.value ? 'bg-status-ai/10' : ''}
                  `}
                >
                  <div className={`
                    w-2 h-2 rounded-full
                    ${revitVersion === version.value ? 'bg-status-ai' : 'bg-white/20'}
                  `} />
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className={`font-medium ${revitVersion === version.value ? 'text-status-ai' : 'text-white'}`}>
                        {version.labelHe}
                      </span>
                      <span className="text-xs text-white/50 block">{version.description}</span>
                    </div>
                    <div className={`
                      w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold
                      ${version.value === 'auto' ? 'bg-status-ai/20 text-status-ai' : 'bg-cyan-500/20 text-cyan-400'}
                    `}>
                      {version.value === 'auto' ? 'A' : version.value.slice(-2)}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Notes Input */}
      <div className="space-y-2">
        <label className="text-sm text-text-secondary flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          דגשים מיוחדים לתכנון (אופציונלי)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={isProcessing}
          placeholder="לדוגמה: שים לב לגובה תקרה נמוך בקומה 3..."
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                   placeholder:text-white/30 resize-none h-20
                   focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30
                   disabled:opacity-50"
        />
      </div>

      {/* Progress Section */}
      {isProcessing && (
        <div className="space-y-4">
          {/* Progress Bar */}
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-status-ai to-cyan-400 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Current Stage */}
          <div className="flex items-center gap-3 p-4 rounded-xl bg-status-ai/10 border border-status-ai/30">
            <StageIcon className="w-6 h-6 text-status-ai animate-pulse" />
            <div className="flex-1">
              <p className="text-white font-medium">{STAGE_CONFIG[stage].labelHe}</p>
              <p className="text-xs text-text-secondary">{STAGE_CONFIG[stage].label}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono text-status-ai">{progress}%</span>
              <Loader2 className="w-5 h-5 text-status-ai animate-spin" />
            </div>
          </div>

          {/* Stage Timeline */}
          <div className="flex justify-between px-2">
            {(['extracting', 'voxelizing', 'routing', 'calculating', 'validating', 'generating'] as ProcessStage[]).map((s, i) => {
              const Icon = STAGE_CONFIG[s].icon;
              const stageOrder = ['queued', 'initializing', 'extracting', 'voxelizing', 'routing', 'calculating', 'validating', 'generating', 'signaling'];
              const currentIndex = stageOrder.indexOf(stage);
              const targetIndex = stageOrder.indexOf(s);
              const isActive = s === stage;
              const isComplete = targetIndex < currentIndex;

              return (
                <div key={s} className="flex flex-col items-center gap-1">
                  <div className={`
                    w-8 h-8 rounded-full flex items-center justify-center transition-all
                    ${isActive ? 'bg-status-ai/30 text-status-ai glow-ai' : ''}
                    ${isComplete ? 'bg-status-success/30 text-status-success' : ''}
                    ${!isActive && !isComplete ? 'bg-white/10 text-white/30' : ''}
                  `}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Result Section */}
      {result && (stage === 'completed' || stage === 'failed') && (
        <div className={`
          p-5 rounded-xl border transition-all
          ${result.traffic_light?.status === 'GREEN' ? 'bg-status-success/10 border-status-success/30 glow-success' : ''}
          ${result.traffic_light?.status === 'YELLOW' ? 'bg-status-warning/10 border-status-warning/30 glow-warning' : ''}
          ${result.traffic_light?.status === 'RED' ? 'bg-status-error/10 border-status-error/30 glow-error' : ''}
        `}>
          <div className="flex items-center gap-4 mb-4">
            <div className={`
              w-12 h-12 rounded-full flex items-center justify-center
              ${getTrafficLightColor(result.traffic_light?.status)}
            `}>
              {result.traffic_light?.status === 'GREEN' && <CheckCircle2 className="w-6 h-6 text-white" />}
              {result.traffic_light?.status === 'YELLOW' && <AlertTriangle className="w-6 h-6 text-white" />}
              {result.traffic_light?.status === 'RED' && <AlertCircle className="w-6 h-6 text-white" />}
            </div>
            <div>
              <p className={`text-lg font-bold ${
                result.traffic_light?.status === 'GREEN' ? 'text-status-success' :
                result.traffic_light?.status === 'YELLOW' ? 'text-status-warning' : 'text-status-error'
              }`}>
                {result.traffic_light?.message || (stage === 'failed' ? 'שגיאה בתהליך' : 'הושלם')}
              </p>
              <p className="text-sm text-text-secondary">
                {result.traffic_light?.status === 'GREEN' ? 'התכנון אושר - ניתן להמשיך' :
                 result.traffic_light?.status === 'YELLOW' ? 'נדרשת בדיקה נוספת' :
                 result.error_message || 'נדרשת התערבות'}
              </p>
            </div>
          </div>

          {/* Details */}
          {result.traffic_light?.details && (
            <div className="space-y-2">
              {result.traffic_light.details.map((detail, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-white/70">
                  <CheckCircle2 className="w-4 h-4 text-status-success" />
                  {detail}
                </div>
              ))}
            </div>
          )}

          {/* Metrics - Using Real API Data */}
          {result.routing_summary && (
            <div className="grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/10">
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{result.routing_summary.total_segments}</p>
                <p className="text-xs text-text-secondary">קטעי צנרת</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{result.routing_summary.total_length_m?.toFixed(1) || '0'}</p>
                <p className="text-xs text-text-secondary">מטר אורך</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{result.traffic_light?.metrics?.pressureLoss?.toFixed(1) || '0'}</p>
                <p className="text-xs text-text-secondary">PSI אובדן</p>
              </div>
              <div className="text-center">
                <p className={`text-2xl font-bold ${(result.traffic_light?.metrics?.maxVelocity || 0) < 20 ? 'text-status-success' : 'text-status-warning'}`}>
                  {result.traffic_light?.metrics?.maxVelocity?.toFixed(1) || '0'}
                </p>
                <p className="text-xs text-text-secondary">fps מהירות</p>
              </div>
            </div>
          )}

          {/* Extra Row: Sprinklers & Duration */}
          {result.routing_summary && (
            <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-white/10">
              <div className="text-center">
                <p className="text-xl font-bold text-status-ai">{result.routing_summary.total_sprinklers}</p>
                <p className="text-xs text-text-secondary">ספרינקלרים</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-white">{result.traffic_light?.metrics?.clashCount || 0}</p>
                <p className="text-xs text-text-secondary">התנגשויות</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-cyan-400">{result.duration_seconds?.toFixed(1) || '0'}s</p>
                <p className="text-xs text-text-secondary">זמן עיבוד</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Launch Button */}
      <button
        onClick={startProcess}
        disabled={isProcessing}
        className={`
          w-full py-5 rounded-xl font-bold text-lg transition-all
          flex items-center justify-center gap-3
          ${isProcessing
            ? 'bg-white/10 text-white/50 cursor-not-allowed'
            : 'bg-status-success/20 hover:bg-status-success/30 border border-status-success/50 text-status-success glow-success'
          }
        `}
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-6 h-6 animate-spin" />
            מעבד... {progress}%
          </>
        ) : (
          <>
            <Rocket className="w-6 h-6" />
            הפעל סוכני תכנון
          </>
        )}
      </button>

      {/* Footer Note */}
      <p className="text-xs text-center text-white/30">
        Powered by AquaBrain AI Engine V3.1 | Total Memory | Command Center | NFPA 13
      </p>
    </div>
  );
}
