"""Stable source-root anchor for application configuration and persistent data.

Keep this module at agent/config/paths.py during package migration. The inspected
project boundary (AI_PROJECT_ROOT or a user declaration) is deliberately separate.
Importing this module does not load .env, create directories or open databases.
"""
from pathlib import Path

APPLICATION_ROOT = Path(__file__).resolve().parents[2]
