"""Legacy RAG commands launch the supported console without provider-specific loops."""
from pathlib import Path
import sys


def launch_console():
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from agent.langgraph.langgraph_agent import main
    return main()
