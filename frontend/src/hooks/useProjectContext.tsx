"use client";

/**
 * AquaBrain Project Context - Total Memory System
 * ================================================
 * Provides persistent state across page navigation and browser sessions.
 * All project-related data survives page reloads and tab switches.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";

// ============================================================================
// TYPES
// ============================================================================

export type RevitVersion = "auto" | "2024" | "2025" | "2026";
export type HazardClass = "light" | "ordinary_1" | "ordinary_2" | "extra_1" | "extra_2";

export interface ProjectState {
  projectId: string;
  projectName: string;
  notes: string;
  revitVersion: RevitVersion;
  hazardClass: HazardClass;
  lastRunId: string | null;
  lastUpdated: string | null;
}

export interface ProjectContextType extends ProjectState {
  // Setters
  setProjectId: (id: string) => void;
  setProjectName: (name: string) => void;
  setNotes: (notes: string) => void;
  setRevitVersion: (version: RevitVersion) => void;
  setHazardClass: (hazard: HazardClass) => void;
  setLastRunId: (runId: string | null) => void;

  // Bulk operations
  updateProject: (updates: Partial<ProjectState>) => void;
  clearProject: () => void;

  // Status
  isHydrated: boolean;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const STORAGE_KEY = "aquabrain_project_state";

const DEFAULT_STATE: ProjectState = {
  projectId: "",
  projectName: "",
  notes: "",
  revitVersion: "auto",
  hazardClass: "ordinary_1",
  lastRunId: null,
  lastUpdated: null,
};

// ============================================================================
// CONTEXT
// ============================================================================

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

// ============================================================================
// PROVIDER
// ============================================================================

interface ProjectProviderProps {
  children: ReactNode;
}

export function ProjectProvider({ children }: ProjectProviderProps) {
  const [state, setState] = useState<ProjectState>(DEFAULT_STATE);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as ProjectState;
        setState(parsed);
        console.log("[ProjectContext] Loaded state from localStorage:", parsed.projectId || "(empty)");
      }
    } catch (error) {
      console.warn("[ProjectContext] Failed to load from localStorage:", error);
    }
    setIsHydrated(true);
  }, []);

  // Save to localStorage on state change
  useEffect(() => {
    if (!isHydrated) return;

    try {
      const toSave = {
        ...state,
        lastUpdated: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch (error) {
      console.warn("[ProjectContext] Failed to save to localStorage:", error);
    }
  }, [state, isHydrated]);

  // Individual setters
  const setProjectId = useCallback((projectId: string) => {
    setState((prev) => ({ ...prev, projectId }));
  }, []);

  const setProjectName = useCallback((projectName: string) => {
    setState((prev) => ({ ...prev, projectName }));
  }, []);

  const setNotes = useCallback((notes: string) => {
    setState((prev) => ({ ...prev, notes }));
  }, []);

  const setRevitVersion = useCallback((revitVersion: RevitVersion) => {
    setState((prev) => ({ ...prev, revitVersion }));
  }, []);

  const setHazardClass = useCallback((hazardClass: HazardClass) => {
    setState((prev) => ({ ...prev, hazardClass }));
  }, []);

  const setLastRunId = useCallback((lastRunId: string | null) => {
    setState((prev) => ({ ...prev, lastRunId }));
  }, []);

  // Bulk update
  const updateProject = useCallback((updates: Partial<ProjectState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  // Clear all
  const clearProject = useCallback(() => {
    setState(DEFAULT_STATE);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.warn("[ProjectContext] Failed to clear localStorage:", error);
    }
  }, []);

  const value: ProjectContextType = {
    ...state,
    setProjectId,
    setProjectName,
    setNotes,
    setRevitVersion,
    setHazardClass,
    setLastRunId,
    updateProject,
    clearProject,
    isHydrated,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

// ============================================================================
// HOOK
// ============================================================================

export function useProjectContext(): ProjectContextType {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error("useProjectContext must be used within a ProjectProvider");
  }
  return context;
}

// ============================================================================
// UTILITY HOOK - For components that don't need full context
// ============================================================================

export function useProjectId(): [string, (id: string) => void] {
  const { projectId, setProjectId } = useProjectContext();
  return [projectId, setProjectId];
}

export function useProjectNotes(): [string, (notes: string) => void] {
  const { notes, setNotes } = useProjectContext();
  return [notes, setNotes];
}

export default ProjectProvider;
