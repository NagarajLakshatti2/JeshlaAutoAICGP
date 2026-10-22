"""Compatibility alias for agent.tools.web_page_worker."""
import sys
from agent.tools import web_page_worker as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
