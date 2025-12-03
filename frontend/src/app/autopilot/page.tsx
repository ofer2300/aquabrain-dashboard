"use client";

import { DashboardShell } from "@/components/DashboardShell";
import { ProjectCapsule } from "@/components/ProjectCapsule";
import { Brain, Zap, Shield, Clock } from "lucide-react";

export default function AutoPilotPage() {
  return (
    <DashboardShell>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="w-20 h-20 rounded-2xl bg-status-ai/20 flex items-center justify-center glow-ai">
              <Brain className="w-12 h-12 text-status-ai" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-white">
            Auto-Pilot Mode
            <span className="text-gradient-ai mr-2"> (הטסלה של ההנדסה)</span>
          </h1>
          <p className="text-text-secondary max-w-2xl mx-auto">
            לחיצה אחת → תכנון מערכת ספרינקלרים מלאה LOD 500.
            הבינה המלאכותית מנתחת, מתכננת, ומאמתת - אתה רק מאשר.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-3 gap-4">
          <FeatureCard
            icon={Zap}
            title="תכנון בזק"
            description="מהתחלה ועד LOD 500 בדקות"
            color="warning"
          />
          <FeatureCard
            icon={Shield}
            title="תאימות NFPA 13"
            description="בדיקה אוטומטית של כל התקנים"
            color="success"
          />
          <FeatureCard
            icon={Clock}
            title="חיסכון של 80%"
            description="בזמן תכנון לעומת שיטות מסורתיות"
            color="ai"
          />
        </div>

        {/* The Capsule */}
        <ProjectCapsule
          projectId="PRJ-500"
          projectName="מגדל אקווה - קומות 1-5"
        />

        {/* How it Works */}
        <div className="glass rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-4">איך זה עובד?</h3>
          <div className="grid grid-cols-6 gap-2 text-center text-xs">
            <StepIndicator step={1} label="שאיבת תוכניות" sublabel="Revit" />
            <StepIndicator step={2} label="ניתוח גיאומטריה" sublabel="Voxel" />
            <StepIndicator step={3} label="תכנון תוואי" sublabel="A*" />
            <StepIndicator step={4} label="חישוב הידראולי" sublabel="H-W" />
            <StepIndicator step={5} label="יצירת מודל" sublabel="LOD 500" />
            <StepIndicator step={6} label="אימות תקן" sublabel="NFPA" />
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}

interface FeatureCardProps {
  icon: React.ElementType;
  title: string;
  description: string;
  color: 'ai' | 'success' | 'warning';
}

function FeatureCard({ icon: Icon, title, description, color }: FeatureCardProps) {
  const colorClasses = {
    ai: 'bg-status-ai/20 text-status-ai glow-ai',
    success: 'bg-status-success/20 text-status-success glow-success',
    warning: 'bg-status-warning/20 text-status-warning glow-warning',
  };

  return (
    <div className="glass rounded-xl p-4 text-center">
      <div className={`w-12 h-12 rounded-xl ${colorClasses[color]} flex items-center justify-center mx-auto mb-3`}>
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="font-bold text-white">{title}</h4>
      <p className="text-xs text-text-secondary mt-1">{description}</p>
    </div>
  );
}

interface StepIndicatorProps {
  step: number;
  label: string;
  sublabel: string;
}

function StepIndicator({ step, label, sublabel }: StepIndicatorProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="w-8 h-8 rounded-full bg-status-ai/20 text-status-ai flex items-center justify-center font-bold text-sm">
        {step}
      </div>
      <span className="text-white/70">{label}</span>
      <span className="text-white/40 text-[10px]">{sublabel}</span>
    </div>
  );
}
