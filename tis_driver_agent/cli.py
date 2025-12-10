"""CLI entry point for TIS Driver Agent (legacy module location).

This module is kept for backwards compatibility.
The actual implementation is now in tis_driver_agent/cli/__init__.py
"""
# PYTHON_ARGCOMPLETE_OK

from .cli import main

if __name__ == "__main__":
    main()
