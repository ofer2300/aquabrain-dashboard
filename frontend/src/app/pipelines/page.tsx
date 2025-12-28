'use client';

import React, { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { DashboardShell } from '@/components/DashboardShell';
import { Node, Edge } from '@xyflow/react';

// Dynamic import to avoid SSR issues with react-flow
const SkillPipelineBuilder = dynamic(
  () => import('@/components/SkillPipelineBuilder'),
  { ssr: false }
);

interface PipelineNodeData extends Record<string, unknown> {
  skill: {
    id: string;
    name: string;
    description: string;
    category: string;
    icon: string;
    color: string;
  };
  inputs: Record<string, unknown>;
  inputMappings: Record<string, string>;
  status?: 'pending' | 'running' | 'success' | 'failed';
}

export default function PipelinesPage() {
  const [savedPipelines, setSavedPipelines] = useState<Array<{
    id: string;
    name: string;
    nodes: Node<PipelineNodeData>[];
    edges: Edge[];
  }>>([]);

  const handleSave = useCallback((nodes: Node<PipelineNodeData>[], edges: Edge[]) => {
    const pipelineData = {
      name: `Pipeline ${Date.now()}`,
      description: 'Custom engineering pipeline',
      nodes: nodes.map((n) => ({
        id: n.id,
        skill_id: n.data.skill.id,
        inputs: n.data.inputs,
        input_mappings: n.data.inputMappings,
        position: n.position,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle,
        target_handle: e.targetHandle,
      })),
    };

    // Save to backend
    fetch('http://localhost:8000/api/pipelines', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pipelineData),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log('Pipeline saved:', data);
        alert('Pipeline saved successfully!');
      })
      .catch((err) => {
        console.error('Failed to save pipeline:', err);
        alert('Failed to save pipeline');
      });
  }, []);

  const handleExecute = useCallback(async (nodes: Node<PipelineNodeData>[], edges: Edge[]) => {
    const pipelineData = {
      name: 'Inline Pipeline',
      description: 'Executing inline',
      nodes: nodes.map((n) => ({
        id: n.id,
        skill_id: n.data.skill.id,
        inputs: n.data.inputs,
        input_mappings: n.data.inputMappings,
        position: n.position,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle,
        target_handle: e.targetHandle,
      })),
    };

    const response = await fetch('http://localhost:8000/api/pipelines/execute-inline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pipelineData),
    });

    return response.json();
  }, []);

  return (
    <DashboardShell>
      <div className="h-[calc(100vh-64px)]">
        <SkillPipelineBuilder
          onSave={handleSave}
          onExecute={handleExecute}
        />
      </div>
    </DashboardShell>
  );
}
