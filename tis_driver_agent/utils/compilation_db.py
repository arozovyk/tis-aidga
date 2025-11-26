"""Compilation database parser."""

import json
import re
import shlex
from dataclasses import asdict
from typing import List, Dict, Optional
from pathlib import Path

from ..config import FileInfo


def parse_compilation_database(db_path: str) -> List[FileInfo]:
    """
    Parse a compile_commands.json file and extract file information.

    Args:
        db_path: Path to compile_commands.json

    Returns:
        List of FileInfo objects with file metadata
    """
    with open(db_path, "r") as f:
        entries = json.load(f)

    # Deduplicate by file path (some files appear multiple times)
    seen_files: Dict[str, FileInfo] = {}

    for entry in entries:
        file_path = entry.get("file", "")
        directory = entry.get("directory", "")
        command = entry.get("command", "")

        if not file_path:
            continue

        # Skip if already processed
        if file_path in seen_files:
            continue

        # Parse includes and defines from command
        includes = parse_includes_from_command(command)
        defines = parse_defines_from_command(command)

        # Get base filename
        name = Path(file_path).name

        file_info = FileInfo(
            name=name,
            path=file_path,
            directory=directory,
            includes=includes,
            defines=defines,
        )

        seen_files[file_path] = file_info

    return list(seen_files.values())


def parse_includes_from_command(command: str) -> List[str]:
    """Extract -I include paths from a compilation command."""
    includes = []

    # Try to parse with shlex for proper handling of quoted paths
    try:
        parts = shlex.split(command)
    except ValueError:
        # Fallback to regex if shlex fails
        pattern = r"-I\s*([^\s]+)"
        return re.findall(pattern, command)

    i = 0
    while i < len(parts):
        part = parts[i]
        if part == "-I" and i + 1 < len(parts):
            includes.append(parts[i + 1])
            i += 2
        elif part.startswith("-I"):
            includes.append(part[2:])
            i += 1
        else:
            i += 1

    return includes


def parse_defines_from_command(command: str) -> List[str]:
    """Extract -D preprocessor defines from a compilation command."""
    defines = []

    try:
        parts = shlex.split(command)
    except ValueError:
        pattern = r"-D\s*([^\s]+)"
        return re.findall(pattern, command)

    i = 0
    while i < len(parts):
        part = parts[i]
        if part == "-D" and i + 1 < len(parts):
            defines.append(parts[i + 1])
            i += 2
        elif part.startswith("-D"):
            defines.append(part[2:])
            i += 1
        else:
            i += 1

    return defines


def get_project_remote_dir(entries: List[dict]) -> Optional[str]:
    """
    Determine the common remote working directory from compilation entries.

    Args:
        entries: Raw entries from compile_commands.json

    Returns:
        Common directory path or None
    """
    if not entries:
        return None

    # Get all directories
    directories = [e.get("directory", "") for e in entries if e.get("directory")]

    if not directories:
        return None

    # Find common prefix
    common = directories[0]
    for d in directories[1:]:
        while not d.startswith(common) and common:
            common = str(Path(common).parent)

    return common if common else None


def file_info_to_dict(file_info: FileInfo) -> dict:
    """Convert FileInfo to dictionary for JSON serialization."""
    return asdict(file_info)


def dict_to_file_info(data: dict) -> FileInfo:
    """Create FileInfo from dictionary."""
    return FileInfo(
        name=data["name"],
        path=data["path"],
        directory=data["directory"],
        includes=data.get("includes", []),
        defines=data.get("defines", []),
    )
