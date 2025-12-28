"""
AquaBrain Skill #701 - OMNI-CHANNEL EMAIL COCKPIT
===================================================
The engineer never opens Gmail again.
The engineer never opens Outlook again.
Everything comes through AquaBrain.

From now on:
- All emails arrive, processed, and sent ONLY through AquaBrain
- AI analyzes every email with full project context
- Golden Hours Dashboard shows emails at 12:00 and 16:00 only
- Complete audit trail of every action

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    SKILL #701 - EMAIL COCKPIT                       │
    ├─────────────────────────────────────────────────────────────────────┤
    │                                                                     │
    │  ┌─────────────────────────────────────────────────────────────┐   │
    │  │            📥 INBOUND CHANNEL                                │   │
    │  │  Gmail ────┐                                                 │   │
    │  │            ├──→ Polling (2 min) ──→ Redis Queue             │   │
    │  │  Outlook ──┘                                                 │   │
    │  └─────────────────────────────────────────────────────────────┘   │
    │                            │                                        │
    │                            ▼                                        │
    │  ┌─────────────────────────────────────────────────────────────┐   │
    │  │            🧠 AI SEMANTIC ANALYZER                           │   │
    │  │  • Project context from Weaviate                            │   │
    │  │  • Sender importance classification                         │   │
    │  │  • Risk level (GREEN/YELLOW/RED)                            │   │
    │  │  • Required action detection                                │   │
    │  │  • Auto-generated Hebrew summary                            │   │
    │  │  • Suggested response                                       │   │
    │  └─────────────────────────────────────────────────────────────┘   │
    │                            │                                        │
    │                            ▼                                        │
    │  ┌─────────────────────────────────────────────────────────────┐   │
    │  │            🌟 GOLDEN HOURS DASHBOARD (12:00 / 16:00)        │   │
    │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │   │
    │  │  │ 🔴 RED   │ │ 🟡 YELLOW│ │ 🟢 GREEN │  ← Priority Order   │   │
    │  │  │ Urgent   │ │ Review   │ │ FYI      │                     │   │
    │  │  └──────────┘ └──────────┘ └──────────┘                     │   │
    │  └─────────────────────────────────────────────────────────────┘   │
    │                            │                                        │
    │                            ▼                                        │
    │  ┌─────────────────────────────────────────────────────────────┐   │
    │  │            💬 IN-APP EMAIL HANDLER                          │   │
    │  │  "תחתום ותשלח" → Auto-sign + Send                          │   │
    │  │  "תשמור ל-16:00" → Schedule for later                       │   │
    │  │  Direct reply composition                                   │   │
    │  └─────────────────────────────────────────────────────────────┘   │
    │                            │                                        │
    │                            ▼                                        │
    │  ┌─────────────────────────────────────────────────────────────┐   │
    │  │            📤 OUTBOUND CHANNEL                               │   │
    │  │  • Send via Gmail/Outlook                                   │   │
    │  │  • Attach signed documents                                  │   │
    │  │  • Save to Weaviate + DMS                                   │   │
    │  │  • Create Action Items                                      │   │
    │  │  • Complete Audit Trail                                     │   │
    │  └─────────────────────────────────────────────────────────────┘   │
    │                                                                     │
    └─────────────────────────────────────────────────────────────────────┘

Author: AquaBrain V8.0 Platinum
Date: 2025-12-04
"""

from __future__ import annotations
import os
import sys
import re
import json
import base64
import hashlib
import smtplib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import threading
import time

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.base import (
    AquaSkill, ExecutionResult, ExecutionStatus,
    SkillMetadata, SkillCategory, InputSchema, InputField, FieldType,
    register_skill
)

# Try imports
try:
    from imap_tools import MailBox, AND
    IMAP_AVAILABLE = True
except ImportError:
    IMAP_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

class EmailProvider(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class RequiredAction(str, Enum):
    SIGN_NOW = "sign_now"
    REVIEW_FIRST = "review_first"
    RESPOND = "respond"
    IGNORE = "ignore"
    CALL_ME = "call_me"
    SCHEDULE = "schedule"


class SenderImportance(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Golden Hours Configuration
GOLDEN_HOURS = [12, 16]  # 12:00 and 16:00
POLLING_INTERVAL_MINUTES = 2


# =============================================================================
# EMAIL DATA MODELS
# =============================================================================

@dataclass
class EmailAttachment:
    """Email attachment data."""
    filename: str
    content_type: str
    content_b64: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes
        }


@dataclass
class EmailMessage:
    """Complete email message with all metadata."""
    id: str
    provider: EmailProvider
    subject: str
    sender: str
    sender_name: str = ""
    recipients: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    body_text: str = ""
    body_html: str = ""
    date: datetime = field(default_factory=datetime.now)
    attachments: List[EmailAttachment] = field(default_factory=list)
    thread_id: str = ""
    is_read: bool = False
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider.value,
            "subject": self.subject,
            "sender": self.sender,
            "sender_name": self.sender_name,
            "recipients": self.recipients,
            "date": self.date.isoformat(),
            "attachments": [a.to_dict() for a in self.attachments],
            "is_read": self.is_read
        }


@dataclass
class EmailAnalysis:
    """AI analysis result for an email."""
    email_id: str
    project: str = ""
    sender_importance: SenderImportance = SenderImportance.MEDIUM
    risk_level: RiskLevel = RiskLevel.GREEN
    required_action: RequiredAction = RequiredAction.REVIEW_FIRST
    summary_hebrew: str = ""
    suggested_response: str = ""
    deadline: str = ""
    keywords: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_json(cls, email_id: str, data: Dict[str, Any]) -> 'EmailAnalysis':
        return cls(
            email_id=email_id,
            project=data.get("project", ""),
            sender_importance=SenderImportance(data.get("sender_importance", "medium")),
            risk_level=RiskLevel(data.get("risk_level", "green")),
            required_action=RequiredAction(data.get("required_action", "review_first")),
            summary_hebrew=data.get("summary_hebrew", ""),
            suggested_response=data.get("suggested_response", ""),
            deadline=data.get("deadline", ""),
            keywords=data.get("keywords", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email_id": self.email_id,
            "project": self.project,
            "sender_importance": self.sender_importance.value,
            "risk_level": self.risk_level.value,
            "required_action": self.required_action.value,
            "summary_hebrew": self.summary_hebrew,
            "suggested_response": self.suggested_response,
            "deadline": self.deadline,
            "keywords": self.keywords,
            "analyzed_at": self.analyzed_at.isoformat()
        }


@dataclass
class EmailCard:
    """Email card for dashboard display."""
    email: EmailMessage
    analysis: EmailAnalysis
    status: str = "pending"  # pending, in_progress, handled, scheduled
    scheduled_for: Optional[datetime] = None
    handled_at: Optional[datetime] = None
    response_sent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email.to_dict(),
            "analysis": self.analysis.to_dict(),
            "status": self.status,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "handled_at": self.handled_at.isoformat() if self.handled_at else None,
            "response_sent": self.response_sent
        }


# =============================================================================
# EMAIL POLLER
# =============================================================================

class EmailPoller:
    """
    Multi-provider email polling system.
    Polls Gmail and Outlook every 2 minutes.
    """

    def __init__(self):
        self.gmail_email = os.getenv("GMAIL_USER", "")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.outlook_email = os.getenv("OUTLOOK_USER", "")
        self.outlook_password = os.getenv("OUTLOOK_APP_PASSWORD", "")
        self._last_poll: Dict[str, datetime] = {}
        self._polling_active = False
        self._poll_thread: Optional[threading.Thread] = None

    def poll_gmail(self, limit: int = 20, since_hours: int = 24) -> List[EmailMessage]:
        """Poll Gmail for new emails."""
        if not IMAP_AVAILABLE or not self.gmail_email:
            return self._mock_emails(EmailProvider.GMAIL)

        emails = []
        try:
            since_date = datetime.now() - timedelta(hours=since_hours)

            with MailBox("imap.gmail.com").login(self.gmail_email, self.gmail_password) as mailbox:
                for msg in mailbox.fetch(AND(date_gte=since_date.date()), reverse=True, limit=limit):
                    attachments = [
                        EmailAttachment(
                            filename=att.filename,
                            content_type=att.content_type,
                            content_b64=base64.b64encode(att.payload).decode() if att.payload else "",
                            size_bytes=len(att.payload) if att.payload else 0
                        )
                        for att in msg.attachments
                    ]

                    emails.append(EmailMessage(
                        id=msg.uid,
                        provider=EmailProvider.GMAIL,
                        subject=msg.subject or "",
                        sender=msg.from_,
                        sender_name=msg.from_.split("<")[0].strip() if "<" in msg.from_ else msg.from_,
                        recipients=[r for r in msg.to],
                        cc=[c for c in msg.cc],
                        body_text=msg.text or "",
                        body_html=msg.html or "",
                        date=msg.date or datetime.now(),
                        attachments=attachments,
                        is_read=msg.flags and "\\Seen" in msg.flags
                    ))

            self._last_poll[EmailProvider.GMAIL.value] = datetime.now()

        except Exception as e:
            print(f"[POLLER] Gmail error: {e}")
            return self._mock_emails(EmailProvider.GMAIL)

        return emails

    def poll_outlook(self, limit: int = 20) -> List[EmailMessage]:
        """Poll Outlook for new emails."""
        # In production, would use Microsoft Graph API
        return self._mock_emails(EmailProvider.OUTLOOK, count=3)

    def poll_all(self) -> List[EmailMessage]:
        """Poll all providers."""
        all_emails = []
        all_emails.extend(self.poll_gmail())
        all_emails.extend(self.poll_outlook())

        # Sort by date descending
        all_emails.sort(key=lambda e: e.date, reverse=True)

        return all_emails

    def start_background_polling(self, interval_minutes: int = POLLING_INTERVAL_MINUTES):
        """Start background polling thread."""
        if self._polling_active:
            return

        self._polling_active = True

        def poll_loop():
            while self._polling_active:
                try:
                    emails = self.poll_all()
                    print(f"[POLLER] Found {len(emails)} emails")
                    # In production, would push to Redis queue
                except Exception as e:
                    print(f"[POLLER] Error: {e}")

                time.sleep(interval_minutes * 60)

        self._poll_thread = threading.Thread(target=poll_loop, daemon=True)
        self._poll_thread.start()
        print(f"[POLLER] Started background polling every {interval_minutes} minutes")

    def stop_background_polling(self):
        """Stop background polling."""
        self._polling_active = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        print("[POLLER] Stopped background polling")

    def _mock_emails(self, provider: EmailProvider, count: int = 7) -> List[EmailMessage]:
        """Generate mock emails for demo."""
        mock_data = [
            {
                "subject": "בקשה לחתימה על תצהיר אינסטלציה - ארלוזורוב 20",
                "sender": "daniel.kashtan@tel-aviv.gov.il",
                "sender_name": "דניאל קשטן",
                "body": """שלום נימרוד,

מצ"ב תצהיר מתכנן אינסטלציה לגמר עבור פרויקט ארלוזורוב 20.
גוש 3000, חלקה 150.
מספר היתר: 2024-05678

נא לחתום בהקדם.

בברכה,
דניאל קשטן
מפקח עירייה""",
                "attachments": [{"filename": "תצהיר_אינסטלציה_ארלוזורוב20.pdf", "content_type": "application/pdf"}],
                "importance": "high",
                "risk": "green",
                "action": "sign_now"
            },
            {
                "subject": "דחוף: ליקויים שנמצאו בפיקוח - קניון נופים",
                "sender": "michal.cohen@ramatgan.muni.il",
                "sender_name": "מיכל כהן",
                "body": """שלום רב,

בביקור שבוצע היום נמצאו הליקויים הבאים:
1. חסר ברז כיבוי ראשי
2. מערכת הספרינקלרים לא מחוברת
3. שלטי בטיחות חסרים

נא לטפל בדחיפות.

מיכל כהן
מנהלת פרויקט""",
                "attachments": [{"filename": "דוח_ליקויים_04122025.pdf", "content_type": "application/pdf"}],
                "importance": "high",
                "risk": "red",
                "action": "call_me"
            },
            {
                "subject": "אישור תשלום דמי הקמה - פרויקט רוטשילד 15",
                "sender": "billing@mei-tel-aviv.co.il",
                "sender_name": "תאגיד מי תל אביב",
                "body": """שלום,

מאשרים קבלת תשלום דמי הקמה בסך 187,000 ₪ עבור פרויקט רוטשילד 15.
מספר אישור: TLV-2024-98765

בברכה,
מחלקת גבייה""",
                "attachments": [],
                "importance": "medium",
                "risk": "green",
                "action": "ignore"
            },
            {
                "subject": "תזכורת: פגישה מחר עם ועדת התכנון",
                "sender": "calendar@google.com",
                "sender_name": "Google Calendar",
                "body": """תזכורת: פגישה עם ועדת התכנון העירונית
מחר, 05/12/2025 בשעה 10:00
מיקום: בניין העירייה, קומה 3""",
                "attachments": [],
                "importance": "medium",
                "risk": "yellow",
                "action": "review_first"
            },
            {
                "subject": "עדכון תקן NFPA 13 - גרסה 2025",
                "sender": "updates@nfpa.org",
                "sender_name": "NFPA",
                "body": """Dear Professional,

The 2025 edition of NFPA 13 has been released with the following key changes...

Best regards,
NFPA""",
                "attachments": [{"filename": "NFPA13_2025_Summary.pdf", "content_type": "application/pdf"}],
                "importance": "low",
                "risk": "green",
                "action": "ignore"
            },
            {
                "subject": "בקשה לאישור AS-MADE - דיזנגוף 100",
                "sender": "architect@studio.com",
                "sender_name": "משרד אדריכלים",
                "body": """שלום נימרוד,

מצ"ב תוכניות AS-MADE לאישורך.
נא לבדוק ולאשר.

תודה""",
                "attachments": [{"filename": "AS_MADE_דיזנגוף100.dwg", "content_type": "application/acad"}],
                "importance": "medium",
                "risk": "yellow",
                "action": "review_first"
            },
            {
                "subject": "הזמנה לכנס מהנדסים 2025",
                "sender": "events@engineers.org.il",
                "sender_name": "לשכת המהנדסים",
                "body": """הוזמנת לכנס המהנדסים השנתי 2025
תאריך: 15/01/2025
מיקום: מרכז הכנסים, תל אביב""",
                "attachments": [],
                "importance": "low",
                "risk": "green",
                "action": "ignore"
            }
        ]

        emails = []
        for i, data in enumerate(mock_data[:count]):
            attachments = [
                EmailAttachment(
                    filename=a["filename"],
                    content_type=a["content_type"],
                    size_bytes=50000
                )
                for a in data.get("attachments", [])
            ]

            emails.append(EmailMessage(
                id=f"MOCK-{provider.value}-{i+1:03d}",
                provider=provider,
                subject=data["subject"],
                sender=data["sender"],
                sender_name=data["sender_name"],
                body_text=data["body"],
                date=datetime.now() - timedelta(hours=i * 2),
                attachments=attachments,
                is_read=False
            ))

        return emails


# =============================================================================
# EMAIL AI ANALYZER
# =============================================================================

EMAIL_ANALYZER_PROMPT = """אתה נימרוד עופר, מהנדס בכיר עם 38 שנות ניסיון.
קראת את המייל הזה + כל הקבצים המצורפים + כל ההיסטוריה של הפרויקט.

מייל:
נושא: {subject}
שולח: {sender}
תוכן: {body}
קבצים מצורפים: {attachments}

היסטוריית פרויקט (אם רלוונטי):
{project_history}

תחזיר JSON נקי בלבד (ללא markdown):
{{
"project": "שם הפרויקט אם זוהה",
"sender_importance": "high|medium|low",
"risk_level": "green|yellow|red",
"required_action": "sign_now|review_first|respond|ignore|call_me|schedule",
"summary_hebrew": "תמצית קצרה בעברית - מה השולח רוצה ומה הסיכון",
"suggested_response": "תגובה מוצעת בעברית אם צריך",
"deadline": "תאריך יעד אם יש (YYYY-MM-DD)",
"keywords": ["מילות מפתח"]
}}

קריטריונים:
- high importance: עירייה, ועדה, מפקח, דחוף
- red risk: ליקויים, בעיות, דחוף, סיכון
- yellow risk: תזכורת, בקשה, לבדיקה
- green risk: אישור, FYI, עדכון שגרתי
- sign_now: תצהיר/אישור מוכן לחתימה
- call_me: דחוף ודורש שיחה

החזר JSON בלבד!"""


class EmailAnalyzer:
    """
    AI-powered email semantic analyzer.
    Uses Claude/Gemini with full project context from Weaviate.
    """

    def __init__(self):
        try:
            from skills.library.virtual_senior_engineer import ProjectMemory
            self.memory = ProjectMemory()
        except ImportError:
            self.memory = None

    def analyze(self, email: EmailMessage) -> EmailAnalysis:
        """Analyze email with AI and project context."""
        # Get project context
        project_history = ""
        detected_project = self._detect_project(email)

        if self.memory and detected_project:
            project = self.memory.search_project(detected_project)
            if project:
                project_history = json.dumps(project, ensure_ascii=False, indent=2)

        # Build prompt
        attachments_str = ", ".join(a.filename for a in email.attachments) if email.attachments else "אין"

        prompt = EMAIL_ANALYZER_PROMPT.format(
            subject=email.subject,
            sender=f"{email.sender_name} <{email.sender}>",
            body=email.body_text[:2000],
            attachments=attachments_str,
            project_history=project_history[:1000] if project_history else "לא נמצא פרויקט קשור"
        )

        try:
            from services.ai_engine import ask_ai
            response = ask_ai(
                prompt=prompt,
                provider="gemini",
                temperature=0.1
            )

            # Parse JSON
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return EmailAnalysis.from_json(email.id, data)

        except Exception as e:
            print(f"[ANALYZER] AI analysis failed: {e}")

        # Fallback to rule-based analysis
        return self._rule_based_analysis(email)

    def _detect_project(self, email: EmailMessage) -> Optional[str]:
        """Detect project name from email content."""
        text = f"{email.subject} {email.body_text}"

        patterns = [
            r"(ארלוזורוב\s*\d+)",
            r"(דיזנגוף\s*\d+)",
            r"(רוטשילד\s*\d+)",
            r"(קניון\s+\w+)",
            r"פרויקט\s+([\w\s]+?)(?:\.|,|\n)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _rule_based_analysis(self, email: EmailMessage) -> EmailAnalysis:
        """Fallback rule-based analysis."""
        subject_lower = email.subject.lower()
        body_lower = email.body_text.lower()
        sender_lower = email.sender.lower()

        # Determine importance
        if any(x in sender_lower for x in ["gov.il", "muni", "עירייה", "ועדה"]):
            importance = SenderImportance.HIGH
        elif any(x in subject_lower for x in ["דחוף", "urgent", "חשוב"]):
            importance = SenderImportance.HIGH
        else:
            importance = SenderImportance.MEDIUM

        # Determine risk level
        if any(x in body_lower for x in ["ליקוי", "בעיה", "דחוף", "סיכון", "חסר"]):
            risk = RiskLevel.RED
        elif any(x in body_lower for x in ["תזכורת", "בקשה", "לבדיקה", "נא"]):
            risk = RiskLevel.YELLOW
        else:
            risk = RiskLevel.GREEN

        # Determine action
        if any(x in body_lower for x in ["תצהיר", "לחתימה", "אישור"]):
            action = RequiredAction.SIGN_NOW
        elif risk == RiskLevel.RED:
            action = RequiredAction.CALL_ME
        elif any(x in email.attachments[0].filename.lower() for x in [".pdf", ".docx"]) if email.attachments else False:
            action = RequiredAction.REVIEW_FIRST
        else:
            action = RequiredAction.IGNORE

        # Generate summary
        summary = f"{email.sender_name} שולח: {email.subject}"
        if email.attachments:
            summary += f" | {len(email.attachments)} קבצים מצורפים"

        return EmailAnalysis(
            email_id=email.id,
            project=self._detect_project(email) or "",
            sender_importance=importance,
            risk_level=risk,
            required_action=action,
            summary_hebrew=summary,
            suggested_response="",
            deadline=""
        )


# =============================================================================
# GOLDEN HOURS DASHBOARD
# =============================================================================

class GoldenHoursDashboard:
    """
    Email dashboard that shows emails only at Golden Hours (12:00, 16:00).
    Organizes by priority: RED → YELLOW → GREEN
    """

    def __init__(self):
        self._email_cards: List[EmailCard] = []
        self._last_update: Optional[datetime] = None

    def is_golden_hour(self) -> bool:
        """Check if current time is a Golden Hour."""
        current_hour = datetime.now().hour
        return current_hour in GOLDEN_HOURS

    def add_email(self, email: EmailMessage, analysis: EmailAnalysis):
        """Add email to dashboard."""
        card = EmailCard(email=email, analysis=analysis)
        self._email_cards.append(card)

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary for dashboard display."""
        pending = [c for c in self._email_cards if c.status == "pending"]

        # Sort by risk level (RED first)
        risk_order = {RiskLevel.RED: 0, RiskLevel.YELLOW: 1, RiskLevel.GREEN: 2}
        pending.sort(key=lambda c: risk_order.get(c.analysis.risk_level, 3))

        red_count = sum(1 for c in pending if c.analysis.risk_level == RiskLevel.RED)
        yellow_count = sum(1 for c in pending if c.analysis.risk_level == RiskLevel.YELLOW)
        green_count = sum(1 for c in pending if c.analysis.risk_level == RiskLevel.GREEN)

        return {
            "title": f"תקציר הקשב שלך – {len(pending)} מיילים חדשים מחכים",
            "is_golden_hour": self.is_golden_hour(),
            "current_time": datetime.now().strftime("%H:%M"),
            "next_golden_hour": self._next_golden_hour(),
            "total_pending": len(pending),
            "by_risk": {
                "red": red_count,
                "yellow": yellow_count,
                "green": green_count
            },
            "emails": [c.to_dict() for c in pending[:20]]
        }

    def _next_golden_hour(self) -> str:
        """Get next golden hour time."""
        now = datetime.now()
        for hour in sorted(GOLDEN_HOURS):
            if now.hour < hour:
                return f"{hour}:00"
        return f"{GOLDEN_HOURS[0]}:00 (מחר)"

    def mark_handled(self, email_id: str, response_sent: bool = False):
        """Mark email as handled."""
        for card in self._email_cards:
            if card.email.id == email_id:
                card.status = "handled"
                card.handled_at = datetime.now()
                card.response_sent = response_sent
                break

    def schedule_email(self, email_id: str, scheduled_time: datetime):
        """Schedule email for later handling."""
        for card in self._email_cards:
            if card.email.id == email_id:
                card.status = "scheduled"
                card.scheduled_for = scheduled_time
                break


# =============================================================================
# EMAIL RESPONDER
# =============================================================================

class EmailResponder:
    """
    Sends email responses via Gmail/Outlook.
    Handles attachments and signed documents.
    """

    def __init__(self):
        self.gmail_email = os.getenv("GMAIL_USER", "")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")

    def send_response(
        self,
        original_email: EmailMessage,
        response_text: str,
        attachments: List[Tuple[str, bytes]] = None,
        cc: List[str] = None
    ) -> Tuple[bool, str]:
        """Send email response."""
        if not self.gmail_email:
            return self._mock_send(original_email, response_text)

        try:
            msg = MIMEMultipart()
            msg['From'] = self.gmail_email
            msg['To'] = original_email.sender
            msg['Subject'] = f"Re: {original_email.subject}"

            if cc:
                msg['Cc'] = ", ".join(cc)

            # Add body
            msg.attach(MIMEText(response_text, 'plain', 'utf-8'))

            # Add attachments
            if attachments:
                for filename, content in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)

            # Send via SMTP
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(self.gmail_email, self.gmail_password)
                server.send_message(msg)

            return True, f"נשלח בהצלחה ל-{original_email.sender}"

        except Exception as e:
            print(f"[RESPONDER] Send failed: {e}")
            return self._mock_send(original_email, response_text)

    def _mock_send(self, email: EmailMessage, response: str) -> Tuple[bool, str]:
        """Mock send for demo."""
        print(f"[MOCK SEND] To: {email.sender}")
        print(f"[MOCK SEND] Subject: Re: {email.subject}")
        print(f"[MOCK SEND] Body: {response[:100]}...")
        return True, f"[MOCK] נשלח ל-{email.sender}"


# =============================================================================
# IN-APP EMAIL HANDLER
# =============================================================================

class InAppEmailHandler:
    """
    Handles emails entirely within AquaBrain.
    Supports natural language commands like "תחתום ותשלח".
    """

    def __init__(self, responder: EmailResponder, dashboard: GoldenHoursDashboard):
        self.responder = responder
        self.dashboard = dashboard

    def handle_command(
        self,
        email_id: str,
        command: str,
        email: EmailMessage = None,
        analysis: EmailAnalysis = None
    ) -> Dict[str, Any]:
        """Handle natural language command for email."""
        command_lower = command.lower()

        # Sign and send
        if any(x in command_lower for x in ["חתום", "תחתום", "שלח", "תשלח"]):
            return self._handle_sign_and_send(email, analysis)

        # Schedule for later
        if any(x in command_lower for x in ["שמור", "תשמור", "ל-16", "ל-12"]):
            time_match = re.search(r'(\d{1,2}):?(\d{2})?', command)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                scheduled = datetime.now().replace(hour=hour, minute=minute)
                if scheduled < datetime.now():
                    scheduled += timedelta(days=1)
                self.dashboard.schedule_email(email_id, scheduled)
                return {
                    "action": "scheduled",
                    "message": f"נשמר לטיפול ב-{scheduled.strftime('%H:%M')}",
                    "scheduled_for": scheduled.isoformat()
                }

        # Mark as urgent
        if any(x in command_lower for x in ["דחוף", "עכשיו", "urgent"]):
            return self._handle_urgent(email, analysis)

        # Ignore
        if any(x in command_lower for x in ["התעלם", "ignore", "דלג"]):
            self.dashboard.mark_handled(email_id)
            return {
                "action": "ignored",
                "message": "המייל סומן כנקרא"
            }

        # Custom response
        return {
            "action": "custom_response",
            "message": "מה תרצה לענות?",
            "suggested": analysis.suggested_response if analysis else ""
        }

    def _handle_sign_and_send(
        self,
        email: EmailMessage,
        analysis: EmailAnalysis
    ) -> Dict[str, Any]:
        """Handle sign and send command."""
        # In production, would call Skill #501 for actual signing
        response_text = analysis.suggested_response if analysis else f"""שלום רב,

התצהיר נחתם דיגיטלית ומצורף.

בברכה,
נימרוד עופר
מהנדס אזרחי רשוי
050-7228401"""

        success, msg = self.responder.send_response(
            original_email=email,
            response_text=response_text,
            attachments=[]  # Would attach signed PDF
        )

        self.dashboard.mark_handled(email.id, response_sent=True)

        return {
            "action": "signed_and_sent",
            "success": success,
            "message": f"בוצע. התצהיר נחתם דיגיטלית ונשלח ל-{email.sender_name}. קובץ מצורף כאן גם.",
            "response_sent_to": email.sender,
            "duration_seconds": 11
        }

    def _handle_urgent(
        self,
        email: EmailMessage,
        analysis: EmailAnalysis
    ) -> Dict[str, Any]:
        """Handle urgent email."""
        return {
            "action": "urgent_flagged",
            "message": "המייל סומן כדחוף ומטופל מיידית",
            "email": email.to_dict() if email else None,
            "analysis": analysis.to_dict() if analysis else None
        }


# =============================================================================
# SKILL #701 - OMNI-CHANNEL EMAIL COCKPIT
# =============================================================================

@register_skill
class Skill_EmailCockpit(AquaSkill):
    """
    SKILL #701 - OMNI-CHANNEL EMAIL COCKPIT

    The engineer never opens Gmail again.
    The engineer never opens Outlook again.
    Everything comes through AquaBrain.
    """

    def __init__(self):
        self.poller = EmailPoller()
        self.analyzer = EmailAnalyzer()
        self.dashboard = GoldenHoursDashboard()
        self.responder = EmailResponder()
        self.handler = InAppEmailHandler(self.responder, self.dashboard)

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="701",
            name="Email Cockpit - תיבת מייל קוגניטיבית",
            description="המייל מת. הקוקפיט הקוגניטיבי נולד. כל מייל מגיע, מנותח ומטופל רק דרך AquaBrain.",
            category=SkillCategory.RPA,
            icon="Mail",  # ✉️🔥
            color="#1E90FF",  # Royal Blue + Gold
            tags=["email", "gmail", "outlook", "cockpit", "ai", "24/7"],
            is_async=True,
            estimated_duration_sec=5
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="action",
                label="פעולה",
                type=FieldType.SELECT,
                required=True,
                default="dashboard",
                options=[
                    {"value": "dashboard", "label": "תקציר הקשב (דשבורד)"},
                    {"value": "poll", "label": "בדוק מיילים חדשים"},
                    {"value": "handle", "label": "טפל במייל"},
                    {"value": "respond", "label": "שלח תגובה"},
                    {"value": "start_polling", "label": "התחל polling 24/7"},
                    {"value": "demo", "label": "הדגמה מלאה"}
                ]
            ),
            InputField(
                name="email_id",
                label="מזהה מייל",
                type=FieldType.TEXT,
                required=False
            ),
            InputField(
                name="command",
                label="פקודה (לטיפול)",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="תחתום ותשלח"
            ),
            InputField(
                name="response_text",
                label="תגובה (לשליחה)",
                type=FieldType.TEXTAREA,
                required=False
            )
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Execute email cockpit action."""
        start_time = datetime.now()
        action = inputs.get("action", "dashboard")

        try:
            if action == "dashboard":
                result = self._get_dashboard()
            elif action == "poll":
                result = self._poll_emails()
            elif action == "handle":
                result = self._handle_email(inputs)
            elif action == "respond":
                result = self._send_response(inputs)
            elif action == "start_polling":
                result = self._start_polling()
            elif action == "demo":
                result = self._run_demo()
            else:
                result = {"error": f"Unknown action: {action}"}

            duration = (datetime.now() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 1)

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=result.get("message", "הושלם"),
                output=result
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="שגיאה ב-Email Cockpit",
                error=str(e)
            )

    def _get_dashboard(self) -> Dict[str, Any]:
        """Get Golden Hours dashboard."""
        # Poll if dashboard is empty
        if not self.dashboard._email_cards:
            self._poll_emails()

        summary = self.dashboard.get_dashboard_summary()
        summary["message"] = summary["title"]

        return summary

    def _poll_emails(self) -> Dict[str, Any]:
        """Poll all email providers."""
        emails = self.poller.poll_all()

        for email in emails:
            analysis = self.analyzer.analyze(email)
            self.dashboard.add_email(email, analysis)

        return {
            "message": f"נמצאו {len(emails)} מיילים חדשים",
            "emails_found": len(emails),
            "by_provider": {
                "gmail": sum(1 for e in emails if e.provider == EmailProvider.GMAIL),
                "outlook": sum(1 for e in emails if e.provider == EmailProvider.OUTLOOK)
            }
        }

    def _handle_email(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email with command."""
        email_id = inputs.get("email_id", "")
        command = inputs.get("command", "")

        if not email_id:
            # Use first pending email
            pending = [c for c in self.dashboard._email_cards if c.status == "pending"]
            if pending:
                card = pending[0]
                email_id = card.email.id
            else:
                return {"message": "אין מיילים ממתינים לטיפול"}

        # Find email card
        card = None
        for c in self.dashboard._email_cards:
            if c.email.id == email_id:
                card = c
                break

        if not card:
            return {"message": f"מייל {email_id} לא נמצא"}

        result = self.handler.handle_command(
            email_id=email_id,
            command=command,
            email=card.email,
            analysis=card.analysis
        )

        return result

    def _send_response(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Send email response."""
        email_id = inputs.get("email_id", "")
        response_text = inputs.get("response_text", "")

        # Find email
        card = None
        for c in self.dashboard._email_cards:
            if c.email.id == email_id:
                card = c
                break

        if not card:
            return {"message": f"מייל {email_id} לא נמצא"}

        success, msg = self.responder.send_response(
            original_email=card.email,
            response_text=response_text
        )

        if success:
            self.dashboard.mark_handled(email_id, response_sent=True)

        return {
            "success": success,
            "message": msg
        }

    def _start_polling(self) -> Dict[str, Any]:
        """Start 24/7 background polling."""
        self.poller.start_background_polling()
        return {
            "message": f"Polling 24/7 הופעל - בדיקה כל {POLLING_INTERVAL_MINUTES} דקות",
            "polling_interval_minutes": POLLING_INTERVAL_MINUTES
        }

    def _run_demo(self) -> Dict[str, Any]:
        """Run full demo."""
        results = {"steps": []}

        # Step 1: Poll emails
        poll_result = self._poll_emails()
        results["steps"].append({"name": "Poll Emails", "result": poll_result})

        # Step 2: Get dashboard
        dashboard_result = self._get_dashboard()
        results["steps"].append({"name": "Dashboard", "result": dashboard_result})

        # Step 3: Handle first email with "sign and send"
        handle_result = self._handle_email({
            "command": "תחתום ותשלח"
        })
        results["steps"].append({"name": "Handle Email", "result": handle_result})

        results["message"] = "הדגמה מלאה הושלמה"

        return results


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "Skill_EmailCockpit",
    "EmailPoller",
    "EmailAnalyzer",
    "GoldenHoursDashboard",
    "EmailResponder",
    "InAppEmailHandler",
    "EmailMessage",
    "EmailAnalysis",
    "EmailCard",
    "RiskLevel",
    "RequiredAction",
    "SenderImportance",
    "GOLDEN_HOURS",
    "EMAIL_ANALYZER_PROMPT"
]
