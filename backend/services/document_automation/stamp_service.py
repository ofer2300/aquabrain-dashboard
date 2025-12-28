"""
Stamp Service
=============
Handles dynamic stamp embedding in PDF documents.

Uses pdf-lib equivalent in Python (PyPDF2 + reportlab) for:
- Embedding stamp images at specific positions
- Adding dynamic text overlays (date, name, ID)
- Supporting transparent PNG stamps
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from io import BytesIO

# Try to import PDF libraries
try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[STAMP] PDF libraries not available (PyPDF2, reportlab)")


class StampService:
    """
    Service for embedding stamps and signatures in PDF documents.

    Features:
    - Embeds PNG/JPEG stamp images
    - Adds dynamic text (date, engineer details)
    - Positions stamp at configurable location
    - Supports transparency
    """

    DEFAULT_POSITION = (400, 100)  # Bottom right area (x, y in points)
    DEFAULT_SIZE = (150, 80)  # Width, Height in points

    def __init__(
        self,
        position: Tuple[int, int] = None,
        size: Tuple[int, int] = None,
    ):
        """
        Initialize stamp service.

        Args:
            position: (x, y) position in points from bottom-left
            size: (width, height) of stamp in points
        """
        self.position = position or self.DEFAULT_POSITION
        self.size = size or self.DEFAULT_SIZE

    def embed_stamp(
        self,
        pdf_bytes: bytes,
        stamp_image_path: str,
        engineer_name: str,
        engineer_id: str,
        signature_date: Optional[datetime] = None,
        page_numbers: Optional[list] = None,
    ) -> bytes:
        """
        Embed stamp image and text into PDF.

        Args:
            pdf_bytes: Original PDF as bytes
            stamp_image_path: Path to stamp image (PNG/JPEG)
            engineer_name: Name to display below stamp
            engineer_id: ID number to display
            signature_date: Date to display (defaults to today)
            page_numbers: List of page numbers to stamp (0-indexed), None = last page only

        Returns:
            Modified PDF as bytes
        """
        if not PDF_SUPPORT:
            print("[STAMP] PDF support not available, returning original")
            return pdf_bytes

        if not os.path.exists(stamp_image_path):
            print(f"[STAMP] Image not found: {stamp_image_path}")
            return pdf_bytes

        date = signature_date or datetime.now()
        date_str = date.strftime("%d/%m/%Y")
        hebrew_date = self._format_hebrew_date(date)

        try:
            # Read original PDF
            pdf_reader = PdfReader(BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()

            # Determine which pages to stamp
            total_pages = len(pdf_reader.pages)
            if page_numbers is None:
                # Default: last page only
                pages_to_stamp = {total_pages - 1}
            else:
                pages_to_stamp = set(page_numbers)

            # Process each page
            for i, page in enumerate(pdf_reader.pages):
                if i in pages_to_stamp:
                    # Create overlay with stamp
                    overlay = self._create_stamp_overlay(
                        page_size=(float(page.mediabox.width), float(page.mediabox.height)),
                        stamp_image_path=stamp_image_path,
                        engineer_name=engineer_name,
                        engineer_id=engineer_id,
                        date_str=date_str,
                    )
                    # Merge overlay onto page
                    page.merge_page(PdfReader(BytesIO(overlay)).pages[0])

                pdf_writer.add_page(page)

            # Write to bytes
            output = BytesIO()
            pdf_writer.write(output)
            output.seek(0)

            print(f"[STAMP] Successfully embedded stamp on pages {pages_to_stamp}")
            return output.read()

        except Exception as e:
            print(f"[STAMP] Error embedding stamp: {e}")
            return pdf_bytes

    def _create_stamp_overlay(
        self,
        page_size: Tuple[float, float],
        stamp_image_path: str,
        engineer_name: str,
        engineer_id: str,
        date_str: str,
    ) -> bytes:
        """
        Create a PDF overlay with stamp image and text.

        Returns PDF bytes containing just the stamp elements.
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=page_size)

        x, y = self.position
        width, height = self.size

        # Draw stamp image
        try:
            img = ImageReader(stamp_image_path)
            c.drawImage(
                img,
                x, y + 30,  # Position above text
                width=width,
                height=height,
                mask='auto',  # Enable transparency
                preserveAspectRatio=True,
            )
        except Exception as e:
            print(f"[STAMP] Error drawing image: {e}")

        # Add text below stamp
        c.setFont("Helvetica", 9)

        # Engineer name
        c.drawString(x, y + 20, engineer_name)

        # ID number
        c.drawString(x, y + 8, f"ת.ז: {engineer_id}")

        # Date
        c.drawString(x, y - 4, f"תאריך: {date_str}")

        c.save()
        buffer.seek(0)
        return buffer.read()

    def _format_hebrew_date(self, date: datetime) -> str:
        """
        Format date in Hebrew style.
        For now, returns standard format. Can be enhanced with pyluach.
        """
        months_he = [
            "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
            "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
        ]
        return f"{date.day} ב{months_he[date.month - 1]} {date.year}"

    @staticmethod
    def is_available() -> bool:
        """Check if PDF stamping is available."""
        return PDF_SUPPORT


def create_signed_pdf(
    pdf_path: str,
    stamp_path: str,
    engineer_profile: dict,
    output_path: Optional[str] = None,
) -> str:
    """
    Convenience function to stamp a PDF file.

    Args:
        pdf_path: Path to input PDF
        stamp_path: Path to stamp image
        engineer_profile: Dict with full_name, id_number
        output_path: Path for output (default: adds _signed suffix)

    Returns:
        Path to signed PDF
    """
    service = StampService()

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    signed_bytes = service.embed_stamp(
        pdf_bytes=pdf_bytes,
        stamp_image_path=stamp_path,
        engineer_name=engineer_profile.get('full_name', ''),
        engineer_id=engineer_profile.get('id_number', ''),
    )

    if not output_path:
        base, ext = os.path.splitext(pdf_path)
        output_path = f"{base}_signed{ext}"

    with open(output_path, 'wb') as f:
        f.write(signed_bytes)

    return output_path
