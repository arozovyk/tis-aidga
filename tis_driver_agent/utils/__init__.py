"""Utility modules for TIS Driver Agent."""

from .context_detector import (
    detect_context_files_from_content,
    extract_function_signature,
    extract_function,
    parse_includes,
)
from .compilation_db import (
    parse_compilation_database,
    parse_includes_from_command,
    parse_defines_from_command,
    get_project_remote_dir,
    file_info_to_dict,
    dict_to_file_info,
)
from .project_manager import ProjectManager
from .context_builder import ContextBuilder

__all__ = [
    "detect_context_files_from_content",
    "extract_function_signature",
    "extract_function",
    "parse_includes",
    "parse_compilation_database",
    "parse_includes_from_command",
    "parse_defines_from_command",
    "get_project_remote_dir",
    "file_info_to_dict",
    "dict_to_file_info",
    "ProjectManager",
    "ContextBuilder",
]
