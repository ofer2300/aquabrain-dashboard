"""
AquaBrain Logging System - Enterprise Grade
============================================
Centralized logging with Loguru.

Features:
- Colored console output
- File rotation (500 MB, 10 days retention)
- Standard library interception
- Structured logging support
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path
from loguru import logger

# Log directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "aquabrain.log"


class InterceptHandler(logging.Handler):
    """
    Intercept standard library logging and redirect to Loguru.
    This ensures all logs go through our centralized system.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(
    level: str = "INFO",
    console: bool = True,
    file: bool = True,
    rotation: str = "500 MB",
    retention: str = "10 days",
) -> None:
    """
    Configure the centralized logging system.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Enable colored console output
        file: Enable file logging
        rotation: File rotation size
        retention: Log file retention period
    """
    # Remove default handler
    logger.remove()

    # Console handler with colors
    if console:
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # File handler with rotation
    if file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(LOG_FILE),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Thread-safe
        )

    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Intercept uvicorn and fastapi loggers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]

    logger.info("AquaBrain Logger initialized")
    logger.info(f"Log level: {level}")
    if file:
        logger.info(f"Log file: {LOG_FILE}")


def get_logger(name: str = "aquabrain"):
    """
    Get a named logger instance.

    Usage:
        from core.logger import get_logger
        log = get_logger(__name__)
        log.info("Processing started")
    """
    return logger.bind(name=name)


# Initialize logger on module load with defaults
# Can be reconfigured by calling setup_logger() with custom params
setup_logger(level="DEBUG", console=True, file=True)
