import { DashboardShell } from "@/components/DashboardShell";
import { CommunicationHub } from "@/components/CommunicationHub";

export default function CommunicationPage() {
  return (
    <DashboardShell>
      <div className="flex flex-col h-[calc(100vh-100px)] gap-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">מרכז תקשורת (Communication Hub)</h1>
            <p className="text-white/60">ניהול תקשורת בזמן אמת מול יועצים וקבלנים</p>
          </div>
          <div className="flex gap-2">
            <span className="bg-[var(--status-success)]/20 text-[var(--status-success)] px-3 py-1 rounded-full text-xs font-bold animate-pulse border border-[var(--status-success)]/30">
              ● LIVE SYSTEM
            </span>
          </div>
        </div>

        {/* The Main Chat Component */}
        <CommunicationHub />
      </div>
    </DashboardShell>
  );
}
