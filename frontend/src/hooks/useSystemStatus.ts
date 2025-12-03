"use client";

import { useState, useEffect, useCallback } from 'react';

interface SystemStatus {
  system: string;
  status: string;
  ai_engine: string;
  timestamp: string;
  uptime_seconds?: number;
}

interface UseSystemStatusReturn {
  status: SystemStatus | null;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_INTERVAL = 5000; // 5 seconds

export function useSystemStatus(): UseSystemStatusReturn {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: SystemStatus = await response.json();
      setStatus(data);
      setIsConnected(true);
      setError(null);
    } catch (err) {
      setIsConnected(false);
      setError(err instanceof Error ? err.message : 'Connection failed');
      setStatus(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchStatus();

    // Set up polling every 5 seconds
    const intervalId = setInterval(fetchStatus, POLL_INTERVAL);

    // Cleanup on unmount
    return () => clearInterval(intervalId);
  }, [fetchStatus]);

  return {
    status,
    isConnected,
    isLoading,
    error,
    refetch: fetchStatus,
  };
}
