"""
AquaBrain Email OTP Reader Service
===================================
Intercepts OTP codes from emails for 2FA automation.
Supports Gmail via IMAP.
"""

import os
import re
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta
from imap_tools import MailBox, AND
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailOTPReader:
    """
    Email reader for intercepting OTP (One-Time Password) codes.
    Used for automating 2FA authentication flows.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        imap_server: str = "imap.gmail.com"
    ):
        """
        Initialize the email OTP reader.

        Args:
            email: Gmail address (defaults to GMAIL_USER env var)
            password: Gmail App Password (defaults to GMAIL_APP_PASSWORD env var)
            imap_server: IMAP server address
        """
        self.email = email or os.getenv("GMAIL_USER")
        self.password = password or os.getenv("GMAIL_APP_PASSWORD")
        self.imap_server = imap_server

        if not self.email or not self.password:
            raise ValueError(
                "Gmail credentials not configured. "
                "Set GMAIL_USER and GMAIL_APP_PASSWORD in .env file."
            )

    def get_latest_otp(
        self,
        sender_contains: str = "",
        subject_contains: str = "",
        timeout_seconds: int = 60,
        poll_interval: int = 5,
        otp_pattern: str = r"\b(\d{4,8})\b"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Wait for and extract an OTP code from a new email.

        Args:
            sender_contains: Filter emails by sender (partial match)
            subject_contains: Filter emails by subject (partial match)
            timeout_seconds: Maximum time to wait for the email
            poll_interval: Seconds between mailbox checks
            otp_pattern: Regex pattern to extract OTP (default: 4-8 digit number)

        Returns:
            Tuple of (otp_code, email_subject) or (None, error_message)
        """
        start_time = time.time()
        check_from_time = datetime.now() - timedelta(minutes=2)

        print(f"[EmailOTP] Waiting for OTP from '{sender_contains}' (timeout: {timeout_seconds}s)")

        while time.time() - start_time < timeout_seconds:
            try:
                with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                    # Build search criteria
                    criteria = AND(date_gte=check_from_time.date())

                    # Fetch recent emails
                    for msg in mailbox.fetch(criteria, reverse=True, limit=10):
                        # Check sender filter
                        if sender_contains and sender_contains.lower() not in msg.from_.lower():
                            continue

                        # Check subject filter
                        if subject_contains and subject_contains.lower() not in msg.subject.lower():
                            continue

                        # Check if email is recent enough
                        if msg.date and msg.date < check_from_time:
                            continue

                        # Extract OTP from email body
                        email_text = msg.text or msg.html or ""
                        otp_match = re.search(otp_pattern, email_text)

                        if otp_match:
                            otp_code = otp_match.group(1)
                            print(f"[EmailOTP] Found OTP: {otp_code} from '{msg.subject}'")
                            return (otp_code, msg.subject)

            except Exception as e:
                print(f"[EmailOTP] Error checking mailbox: {e}")

            # Wait before next poll
            print(f"[EmailOTP] No OTP found yet, waiting {poll_interval}s...")
            time.sleep(poll_interval)

        return (None, f"Timeout: No OTP received within {timeout_seconds} seconds")

    def get_mei_avivim_otp(self, timeout_seconds: int = 90) -> Tuple[Optional[str], Optional[str]]:
        """
        Specifically get OTP from Mei Avivim (מי אביבים).

        Args:
            timeout_seconds: Maximum time to wait

        Returns:
            Tuple of (otp_code, status_message)
        """
        return self.get_latest_otp(
            sender_contains="mei-avivim",
            subject_contains="",
            timeout_seconds=timeout_seconds,
            otp_pattern=r"\b(\d{6})\b"  # Mei Avivim uses 6-digit codes
        )


# Singleton instance for easy import
email_otp_reader: Optional[EmailOTPReader] = None


def get_email_reader() -> EmailOTPReader:
    """Get or create the email OTP reader singleton."""
    global email_otp_reader
    if email_otp_reader is None:
        try:
            email_otp_reader = EmailOTPReader()
        except ValueError as e:
            print(f"[EmailOTP] Warning: {e}")
            raise
    return email_otp_reader


def get_latest_otp(
    sender_contains: str = "",
    timeout_seconds: int = 60
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convenience function to get OTP without instantiating the class.

    Args:
        sender_contains: Filter by sender
        timeout_seconds: Timeout in seconds

    Returns:
        Tuple of (otp_code, status_message)
    """
    reader = get_email_reader()
    return reader.get_latest_otp(
        sender_contains=sender_contains,
        timeout_seconds=timeout_seconds
    )


# Export for easy import
__all__ = [
    'EmailOTPReader',
    'get_email_reader',
    'get_latest_otp',
]
