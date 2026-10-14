"""Shared configuration for the MCP server.

The database path is the single source of truth for which SQLite file the
server talks to. It always points at the working copy, never the original.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_PATH = ROOT / os.environ.get("DATABASE_PATH", "data/campus_customs_new.db")
