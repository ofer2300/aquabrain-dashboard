'use client';

import React, { useCallback, useState, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  BackgroundVariant,
  NodeTypes,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Play,
  Save,
  Plus,
  Trash2,
  Zap,
  GitBranch,
  Workflow,
  Check,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface SkillMeta {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
}

interface PipelineNodeData {
  skill: SkillMeta;
  inputs: Record<string, unknown>;
  inputMappings: Record<string, string>;
  status?: 'pending' | 'running' | 'success' | 'failed';
}

interface PipelineExecutionResult {
  run_id: string;
  status: string;
  progress_percent: number;
  node_results: Array<{
    node_id: string;
    status: string;
    output?: Record<string, unknown>;
    error?: string;
  }>;
  final_output?: Record<string, unknown>;
  error?: string;
}

// ============================================================================
// CUSTOM SKILL NODE
// ============================================================================

function SkillNode({ data, selected }: { data: PipelineNodeData; selected: boolean }) {
  const statusColors = {
    pending: 'border-slate-500',
    running: 'border-blue-500 animate-pulse',
    success: 'border-green-500',
    failed: 'border-red-500',
  };

  const statusIcons = {
    pending: null,
    running: <Loader2 className="w-4 h-4 animate-spin text-blue-400" />,
    success: <Check className="w-4 h-4 text-green-400" />,
    failed: <AlertTriangle className="w-4 h-4 text-red-400" />,
  };

  return (
    <div
      className={`
        relative px-4 py-3 rounded-xl border-2 transition-all duration-300
        ${selected ? 'ring-2 ring-purple-500/50 scale-105' : ''}
        ${data.status ? statusColors[data.status] : 'border-white/20'}
        bg-gradient-to-br from-slate-900/90 to-slate-800/90
        backdrop-blur-xl shadow-xl min-w-[180px]
      `}
      style={{
        boxShadow: `0 0 20px ${data.skill.color}40`,
      }}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-purple-500 !border-2 !border-purple-300"
      />

      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
          style={{ backgroundColor: data.skill.color }}
        >
          {data.skill.icon.charAt(0)}
        </div>
        <div className="flex-1">
          <div className="text-white font-medium text-sm truncate max-w-[120px]">
            {data.skill.name}
          </div>
          <div className="text-slate-400 text-xs truncate max-w-[120px]">
            {data.skill.category}
          </div>
        </div>
        {data.status && statusIcons[data.status]}
      </div>

      {/* Skill ID */}
      <div className="text-[10px] text-slate-500 font-mono">
        {data.skill.id}
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-cyan-500 !border-2 !border-cyan-300"
      />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  skillNode: SkillNode,
};

// ============================================================================
// AVAILABLE SKILLS PANEL
// ============================================================================

interface SkillsPanelProps {
  skills: SkillMeta[];
  onAddSkill: (skill: SkillMeta) => void;
}

function SkillsPanel({ skills, onAddSkill }: SkillsPanelProps) {
  const [search, setSearch] = useState('');

  const filteredSkills = useMemo(() => {
    if (!search) return skills;
    const q = search.toLowerCase();
    return skills.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.category.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q)
    );
  }, [skills, search]);

  const categories = useMemo(() => {
    const cats = new Set(skills.map((s) => s.category));
    return Array.from(cats);
  }, [skills]);

  return (
    <div className="absolute left-4 top-4 bottom-4 w-64 bg-slate-900/95 backdrop-blur-xl rounded-xl border border-white/10 overflow-hidden flex flex-col z-10">
      {/* Header */}
      <div className="p-3 border-b border-white/10">
        <div className="flex items-center gap-2 text-white font-medium mb-2">
          <Zap className="w-4 h-4 text-purple-400" />
          <span>Skills Library</span>
        </div>
        <input
          type="text"
          placeholder="חפש skill..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-2 bg-slate-800/50 border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-500 focus:outline-none focus:border-purple-500"
          dir="rtl"
        />
      </div>

      {/* Skills List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredSkills.map((skill) => (
          <button
            key={skill.id}
            onClick={() => onAddSkill(skill)}
            className="w-full p-2 rounded-lg hover:bg-white/5 transition-colors text-left group"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded flex items-center justify-center text-white text-xs font-bold"
                style={{ backgroundColor: skill.color }}
              >
                {skill.icon.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-white text-sm truncate">{skill.name}</div>
                <div className="text-slate-500 text-xs truncate">{skill.category}</div>
              </div>
              <Plus className="w-4 h-4 text-slate-500 group-hover:text-purple-400 transition-colors" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// MAIN PIPELINE BUILDER
// ============================================================================

interface SkillPipelineBuilderProps {
  initialNodes?: Node<PipelineNodeData>[];
  initialEdges?: Edge[];
  availableSkills?: SkillMeta[];
  onSave?: (nodes: Node<PipelineNodeData>[], edges: Edge[]) => void;
  onExecute?: (nodes: Node<PipelineNodeData>[], edges: Edge[]) => Promise<PipelineExecutionResult>;
}

export default function SkillPipelineBuilder({
  initialNodes = [],
  initialEdges = [],
  availableSkills = [],
  onSave,
  onExecute,
}: SkillPipelineBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<PipelineNodeData>>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<PipelineExecutionResult | null>(null);

  // Default skills for demo
  const defaultSkills: SkillMeta[] = availableSkills.length > 0 ? availableSkills : [
    { id: 'builtin_revit_extract', name: 'Revit Extract', description: 'Extract data from Revit', category: 'revit', icon: 'Building2', color: '#FF6B35' },
    { id: 'builtin_hydraulic', name: 'Hydraulic Calc', description: 'Hazen-Williams calculation', category: 'hydraulics', icon: 'Droplets', color: '#00BFFF' },
    { id: 'builtin_report_gen', name: 'Generate Report', description: 'Create PDF report', category: 'reporting', icon: 'FileText', color: '#00E676' },
    { id: 'library_whatsapp_notify', name: 'WhatsApp Notify', description: 'Send WhatsApp message', category: 'integration', icon: 'MessageCircle', color: '#25D366' },
    { id: 'library_email_notify', name: 'Email Notify', description: 'Send email', category: 'integration', icon: 'Mail', color: '#EA4335' },
  ];

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'smoothstep',
            animated: true,
            style: { stroke: '#BD00FF', strokeWidth: 2 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#BD00FF',
            },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const handleAddSkill = useCallback(
    (skill: SkillMeta) => {
      const newNode: Node<PipelineNodeData> = {
        id: `node_${Date.now()}`,
        type: 'skillNode',
        position: { x: 300 + nodes.length * 50, y: 200 + nodes.length * 30 },
        data: {
          skill,
          inputs: {},
          inputMappings: {},
          status: 'pending',
        },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [nodes, setNodes]
  );

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(nodes, edges);
    }
  }, [nodes, edges, onSave]);

  const handleExecute = useCallback(async () => {
    if (!onExecute) return;

    setIsExecuting(true);
    setExecutionResult(null);

    // Reset all node statuses
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, status: 'pending' as const },
      }))
    );

    try {
      const result = await onExecute(nodes, edges);
      setExecutionResult(result);

      // Update node statuses based on result
      setNodes((nds) =>
        nds.map((n) => {
          const nodeResult = result.node_results.find((r) => r.node_id === n.id);
          return {
            ...n,
            data: {
              ...n.data,
              status: nodeResult
                ? (nodeResult.status as 'pending' | 'running' | 'success' | 'failed')
                : 'pending',
            },
          };
        })
      );
    } catch (error) {
      console.error('Pipeline execution failed:', error);
    } finally {
      setIsExecuting(false);
    }
  }, [nodes, edges, onExecute, setNodes]);

  const handleClear = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setExecutionResult(null);
  }, [setNodes, setEdges]);

  return (
    <div className="w-full h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        className="bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950"
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#BD00FF', strokeWidth: 2 },
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#374151"
        />
        <Controls className="!bg-slate-900/90 !border-white/10 !rounded-xl" />
        <MiniMap
          className="!bg-slate-900/90 !border-white/10 !rounded-xl"
          nodeColor={(node) => {
            const data = node.data as PipelineNodeData;
            return data?.skill?.color || '#BD00FF';
          }}
        />

        {/* Top Panel - Pipeline Name & Actions */}
        <Panel position="top-center" className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-900/90 backdrop-blur-xl rounded-xl border border-white/10">
            <GitBranch className="w-5 h-5 text-purple-400" />
            <span className="text-white font-medium">Pipeline Builder</span>
            <span className="text-slate-500 text-sm ml-2">
              {nodes.length} nodes • {edges.length} connections
            </span>
          </div>
        </Panel>

        {/* Action Buttons */}
        <Panel position="top-right" className="flex items-center gap-2">
          <button
            onClick={handleClear}
            className="p-2 bg-slate-900/90 backdrop-blur-xl rounded-lg border border-white/10 text-slate-400 hover:text-red-400 hover:border-red-500/50 transition-all"
            title="Clear Pipeline"
          >
            <Trash2 className="w-5 h-5" />
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900/90 backdrop-blur-xl rounded-lg border border-white/10 text-white hover:border-purple-500/50 transition-all"
          >
            <Save className="w-4 h-4" />
            <span>Save</span>
          </button>
          <button
            onClick={handleExecute}
            disabled={isExecuting || nodes.length === 0}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
              ${isExecuting
                ? 'bg-purple-500/50 text-white/50 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-600 to-cyan-600 text-white hover:from-purple-500 hover:to-cyan-500 shadow-lg shadow-purple-500/25'
              }
            `}
          >
            {isExecuting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Execute</span>
              </>
            )}
          </button>
        </Panel>

        {/* Execution Result Panel */}
        {executionResult && (
          <Panel position="bottom-center">
            <div className={`
              px-4 py-2 rounded-xl backdrop-blur-xl border
              ${executionResult.status === 'completed'
                ? 'bg-green-900/90 border-green-500/50 text-green-200'
                : executionResult.status === 'failed'
                ? 'bg-red-900/90 border-red-500/50 text-red-200'
                : 'bg-slate-900/90 border-white/10 text-white'
              }
            `}>
              <div className="flex items-center gap-2">
                {executionResult.status === 'completed' ? (
                  <Check className="w-4 h-4" />
                ) : executionResult.status === 'failed' ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : (
                  <Workflow className="w-4 h-4" />
                )}
                <span>
                  Pipeline {executionResult.status} • {executionResult.progress_percent.toFixed(0)}%
                </span>
                {executionResult.error && (
                  <span className="text-red-300 text-sm ml-2">
                    {executionResult.error}
                  </span>
                )}
              </div>
            </div>
          </Panel>
        )}
      </ReactFlow>

      {/* Skills Panel */}
      <SkillsPanel skills={defaultSkills} onAddSkill={handleAddSkill} />
    </div>
  );
}
