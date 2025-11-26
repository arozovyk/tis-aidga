"""Automatic context file detection."""

import re
from typing import List, Optional


def detect_context_files_from_content(
    source_content: str,
    function_name: str,
) -> List[str]:
    """
    Parse #include directives from source content to identify headers.

    Args:
        source_content: Content of the source file
        function_name: Name of the function to generate driver for

    Returns:
        List of header names (not full paths)
    """
    return parse_includes(source_content)


def parse_includes(content: str) -> List[str]:
    """Parse #include directives from C source content."""
    includes = []

    # Match both #include "file.h" and #include <file.h>
    pattern = r'#include\s*[<"]([^>"]+)[>"]'
    matches = re.findall(pattern, content)
    includes.extend(matches)

    return includes


def extract_function_signature(content: str, function_name: str) -> Optional[str]:
    """Extract function signature from file content."""
    # Pattern to match function declaration/definition
    # Matches: return_type [*] function_name(params)
    pattern = rf"(\w+(?:\s*\*)*\s+\*?\s*{re.escape(function_name)}\s*\([^)]*\))"
    match = re.search(pattern, content)

    if match:
        return match.group(1).strip()

    return None
