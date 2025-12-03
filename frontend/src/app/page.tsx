"use client";

import { useState } from "react";
import { DashboardShell } from "@/components/DashboardShell";
import { SmartResolutionCard } from "@/components/SmartResolutionCard";
import { SkillWizardModal } from "@/components/SkillWizardModal";
import {
  AlertTriangle,
  CheckCircle2,
  Brain,
  Zap,
  TrendingUp,
  Clock,
  Activity,
  Plus,
  Droplets,
  Building2,
  FileBarChart,
  Cog,
  Wand2,
} from "lucide-react";

// Built-in skills data
const BUILTIN_SKILLS = [
  { id: 'builtin_hydraulic', name: 'חישוב הידראולי', icon: 'Droplets', color: '#00E676' },
  { id: 'builtin_revit_extract', name: 'שליפת Revit', icon: 'Building2', color: '#4FACFE' },
  { id: 'builtin_report_gen', name: 'יצירת דוחות', icon: 'FileBarChart', color: '#BD00FF' },
];

export default function Home() {
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [customSkills, setCustomSkills] = useState<Array<{id: string; name: string; icon: string; color: string}>>([]);

  const handleSkillCreated = (skill: any) => {
    setCustomSkills(prev => [...prev, {
      id: skill.skill_id,
      name: skill.name,
      icon: skill.icon,
      color: skill.color,
    }]);
  };

  // נתוני דוגמה לפתרון התנגשות
  const sampleResolution = {
    id: "CLH-1247",
    title: "הסטת צינור HVAC מערבה",
    description: "הזזת צינור האוורור ב-15 ס\"מ מערבה תפתור את ההתנגשות עם קו המים הראשי ללא פגיעה בביצועי המערכת.",
    confidence: 94,
    standard: "NFPA 13",
    timeToResolve: "5 דק'",
  };

  return (
    <DashboardShell>
      <div className="space-y-8">
        {/* ===== HEADER ===== */}
        <header className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              לוח בקרה הנדסי
              <span className="text-gradient-ai mr-2">(AquaBrain)</span>
            </h1>
            <p className="text-white/50">מערכת AI לזיהוי וניהול התנגשויות MEP</p>
          </div>
          <div className="flex items-center gap-3 glass-heavy rounded-full px-4 py-2">
            <div className="status-dot live" />
            <span className="text-status-success text-sm font-medium">מערכת פעילה</span>
          </div>
        </header>

        {/* ===== KPI CARDS GRID ===== */}
        <section className="grid grid-cols-4 gap-4">
          <KPICard
            icon={AlertTriangle}
            label="התנגשויות פתוחות"
            value="127"
            change="-12%"
            trend="down"
            accentColor="critical"
          />
          <KPICard
            icon={CheckCircle2}
            label="נפתרו היום"
            value="34"
            change="+8%"
            trend="up"
            accentColor="success"
          />
          <KPICard
            icon={Brain}
            label="פעילות AI"
            value="89"
            change="+23%"
            trend="up"
            accentColor="ai"
          />
          <KPICard
            icon={Zap}
            label="זמן תגובה ממוצע"
            value="2.3s"
            change="-15%"
            trend="down"
            accentColor="warning"
          />
        </section>

        {/* ===== MAIN CONTENT ===== */}
        <section className="grid grid-cols-2 gap-6">
          {/* Smart Resolution Card - Center Stage */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="status-dot ai" />
              <h2 className="text-xl font-bold">פתרון התנגשות פעיל</h2>
              <span className="text-xs text-white/40 glass rounded-full px-3 py-1">Live Demo</span>
            </div>
            <SmartResolutionCard
              resolution={sampleResolution}
              initialState="detecting"
              autoProgress={true}
              onApprove={(id) => console.log('Approved:', id)}
              onReject={(id) => console.log('Rejected:', id)}
            />
          </div>

          {/* Recent Activity */}
          <div className="glass-heavy rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-status-ai" />
                <h2 className="text-xl font-bold">פעילות אחרונה</h2>
              </div>
              <span className="text-xs text-white/40">עודכן לפני 30 שניות</span>
            </div>

            <div className="space-y-3">
              <ActivityItem
                status="completed"
                title="CLH-1245 נפתר בהצלחה"
                time="לפני 2 דקות"
                detail="הסטת צינור ניקוז"
              />
              <ActivityItem
                status="in_progress"
                title="CLH-1247 בעיבוד AI"
                time="עכשיו"
                detail="ניתוח התנגשות HVAC"
              />
              <ActivityItem
                status="pending"
                title="CLH-1248 ממתין לסריקה"
                time="בתור"
                detail="קומה 15, גריד D-2"
              />
              <ActivityItem
                status="completed"
                title="בדיקת תאימות NFPA 13"
                time="לפני 5 דקות"
                detail="כל הבדיקות עברו"
              />
            </div>
          </div>
        </section>

        {/* ===== BOTTOM STATS ===== */}
        <section className="grid grid-cols-3 gap-6">
          {/* Performance Metrics */}
          <div className="glass-heavy rounded-2xl p-6 col-span-2 space-y-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-status-success" />
              <h2 className="text-lg font-bold">מדדי ביצועים</h2>
            </div>
            <div className="grid grid-cols-4 gap-4">
              <MetricCard label="דיוק AI" value="94%" color="ai" />
              <MetricCard label="זמן פתרון ממוצע" value="4.2 דק'" color="success" />
              <MetricCard label="עמידה בתקנים" value="100%" color="success" />
              <MetricCard label="התנגשויות/שעה" value="12" color="warning" />
            </div>
          </div>

          {/* Quick Stats */}
          <div className="glass-heavy rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-status-warning" />
              <h2 className="text-lg font-bold">סטטוס מערכת</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-white/60">זמן פעולה</span>
                <span className="font-mono text-status-success">99.9%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60">מודלים נטענו</span>
                <span className="font-mono">3/3</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60">גרסת AI</span>
                <span className="font-mono text-status-ai">v3.0</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60">עדכון אחרון</span>
                <span className="font-mono text-white/40">היום, 14:30</span>
              </div>
            </div>
          </div>
        </section>

        {/* ===== SKILL FACTORY ===== */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Wand2 className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-bold">Skill Factory</h2>
              <span className="text-xs text-white/40 glass rounded-full px-3 py-1">AI Powered</span>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-4">
            {/* Built-in Skills */}
            {BUILTIN_SKILLS.map((skill) => (
              <SkillCard key={skill.id} skill={skill} />
            ))}

            {/* Custom Skills */}
            {customSkills.map((skill) => (
              <SkillCard key={skill.id} skill={skill} isCustom />
            ))}

            {/* Create New Skill Card */}
            <button
              onClick={() => setIsWizardOpen(true)}
              className="glass-heavy rounded-2xl p-5 hover:glow-ai transition-all duration-300 group border-2 border-dashed border-white/20 hover:border-purple-500/50 flex flex-col items-center justify-center gap-3 min-h-[140px]"
            >
              <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Plus className="w-6 h-6 text-purple-400" />
              </div>
              <span className="text-sm text-white/60 group-hover:text-purple-300 transition-colors">
                צור Skill חדש
              </span>
            </button>
          </div>
        </section>
      </div>

      {/* Skill Wizard Modal */}
      <SkillWizardModal
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onSkillCreated={handleSkillCreated}
      />
    </DashboardShell>
  );
}

/* =============================================
   SKILL CARD COMPONENT
   ============================================= */

interface SkillCardProps {
  skill: { id: string; name: string; icon: string; color: string };
  isCustom?: boolean;
}

function SkillCard({ skill, isCustom }: SkillCardProps) {
  const IconComponent = () => {
    switch (skill.icon) {
      case 'Droplets': return <Droplets className="w-6 h-6" />;
      case 'Building2': return <Building2 className="w-6 h-6" />;
      case 'FileBarChart': return <FileBarChart className="w-6 h-6" />;
      default: return <Cog className="w-6 h-6" />;
    }
  };

  return (
    <div
      className="glass-heavy rounded-2xl p-5 hover:scale-105 transition-all duration-300 cursor-pointer group"
      style={{ boxShadow: `0 0 20px ${skill.color}20` }}
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform"
          style={{ backgroundColor: `${skill.color}30` }}
        >
          <span style={{ color: skill.color }}>
            <IconComponent />
          </span>
        </div>
        <span className="text-sm text-white/80 text-center">{skill.name}</span>
        {isCustom && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">
            Custom
          </span>
        )}
      </div>
    </div>
  );
}

/* =============================================
   SUB COMPONENTS
   ============================================= */

interface KPICardProps {
  icon: React.ElementType;
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  accentColor: 'ai' | 'success' | 'critical' | 'warning';
}

function KPICard({ icon: Icon, label, value, change, trend, accentColor }: KPICardProps) {
  const colorClasses = {
    ai: {
      bg: 'bg-status-ai/20',
      text: 'text-status-ai',
      glow: 'glow-ai',
    },
    success: {
      bg: 'bg-status-success/20',
      text: 'text-status-success',
      glow: 'glow-success',
    },
    critical: {
      bg: 'bg-status-critical/20',
      text: 'text-status-critical',
      glow: 'glow-critical',
    },
    warning: {
      bg: 'bg-status-warning/20',
      text: 'text-status-warning',
      glow: 'glow-warning',
    },
  };

  const colors = colorClasses[accentColor];
  const isPositive = trend === 'up' ? accentColor === 'success' || accentColor === 'ai' : accentColor === 'critical' || accentColor === 'success';

  return (
    <div className={`glass-heavy rounded-2xl p-5 hover:${colors.glow} transition-all duration-300 group`}>
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center group-hover:scale-110 transition-transform`}>
          <Icon className={`w-6 h-6 ${colors.text}`} />
        </div>
      </div>
      <p className="text-sm text-white/50 mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-bold ${colors.text}`}>{value}</span>
        <span className={`text-sm ${isPositive ? 'text-status-success' : 'text-status-critical'}`}>
          {change}
        </span>
      </div>
    </div>
  );
}

interface ActivityItemProps {
  status: 'completed' | 'in_progress' | 'pending';
  title: string;
  time: string;
  detail: string;
}

function ActivityItem({ status, title, time, detail }: ActivityItemProps) {
  const statusConfig = {
    completed: {
      dot: 'bg-status-success',
      text: 'text-status-success',
    },
    in_progress: {
      dot: 'bg-status-ai animate-pulse',
      text: 'text-status-ai',
    },
    pending: {
      dot: 'bg-white/30',
      text: 'text-white/40',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/10 transition-all">
      <div className={`w-2 h-2 rounded-full mt-2 ${config.dot}`} />
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium truncate ${status === 'pending' ? 'text-white/50' : 'text-white'}`}>
          {title}
        </p>
        <p className="text-xs text-white/40 truncate">{detail}</p>
      </div>
      <span className={`text-xs ${config.text} whitespace-nowrap`}>{time}</span>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  color: 'ai' | 'success' | 'warning';
}

function MetricCard({ label, value, color }: MetricCardProps) {
  const colorClasses = {
    ai: 'text-status-ai',
    success: 'text-status-success',
    warning: 'text-status-warning',
  };

  return (
    <div className="glass rounded-xl p-4 text-center">
      <p className="text-xs text-white/50 mb-2">{label}</p>
      <p className={`text-2xl font-bold font-mono ${colorClasses[color]}`}>{value}</p>
    </div>
  );
}
