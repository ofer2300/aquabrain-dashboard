'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { DashboardShell } from '@/components/DashboardShell';
import {
  Zap,
  Search,
  Plus,
  Play,
  Settings,
  Star,
  Clock,
  TrendingUp,
  Filter,
  Grid3X3,
  List,
  Building2,
  Droplets,
  FileText,
  MessageCircle,
  Mail,
  Cog,
  Sparkles,
  GitBranch,
  Workflow,
  ChevronRight,
  X,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  version: string;
  author: string;
  tags: string[];
  is_async: boolean;
  estimated_duration_sec: number | null;
  usage_count?: number;
  last_used?: string;
}

interface Pipeline {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  node_count: number;
  edge_count: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// ICON MAP
// ============================================================================

const iconMap: Record<string, React.ElementType> = {
  Building2,
  Droplets,
  FileText,
  MessageCircle,
  Mail,
  Cog,
  Zap,
  Sparkles,
  GitBranch,
  Workflow,
  Star,
  TrendingUp,
};

function getIcon(iconName: string): React.ElementType {
  return iconMap[iconName] || Cog;
}

// ============================================================================
// SKILL CARD
// ============================================================================

interface SkillCardProps {
  skill: Skill;
  onRun: (skill: Skill) => void;
  onSettings: (skill: Skill) => void;
}

function SkillCard({ skill, onRun, onSettings }: SkillCardProps) {
  const Icon = getIcon(skill.icon);

  return (
    <div
      className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl"
      style={{
        boxShadow: `0 4px 30px ${skill.color}20`,
      }}
    >
      {/* Glow effect */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{
          background: `radial-gradient(circle at 50% 0%, ${skill.color}30, transparent 70%)`,
        }}
      />

      {/* Content */}
      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg"
            style={{
              backgroundColor: skill.color,
              boxShadow: `0 4px 20px ${skill.color}50`,
            }}
          >
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div className="flex items-center gap-1">
            {skill.is_async && (
              <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-medium rounded-full">
                ASYNC
              </span>
            )}
            <span className="px-2 py-0.5 bg-white/10 text-slate-400 text-[10px] font-medium rounded-full uppercase">
              {skill.category}
            </span>
          </div>
        </div>

        {/* Title & Description */}
        <h3 className="text-white font-semibold text-lg mb-1 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-white group-hover:to-purple-300 transition-all">
          {skill.name}
        </h3>
        <p className="text-slate-400 text-sm line-clamp-2 mb-4">
          {skill.description}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-4">
          {skill.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-white/5 text-slate-500 text-xs rounded-full"
            >
              #{tag}
            </span>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-white/5">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>v{skill.version}</span>
            {skill.estimated_duration_sec && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {skill.estimated_duration_sec}s
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onSettings(skill)}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all"
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              onClick={() => onRun(skill)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-cyan-600 text-white text-sm font-medium hover:from-purple-500 hover:to-cyan-500 transition-all shadow-lg shadow-purple-500/20"
            >
              <Play className="w-3.5 h-3.5" />
              <span>הרץ</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// PIPELINE CARD
// ============================================================================

interface PipelineCardProps {
  pipeline: Pipeline;
  onRun: (pipeline: Pipeline) => void;
  onEdit: (pipeline: Pipeline) => void;
}

function PipelineCard({ pipeline, onRun, onEdit }: PipelineCardProps) {
  return (
    <div
      className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-900/30 to-cyan-900/30 backdrop-blur-xl border border-purple-500/20 hover:border-purple-500/40 transition-all duration-300 hover:scale-[1.02]"
    >
      <div className="relative p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-r from-purple-600 to-cyan-600 flex items-center justify-center">
            <GitBranch className="w-5 h-5 text-white" />
          </div>
          <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-[10px] font-medium rounded-full">
            PIPELINE
          </span>
        </div>

        <h3 className="text-white font-semibold mb-1">{pipeline.name}</h3>
        <p className="text-slate-400 text-sm line-clamp-2 mb-3">
          {pipeline.description}
        </p>

        <div className="flex items-center gap-3 text-xs text-slate-500 mb-4">
          <span>{pipeline.node_count} nodes</span>
          <span>{pipeline.edge_count} edges</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onEdit(pipeline)}
            className="flex-1 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white text-sm transition-all"
          >
            Edit
          </button>
          <button
            onClick={() => onRun(pipeline)}
            className="flex-1 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-cyan-600 text-white text-sm font-medium transition-all"
          >
            Execute
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// CATEGORY ROW (NETFLIX STYLE)
// ============================================================================

interface CategoryRowProps {
  title: string;
  icon: React.ElementType;
  skills: Skill[];
  onRunSkill: (skill: Skill) => void;
  onSettingsSkill: (skill: Skill) => void;
}

function CategoryRow({ title, icon: Icon, skills, onRunSkill, onSettingsSkill }: CategoryRowProps) {
  if (skills.length === 0) return null;

  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-5 h-5 text-purple-400" />
        <h2 className="text-white text-xl font-semibold">{title}</h2>
        <span className="text-slate-500 text-sm">({skills.length})</span>
        <ChevronRight className="w-4 h-4 text-slate-500 ml-auto" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {skills.map((skill) => (
          <SkillCard
            key={skill.id}
            skill={skill}
            onRun={onRunSkill}
            onSettings={onSettingsSkill}
          />
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// CREATE SKILL MODAL
// ============================================================================

interface CreateSkillModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (description: string) => void;
}

function CreateSkillModal({ isOpen, onClose, onSubmit }: CreateSkillModalProps) {
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setIsLoading(true);
    await onSubmit(description);
    setIsLoading(false);
    setDescription('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-2xl border border-white/10 w-full max-w-lg overflow-hidden">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-white font-semibold">יצירת Skill חדש</h3>
                <p className="text-slate-400 text-sm">תאר מה ה-Skill צריך לעשות</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/5 text-slate-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="לדוגמה: צור skill שמחשב שטח מלבן לפי רוחב וגובה..."
            className="w-full h-32 p-4 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder:text-slate-500 resize-none focus:outline-none focus:border-purple-500 transition-colors"
            dir="rtl"
          />

          <div className="flex justify-end gap-3 mt-4">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-white/5 text-white hover:bg-white/10 transition-colors"
            >
              ביטול
            </button>
            <button
              onClick={handleSubmit}
              disabled={!description.trim() || isLoading}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'יוצר...' : 'צור Skill'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN SKILLS PAGE
// ============================================================================

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch skills and pipelines
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch skills
        const skillsRes = await fetch('http://localhost:8000/api/skills');
        if (skillsRes.ok) {
          const skillsData = await skillsRes.json();
          setSkills(skillsData.skills || []);
        }

        // Fetch pipelines
        const pipelinesRes = await fetch('http://localhost:8000/api/pipelines');
        if (pipelinesRes.ok) {
          const pipelinesData = await pipelinesRes.json();
          setPipelines(pipelinesData.pipelines || []);
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
        // Use demo data if fetch fails
        setSkills([
          {
            id: 'builtin_revit_extract',
            name: 'Revit Extract',
            description: 'Extract geometry and metadata from Revit model',
            category: 'revit',
            icon: 'Building2',
            color: '#FF6B35',
            version: '1.0.0',
            author: 'AquaBrain',
            tags: ['revit', 'bim', 'extract'],
            is_async: true,
            estimated_duration_sec: 30,
          },
          {
            id: 'builtin_hydraulic',
            name: 'Hydraulic Calculator',
            description: 'Hazen-Williams hydraulic calculations for LOD 500',
            category: 'hydraulics',
            icon: 'Droplets',
            color: '#00BFFF',
            version: '1.0.0',
            author: 'AquaBrain',
            tags: ['hydraulics', 'nfpa13', 'calculation'],
            is_async: false,
            estimated_duration_sec: 5,
          },
          {
            id: 'builtin_report_gen',
            name: 'Report Generator',
            description: 'Generate PDF engineering reports',
            category: 'reporting',
            icon: 'FileText',
            color: '#00E676',
            version: '1.0.0',
            author: 'AquaBrain',
            tags: ['pdf', 'report', 'documentation'],
            is_async: false,
            estimated_duration_sec: 10,
          },
          {
            id: 'library_whatsapp_notify',
            name: 'WhatsApp Notify',
            description: 'Send WhatsApp notifications',
            category: 'integration',
            icon: 'MessageCircle',
            color: '#25D366',
            version: '1.0.0',
            author: 'AquaBrain',
            tags: ['whatsapp', 'notification', 'messaging'],
            is_async: false,
            estimated_duration_sec: 5,
          },
          {
            id: 'library_email_notify',
            name: 'Email Notify',
            description: 'Send email notifications with attachments',
            category: 'integration',
            icon: 'Mail',
            color: '#EA4335',
            version: '1.0.0',
            author: 'AquaBrain',
            tags: ['email', 'notification', 'smtp'],
            is_async: false,
            estimated_duration_sec: 10,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter skills
  const filteredSkills = useMemo(() => {
    let result = skills;

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.tags.some((t) => t.toLowerCase().includes(q))
      );
    }

    if (selectedCategory) {
      result = result.filter((s) => s.category === selectedCategory);
    }

    return result;
  }, [skills, searchQuery, selectedCategory]);

  // Group by category
  const skillsByCategory = useMemo(() => {
    const grouped: Record<string, Skill[]> = {};
    filteredSkills.forEach((skill) => {
      if (!grouped[skill.category]) {
        grouped[skill.category] = [];
      }
      grouped[skill.category].push(skill);
    });
    return grouped;
  }, [filteredSkills]);

  // Categories
  const categories = useMemo(() => {
    const cats = new Set(skills.map((s) => s.category));
    return Array.from(cats);
  }, [skills]);

  // Handlers
  const handleRunSkill = (skill: Skill) => {
    window.location.href = `/projects/demo?skill=${skill.id}`;
  };

  const handleSettingsSkill = (skill: Skill) => {
    console.log('Settings for skill:', skill.id);
  };

  const handleRunPipeline = (pipeline: Pipeline) => {
    console.log('Run pipeline:', pipeline.id);
  };

  const handleEditPipeline = (pipeline: Pipeline) => {
    window.location.href = `/pipelines/${pipeline.id}`;
  };

  const handleCreateSkill = async (description: string) => {
    try {
      const res = await fetch('http://localhost:8000/api/factory/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, use_llm: false }),
      });

      if (res.ok) {
        const newSkill = await res.json();
        console.log('Created skill:', newSkill);
        // Refresh skills list
        window.location.reload();
      }
    } catch (error) {
      console.error('Failed to create skill:', error);
    }
  };

  const categoryMeta: Record<string, { label: string; icon: React.ElementType }> = {
    revit: { label: 'Revit & BIM', icon: Building2 },
    hydraulics: { label: 'Hydraulics', icon: Droplets },
    reporting: { label: 'Reports & Documents', icon: FileText },
    integration: { label: 'Integrations', icon: MessageCircle },
    custom: { label: 'Custom Skills', icon: Cog },
    rpa: { label: 'RPA & Automation', icon: Workflow },
  };

  return (
    <DashboardShell>
      <div className="p-6 min-h-screen">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <Zap className="w-8 h-8 text-purple-400" />
              Skills Factory
            </h1>
            <p className="text-slate-400 mt-1">
              מפעל האוטומציות שלך • {skills.length} skills זמינים
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="חפש skills..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500 w-64"
                dir="rtl"
              />
            </div>

            {/* View Toggle */}
            <div className="flex items-center gap-1 p-1 bg-slate-800/50 rounded-lg border border-white/10">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-md transition-colors ${
                  viewMode === 'grid' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-md transition-colors ${
                  viewMode === 'list' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Create Button */}
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-medium rounded-xl hover:from-purple-500 hover:to-pink-500 transition-all shadow-lg shadow-purple-500/25"
            >
              <Plus className="w-4 h-4" />
              <span>צור Skill חדש</span>
            </button>
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap transition-all ${
              !selectedCategory
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white border border-white/10'
            }`}
          >
            הכל
          </button>
          {categories.map((cat) => {
            const meta = categoryMeta[cat] || { label: cat, icon: Cog };
            const Icon = meta.icon;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-all ${
                  selectedCategory === cat
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800/50 text-slate-400 hover:text-white border border-white/10'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{meta.label}</span>
              </button>
            );
          })}
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500" />
          </div>
        ) : (
          <>
            {/* Pipelines Section */}
            {pipelines.length > 0 && !selectedCategory && (
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <GitBranch className="w-5 h-5 text-purple-400" />
                  <h2 className="text-white text-xl font-semibold">Pipelines</h2>
                  <span className="text-slate-500 text-sm">({pipelines.length})</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {pipelines.map((pipeline) => (
                    <PipelineCard
                      key={pipeline.id}
                      pipeline={pipeline}
                      onRun={handleRunPipeline}
                      onEdit={handleEditPipeline}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Skills by Category (Netflix Style) */}
            {selectedCategory ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredSkills.map((skill) => (
                  <SkillCard
                    key={skill.id}
                    skill={skill}
                    onRun={handleRunSkill}
                    onSettings={handleSettingsSkill}
                  />
                ))}
              </div>
            ) : (
              Object.entries(skillsByCategory).map(([category, categorySkills]) => {
                const meta = categoryMeta[category] || { label: category, icon: Cog };
                return (
                  <CategoryRow
                    key={category}
                    title={meta.label}
                    icon={meta.icon}
                    skills={categorySkills}
                    onRunSkill={handleRunSkill}
                    onSettingsSkill={handleSettingsSkill}
                  />
                );
              })
            )}

            {/* Empty State */}
            {filteredSkills.length === 0 && (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <Zap className="w-16 h-16 text-slate-700 mb-4" />
                <h3 className="text-white text-xl font-semibold mb-2">
                  לא נמצאו Skills
                </h3>
                <p className="text-slate-400 mb-4">
                  נסה לחפש משהו אחר או צור Skill חדש
                </p>
                <button
                  onClick={() => setIsCreateModalOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span>צור Skill חדש</span>
                </button>
              </div>
            )}
          </>
        )}

        {/* Create Skill Modal */}
        <CreateSkillModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateSkill}
        />
      </div>
    </DashboardShell>
  );
}
