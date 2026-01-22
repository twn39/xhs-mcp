import logging
import structlog
import orjson
from typing import Optional

def configure_logging():
    """Configure structlog with orjson serialization and file output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(serializer=lambda v, **kw: orjson.dumps(v, **kw).decode()),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=open("log.txt", "a", encoding="utf-8")),
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        cache_logger_on_first_use=True,
    )

def get_logger(name: Optional[str] = None):
    return structlog.get_logger(name)
