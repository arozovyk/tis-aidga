"""CLI helper functions."""

import os
from typing import Optional

from dotenv import load_dotenv


def load_env_files():
    """Load .env from multiple locations (first found wins for each var)."""
    # Priority: cwd > ~/.config/tischiron/.env > ~/.tischiron.env
    load_dotenv()  # Current working directory

    config_dir = os.path.expanduser("~/.config/tischiron/.env")
    if os.path.exists(config_dir):
        load_dotenv(config_dir)

    home_env = os.path.expanduser("~/.tischiron.env")
    if os.path.exists(home_env):
        load_dotenv(home_env)


def read_file_local_first(
    path: str,
    tis_runner=None,
    include_paths: list = None,
    verbose: bool = False,
) -> Optional[str]:
    """
    Read a file, trying local first then remote.

    Args:
        path: File path to read
        tis_runner: Optional TIS runner for remote reading
        include_paths: Include paths to search for headers
        verbose: Print debug info

    Returns:
        File content or None if not found
    """
    # Try local first
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception:
            pass

    # If it's a header name (not a full path), search in include paths
    if include_paths and not os.path.isabs(path):
        for inc_path in include_paths:
            full_path = os.path.join(inc_path, path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r") as f:
                        return f.read()
                except Exception:
                    pass

    # Try remote via TIS runner
    if tis_runner:
        content = tis_runner.read_remote_file(path)
        if content:
            return content

        # Try finding header in include paths remotely
        if include_paths and not os.path.isabs(path):
            header_path = tis_runner.find_header_files(include_paths, path)
            if header_path:
                return tis_runner.read_remote_file(header_path)

    return None
