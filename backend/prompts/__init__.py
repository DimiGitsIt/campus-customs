"""Loads shared_rules.md + a per-agent prompt file from disk (no inlined
duplicate prompt text in Python)."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent
SHARED_RULES = (PROMPTS_DIR / "shared_rules.md").read_text(encoding="utf-8")


def load_instructions(agent_file_name: str) -> str:
    agent_text = (PROMPTS_DIR / agent_file_name).read_text(encoding="utf-8")
    return f"{SHARED_RULES}\n\n{agent_text}"
