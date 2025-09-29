# utils/logger.py
from loguru import logger
import sys
from pathlib import Path
import json

class FactCheckerLogger:
    """Centralized logging with structured output for testing"""

    def __init__(self, log_level: str = "DEBUG"):
        # Remove default handler
        logger.remove()

        # Console handler with color coding
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )

        # File handler for all logs
        logger.add(
            "logs/fact_checker_{time:YYYY-MM-DD}.log",
            rotation="500 MB",
            retention="10 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )

        # Separate file for errors only
        logger.add(
            "logs/errors_{time:YYYY-MM-DD}.log",
            rotation="100 MB",
            retention="30 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )

        # JSON structured logs for testing/analysis
        logger.add(
            "logs/structured_{time:YYYY-MM-DD}.jsonl",
            rotation="500 MB",
            retention="10 days",
            level="INFO",
            serialize=True
        )

        self.logger = logger

    def log_component_start(self, component: str, **kwargs):
        """Log component execution start with context"""
        self.logger.info(
            f"🚀 STARTING: {component}",
            extra={
                "component": component,
                "action": "start",
                **kwargs
            }
        )

    def log_component_complete(self, component: str, duration: float, **kwargs):
        """Log component completion with metrics"""
        self.logger.info(
            f"✅ COMPLETED: {component} in {duration:.2f}s",
            extra={
                "component": component,
                "action": "complete",
                "duration": duration,
                **kwargs
            }
        )

    def log_component_error(self, component: str, error: Exception, **kwargs):
        """Log component errors with full context"""
        self.logger.error(
            f"❌ ERROR in {component}: {str(error)}",
            extra={
                "component": component,
                "action": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                **kwargs
            }
        )

    def log_langchain_trace(self, run_id: str, component: str, inputs: dict, outputs: dict):
        """Log LangChain execution details"""
        self.logger.debug(
            f"🔗 LANGCHAIN TRACE: {component}",
            extra={
                "component": component,
                "run_id": run_id,
                "inputs": inputs,
                "outputs": outputs,
                "action": "langchain_trace"
            }
        )

# Global logger instance
fact_logger = FactCheckerLogger()