/**
 * AquaBrain API Service
 * Handles all communication with the FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// === Types ===
export interface SystemStatus {
  system: string;
  status: string;
  ai_engine: string;
  timestamp: string;
  uptime_seconds?: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai' | 'system';
  text: string;
  timestamp: string;
}

export interface ChatResponse {
  message: string;
  analysis?: string;
  confidence?: number;
  timestamp: string;
}

export interface ClashData {
  clash_id: string;
  clash_type: 'pipe_duct' | 'pipe_pipe' | 'duct_structure' | 'electrical_pipe' | 'generic';
  severity: 'low' | 'medium' | 'high' | 'critical';
  element_a: string;
  element_b: string;
  location?: string;
  distance_mm?: number;
}

export interface ClashResolution {
  clash_id: string;
  resolution: string;
  confidence: number;
  suggested_action: string;
  elements_involved?: string;
  location?: string;
}

// === API Functions ===

/**
 * Get system status
 */
export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE_URL}/api/status`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * Send a chat message and get AI response
 */
export async function sendChatMessage(message: string, context?: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, context }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * Resolve a clash
 */
export async function resolveClash(clashData: ClashData): Promise<ClashResolution> {
  const response = await fetch(`${API_BASE_URL}/api/clash/resolve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(clashData),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}
