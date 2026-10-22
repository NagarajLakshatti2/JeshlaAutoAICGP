"""Separate immutable installed code from settings and persistent runtime data.

Source checkouts keep their historical data location. Installed wheels default
outside site-packages. JESHLA_HOME must be set before startup, independently of
AI_PROJECT_ROOT, which selects a repository to inspect. Importing creates no
folders, loads no .env and opens no databases.
"""
import os
from pathlib import Path

APPLICATION_ROOT = Path(__file__).resolve().parents[2]


def resolve_data_root(package_root, *, environ=None, platform=None, user_home=None):
    """Resolve startup paths without relying on cwd or probing write access."""
    values = os.environ if environ is None else environ
    selected = values.get("JESHLA_HOME", "").strip()
    if selected:
        result = Path(selected).expanduser()
        if not result.is_absolute():
            raise ValueError("JESHLA_HOME must be an absolute directory path.")
        return result.resolve()
    root = Path(package_root).resolve()
    if (root / "pyproject.toml").is_file() and (root / "agent/config/paths.py").is_file():
        return root
    windows = (os.name if platform is None else platform) == "nt"
    home = Path.home() if user_home is None else Path(user_home)
    variable = "LOCALAPPDATA" if windows else "XDG_DATA_HOME"
    base = values.get(variable, "").strip()
    if base:
        parent = Path(base).expanduser()
        if not parent.is_absolute():
            raise ValueError(variable + " must be an absolute directory path.")
    else:
        parent = home / "AppData/Local" if windows else home / ".local/share"
    return (parent / ("JeshlaAutoAI" if windows else "jeshlaautoai")).resolve()


DATA_ROOT = resolve_data_root(APPLICATION_ROOT)
