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


def extract_function(content: str, function_name: str) -> Optional[str]:
    """
    Extract a complete function definition using brace counting.

    Args:
        content: Source file content
        function_name: Name of the function to extract

    Returns:
        Complete function code (signature + body) or None if not found
    """
    # Pattern to find function definition start
    # Matches: return_type [*] function_name(params) with possible whitespace/newlines before {
    pattern = rf"(\w+(?:\s*\*)*\s+\*?\s*{re.escape(function_name)}\s*\([^)]*\))\s*\{{"
    match = re.search(pattern, content)

    if not match:
        return None

    # Get the signature
    signature = match.group(1)

    # Find where the opening brace is
    brace_start = match.end() - 1  # Position of '{'

    # Count braces to find the end of the function
    brace_count = 1
    pos = brace_start + 1
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escape_next = False

    while pos < len(content) and brace_count > 0:
        char = content[pos]
        prev_char = content[pos - 1] if pos > 0 else ''

        # Handle escape sequences
        if escape_next:
            escape_next = False
            pos += 1
            continue

        if char == '\\' and (in_string or in_char):
            escape_next = True
            pos += 1
            continue

        # Handle comments
        if not in_string and not in_char:
            if in_line_comment:
                if char == '\n':
                    in_line_comment = False
                pos += 1
                continue

            if in_block_comment:
                if char == '/' and prev_char == '*':
                    in_block_comment = False
                pos += 1
                continue

            # Check for comment start
            if char == '/' and pos + 1 < len(content):
                next_char = content[pos + 1]
                if next_char == '/':
                    in_line_comment = True
                    pos += 2
                    continue
                elif next_char == '*':
                    in_block_comment = True
                    pos += 2
                    continue

        # Handle strings and chars
        if not in_line_comment and not in_block_comment:
            if char == '"' and not in_char:
                in_string = not in_string
            elif char == "'" and not in_string:
                in_char = not in_char

            # Count braces only outside strings/chars/comments
            if not in_string and not in_char:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

        pos += 1

    if brace_count != 0:
        # Unbalanced braces - return None
        return None

    # Extract the complete function
    func_start = match.start()
    func_end = pos

    return content[func_start:func_end]
