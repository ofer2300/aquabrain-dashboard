"use client";

import React, { useState, useEffect } from 'react';
import {
  Search,
  AlertTriangle,
  Brain,
  FileCheck,
  CheckCircle2,
  Loader2,
  Zap
} from 'lucide-react';

type ResolutionState =
  | 'detecting'
  | 'clash-found'
  | 'ai-reasoning'
  | 'proposal-ready'
  | 'resolved';

interface Resolution {
  id: string;
  title: string;
  description: string;
  confidence?: number;
  standard?: string;
  timeToResolve?: string;
}

interface SmartResolutionCardProps {
  resolution?: Resolution;
  initialState?: ResolutionState;
  autoProgress?: boolean;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onViewImpact?: (id: string) => void;
}

const STATE_CONFIG = {
  detecting: {
    icon: Search,
    title: 'מנתח גיאומטריה...',
    subtitle: 'סורק מערכות MEP לאיתור התנגשויות',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  'clash-found': {
    icon: AlertTriangle,
    title: 'התנגשות זוהתה',
    subtitle: 'נמצאה בעיה קריטית במערכת',
    color: 'text-status-critical',
    bgColor: 'bg-status-critical/10',
    borderColor: 'border-status-critical/30',
  },
  'ai-reasoning': {
    icon: Brain,
    title: 'AI מעבד...',
    subtitle: 'מייעץ לתקנים ומחשב פתרון',
    color: 'text-status-ai',
    bgColor: 'bg-status-ai/10',
    borderColor: 'border-status-ai/30',
  },
  'proposal-ready': {
    icon: FileCheck,
    title: 'פתרון מוצע לאישור',
    subtitle: 'הפתרון ממתין לאישור המהנדס',
    color: 'text-status-warning',
    bgColor: 'bg-status-warning/10',
    borderColor: 'border-status-warning/30',
  },
  resolved: {
    icon: CheckCircle2,
    title: 'נפתר ומסונכרן',
    subtitle: 'השינויים הוטמעו במודל',
    color: 'text-status-success',
    bgColor: 'bg-status-success/10',
    borderColor: 'border-status-success/30',
  },
};

const STATES: ResolutionState[] = [
  'detecting',
  'clash-found',
  'ai-reasoning',
  'proposal-ready',
  'resolved'
];

export function SmartResolutionCard({
  resolution,
  initialState = 'detecting',
  autoProgress = false,
  onApprove,
  onReject,
  onViewImpact,
}: SmartResolutionCardProps) {
  const [currentState, setCurrentState] = useState<ResolutionState>(initialState);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!autoProgress) return;

    const stateIndex = STATES.indexOf(currentState);
    if (stateIndex >= STATES.length - 1) return;

    // Progress animation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 2;
      });
    }, 40);

    // State transition
    const timeout = setTimeout(() => {
      setProgress(0);
      setCurrentState(STATES[stateIndex + 1]);
    }, 2000);

    return () => {
      clearInterval(progressInterval);
      clearTimeout(timeout);
    };
  }, [currentState, autoProgress]);

  const config = STATE_CONFIG[currentState];
  const Icon = config.icon;
  const currentIndex = STATES.indexOf(currentState);

  return (
    <div className={`glass-card p-6 space-y-6 ${config.borderColor} border`}>
      {/* State Progress Bar */}
      <div className="flex items-center justify-between gap-2">
        {STATES.map((state, index) => {
          const stateConfig = STATE_CONFIG[state];
          const StateIcon = stateConfig.icon;
          const isActive = index === currentIndex;
          const isCompleted = index < currentIndex;
          const isPending = index > currentIndex;

          return (
            <React.Fragment key={state}>
              <div className={`
                flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300
                ${isActive ? `${stateConfig.bgColor} ${stateConfig.color} ring-2 ring-offset-2 ring-offset-[#030305] ring-current` : ''}
                ${isCompleted ? 'bg-status-success/20 text-status-success' : ''}
                ${isPending ? 'bg-white/5 text-white/30' : ''}
              `}>
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : (
                  <StateIcon className={`w-5 h-5 ${isActive ? 'animate-pulse' : ''}`} />
                )}
              </div>
              {index < STATES.length - 1 && (
                <div className={`flex-1 h-0.5 ${isCompleted ? 'bg-status-success' : 'bg-white/10'}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Current State Display */}
      <div className={`${config.bgColor} rounded-xl p-4 border ${config.borderColor}`}>
        <div className="flex items-center gap-3">
          {currentState === 'detecting' || currentState === 'ai-reasoning' ? (
            <Loader2 className={`w-6 h-6 ${config.color} animate-spin`} />
          ) : (
            <Icon className={`w-6 h-6 ${config.color}`} />
          )}
          <div>
            <h3 className={`font-semibold ${config.color}`}>{config.title}</h3>
            <p className="text-sm text-white/50">{config.subtitle}</p>
          </div>
        </div>

        {/* Progress Bar for scanning states */}
        {(currentState === 'detecting' || currentState === 'ai-reasoning') && (
          <div className="mt-4 space-y-2">
            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full ${currentState === 'ai-reasoning' ? 'bg-status-ai' : 'bg-blue-500'} transition-all duration-100`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-white/20 animate-scan" />
            </div>
          </div>
        )}
      </div>

      {/* Resolution Details */}
      {resolution && currentState === 'proposal-ready' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-white">{resolution.title}</h4>
            {resolution.confidence && (
              <span className="text-status-success text-sm font-mono">
                {resolution.confidence}% ביטחון
              </span>
            )}
          </div>
          <p className="text-white/60 text-sm">{resolution.description}</p>

          <div className="grid grid-cols-2 gap-4">
            {resolution.standard && (
              <div className="bg-white/5 rounded-lg p-3 border border-white/10">
                <p className="text-xs text-white/40">תקן</p>
                <p className="text-status-warning font-mono">{resolution.standard}</p>
              </div>
            )}
            {resolution.timeToResolve && (
              <div className="bg-white/5 rounded-lg p-3 border border-white/10">
                <p className="text-xs text-white/40">זמן ביצוע</p>
                <p className="text-status-success font-mono">{resolution.timeToResolve}</p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => onApprove?.(resolution.id)}
              className="flex-1 bg-status-success/20 hover:bg-status-success/30 border border-status-success/50
                       text-status-success rounded-xl py-3 font-semibold transition-all flex items-center justify-center gap-2"
            >
              <Zap className="w-4 h-4" />
              אשר לביצוע
            </button>
            <button
              onClick={() => onReject?.(resolution.id)}
              className="px-4 bg-white/5 hover:bg-white/10 border border-white/10
                       text-white/60 rounded-xl py-3 transition-all"
            >
              דחה
            </button>
          </div>
        </div>
      )}

      {/* Resolved State */}
      {currentState === 'resolved' && (
        <div className="text-center py-4">
          <div className="w-16 h-16 mx-auto rounded-full bg-status-success/20 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-8 h-8 text-status-success" />
          </div>
          <p className="text-status-success font-semibold">הושלם בהצלחה</p>
          <p className="text-white/40 text-sm">השינויים סונכרנו למודל</p>
        </div>
      )}
    </div>
  );
}
