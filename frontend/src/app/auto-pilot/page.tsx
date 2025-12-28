'use client';

/**
 * Auto-Pilot Page
 * ================
 * God Mode terminal interface for AquaBrain
 * Direct connection to Windows Kernel via Local Bridge
 */

import React from 'react';
import AutoPilotTerminal from '@/components/AutoPilotTerminal';

export default function AutoPilotPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-4xl">🚀</div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
                Auto-Pilot Control
              </h1>
              <p className="text-gray-400 text-sm">
                Direct System Access • PowerShell • WSL/Bash • pyRevit
              </p>
            </div>
          </div>

          {/* Status indicators */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700">
              <span className="text-xs text-gray-400">Bridge:</span>
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-xs text-green-400">Port 8080</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700">
              <span className="text-xs text-gray-400">Mode:</span>
              <span className="text-xs text-yellow-400 font-bold">⚡ GOD MODE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Terminal */}
      <div className="max-w-7xl mx-auto">
        <AutoPilotTerminal className="h-[calc(100vh-200px)]" />
      </div>

      {/* Footer */}
      <div className="max-w-7xl mx-auto mt-4 text-center">
        <p className="text-xs text-gray-500">
          ⚠️ This terminal has full system access. Use with caution.
          <span className="mx-2">•</span>
          AquaBrain V10.0 Platinum
          <span className="mx-2">•</span>
          <kbd className="px-1 bg-slate-800 rounded">Ctrl+C</kbd> to stop process
        </p>
      </div>
    </div>
  );
}
