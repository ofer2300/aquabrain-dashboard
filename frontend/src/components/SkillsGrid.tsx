"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Droplets,
  Building2,
  FileBarChart,
  Cog,
  Plus,
  Loader2,
  RefreshCw,
  Sparkles,
  Play,
  AlertCircle,
} from 'lucide-react';
import { SkillWizardModal } from './SkillWizardModal';

// ============================================================================
// TYPES
// ============================================================================

interface SkillMetadata {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  version: string;
  author: string;
  tags: string[];
}

interface SkillsGridProps {
  projectId?: string;
  onSkillRun?: (skillId: string) => void;
}

// ============================================================================
// ICON MAPPING
// ============================================================================

import { Flame, MessageCircle, Mail, Zap, GitBranch, Crown, FileEdit } from 'lucide-react';

const IconMap: Record<string, React.ElementType> = {
  Droplets,
  Building2,
  FileBarChart,
  Cog,
  Sparkles,
  Flame,
  MessageCircle,
  Mail,
  Zap,
  GitBranch,
  Crown,
  FileEdit,
};

// Special skill IDs that get fire/neon styling
const FIRE_SKILLS = ['skill_501_auto_sign', 'skill_501_declaration_auto_sign', '501'];

// Special skill IDs that get royal purple-gold styling
const ROYAL_SKILLS = ['skill_601_virtual_engineer', '601'];

// Special skill IDs that get email cockpit styling (blue-gold)
const EMAIL_COCKPIT_SKILLS = ['701', 'skill_701_email_cockpit'];

// Special skill IDs that get sump pit styling (cyan/water)
const SUMP_PIT_SKILLS = ['801', 'skill_801_sump_pit'];

// Special skill IDs that get DWG updater styling (amber/orange)
const DWG_UPDATER_SKILLS = ['802', 'skill_802_dwg_updater'];

// Special skill IDs that get AquaSkill Core styling (emerald green)
const AQUASKILL_CORE_SKILLS = ['901', 'skill_901_aquaskill_core'];

function getIcon(iconName: string): React.ElementType {
  return IconMap[iconName] || Cog;
}

// ============================================================================
// COMPONENT
// ============================================================================

export function SkillsGrid({ projectId, onSkillRun }: SkillsGridProps) {
  const [skills, setSkills] = useState<SkillMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [runningSkill, setRunningSkill] = useState<string | null>(null);

  // Fetch skills from API
  const fetchSkills = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/orchestrator/skills');

      if (!response.ok) {
        throw new Error('Failed to fetch skills');
      }

      const data = await response.json();
      setSkills(data.skills || []);
    } catch (err) {
      console.error('Error fetching skills:', err);
      setError('Failed to load skills');
      // Set some default skills for demo
      setSkills([
        {
          id: 'builtin_hydraulic',
          name: 'Hydraulic Calculator',
          description: 'Calculate pressure loss using Hazen-Williams',
          category: 'hydraulics',
          icon: 'Droplets',
          color: '#00E676',
          version: '1.0.0',
          author: 'AquaBrain',
          tags: ['hydraulic', 'calculation'],
        },
        {
          id: 'builtin_revit_extract',
          name: 'Revit Geometry Extractor',
          description: 'Extract geometry from Revit models',
          category: 'revit',
          icon: 'Building2',
          color: '#4FACFE',
          version: '1.0.0',
          author: 'AquaBrain',
          tags: ['revit', 'geometry'],
        },
        {
          id: 'builtin_report_gen',
          name: 'Report Generator',
          description: 'Generate engineering reports',
          category: 'reporting',
          icon: 'FileBarChart',
          color: '#BD00FF',
          version: '1.0.0',
          author: 'AquaBrain',
          tags: ['report', 'documentation'],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  // Handle skill creation
  const handleSkillCreated = (skill: any) => {
    // Refresh the skills list
    fetchSkills();
  };

  // Handle running a skill
  const handleRunSkill = async (skillId: string) => {
    setRunningSkill(skillId);

    try {
      // Call the orchestrator trigger endpoint
      const response = await fetch('http://localhost:8000/api/orchestrator/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: skillId,
          payload: projectId ? { project_id: projectId } : {},
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Skill executed:', result);
        onSkillRun?.(skillId);
      } else {
        console.error('Failed to run skill');
      }
    } catch (err) {
      console.error('Error running skill:', err);
    } finally {
      setRunningSkill(null);
    }
  };

  // Determine if skill is custom
  const isCustomSkill = (skill: SkillMetadata): boolean => {
    return skill.id.startsWith('custom_') || skill.author === 'Skill Factory';
  };

  // Determine if skill has fire styling (Skill #501)
  const isFireSkill = (skill: SkillMetadata): boolean => {
    return FIRE_SKILLS.includes(skill.id) || skill.icon === 'Flame';
  };

  // Determine if skill has royal styling (Skill #601)
  const isRoyalSkill = (skill: SkillMetadata): boolean => {
    return ROYAL_SKILLS.includes(skill.id) || skill.icon === 'Crown';
  };

  // Determine if skill has email cockpit styling (Skill #701)
  const isEmailCockpitSkill = (skill: SkillMetadata): boolean => {
    return EMAIL_COCKPIT_SKILLS.includes(skill.id) || skill.icon === 'Mail';
  };

  // Determine if skill has sump pit styling (Skill #801)
  const isSumpPitSkill = (skill: SkillMetadata): boolean => {
    return SUMP_PIT_SKILLS.includes(skill.id) || (skill.icon === 'Droplets' && skill.id.includes('801'));
  };

  // Determine if skill has DWG updater styling (Skill #802)
  const isDWGUpdaterSkill = (skill: SkillMetadata): boolean => {
    return DWG_UPDATER_SKILLS.includes(skill.id) || skill.icon === 'FileEdit';
  };

  // Determine if skill has AquaSkill Core styling (Skill #901)
  const isAquaSkillCoreSkill = (skill: SkillMetadata): boolean => {
    return AQUASKILL_CORE_SKILLS.includes(skill.id) || (skill.icon === 'Zap' && skill.id.includes('901'));
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h2 className="text-xl font-bold text-white">Skills Library</h2>
          <span className="text-xs text-white/40 glass rounded-full px-3 py-1">
            {skills.length} skills
          </span>
        </div>
        <button
          onClick={fetchSkills}
          disabled={isLoading}
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 text-white/60 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && skills.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      )}

      {/* Skills Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {skills.map((skill) => {
          const Icon = getIcon(skill.icon);
          const isCustom = isCustomSkill(skill);
          const isFire = isFireSkill(skill);
          const isRoyal = isRoyalSkill(skill);
          const isEmailCockpit = isEmailCockpitSkill(skill);
          const isSumpPit = isSumpPitSkill(skill);
          const isDWGUpdater = isDWGUpdaterSkill(skill);
          const isAquaSkillCore = isAquaSkillCoreSkill(skill);
          const isRunning = runningSkill === skill.id;

          // Fire skill special gradient
          const fireGradient = isFire
            ? 'bg-gradient-to-br from-red-500/20 via-orange-500/10 to-yellow-500/20 border-red-500/30'
            : '';

          // Royal skill special gradient (purple to gold)
          const royalGradient = isRoyal
            ? 'bg-gradient-to-br from-purple-600/30 via-purple-500/10 to-amber-500/20 border-purple-500/40'
            : '';

          // Email Cockpit special gradient (blue to gold)
          const emailCockpitGradient = isEmailCockpit
            ? 'bg-gradient-to-br from-blue-500/30 via-cyan-500/10 to-amber-400/20 border-blue-500/40'
            : '';

          // Sump Pit special gradient (cyan/water)
          const sumpPitGradient = isSumpPit
            ? 'bg-gradient-to-br from-cyan-500/30 via-sky-500/10 to-teal-400/20 border-cyan-500/40'
            : '';

          // DWG Updater special gradient (amber/orange)
          const dwgUpdaterGradient = isDWGUpdater
            ? 'bg-gradient-to-br from-amber-500/30 via-orange-500/10 to-yellow-400/20 border-amber-500/40'
            : '';

          // AquaSkill Core special gradient (emerald green)
          const aquaSkillCoreGradient = isAquaSkillCore
            ? 'bg-gradient-to-br from-emerald-500/30 via-green-500/10 to-teal-400/20 border-emerald-500/40'
            : '';

          return (
            <div
              key={skill.id}
              className={`
                glass-heavy rounded-2xl p-5 hover:scale-105 transition-all duration-300 group relative
                ${isFire ? fireGradient : ''}
                ${isRoyal ? royalGradient : ''}
                ${isEmailCockpit ? emailCockpitGradient : ''}
                ${isSumpPit ? sumpPitGradient : ''}
                ${isDWGUpdater ? dwgUpdaterGradient : ''}
                ${isAquaSkillCore ? aquaSkillCoreGradient : ''}
                ${isFire ? 'animate-pulse-slow' : ''}
              `}
              style={{
                boxShadow: isFire
                  ? '0 0 30px rgba(239, 68, 68, 0.4), 0 0 60px rgba(251, 146, 60, 0.2)'
                  : isRoyal
                  ? '0 0 40px rgba(147, 51, 234, 0.5), 0 0 80px rgba(251, 191, 36, 0.3)'
                  : isEmailCockpit
                  ? '0 0 40px rgba(30, 144, 255, 0.5), 0 0 80px rgba(251, 191, 36, 0.2)'
                  : isSumpPit
                  ? '0 0 40px rgba(14, 165, 233, 0.5), 0 0 80px rgba(20, 184, 166, 0.3)'
                  : isDWGUpdater
                  ? '0 0 40px rgba(245, 158, 11, 0.5), 0 0 80px rgba(249, 115, 22, 0.3)'
                  : isAquaSkillCore
                  ? '0 0 40px rgba(16, 185, 129, 0.5), 0 0 80px rgba(20, 184, 166, 0.3)'
                  : `0 0 20px ${skill.color}20`,
              }}
            >
              {/* Custom Badge */}
              {isCustom && (
                <div className="absolute top-2 right-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">
                    Custom
                  </span>
                </div>
              )}

              {/* Fire Badge for Skill #501 */}
              {isFire && (
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-red-500 to-yellow-500 text-white font-bold animate-pulse">
                    🔥 #501
                  </span>
                </div>
              )}

              {/* Royal Badge for Skill #601 */}
              {isRoyal && (
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-purple-600 to-amber-500 text-white font-bold">
                    👑 #601
                  </span>
                </div>
              )}

              {/* Email Cockpit Badge for Skill #701 */}
              {isEmailCockpit && (
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-blue-500 to-amber-400 text-white font-bold">
                    ✉️ #701
                  </span>
                </div>
              )}

              {/* Sump Pit Badge for Skill #801 */}
              {isSumpPit && (
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-cyan-500 to-teal-400 text-white font-bold">
                    💧 #801
                  </span>
                </div>
              )}

              {/* DWG Updater Badge for Skill #802 */}
              {isDWGUpdater && (
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white font-bold">
                    📐 #802
                  </span>
                </div>
              )}

              {/* AquaSkill Core Badge for Skill #901 */}
              {isAquaSkillCore && (
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 text-white font-bold">
                    ⚡ #901
                  </span>
                </div>
              )}

              <div className="flex flex-col items-center gap-3">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform"
                  style={{ backgroundColor: `${skill.color}30` }}
                >
                  <span style={{ color: skill.color }}>
                    <Icon className="w-6 h-6" />
                  </span>
                </div>
                <span className="text-sm text-white/80 text-center line-clamp-2">
                  {skill.name}
                </span>
                <p className="text-xs text-white/40 text-center line-clamp-2">
                  {skill.description}
                </p>

                {/* Run Button */}
                <button
                  onClick={() => handleRunSkill(skill.id)}
                  disabled={isRunning}
                  className="
                    mt-2 px-3 py-1.5 rounded-lg text-xs font-medium
                    bg-white/5 border border-white/10 text-white/70
                    hover:bg-white/10 hover:text-white transition-all
                    disabled:opacity-50 disabled:cursor-not-allowed
                    flex items-center gap-1.5
                  "
                >
                  {isRunning ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3" />
                      Run
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}

        {/* Create New Skill Card */}
        <button
          onClick={() => setIsWizardOpen(true)}
          className="
            glass-heavy rounded-2xl p-5 hover:glow-ai transition-all duration-300 group
            border-2 border-dashed border-white/20 hover:border-purple-500/50
            flex flex-col items-center justify-center gap-3 min-h-[180px]
          "
        >
          <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
            <Plus className="w-6 h-6 text-purple-400" />
          </div>
          <span className="text-sm text-white/60 group-hover:text-purple-300 transition-colors">
            Create New Skill
          </span>
          <span className="text-xs text-white/40">
            Powered by AI
          </span>
        </button>
      </div>

      {/* Skill Wizard Modal */}
      <SkillWizardModal
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onSkillCreated={handleSkillCreated}
      />
    </div>
  );
}

export default SkillsGrid;
