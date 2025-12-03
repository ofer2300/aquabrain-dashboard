"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  AlertTriangle,
  MessageSquare,
  Settings,
  Calendar,
  Activity,
  Brain,
  Calculator,
  Rocket
} from 'lucide-react';
import { useSystemStatus } from '@/hooks/useSystemStatus';

interface NavItem {
  icon: React.ElementType;
  label: string;
  href: string;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/" },
  { icon: Rocket, label: "Auto-Pilot", href: "/autopilot", badge: "AI" },
  { icon: Calculator, label: "Hydraulics", href: "/calculation" },
  { icon: AlertTriangle, label: "Clashes", href: "/clashes" },
  { icon: MessageSquare, label: "Communication", href: "/communication", badge: "LIVE" },
  { icon: Calendar, label: "Work Plan", href: "/workplan" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

interface DashboardShellProps {
  children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname();
  const { isConnected, status, isLoading } = useSystemStatus();

  return (
    <div className="flex h-screen bg-transparent">
      {/* Sidebar - Glass Panel */}
      <aside className="w-64 glass-panel flex flex-col m-3 mr-0">
        {/* Logo */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-status-ai/20 flex items-center justify-center glow-ai">
              <Brain className="w-6 h-6 text-status-ai" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-primary">AquaBrain</h1>
              <p className="text-xs text-text-secondary">MEP Intelligence</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-all
                  ${isActive
                    ? 'bg-white/10 border border-white/20 text-text-primary glow-ai'
                    : 'text-text-secondary hover:bg-white/5 hover:text-text-primary border border-transparent'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className={`
                    text-[10px] px-2 py-0.5 rounded-full font-bold
                    ${item.badge === 'LIVE'
                      ? 'bg-status-success/20 text-status-success'
                      : 'bg-status-ai/20 text-status-ai'
                    }
                  `}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* System Status */}
        <div className="p-4 border-t border-white/10">
          <div className={`
            p-3 rounded-xl flex items-center gap-3 transition-all
            ${isConnected
              ? 'bg-status-success/10 glow-success'
              : 'bg-status-error/10 glow-error'
            }
          `}>
            <div className={`status-dot ${isConnected ? 'live' : 'error'}`} />
            <div className="flex-1">
              <p className={`text-sm font-bold ${isConnected ? 'text-status-success' : 'text-status-error'}`}>
                {isLoading ? 'CONNECTING...' : isConnected ? 'SYSTEM LIVE' : 'DISCONNECTED'}
              </p>
              {isConnected && status && (
                <p className="text-[10px] text-text-secondary">
                  AI: {status.ai_engine} | {status.uptime_seconds}s
                </p>
              )}
            </div>
            <Activity className={`w-4 h-4 ${isConnected ? 'text-status-success animate-pulse' : 'text-status-error'}`} />
          </div>
        </div>
      </aside>

      {/* Main Content - Transparent Background */}
      <main className="flex-1 overflow-auto p-3">
        <div className="glass-panel p-6 min-h-full">
          {children}
        </div>
      </main>
    </div>
  );
}
