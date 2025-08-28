#!/usr/bin/env python3
"""Startup script for the Photography Server Sync Worker."""

import asyncio

from pgs_sync.main import main


if __name__ == "__main__":
    asyncio.run(main())
