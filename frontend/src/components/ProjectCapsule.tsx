"use client";

import React, { useState } from 'react';
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
  Hammer
} from 'lucide-react';

// Process stages for the Auto-Pilot
type ProcessStage =
  | 'idle'
  | 'extracting'      // שואב תוכניות מ-Revit
  | 'voxelizing'      // ממיר לרשת ווקסלים
  | 'routing'         // מתכנן תוואי צנרת
  | 'calculating'     // מחשב הידראוליקה
  | 'generating'      // מייצר LOD 500
  | 'validating'      // בודק תאימות
  | 'completed'
  | 'error';

// Traffic Light status
type TrafficLight = 'GREEN' | 'YELLOW' | 'RED' | null;

// API Response Types (LOD 500 - Production Grade)
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

interface EngineeringResponse {
  project_id: string;
  status: string;
  traffic_light: TrafficLightResult;
  routing_summary: RoutingSummary;
  hydraulic_summary: HydraulicSummary;
  duration_seconds: number;
  stages_completed: string[];
}

const STAGE_CONFIG: Record<ProcessStage, { label: string; labelHe: string; icon: React.ElementType }> = {
  idle: { label: 'Ready', labelHe: 'מוכן', icon: Rocket },
  extracting: { label: 'Extracting Plans', labelHe: 'שואב תוכניות...', icon: FileSearch },
  voxelizing: { label: 'Voxelizing Geometry', labelHe: 'מנתח גיאומטריה...', icon: Box },
  routing: { label: 'Planning Routes', labelHe: 'מתכנן תוואי צנרת...', icon: Route },
  calculating: { label: 'Hydraulic Calculation', labelHe: 'מבצע חישוב הידראולי...', icon: Droplets },
  generating: { label: 'Generating LOD 500', labelHe: 'מייצר מודל LOD 500...', icon: Hammer },
  validating: { label: 'Validating NFPA 13', labelHe: 'מאמת תקן NFPA 13...', icon: CheckCircle2 },
  completed: { label: 'Completed', labelHe: 'הושלם', icon: CheckCircle2 },
  error: { label: 'Error', labelHe: 'שגיאה', icon: AlertCircle },
};

interface ProjectCapsuleProps {
  projectId?: string;
  projectName?: string;
}

export function ProjectCapsule({ projectId = 'PRJ-500', projectName = 'מגדל אקווה' }: ProjectCapsuleProps) {
  const [stage, setStage] = useState<ProcessStage>('idle');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<EngineeringResponse | null>(null);
  const [progress, setProgress] = useState(0);

  const isProcessing = !['idle', 'completed', 'error'].includes(stage);

  const startProcess = async () => {
    setStage('extracting');
    setProgress(0);
    setResult(null);

    try {
      // Stage 1: Extract geometry from Revit
      setStage('extracting');
      setProgress(10);
      await simulateStage(1500);

      // Stage 2: Voxelize geometry
      setStage('voxelizing');
      setProgress(25);
      await simulateStage(1200);

      // Stage 3: Route planning (A* algorithm)
      setStage('routing');
      setProgress(45);
      await simulateStage(2000);

      // Stage 4: Hydraulic calculation
      setStage('calculating');
      setProgress(65);

      // Real API call to our backend
      const response = await fetch('http://localhost:8000/api/engineering/start-process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          notes: notes,
          hazard_class: 'ordinary_1'
        })
      });

      if (!response.ok) {
        throw new Error('Process failed');
      }

      const data: EngineeringResponse = await response.json();
      setProgress(80);

      // Stage 5: Generate LOD 500
      setStage('generating');
      setProgress(90);
      await simulateStage(1500);

      // Stage 6: Validate
      setStage('validating');
      setProgress(95);
      await simulateStage(800);

      // Complete - store full response
      setStage('completed');
      setProgress(100);
      setResult(data);

    } catch (error) {
      console.error('Process error:', error);
      setStage('error');
      // Create error response in correct format
      setResult({
        project_id: projectId,
        status: 'error',
        traffic_light: {
          status: 'RED',
          message: 'שגיאה בתהליך',
          details: [error instanceof Error ? error.message : 'Unknown error'],
          action_required: 'בדוק חיבור לשרת',
          confidence: 0,
          metrics: { maxVelocity: 0, pressureLoss: 0, clashCount: 0, nfpaCompliant: false }
        },
        routing_summary: { total_segments: 0, total_length_m: 0, total_sprinklers: 0, branch_count: 0 },
        hydraulic_summary: {
          main_line: { pressure_loss_psi: 0, velocity_fps: 0, actual_diameter: 0, compliant: false },
          totals: { total_pressure_loss_psi: 0, max_velocity_fps: 0, all_compliant: false }
        },
        duration_seconds: 0,
        stages_completed: []
      });
    }
  };

  const simulateStage = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const getTrafficLightColor = (status: TrafficLight) => {
    switch (status) {
      case 'GREEN': return 'bg-status-success';
      case 'YELLOW': return 'bg-status-warning';
      case 'RED': return 'bg-status-error';
      default: return 'bg-white/20';
    }
  };

  const getTrafficLightGlow = (status: TrafficLight) => {
    switch (status) {
      case 'GREEN': return 'glow-success';
      case 'YELLOW': return 'glow-warning';
      case 'RED': return 'glow-error';
      default: return '';
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
            <p className="text-text-secondary text-sm">Auto-Pilot | LOD 500 Generation</p>
          </div>
        </div>

        {/* Traffic Light */}
        <div className="flex gap-2">
          <div className={`w-6 h-6 rounded-full transition-all ${result?.traffic_light?.status === 'RED' ? 'bg-status-error glow-error' : 'bg-white/10'}`} />
          <div className={`w-6 h-6 rounded-full transition-all ${result?.traffic_light?.status === 'YELLOW' ? 'bg-status-warning glow-warning' : 'bg-white/10'}`} />
          <div className={`w-6 h-6 rounded-full transition-all ${result?.traffic_light?.status === 'GREEN' ? 'bg-status-success glow-success' : 'bg-white/10'}`} />
        </div>
      </div>

      {/* Project Info */}
      <div className="glass rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-xs text-text-secondary">פרויקט נבחר</p>
          <p className="text-lg font-bold text-white">{projectName}</p>
        </div>
        <div className="text-left">
          <p className="text-xs text-text-secondary">מזהה</p>
          <p className="font-mono text-status-ai">{projectId}</p>
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
              className="h-full bg-gradient-to-r from-status-ai to-cyan-400 transition-all duration-500"
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
            <Loader2 className="w-5 h-5 text-status-ai animate-spin" />
          </div>

          {/* Stage Timeline */}
          <div className="flex justify-between px-2">
            {(['extracting', 'voxelizing', 'routing', 'calculating', 'generating', 'validating'] as ProcessStage[]).map((s, i) => {
              const Icon = STAGE_CONFIG[s].icon;
              const isActive = s === stage;
              const isComplete = ['extracting', 'voxelizing', 'routing', 'calculating', 'generating', 'validating'].indexOf(stage) > i;

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
      {result && stage === 'completed' && (
        <div className={`
          p-5 rounded-xl border transition-all
          ${result.traffic_light.status === 'GREEN' ? 'bg-status-success/10 border-status-success/30 glow-success' : ''}
          ${result.traffic_light.status === 'YELLOW' ? 'bg-status-warning/10 border-status-warning/30 glow-warning' : ''}
          ${result.traffic_light.status === 'RED' ? 'bg-status-error/10 border-status-error/30 glow-error' : ''}
        `}>
          <div className="flex items-center gap-4 mb-4">
            <div className={`
              w-12 h-12 rounded-full flex items-center justify-center
              ${getTrafficLightColor(result.traffic_light.status)}
            `}>
              {result.traffic_light.status === 'GREEN' && <CheckCircle2 className="w-6 h-6 text-white" />}
              {result.traffic_light.status === 'YELLOW' && <AlertTriangle className="w-6 h-6 text-white" />}
              {result.traffic_light.status === 'RED' && <AlertCircle className="w-6 h-6 text-white" />}
            </div>
            <div>
              <p className={`text-lg font-bold ${
                result.traffic_light.status === 'GREEN' ? 'text-status-success' :
                result.traffic_light.status === 'YELLOW' ? 'text-status-warning' : 'text-status-error'
              }`}>
                {result.traffic_light.message}
              </p>
              <p className="text-sm text-text-secondary">
                {result.traffic_light.status === 'GREEN' ? 'התכנון אושר - ניתן להמשיך' :
                 result.traffic_light.status === 'YELLOW' ? 'נדרשת בדיקה נוספת' : 'נדרשת התערבות'}
              </p>
            </div>
          </div>

          {/* Details */}
          <div className="space-y-2">
            {result.traffic_light.details.map((detail, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-white/70">
                <CheckCircle2 className="w-4 h-4 text-status-success" />
                {detail}
              </div>
            ))}
          </div>

          {/* Metrics - Using Real API Data */}
          <div className="grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/10">
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{result.routing_summary.total_segments}</p>
              <p className="text-xs text-text-secondary">קטעי צנרת</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{result.routing_summary.total_length_m.toFixed(1)}</p>
              <p className="text-xs text-text-secondary">מטר אורך</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{result.traffic_light.metrics.pressureLoss.toFixed(1)}</p>
              <p className="text-xs text-text-secondary">PSI אובדן</p>
            </div>
            <div className="text-center">
              <p className={`text-2xl font-bold ${result.traffic_light.metrics.maxVelocity < 20 ? 'text-status-success' : 'text-status-warning'}`}>
                {result.traffic_light.metrics.maxVelocity.toFixed(1)}
              </p>
              <p className="text-xs text-text-secondary">fps מהירות</p>
            </div>
          </div>

          {/* Extra Row: Sprinklers & Duration */}
          <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-white/10">
            <div className="text-center">
              <p className="text-xl font-bold text-status-ai">{result.routing_summary.total_sprinklers}</p>
              <p className="text-xs text-text-secondary">ספרינקלרים</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-white">{result.traffic_light.metrics.clashCount}</p>
              <p className="text-xs text-text-secondary">התנגשויות</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-cyan-400">{result.duration_seconds.toFixed(1)}s</p>
              <p className="text-xs text-text-secondary">זמן עיבוד</p>
            </div>
          </div>
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
            מעבד...
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
        Powered by AquaBrain AI Engine | NFPA 13 Compliant | LOD 500
      </p>
    </div>
  );
}
