"use client";

import React, { useState } from 'react';
import { DashboardShell } from '@/components/DashboardShell';
import {
  calculateHydraulic,
  HydraulicOutput,
  HazardClass,
  HAZARD_CLASSES,
  PIPE_SIZES,
  C_FACTORS,
} from '@/services/sprinklerApi';
import {
  Calculator,
  Droplets,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ArrowRight,
  Ruler,
  CircleDot,
  Info
} from 'lucide-react';

interface FormData {
  hazardClass: HazardClass;
  flow: string;
  length: string;
  diameter: string;
  cFactor: string;
  schedule: string;
}

export default function CalculationPage() {
  const [formData, setFormData] = useState<FormData>({
    hazardClass: 'light',
    flow: '50',
    length: '100',
    diameter: '2',
    cFactor: '120',
    schedule: '40',
  });

  const [result, setResult] = useState<HydraulicOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await calculateHydraulic({
        flow: parseFloat(formData.flow),
        length: parseFloat(formData.length),
        diameter: parseFloat(formData.diameter),
        hazard: formData.hazardClass,
        c_factor: parseFloat(formData.cFactor),
        schedule: formData.schedule,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Calculation failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <DashboardShell>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[var(--status-ai)]/20 flex items-center justify-center">
            <Calculator className="w-7 h-7 text-[var(--status-ai)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Hydraulic Calculator</h1>
            <p className="text-white/50">Hazen-Williams | SCH 40/10 | NFPA 13 2022</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Form */}
          <div className="glass-heavy rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Droplets className="w-5 h-5 text-blue-400" />
              Input Parameters
            </h2>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Hazard Classification */}
              <div className="space-y-2">
                <label className="text-sm text-white/70 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Hazard Classification
                </label>
                <select
                  value={formData.hazardClass}
                  onChange={(e) => handleInputChange('hazardClass', e.target.value as HazardClass)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                           focus:outline-none focus:border-[var(--status-ai)]/50 focus:ring-1 focus:ring-[var(--status-ai)]/30
                           appearance-none cursor-pointer"
                >
                  {HAZARD_CLASSES.map((option) => (
                    <option key={option.value} value={option.value} className="bg-[#1a1a2e]">
                      {option.label} - {option.description}
                    </option>
                  ))}
                </select>
              </div>

              {/* Flow Rate */}
              <div className="space-y-2">
                <label className="text-sm text-white/70 flex items-center gap-2">
                  <Droplets className="w-4 h-4" />
                  Flow Rate (GPM)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formData.flow}
                  onChange={(e) => handleInputChange('flow', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                           focus:outline-none focus:border-[var(--status-ai)]/50 focus:ring-1 focus:ring-[var(--status-ai)]/30"
                  placeholder="Enter flow rate"
                />
              </div>

              {/* Pipe Length */}
              <div className="space-y-2">
                <label className="text-sm text-white/70 flex items-center gap-2">
                  <Ruler className="w-4 h-4" />
                  Pipe Length (ft)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={formData.length}
                  onChange={(e) => handleInputChange('length', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                           focus:outline-none focus:border-[var(--status-ai)]/50 focus:ring-1 focus:ring-[var(--status-ai)]/30"
                  placeholder="Enter pipe length"
                />
              </div>

              {/* Pipe Diameter */}
              <div className="space-y-2">
                <label className="text-sm text-white/70 flex items-center gap-2">
                  <CircleDot className="w-4 h-4" />
                  Pipe Diameter (Nominal)
                </label>
                <select
                  value={formData.diameter}
                  onChange={(e) => handleInputChange('diameter', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                           focus:outline-none focus:border-[var(--status-ai)]/50 focus:ring-1 focus:ring-[var(--status-ai)]/30
                           appearance-none cursor-pointer"
                >
                  {PIPE_SIZES.map((size) => (
                    <option key={size.value} value={size.value} className="bg-[#1a1a2e]">
                      {size.nominal}
                    </option>
                  ))}
                </select>
              </div>

              {/* C-Factor & Schedule Row */}
              <div className="grid grid-cols-2 gap-4">
                {/* C-Factor */}
                <div className="space-y-2">
                  <label className="text-sm text-white/70 flex items-center gap-2">
                    <Gauge className="w-4 h-4" />
                    C-Factor
                  </label>
                  <select
                    value={formData.cFactor}
                    onChange={(e) => handleInputChange('cFactor', e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                             focus:outline-none focus:border-[var(--status-ai)]/50 focus:ring-1 focus:ring-[var(--status-ai)]/30
                             appearance-none cursor-pointer text-sm"
                  >
                    {C_FACTORS.map((cf) => (
                      <option key={cf.value} value={cf.value} className="bg-[#1a1a2e]">
                        {cf.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Pipe Schedule */}
                <div className="space-y-2">
                  <label className="text-sm text-white/70 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    Schedule
                  </label>
                  <select
                    value={formData.schedule}
                    onChange={(e) => handleInputChange('schedule', e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white
                             focus:outline-none focus:border-[var(--status-ai)]/50 focus:ring-1 focus:ring-[var(--status-ai)]/30
                             appearance-none cursor-pointer"
                  >
                    <option value="40" className="bg-[#1a1a2e]">SCH 40</option>
                    <option value="10" className="bg-[#1a1a2e]">SCH 10</option>
                  </select>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-[var(--status-ai)]/20 hover:bg-[var(--status-ai)]/30
                         border border-[var(--status-ai)]/50 text-[var(--status-ai)]
                         rounded-xl px-6 py-4 font-semibold transition-all
                         flex items-center justify-center gap-2
                         disabled:opacity-50 disabled:cursor-not-allowed
                         glow-purple"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Calculator className="w-5 h-5" />
                    Calculate
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            {/* Error State */}
            {error && (
              <div className="glass rounded-2xl p-6 border border-[var(--status-error)]/30 glow-red">
                <div className="flex items-center gap-3 text-[var(--status-error)]">
                  <AlertTriangle className="w-6 h-6" />
                  <div>
                    <h3 className="font-semibold">Calculation Error</h3>
                    <p className="text-sm opacity-80">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Results */}
            {result && (
              <>
                {/* Compliance Status Card */}
                <div className={`
                  glass rounded-2xl p-6 border transition-all
                  ${result.compliant
                    ? 'border-[var(--status-success)]/30 glow-green'
                    : 'border-[var(--status-error)]/30 glow-red'
                  }
                `}>
                  <div className="flex items-center gap-4">
                    {result.compliant ? (
                      <div className="w-14 h-14 rounded-full bg-[var(--status-success)]/20 flex items-center justify-center">
                        <CheckCircle2 className="w-8 h-8 text-[var(--status-success)]" />
                      </div>
                    ) : (
                      <div className="w-14 h-14 rounded-full bg-[var(--status-error)]/20 flex items-center justify-center">
                        <AlertTriangle className="w-8 h-8 text-[var(--status-error)]" />
                      </div>
                    )}
                    <div>
                      <h3 className={`text-xl font-bold ${result.compliant ? 'text-[var(--status-success)]' : 'text-[var(--status-error)]'}`}>
                        {result.compliant ? 'NFPA 13 COMPLIANT' : 'NON-COMPLIANT'}
                      </h3>
                      <p className="text-white/50 text-sm">
                        Velocity: {result.velocity} fps (max: 32 fps)
                      </p>
                    </div>
                  </div>
                </div>

                {/* Results Grid */}
                <div className="glass-heavy rounded-2xl p-6 space-y-4">
                  <h3 className="text-lg font-semibold text-white">Calculation Results</h3>

                  <div className="grid grid-cols-2 gap-4">
                    {/* Pressure Loss */}
                    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                      <p className="text-xs text-white/50 uppercase tracking-wide">Pressure Loss</p>
                      <p className="text-2xl font-bold text-white mt-1">
                        {result.pressure_loss.toFixed(2)}
                        <span className="text-sm font-normal text-white/50 ml-1">PSI</span>
                      </p>
                    </div>

                    {/* Velocity */}
                    <div className={`rounded-xl p-4 border ${
                      result.compliant
                        ? 'bg-white/5 border-white/10'
                        : 'bg-[var(--status-error)]/10 border-[var(--status-error)]/30'
                    }`}>
                      <p className="text-xs text-white/50 uppercase tracking-wide">Velocity</p>
                      <p className={`text-2xl font-bold mt-1 ${result.compliant ? 'text-white' : 'text-[var(--status-error)]'}`}>
                        {result.velocity.toFixed(2)}
                        <span className="text-sm font-normal text-white/50 ml-1">fps</span>
                      </p>
                    </div>

                    {/* Actual Diameter */}
                    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                      <p className="text-xs text-white/50 uppercase tracking-wide">Actual ID</p>
                      <p className="text-2xl font-bold text-white mt-1">
                        {result.actual_diameter.toFixed(3)}
                        <span className="text-sm font-normal text-white/50 ml-1">in</span>
                      </p>
                    </div>

                    {/* Friction per Foot */}
                    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                      <p className="text-xs text-white/50 uppercase tracking-wide">Friction/ft</p>
                      <p className="text-2xl font-bold text-white mt-1">
                        {(result.friction_per_ft * 1000).toFixed(2)}
                        <span className="text-sm font-normal text-white/50 ml-1">×10⁻³</span>
                      </p>
                    </div>
                  </div>

                  {/* Notes */}
                  {result.notes.length > 0 && (
                    <div className="mt-4 bg-blue-500/10 rounded-xl p-4 border border-blue-500/30">
                      <h4 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
                        <Info className="w-4 h-4" />
                        Notes
                      </h4>
                      <ul className="mt-2 space-y-1">
                        {result.notes.map((note, i) => (
                          <li key={i} className="text-sm text-white/70">
                            {note}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* NFPA Requirements */}
                  <div className="mt-4 pt-4 border-t border-white/10">
                    <h4 className="text-sm font-semibold text-white/70 mb-3">
                      NFPA 13 Requirements ({result.nfpa_requirements.description || formData.hazardClass})
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="flex justify-between text-white/50">
                        <span>Min Density:</span>
                        <span className="text-white">{result.nfpa_requirements.density_gpm_ft2} gpm/ft²</span>
                      </div>
                      <div className="flex justify-between text-white/50">
                        <span>Max Coverage:</span>
                        <span className="text-white">{result.nfpa_requirements.max_coverage_ft2} ft²</span>
                      </div>
                      <div className="flex justify-between text-white/50">
                        <span>Max Spacing:</span>
                        <span className="text-white">{result.nfpa_requirements.max_spacing_ft} ft</span>
                      </div>
                      <div className="flex justify-between text-white/50">
                        <span>Min Pressure:</span>
                        <span className="text-white">{result.nfpa_requirements.min_pressure_psi} PSI</span>
                      </div>
                    </div>
                  </div>

                  {/* Timestamp */}
                  <p className="text-xs text-white/30 text-right mt-4">
                    Calculated: {new Date(result.timestamp).toLocaleString()}
                  </p>
                </div>
              </>
            )}

            {/* Empty State */}
            {!result && !error && (
              <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                  <Calculator className="w-8 h-8 text-white/30" />
                </div>
                <h3 className="text-lg font-semibold text-white/50">No Calculation Yet</h3>
                <p className="text-sm text-white/30 mt-1">
                  Fill in the parameters and click Calculate
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Formula Reference */}
        <div className="glass rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-white/70 mb-3">Hazen-Williams Formula (LOD 500)</h3>
          <div className="flex flex-wrap items-center gap-4 text-white/50 text-sm font-mono">
            <span>P = 4.52 × Q<sup>1.85</sup> / (C<sup>1.85</sup> × d<sup>4.87</sup>)</span>
            <span className="text-white/30">|</span>
            <span>Nominal → Actual ID (SCH 40/10)</span>
            <span className="text-white/30">|</span>
            <span>V<sub>max</sub> = 32 fps</span>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
