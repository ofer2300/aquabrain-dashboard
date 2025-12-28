"""
WhatsApp Notification Skill
===========================
Send WhatsApp messages via multiple providers.

Supports:
- Twilio WhatsApp API
- WhatsApp Business API
- CallMeBot (free tier)
"""

from typing import Dict, Any
import os
import urllib.request
import urllib.parse
import json

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
class WhatsAppNotifySkill(AquaSkill):
    """
    Send WhatsApp notifications.

    Useful for alerting engineers about:
    - Completed documents
    - Pipeline status updates
    - Critical warnings
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id="library_whatsapp_notify",
            name="שלח הודעת WhatsApp",
            description="שליחת התראות WhatsApp לטלפון הנייד",
            category=SkillCategory.INTEGRATION,
            icon="MessageCircle",
            color="#25D366",
            version="1.0.0",
            author="AquaBrain",
            tags=["whatsapp", "notification", "messaging", "alert"],
            is_async=False,
            estimated_duration_sec=5,
        )

    @property
    def input_schema(self) -> InputSchema:
        return InputSchema(fields=[
            InputField(
                name="phone",
                label="מספר טלפון",
                type=FieldType.TEXT,
                required=True,
                placeholder="972501234567",
                description="מספר טלפון בפורמט בינלאומי (ללא + או 0)",
            ),
            InputField(
                name="message",
                label="הודעה",
                type=FieldType.TEXTAREA,
                required=True,
                placeholder="התצהיר שלך נוצר בהצלחה!",
                description="תוכן ההודעה לשליחה",
            ),
            InputField(
                name="provider",
                label="ספק",
                type=FieldType.SELECT,
                required=True,
                default="callmebot",
                options=[
                    {"value": "callmebot", "label": "CallMeBot (חינמי)"},
                    {"value": "twilio", "label": "Twilio (בתשלום)"},
                    {"value": "mock", "label": "סימולציה (לבדיקות)"},
                ],
                description="ספק שירות WhatsApp",
            ),
            InputField(
                name="api_key",
                label="מפתח API (אופציונלי)",
                type=FieldType.TEXT,
                required=False,
                description="מפתח API לספק - או מ-ENV",
            ),
        ])

    def execute(self, inputs: Dict[str, Any]) -> ExecutionResult:
        """Send WhatsApp message."""
        phone = inputs.get("phone", "")
        message = inputs.get("message", "")
        provider = inputs.get("provider", "mock")
        api_key = inputs.get("api_key") or os.environ.get("WHATSAPP_API_KEY", "")

        # Clean phone number
        phone = phone.replace("+", "").replace("-", "").replace(" ", "")
        if phone.startswith("0"):
            phone = "972" + phone[1:]

        try:
            if provider == "mock":
                # Simulation mode
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    skill_id=self.metadata.id,
                    message=f"[MOCK] הודעה נשלחה ל-{phone}",
                    output={
                        "sent": True,
                        "phone": phone,
                        "message": message,
                        "provider": "mock",
                        "mock_mode": True,
                    },
                )

            elif provider == "callmebot":
                # CallMeBot free API
                # User needs to register first: https://www.callmebot.com/blog/free-api-whatsapp-messages/
                result = self._send_callmebot(phone, message, api_key)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    skill_id=self.metadata.id,
                    message=f"הודעה נשלחה ל-{phone} דרך CallMeBot",
                    output={
                        "sent": True,
                        "phone": phone,
                        "provider": "callmebot",
                        "response": result,
                    },
                )

            elif provider == "twilio":
                # Twilio WhatsApp API
                result = self._send_twilio(phone, message, api_key)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    skill_id=self.metadata.id,
                    message=f"הודעה נשלחה ל-{phone} דרך Twilio",
                    output={
                        "sent": True,
                        "phone": phone,
                        "provider": "twilio",
                        "sid": result.get("sid"),
                    },
                )

            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    skill_id=self.metadata.id,
                    message=f"ספק לא נתמך: {provider}",
                    error=f"Unknown provider: {provider}",
                )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                skill_id=self.metadata.id,
                message="שליחת ההודעה נכשלה",
                error=str(e),
            )

    def _send_callmebot(self, phone: str, message: str, api_key: str) -> Dict[str, Any]:
        """Send via CallMeBot API."""
        if not api_key:
            raise ValueError("CallMeBot API key required. Get one at callmebot.com")

        url = (
            f"https://api.callmebot.com/whatsapp.php?"
            f"phone={phone}&text={urllib.parse.quote(message)}&apikey={api_key}"
        )

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            return {"status": response.status, "body": response.read().decode()}

    def _send_twilio(self, phone: str, message: str, api_key: str) -> Dict[str, Any]:
        """Send via Twilio WhatsApp API."""
        # api_key format: "ACCOUNT_SID:AUTH_TOKEN:FROM_NUMBER"
        if not api_key:
            api_key = os.environ.get("TWILIO_WHATSAPP_KEY", "")

        if not api_key or ":" not in api_key:
            raise ValueError("Twilio credentials required (ACCOUNT_SID:AUTH_TOKEN:FROM_NUMBER)")

        parts = api_key.split(":")
        if len(parts) != 3:
            raise ValueError("Invalid Twilio key format")

        account_sid, auth_token, from_number = parts

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        data = urllib.parse.urlencode({
            "From": f"whatsapp:+{from_number}",
            "To": f"whatsapp:+{phone}",
            "Body": message,
        }).encode()

        # Create request with basic auth
        import base64
        auth = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
