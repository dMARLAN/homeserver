#!/usr/bin/env python3
"""Startup script for the Photography Server API."""

import uvicorn
import logging

from pgs_api.config import api_config


def main() -> None:
    """Run the FastAPI server."""
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    uvicorn.run(
        "pgs_api.main:app",
        host=api_config.host,
        port=api_config.port,
        reload=api_config.reload,
        workers=api_config.workers if not api_config.reload else None,
        access_log=True,
        log_level=api_config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
