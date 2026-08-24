"""Development entrypoint: ``python run.py`` (or ``uvicorn app.main:app``)."""

from __future__ import annotations

import uvicorn

from app.config import get_settings
from app.logging_config import configure_logging

if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
