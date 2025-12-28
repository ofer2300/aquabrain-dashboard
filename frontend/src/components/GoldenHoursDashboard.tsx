"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Mail,
  Clock,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Send,
  Calendar,
  Paperclip,
  MessageSquare,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface EmailAttachment {
  filename: string;
  content_type: string;
  size_bytes: number;
}

interface EmailMessage {
  id: string;
  provider: string;
  subject: string;
  sender: string;
  sender_name: string;
  recipients: string[];
  date: string;
  attachments: EmailAttachment[];
  is_read: boolean;
}

interface EmailAnalysis {
  email_id: string;
  project: string;
  sender_importance: 'high' | 'medium' | 'low';
  risk_level: 'green' | 'yellow' | 'red';
  required_action: string;
  summary_hebrew: string;
  suggested_response: string;
  deadline: string;
  keywords: string[];
  analyzed_at: string;
}

interface EmailCard {
  email: EmailMessage;
  analysis: EmailAnalysis;
  status: string;
  scheduled_for: string | null;
  handled_at: string | null;
  response_sent: boolean;
}

interface DashboardData {
  title: string;
  is_golden_hour: boolean;
  current_time: string;
  next_golden_hour: string;
  total_pending: number;
  by_risk: {
    red: number;
    yellow: number;
    green: number;
  };
  emails: EmailCard[];
}

interface GoldenHoursDashboardProps {
  onEmailAction?: (emailId: string, action: string) => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const getRiskColor = (risk: string) => {
  switch (risk) {
    case 'red': return 'text-red-400 bg-red-500/20 border-red-500/30';
    case 'yellow': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
    case 'green': return 'text-green-400 bg-green-500/20 border-green-500/30';
    default: return 'text-gray-400 bg-gray-500/20 border-gray-500/30';
  }
};

const getRiskIcon = (risk: string) => {
  switch (risk) {
    case 'red': return <AlertCircle className="w-4 h-4" />;
    case 'yellow': return <AlertTriangle className="w-4 h-4" />;
    case 'green': return <CheckCircle className="w-4 h-4" />;
    default: return <Mail className="w-4 h-4" />;
  }
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleString('he-IL', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// ============================================================================
// EMAIL CARD COMPONENT
// ============================================================================

function EmailCardComponent({
  card,
  onAction,
  isExpanded,
  onToggle,
}: {
  card: EmailCard;
  onAction: (action: string) => void;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const { email, analysis } = card;

  return (
    <div
      className={`
        glass-heavy rounded-xl overflow-hidden transition-all duration-300
        border ${getRiskColor(analysis.risk_level)}
      `}
    >
      {/* Header */}
      <div
        className="p-4 cursor-pointer hover:bg-white/5"
        onClick={onToggle}
      >
        <div className="flex items-start gap-3">
          {/* Risk Indicator */}
          <div className={`p-2 rounded-lg ${getRiskColor(analysis.risk_level)}`}>
            {getRiskIcon(analysis.risk_level)}
          </div>

          {/* Email Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-white truncate">
                {email.sender_name}
              </span>
              {analysis.sender_importance === 'high' && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                  חשוב
                </span>
              )}
            </div>
            <p className="text-sm text-white/70 truncate">{email.subject}</p>
            <div className="flex items-center gap-2 mt-1 text-xs text-white/40">
              <Clock className="w-3 h-3" />
              {formatDate(email.date)}
              {email.attachments.length > 0 && (
                <span className="flex items-center gap-1">
                  <Paperclip className="w-3 h-3" />
                  {email.attachments.length}
                </span>
              )}
              {analysis.project && (
                <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300">
                  {analysis.project}
                </span>
              )}
            </div>
          </div>

          {/* Toggle */}
          <button className="text-white/40 hover:text-white/70">
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-white/10">
          {/* AI Summary */}
          <div className="mt-3 p-3 rounded-lg bg-white/5" dir="rtl">
            <p className="text-sm text-white/80 leading-relaxed">
              {analysis.summary_hebrew}
            </p>
          </div>

          {/* Keywords */}
          {analysis.keywords.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {analysis.keywords.slice(0, 6).map((keyword, i) => (
                <span
                  key={i}
                  className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300"
                >
                  {keyword}
                </span>
              ))}
            </div>
          )}

          {/* Suggested Response */}
          {analysis.suggested_response && (
            <div className="mt-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20" dir="rtl">
              <p className="text-xs text-white/40 mb-1">תגובה מוצעת:</p>
              <p className="text-sm text-white/70 whitespace-pre-wrap">
                {analysis.suggested_response.slice(0, 300)}
                {analysis.suggested_response.length > 300 && '...'}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-4 flex flex-wrap gap-2">
            {analysis.required_action === 'sign_now' && (
              <button
                onClick={() => onAction('תחתום ותשלח')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/20 text-green-400 text-sm hover:bg-green-500/30 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                חתום ושלח
              </button>
            )}
            <button
              onClick={() => onAction('respond')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 text-sm hover:bg-blue-500/30 transition-colors"
            >
              <Send className="w-4 h-4" />
              השב
            </button>
            <button
              onClick={() => onAction('תשמור ל-16:00')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-500/20 text-purple-400 text-sm hover:bg-purple-500/30 transition-colors"
            >
              <Calendar className="w-4 h-4" />
              תזמן
            </button>
            <button
              onClick={() => onAction('התעלם')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-white/50 text-sm hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" />
              התעלם
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

export function GoldenHoursDashboard({ onEmailAction }: GoldenHoursDashboardProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedEmail, setExpandedEmail] = useState<string | null>(null);

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/orchestrator/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: '701',
          payload: { action: 'dashboard' },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard');
      }

      // For async tasks, we poll for result
      const taskResult = await response.json();

      // Simulate dashboard data for immediate display
      // In production, would poll for task completion
      setTimeout(async () => {
        try {
          const dashboardResponse = await fetch('http://localhost:8000/api/orchestrator/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              skill_id: '701',
              payload: { action: 'dashboard' },
            }),
          });
          // Use mock data for immediate display
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 2000);

      // Use sample data for now
      setData({
        title: 'תקציר הקשב שלך – טוען...',
        is_golden_hour: false,
        current_time: new Date().toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' }),
        next_golden_hour: '16:00',
        total_pending: 0,
        by_risk: { red: 0, yellow: 0, green: 0 },
        emails: [],
      });
    } catch (err) {
      console.error('Error fetching dashboard:', err);
      setError('שגיאה בטעינת הדשבורד');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Handle email action
  const handleEmailAction = async (emailId: string, action: string) => {
    try {
      await fetch('http://localhost:8000/api/orchestrator/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: '701',
          payload: {
            action: 'handle',
            email_id: emailId,
            command: action,
          },
        }),
      });

      onEmailAction?.(emailId, action);
      fetchDashboard(); // Refresh
    } catch (err) {
      console.error('Error handling email:', err);
    }
  };

  return (
    <div className="space-y-4" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/30 to-amber-400/20">
            <Mail className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Email Cockpit</h2>
            <p className="text-sm text-white/40">
              {data?.is_golden_hour ? (
                <span className="text-amber-400">שעת זהב פעילה</span>
              ) : (
                `שעת הזהב הבאה: ${data?.next_golden_hour || '...'}`
              )}
            </p>
          </div>
        </div>

        <button
          onClick={fetchDashboard}
          disabled={isLoading}
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 text-white/60 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Stats Bar */}
      {data && (
        <div className="grid grid-cols-4 gap-3">
          <div className="glass-heavy rounded-xl p-3 text-center">
            <p className="text-2xl font-bold text-white">{data.total_pending}</p>
            <p className="text-xs text-white/40">ממתינים</p>
          </div>
          <div className="glass-heavy rounded-xl p-3 text-center border border-red-500/30">
            <p className="text-2xl font-bold text-red-400">{data.by_risk.red}</p>
            <p className="text-xs text-red-400/70">דחוף</p>
          </div>
          <div className="glass-heavy rounded-xl p-3 text-center border border-yellow-500/30">
            <p className="text-2xl font-bold text-yellow-400">{data.by_risk.yellow}</p>
            <p className="text-xs text-yellow-400/70">לבדיקה</p>
          </div>
          <div className="glass-heavy rounded-xl p-3 text-center border border-green-500/30">
            <p className="text-2xl font-bold text-green-400">{data.by_risk.green}</p>
            <p className="text-xs text-green-400/70">לידיעה</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && !data && (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          <p className="text-white/40 mt-2">טוען מיילים...</p>
        </div>
      )}

      {/* Email Cards */}
      {data && data.emails.length > 0 && (
        <div className="space-y-3">
          {data.emails.map((card) => (
            <EmailCardComponent
              key={card.email.id}
              card={card}
              onAction={(action) => handleEmailAction(card.email.id, action)}
              isExpanded={expandedEmail === card.email.id}
              onToggle={() => setExpandedEmail(
                expandedEmail === card.email.id ? null : card.email.id
              )}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {data && data.emails.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
          <h3 className="text-lg font-medium text-white">אין מיילים ממתינים</h3>
          <p className="text-white/40 mt-1">כל המיילים טופלו</p>
        </div>
      )}
    </div>
  );
}

export default GoldenHoursDashboard;
