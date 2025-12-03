"""
AquaBrain Web Agent Service
============================
Base class for web automation / RPA tasks.
Provides common functionality for browser automation with Playwright.
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


class AgentStatus(Enum):
    """Status of a web agent execution."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    NAVIGATING = "navigating"
    FILLING_FORM = "filling_form"
    WAITING_OTP = "waiting_otp"
    UPLOADING = "uploading"
    SUBMITTING = "submitting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentStep:
    """A single step in the agent's workflow."""
    name: str
    status: AgentStatus
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result of a web agent execution."""
    success: bool
    steps: List[AgentStep] = field(default_factory=list)
    final_screenshot: Optional[str] = None
    confirmation_number: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    total_duration_seconds: float = 0


class WebAgent(ABC):
    """
    Base class for web automation agents.

    Provides common functionality:
    - Browser management (Playwright)
    - Screenshot capture
    - Step tracking
    - Error handling
    - OTP interception integration
    """

    def __init__(
        self,
        name: str = "WebAgent",
        headless: bool = True,
        screenshot_dir: str = "output/screenshots",
        timeout_ms: int = 30000
    ):
        self.name = name
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.timeout_ms = timeout_ms
        self.steps: List[AgentStep] = []
        self.browser = None
        self.page = None

        # Ensure screenshot directory exists
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize the browser."""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(self.timeout_ms)
            self._log_step("initialize", AgentStatus.INITIALIZING)
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()

    def _log_step(
        self,
        name: str,
        status: AgentStatus,
        screenshot_path: Optional[str] = None,
        error: Optional[str] = None,
        data: Optional[Dict] = None
    ):
        """Log a step in the agent's workflow."""
        step = AgentStep(
            name=name,
            status=status,
            timestamp=datetime.now(),
            screenshot_path=screenshot_path,
            error=error,
            data=data or {}
        )
        self.steps.append(step)
        print(f"[{self.name}] Step: {name} - Status: {status.value}")

    async def take_screenshot(self, name: str) -> str:
        """Take a screenshot and return the path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{name}_{timestamp}.png"
        path = self.screenshot_dir / filename
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def navigate(self, url: str, wait_for: str = "networkidle"):
        """Navigate to a URL."""
        self._log_step(f"navigate_to_{url[:30]}", AgentStatus.NAVIGATING)
        await self.page.goto(url)
        await self.page.wait_for_load_state(wait_for)

    async def fill_form(self, fields: Dict[str, str]):
        """Fill multiple form fields."""
        self._log_step("fill_form", AgentStatus.FILLING_FORM, data={"fields": list(fields.keys())})
        for selector, value in fields.items():
            await self.page.fill(selector, value)

    async def click_and_wait(self, selector: str, wait_for: str = "networkidle"):
        """Click an element and wait for navigation."""
        await self.page.click(selector)
        await self.page.wait_for_load_state(wait_for)

    async def upload_file(self, selector: str, file_path: str):
        """Upload a file to a file input."""
        self._log_step("upload_file", AgentStatus.UPLOADING, data={"file": file_path})
        file_input = await self.page.query_selector(selector)
        if file_input:
            await file_input.set_input_files(file_path)
        else:
            raise ValueError(f"File input not found: {selector}")

    async def wait_for_otp(
        self,
        sender_contains: str = "",
        timeout_seconds: int = 90
    ) -> Optional[str]:
        """Wait for OTP from email."""
        self._log_step("wait_for_otp", AgentStatus.WAITING_OTP)
        try:
            from services.email_reader import get_email_reader
            reader = get_email_reader()
            otp, status = reader.get_latest_otp(
                sender_contains=sender_contains,
                timeout_seconds=timeout_seconds
            )
            return otp
        except Exception as e:
            self._log_step("otp_error", AgentStatus.FAILED, error=str(e))
            return None

    @abstractmethod
    async def run(self, **kwargs) -> AgentResult:
        """
        Run the agent's main workflow.
        Must be implemented by subclasses.
        """
        pass

    async def execute(self, **kwargs) -> AgentResult:
        """
        Execute the agent with proper initialization and cleanup.
        """
        start_time = datetime.now()

        try:
            await self.initialize()
            result = await self.run(**kwargs)
            result.steps = self.steps
            result.total_duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        except Exception as e:
            self._log_step("execution_error", AgentStatus.FAILED, error=str(e))
            return AgentResult(
                success=False,
                steps=self.steps,
                error=str(e),
                total_duration_seconds=(datetime.now() - start_time).total_seconds()
            )

        finally:
            await self.cleanup()


# Example implementation for testing
class DemoWebAgent(WebAgent):
    """Demo agent for testing the framework."""

    def __init__(self):
        super().__init__(name="DemoAgent", headless=True)

    async def run(self, url: str = "https://example.com", **kwargs) -> AgentResult:
        """Demo workflow: navigate to a page and take a screenshot."""
        await self.navigate(url)
        screenshot = await self.take_screenshot("demo_page")

        return AgentResult(
            success=True,
            final_screenshot=screenshot,
            data={"url": url, "title": await self.page.title()}
        )


__all__ = [
    'WebAgent',
    'AgentStatus',
    'AgentStep',
    'AgentResult',
    'DemoWebAgent',
]
