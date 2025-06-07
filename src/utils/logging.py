import structlog
import logging
import sys
from typing import Any, Dict
from src.config.settings import settings

# Configure standard library logging
# For MCP server, logs should go to stderr to keep stdout clean for JSON-RPC
logging.basicConfig(
    format="%(message)s",
    stream=sys.stderr,
    level=getattr(logging, settings.mcp_log_level.upper()),
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        structlog.dev.ConsoleRenderer() if settings.is_development else structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

def log_error(logger: structlog.BoundLogger, error: Exception, context: Dict[str, Any] = None) -> None:
    """Log an error with context."""
    if context is None:
        context = {}
    
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )