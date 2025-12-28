"""
Document Automation Service
===========================
Generates engineering documents with dynamic stamps and signatures.

Supports:
- DOCX template processing with placeholder replacement
- PDF generation with embedded stamps
- Dynamic date/time insertion
- Hebrew text support (RTL)
"""

from .generator import DocumentGenerator
from .templates import TemplateManager
from .stamp_service import StampService

__all__ = ['DocumentGenerator', 'TemplateManager', 'StampService']
