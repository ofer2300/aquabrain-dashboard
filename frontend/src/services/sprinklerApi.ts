/**
 * AquaBrain Sprinkler API Service V3.0
 * Handles hydraulic calculations and NFPA 13 validation
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// === Types ===

export interface HydraulicInput {
  flow: number;        // Flow rate in GPM
  length: number;      // Pipe length in feet
  diameter: number;    // Nominal pipe diameter in inches
  hazard: HazardClass; // NFPA 13 hazard classification
  c_factor?: number;   // Hazen-Williams C-factor (default: 120)
  schedule?: string;   // Pipe schedule: "40" or "10"
}

export interface HydraulicOutput {
  pressure_loss: number;
  velocity: number;
  compliant: boolean;
  notes: string[];
  actual_diameter: number;
  friction_per_ft: number;
  nfpa_requirements: NFPARequirements;
  timestamp: string;
}

export interface NFPARequirements {
  density_gpm_ft2: number;
  area_ft2: number;
  max_spacing_ft: number;
  max_coverage_ft2: number;
  min_pressure_psi: number;
  hose_allowance_gpm?: number;
  description?: string;
}

export type HazardClass =
  | 'light'
  | 'ordinary_1'
  | 'ordinary_2'
  | 'extra_1'
  | 'extra_2';

export interface PipeSegment {
  id: string;
  name: string;
  flow: number;
  diameter: number;
  length: number;
  c_factor: number;
  schedule?: string;
}

// === API Functions ===

/**
 * Calculate hydraulic parameters for a pipe segment
 * Uses Hazen-Williams formula with SCH 40/10 pipe data
 *
 * @param input { flow: 100, length: 50, diameter: 2, hazard: 'light' }
 * @returns { pressure_loss: 5.2, velocity: 10.5, compliant: true, notes: [...] }
 */
export async function calculateHydraulic(input: HydraulicInput): Promise<HydraulicOutput> {
  const response = await fetch(`${API_BASE_URL}/api/calc/hydraulic`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      flow: input.flow,
      length: input.length,
      diameter: input.diameter,
      hazard: input.hazard,
      c_factor: input.c_factor ?? 120,
      schedule: input.schedule ?? '40',
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Calculate hydraulics for multiple pipe segments
 */
export async function calculateMultiplePipes(
  segments: PipeSegment[],
  hazardClass: HazardClass = 'light'
): Promise<Map<string, HydraulicOutput>> {
  const results = new Map<string, HydraulicOutput>();

  const calculations = segments.map(async (segment) => {
    const result = await calculateHydraulic({
      flow: segment.flow,
      diameter: segment.diameter,
      length: segment.length,
      hazard: hazardClass,
      c_factor: segment.c_factor,
      schedule: segment.schedule,
    });
    return { id: segment.id, result };
  });

  const settled = await Promise.allSettled(calculations);

  settled.forEach((outcome, index) => {
    if (outcome.status === 'fulfilled') {
      results.set(outcome.value.id, outcome.value.result);
    } else {
      console.error(`Failed to calculate segment ${segments[index].id}:`, outcome.reason);
    }
  });

  return results;
}

/**
 * Get total pressure loss for a pipe system
 */
export function getTotalPressureLoss(results: Map<string, HydraulicOutput>): number {
  let total = 0;
  results.forEach((result) => {
    total += result.pressure_loss;
  });
  return Math.round(total * 100) / 100;
}

/**
 * Check if all pipe segments are compliant
 */
export function isSystemCompliant(results: Map<string, HydraulicOutput>): boolean {
  for (const result of results.values()) {
    if (!result.compliant) {
      return false;
    }
  }
  return true;
}

/**
 * Get all notes from calculation results
 */
export function getAllNotes(results: Map<string, HydraulicOutput>): string[] {
  const notes: string[] = [];
  results.forEach((result, id) => {
    result.notes.forEach((note) => {
      notes.push(`[${id}] ${note}`);
    });
  });
  return notes;
}

// === Hazard Class Helpers ===

export const HAZARD_CLASSES: { value: HazardClass; label: string; description: string }[] = [
  { value: 'light', label: 'Light Hazard', description: 'Offices, churches, hospitals' },
  { value: 'ordinary_1', label: 'Ordinary Hazard I', description: 'Parking garages, restaurants' },
  { value: 'ordinary_2', label: 'Ordinary Hazard II', description: 'Machine shops, warehouses' },
  { value: 'extra_1', label: 'Extra Hazard I', description: 'Printing, woodworking' },
  { value: 'extra_2', label: 'Extra Hazard II', description: 'Flammable liquids, plastics' },
];

// === Pipe Size Helpers ===

export const PIPE_SIZES = [
  { nominal: '3/4"', value: 0.75 },
  { nominal: '1"', value: 1 },
  { nominal: '1-1/4"', value: 1.25 },
  { nominal: '1-1/2"', value: 1.5 },
  { nominal: '2"', value: 2 },
  { nominal: '2-1/2"', value: 2.5 },
  { nominal: '3"', value: 3 },
  { nominal: '4"', value: 4 },
  { nominal: '6"', value: 6 },
  { nominal: '8"', value: 8 },
];

export const C_FACTORS = [
  { value: 150, label: '150 - CPVC / HDPE' },
  { value: 140, label: '140 - Copper / Stainless' },
  { value: 120, label: '120 - New Steel / Galvanized' },
  { value: 110, label: '110 - Steel (10 years)' },
  { value: 100, label: '100 - Steel (15 years)' },
  { value: 80, label: '80 - Old Steel' },
];

// === Unit Conversion Functions ===

/** Convert pipe diameter from metric (mm) to imperial (inches) */
export function mmToInches(mm: number): number {
  return Math.round((mm / 25.4) * 1000) / 1000;
}

/** Convert pipe diameter from imperial (inches) to metric (mm) */
export function inchesToMm(inches: number): number {
  return Math.round(inches * 25.4 * 10) / 10;
}

/** Convert flow rate from L/min to GPM */
export function lpmToGpm(lpm: number): number {
  return Math.round((lpm * 0.264172) * 100) / 100;
}

/** Convert flow rate from GPM to L/min */
export function gpmToLpm(gpm: number): number {
  return Math.round((gpm / 0.264172) * 100) / 100;
}

/** Convert length from meters to feet */
export function metersToFeet(meters: number): number {
  return Math.round((meters * 3.28084) * 100) / 100;
}

/** Convert length from feet to meters */
export function feetToMeters(feet: number): number {
  return Math.round((feet / 3.28084) * 100) / 100;
}

/** Convert pressure from bar to PSI */
export function barToPsi(bar: number): number {
  return Math.round((bar * 14.5038) * 100) / 100;
}

/** Convert pressure from PSI to bar */
export function psiToBar(psi: number): number {
  return Math.round((psi / 14.5038) * 100) / 100;
}
