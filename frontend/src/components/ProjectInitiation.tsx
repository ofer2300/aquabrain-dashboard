"use client";

import React, { useState, useCallback } from 'react';
import {
  Upload,
  FileText,
  Rocket,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Zap
} from 'lucide-react';

interface UploadedFile {
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

interface ProjectInitiationProps {
  onProjectStarted?: (projectId: string) => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function ProjectInitiation({ onProjectStarted }: ProjectInitiationProps) {
  const [projectName, setProjectName] = useState('');
  const [projectId, setProjectId] = useState<string | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isIgniting, setIsIgniting] = useState(false);
  const [ignited, setIgnited] = useState(false);

  // Create project
  const createProject = async () => {
    if (!projectName.trim()) return;

    setIsCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName }),
      });
      const data = await res.json();
      if (data.success) {
        setProjectId(data.project_id);
      }
    } catch (err) {
      console.error('Failed to create project:', err);
    } finally {
      setIsCreating(false);
    }
  };

  // Handle file drop
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (!projectId) return;

    const droppedFiles = Array.from(e.dataTransfer.files);
    const newFiles: UploadedFile[] = droppedFiles.map(f => ({
      name: f.name,
      size: f.size,
      status: 'pending' as const,
    }));

    setFiles(prev => [...prev, ...newFiles]);

    // Upload each file
    for (let i = 0; i < droppedFiles.length; i++) {
      const file = droppedFiles[i];
      const fileIndex = files.length + i;

      setFiles(prev => prev.map((f, idx) =>
        idx === fileIndex ? { ...f, status: 'uploading' } : f
      ));

      try {
        const content = await file.arrayBuffer();
        const base64 = btoa(
          new Uint8Array(content).reduce((data, byte) => data + String.fromCharCode(byte), '')
        );

        const res = await fetch(`${API_BASE}/api/projects/${projectId}/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            content_base64: base64,
          }),
        });

        if (res.ok) {
          setFiles(prev => prev.map((f, idx) =>
            idx === fileIndex ? { ...f, status: 'success' } : f
          ));
        } else {
          const err = await res.json();
          setFiles(prev => prev.map((f, idx) =>
            idx === fileIndex ? { ...f, status: 'error', error: err.detail } : f
          ));
        }
      } catch (err) {
        setFiles(prev => prev.map((f, idx) =>
          idx === fileIndex ? { ...f, status: 'error', error: 'Upload failed' } : f
        ));
      }
    }
  }, [projectId, files.length]);

  // IGNITE - Start pipeline
  const handleIgnite = async () => {
    if (!projectId) return;

    setIsIgniting(true);
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/start`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        setIgnited(true);
        onProjectStarted?.(projectId);
      }
    } catch (err) {
      console.error('Failed to ignite:', err);
    } finally {
      setIsIgniting(false);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const successfulUploads = files.filter(f => f.status === 'success').length;
  const canIgnite = successfulUploads > 0 && !ignited;

  // Stage 1: Project Name
  if (!projectId) {
    return (
      <div className="glass-panel p-8 max-w-xl mx-auto space-y-6">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-status-ai/20 flex items-center justify-center mb-4 glow-ai">
            <Rocket className="w-8 h-8 text-status-ai" />
          </div>
          <h2 className="text-2xl font-bold text-text-primary mb-2">New Project</h2>
          <p className="text-text-secondary">Initialize your engineering cockpit</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-2">Project Name</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Enter project name..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-text-primary
                       focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30"
            />
          </div>

          <button
            onClick={createProject}
            disabled={!projectName.trim() || isCreating}
            className="w-full bg-status-ai/20 hover:bg-status-ai/30 border border-status-ai/50
                     text-status-ai rounded-xl px-6 py-4 font-semibold transition-all
                     flex items-center justify-center gap-2 glow-ai
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Zap className="w-5 h-5" />
                Initialize Cockpit
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Stage 2: File Upload + IGNITE
  return (
    <div className="glass-panel p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">{projectName}</h2>
          <p className="text-sm text-text-secondary font-mono">{projectId}</p>
        </div>
        <div className="px-3 py-1 rounded-full bg-status-success/20 text-status-success text-sm">
          Ready
        </div>
      </div>

      {/* Dropzone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer
          ${isDragging
            ? 'border-status-ai bg-status-ai/10 glow-ai'
            : 'border-white/20 hover:border-white/40 hover:bg-white/5'
          }
          ${ignited ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <Upload className={`w-12 h-12 mx-auto mb-4 ${isDragging ? 'text-status-ai' : 'text-text-secondary'}`} />
        <p className="text-lg font-semibold text-text-primary mb-1">
          {isDragging ? 'Drop files here' : 'Drag & Drop Plans'}
        </p>
        <p className="text-sm text-text-secondary">
          Supports: DWG, PDF, RVT, IFC, DXF (max 500MB)
        </p>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-text-secondary">Uploaded Files</h3>
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-3 bg-white/5 rounded-xl p-3 border border-white/10"
            >
              <FileText className="w-5 h-5 text-text-secondary" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary truncate">{file.name}</p>
                <p className="text-xs text-text-secondary">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              {file.status === 'uploading' && (
                <Loader2 className="w-5 h-5 text-status-ai animate-spin" />
              )}
              {file.status === 'success' && (
                <CheckCircle2 className="w-5 h-5 text-status-success" />
              )}
              {file.status === 'error' && (
                <AlertCircle className="w-5 h-5 text-status-error" title={file.error} />
              )}
              {!ignited && file.status !== 'uploading' && (
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 hover:bg-white/10 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4 text-text-secondary" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* IGNITE Button */}
      <button
        onClick={handleIgnite}
        disabled={!canIgnite || isIgniting}
        className={`
          w-full rounded-2xl px-8 py-6 font-bold text-xl transition-all
          flex items-center justify-center gap-3
          ${canIgnite
            ? 'bg-gradient-to-r from-status-success to-emerald-500 text-white glow-success hover:scale-[1.02]'
            : ignited
              ? 'bg-status-success/20 text-status-success border border-status-success/50'
              : 'bg-white/5 text-text-secondary border border-white/10 cursor-not-allowed'
          }
        `}
      >
        {isIgniting ? (
          <>
            <Loader2 className="w-6 h-6 animate-spin" />
            IGNITING...
          </>
        ) : ignited ? (
          <>
            <CheckCircle2 className="w-6 h-6" />
            PIPELINE ACTIVE
          </>
        ) : (
          <>
            <Rocket className="w-6 h-6" />
            🚀 IGNITE ENGINE
          </>
        )}
      </button>

      {ignited && (
        <p className="text-center text-status-success text-sm animate-pulse">
          Processing pipeline initiated. Monitor progress on the dashboard.
        </p>
      )}
    </div>
  );
}
