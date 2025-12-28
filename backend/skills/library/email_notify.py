"""
Email Notification Skill
========================
Send email notifications via SMTP.

Supports:
- Gmail SMTP
- Outlook SMTP
- Custom SMTP servers
"""

from typing import Dict, Any
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from skills.base import (
    AquaSkill,
    SkillMetadata,
    InputSchema,
    InputField,
    FieldType,
    SkillCategory,
    ExecutionResult,
    ExecutionStatus,
    register_skill,
)


@register_skill
class EmailNotifySkill(AquaSkill):
    """
    Send email notifications.

    Useful for:
    - Document delivery
    - Status updates
    - Team notifications
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="library_email_notify",
            name="שלח אימייל",
            description="שליחת הודעות דוא\"ל עם קבצים מצורפים",
            category=SkillCategory.INTEGRATION,
            icon="Mail",
            color="#EA4335",
            version="1.0.0",
            author="AquaBrain",
            tags=["email", "notification", "smtp", "gmail"],
            is_async=False,
            estimated_duration_sec=10,
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="to_email",
                label="נמען",
                type=FieldType.EMAIL,
                required=True,
                placeholder="user@example.com",
                description="כתובת האימייל של הנמען",
            ),
            InputField(
                name="subject",
                label="נושא",
                type=FieldType.TEXT,
                required=True,
                placeholder="מסמך חדש מוכן להורדה",
                description="נושא ההודעה",
            ),
            InputField(
                name="body",
                label="תוכן",
                type=FieldType.TEXTAREA,
                required=True,
                placeholder="שלום,\n\nמצורף המסמך המבוקש.",
                description="תוכן ההודעה",
            ),
            InputField(
                name="provider",
                label="ספק",
                type=FieldType.SELECT,
                required=True,
                default="gmail",
                options=[
                    {"value": "gmail", "label": "Gmail"},
                    {"value": "outlook", "label": "Outlook"},
                    {"value": "custom", "label": "SMTP מותאם"},
                    {"value": "mock", "label": "סימולציה"},
                ],
            ),
            InputField(
                name="from_email",
                label="שולח (אופציונלי)",
                type=FieldType.EMAIL,
                required=False,
                description="כתובת השולח - או מ-ENV",
            ),
            InputField(
                name="smtp_password",
                label="סיסמת SMTP (אופציונלי)",
                type=FieldType.TEXT,
                required=False,
                description="סיסמת אפליקציה - או מ-ENV",
            ),
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Send email."""
        to_email = inputs.get("to_email", "")
        subject = inputs.get("subject", "")
        body = inputs.get("body", "")
        provider = inputs.get("provider", "mock")
        from_email = inputs.get("from_email") or os.environ.get("SMTP_FROM_EMAIL", "")
        password = inputs.get("smtp_password") or os.environ.get("SMTP_PASSWORD", "")

        try:
            if provider == "mock":
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    skill_id=self.metadata.id,
                    message=f"[MOCK] אימייל נשלח ל-{to_email}",
                    output={
                        "sent": True,
                        "to": to_email,
                        "subject": subject,
                        "provider": "mock",
                        "mock_mode": True,
                    },
                )

            # Get SMTP settings based on provider
            smtp_settings = self._get_smtp_settings(provider)

            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Send email
            with smtplib.SMTP(smtp_settings["host"], smtp_settings["port"]) as server:
                server.starttls()
                server.login(from_email, password)
                server.sendmail(from_email, to_email, msg.as_string())

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                skill_id=self.metadata.id,
                message=f"אימייל נשלח ל-{to_email}",
                output={
                    "sent": True,
                    "to": to_email,
                    "subject": subject,
                    "provider": provider,
                },
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="שליחת האימייל נכשלה",
                error=str(e),
            )

    def _get_smtp_settings(self, provider: str) -> Dict[str, Any]:
        """Get SMTP settings for provider."""
        settings = {
            "gmail": {"host": "smtp.gmail.com", "port": 587},
            "outlook": {"host": "smtp.office365.com", "port": 587},
            "custom": {
                "host": os.environ.get("SMTP_HOST", "localhost"),
                "port": int(os.environ.get("SMTP_PORT", "587")),
            },
        }
        return settings.get(provider, settings["custom"])
