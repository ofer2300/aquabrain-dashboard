"""
AquaBrain Mei Avivim (מי אביבים) Submission Bot
================================================
Automated submission of fire sprinkler plans to Mei Avivim water utility.
Handles login, 2FA via email OTP, navigation, and file upload.

This is a Web Agent / RPA skill that automates bureaucratic processes.
"""

import os
import asyncio
from datetime import datetime
from typing import Optional
from pathlib import Path

from skills.base import AquaSkill, ExecutionResult, SkillMetadata, register_skill

# Alias for clarity
SkillResult = ExecutionResult


@register_skill
class MeiAvivimBot(AquaSkill):
    """
    Automated submission bot for Mei Avivim (מי אביבים) water utility.

    This skill:
    1. Logs into the Mei Avivim portal
    2. Handles 2FA by intercepting email OTP
    3. Navigates to submission form
    4. Uploads the sprinkler plan PDF
    5. Returns confirmation screenshot
    """

    metadata = SkillMetadata(
        id="rpa_mei_avivim",
        name="Mei Avivim Submission Bot",
        name_he="בוט הגשה למי אביבים",
        description="Automates fire sprinkler plan submission to Mei Avivim water utility",
        description_he="מגיש באופן אוטומטי תוכניות ספרינקלרים לתאגיד מי אביבים",
        category="rpa",
        icon="Globe",
        version="1.0.0",
        author="AquaBrain",
        tags=["rpa", "automation", "mei-avivim", "water", "submission"],
        requires_auth=True,
        estimated_duration_seconds=120
    )

    # Mei Avivim Portal URLs (placeholder - replace with actual URLs)
    LOGIN_URL = "https://www.mei-avivim.co.il/login"
    SUBMISSION_URL = "https://www.mei-avivim.co.il/submissions/new"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["project_id", "pdf_path"],
            "properties": {
                "project_id": {
                    "type": "string",
                    "title": "מזהה פרויקט",
                    "description": "Project identifier for the submission"
                },
                "pdf_path": {
                    "type": "string",
                    "title": "נתיב לקובץ PDF",
                    "description": "Path to the PDF file to upload"
                },
                "description": {
                    "type": "string",
                    "title": "תיאור ההגשה",
                    "description": "Optional description for the submission",
                    "default": "תוכנית מערכת ספרינקלרים - הוכן ע״י AquaBrain"
                },
                "headless": {
                    "type": "boolean",
                    "title": "מצב רקע",
                    "description": "Run browser in headless mode (no visible window)",
                    "default": True
                }
            }
        }

    async def execute(self, inputs: dict, context: dict) -> SkillResult:
        """
        Execute the Mei Avivim submission automation.

        Args:
            inputs: Contains project_id, pdf_path, description, headless
            context: Execution context

        Returns:
            SkillResult with screenshot and confirmation details
        """
        project_id = inputs.get("project_id", "UNKNOWN")
        pdf_path = inputs.get("pdf_path", "")
        description = inputs.get("description", "תוכנית מערכת ספרינקלרים - הוכן ע״י AquaBrain")
        headless = inputs.get("headless", True)

        # Validate PDF exists
        if pdf_path and not Path(pdf_path).exists():
            return SkillResult(
                success=False,
                error=f"PDF file not found: {pdf_path}",
                data={"stage": "validation"}
            )

        # Load credentials from environment
        user_id = os.getenv("MEI_AVIVIM_ID")
        user_email = os.getenv("MEI_AVIVIM_EMAIL")

        if not user_id or not user_email:
            return SkillResult(
                success=False,
                error="Mei Avivim credentials not configured. Set MEI_AVIVIM_ID and MEI_AVIVIM_EMAIL in .env",
                data={"stage": "credentials"}
            )

        try:
            # Try to import Playwright
            from playwright.async_api import async_playwright
        except ImportError:
            return SkillResult(
                success=False,
                error="Playwright not installed. Run: pip install playwright && playwright install chromium",
                data={"stage": "dependencies"}
            )

        # Create screenshots directory
        screenshots_dir = Path("output/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"mei_avivim_{project_id}_{timestamp}.png"

        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=headless)
                page = await browser.new_page()

                # Step 1: Navigate to login
                await page.goto(self.LOGIN_URL)
                await page.wait_for_load_state("networkidle")

                # Step 2: Fill login form
                await page.fill('input[name="id"]', user_id)
                await page.fill('input[name="email"]', user_email)
                await page.click('button[type="submit"]')

                # Step 3: Wait for OTP request and intercept from email
                from services.email_reader import get_email_reader

                email_reader = get_email_reader()
                otp_code, otp_status = email_reader.get_mei_avivim_otp(timeout_seconds=90)

                if not otp_code:
                    await browser.close()
                    return SkillResult(
                        success=False,
                        error=f"Failed to get OTP: {otp_status}",
                        data={"stage": "otp"}
                    )

                # Step 4: Fill OTP
                await page.fill('input[name="otp"]', otp_code)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle")

                # Step 5: Navigate to submission form
                await page.goto(self.SUBMISSION_URL)
                await page.wait_for_load_state("networkidle")

                # Step 6: Fill submission form
                await page.fill('input[name="project_id"]', project_id)
                await page.fill('textarea[name="description"]', description)

                # Step 7: Upload PDF
                if pdf_path:
                    file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(pdf_path)

                # Step 8: Submit
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle")

                # Step 9: Take screenshot of confirmation
                await page.screenshot(path=str(screenshot_path), full_page=True)

                # Check for success indicators
                success_element = await page.query_selector('.success-message, .confirmation')
                is_success = success_element is not None

                await browser.close()

                return SkillResult(
                    success=is_success,
                    data={
                        "stage": "completed",
                        "project_id": project_id,
                        "screenshot_path": str(screenshot_path),
                        "confirmation": "הגשה הושלמה בהצלחה" if is_success else "יש לבדוק את צילום המסך",
                        "timestamp": timestamp
                    },
                    message="הגשה למי אביבים הושלמה בהצלחה!" if is_success else "ההגשה הסתיימה - בדוק צילום מסך"
                )

        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                data={
                    "stage": "execution_error",
                    "project_id": project_id,
                    "screenshot_path": str(screenshot_path) if screenshot_path.exists() else None
                }
            )


# Mock implementation for testing without actual browser
class MeiAvivimBotMock(MeiAvivimBot):
    """Mock version for testing without browser automation."""

    metadata = SkillMetadata(
        id="rpa_mei_avivim_mock",
        name="Mei Avivim Bot (Mock)",
        name_he="בוט מי אביבים (דמו)",
        description="Mock version for testing",
        description_he="גרסת דמו לבדיקות",
        category="rpa",
        icon="Globe",
        version="1.0.0-mock",
        author="AquaBrain",
        tags=["rpa", "mock", "testing"]
    )

    async def execute(self, inputs: dict, context: dict) -> SkillResult:
        """Mock execution that simulates the submission flow."""
        project_id = inputs.get("project_id", "DEMO-001")
        pdf_path = inputs.get("pdf_path", "")

        # Simulate processing time
        await asyncio.sleep(2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return SkillResult(
            success=True,
            data={
                "stage": "completed",
                "mode": "MOCK",
                "project_id": project_id,
                "screenshot_path": f"output/screenshots/mei_avivim_MOCK_{timestamp}.png",
                "confirmation": "הגשה הושלמה בהצלחה (מצב דמו)",
                "timestamp": timestamp,
                "simulated_steps": [
                    "התחברות לאתר מי אביבים",
                    "הזנת קוד אימות מהמייל",
                    "מילוי טופס הגשה",
                    f"העלאת קובץ: {pdf_path or 'ללא קובץ'}",
                    "שליחת הטופס",
                    "צילום מסך אישור"
                ]
            },
            message="[MOCK MODE] הגשה למי אביבים הושלמה בהצלחה!"
        )


# Register mock version too
register_skill(MeiAvivimBotMock)
