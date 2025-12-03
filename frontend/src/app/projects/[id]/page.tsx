"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { SkillsGrid } from "@/components/SkillsGrid";
import { ProjectCapsule } from "@/components/ProjectCapsule";
import {
  ArrowLeft,
  Building2,
  MapPin,
  Calendar,
  User,
  Activity,
  Layers,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from "lucide-react";
import Link from "next/link";

// ============================================================================
// TYPES
// ============================================================================

interface ProjectData {
  id: string;
  name: string;
  location: string;
  created_at: string;
  updated_at: string;
  owner: string;
  status: "active" | "pending" | "completed";
  floors: number;
  area_sqm: number;
  clashes_open: number;
  clashes_resolved: number;
}

// ============================================================================
// PAGE COMPONENT
// ============================================================================

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<ProjectData | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "skills" | "autopilot">("overview");

  // Mock project data - in real app this would come from API
  useEffect(() => {
    // Simulate API call
    setProject({
      id: projectId,
      name: "מגדל אקווה",
      location: "תל אביב, ישראל",
      created_at: "2024-01-15",
      updated_at: new Date().toISOString(),
      owner: "צוות הנדסה ראשי",
      status: "active",
      floors: 45,
      area_sqm: 85000,
      clashes_open: 127,
      clashes_resolved: 342,
    });
  }, [projectId]);

  if (!project) {
    return (
      <DashboardShell>
        <div className="flex items-center justify-center h-96">
          <div className="animate-pulse text-white/50">טוען פרויקט...</div>
        </div>
      </DashboardShell>
    );
  }

  const statusConfig = {
    active: { color: "text-status-success", bg: "bg-status-success/20", label: "פעיל" },
    pending: { color: "text-status-warning", bg: "bg-status-warning/20", label: "ממתין" },
    completed: { color: "text-status-ai", bg: "bg-status-ai/20", label: "הושלם" },
  };

  const status = statusConfig[project.status];

  return (
    <DashboardShell>
      <div className="space-y-6">
        {/* ===== HEADER ===== */}
        <header className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <Link
              href="/"
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors mt-1"
            >
              <ArrowLeft className="w-5 h-5 text-white/60" />
            </Link>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold text-white">{project.name}</h1>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${status.bg} ${status.color}`}>
                  {status.label}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-white/50">
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {project.location}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {new Date(project.created_at).toLocaleDateString("he-IL")}
                </span>
                <span className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {project.owner}
                </span>
              </div>
            </div>
          </div>

          {/* Project ID */}
          <div className="glass rounded-lg px-4 py-2 text-right">
            <p className="text-xs text-white/50">מזהה פרויקט</p>
            <p className="font-mono text-status-ai">{project.id}</p>
          </div>
        </header>

        {/* ===== TABS ===== */}
        <nav className="flex gap-2 border-b border-white/10 pb-4">
          {[
            { id: "overview", label: "סקירה כללית", icon: Activity },
            { id: "skills", label: "Skills Library", icon: Layers },
            { id: "autopilot", label: "Auto-Pilot", icon: Building2 },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg transition-all
                ${activeTab === tab.id
                  ? "bg-status-ai/20 text-status-ai"
                  : "text-white/60 hover:text-white hover:bg-white/5"
                }
              `}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>

        {/* ===== TAB CONTENT ===== */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-3 gap-6">
            {/* Stats Cards */}
            <div className="glass-heavy rounded-2xl p-6 space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-status-ai" />
                נתוני פרויקט
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-white/60">קומות</span>
                  <span className="font-mono text-white">{project.floors}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-white/60">שטח כולל</span>
                  <span className="font-mono text-white">{project.area_sqm.toLocaleString()} מ"ר</span>
                </div>
              </div>
            </div>

            <div className="glass-heavy rounded-2xl p-6 space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-status-warning" />
                התנגשויות
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-white/60">פתוחות</span>
                  <span className="font-mono text-status-critical">{project.clashes_open}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-white/60">נפתרו</span>
                  <span className="font-mono text-status-success">{project.clashes_resolved}</span>
                </div>
              </div>
            </div>

            <div className="glass-heavy rounded-2xl p-6 space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-white/60" />
                סטטוס
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-white/60">עדכון אחרון</span>
                  <span className="font-mono text-white/80">
                    {new Date(project.updated_at).toLocaleTimeString("he-IL")}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-white/60">אחוז השלמה</span>
                  <span className="font-mono text-status-success">
                    {Math.round((project.clashes_resolved / (project.clashes_open + project.clashes_resolved)) * 100)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="glass-heavy rounded-2xl p-6 col-span-3 space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-status-ai" />
                פעילות אחרונה
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <ActivityCard
                  icon={CheckCircle2}
                  title="CLH-1245 נפתר"
                  time="לפני 5 דקות"
                  color="success"
                />
                <ActivityCard
                  icon={Building2}
                  title="מודל עודכן"
                  time="לפני 12 דקות"
                  color="ai"
                />
                <ActivityCard
                  icon={AlertTriangle}
                  title="התנגשות חדשה"
                  time="לפני 18 דקות"
                  color="warning"
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === "skills" && (
          <SkillsGrid
            projectId={project.id}
            onSkillRun={(skillId) => console.log("Running skill:", skillId)}
          />
        )}

        {activeTab === "autopilot" && (
          <div className="max-w-2xl mx-auto">
            <ProjectCapsule
              projectId={project.id}
              projectName={project.name}
            />
          </div>
        )}
      </div>
    </DashboardShell>
  );
}

// ============================================================================
// SUB COMPONENTS
// ============================================================================

interface ActivityCardProps {
  icon: React.ElementType;
  title: string;
  time: string;
  color: "success" | "ai" | "warning";
}

function ActivityCard({ icon: Icon, title, time, color }: ActivityCardProps) {
  const colorClasses = {
    success: "bg-status-success/20 text-status-success",
    ai: "bg-status-ai/20 text-status-ai",
    warning: "bg-status-warning/20 text-status-warning",
  };

  return (
    <div className="glass rounded-xl p-4 flex items-center gap-3">
      <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1">
        <p className="text-sm text-white font-medium">{title}</p>
        <p className="text-xs text-white/40">{time}</p>
      </div>
    </div>
  );
}
