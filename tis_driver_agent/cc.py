"""Local C compiler validation - always runs locally."""

import os
import re
import subprocess
from dataclasses import dataclass
from typing import List

# Path to TIS stub headers for local CC checks
_STUBS_DIR = os.path.join(os.path.dirname(__file__), "stubs")


@dataclass
class CCResult:
    """Result of CC compilation check."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    errors: List[str]
    command: str


def parse_cc_errors(stderr: str, stdout: str = "") -> List[str]:
    """Extract error messages from cc output.

    Handles multiple compiler error formats:
    - file:line:col: error: message
    - file:line:col: fatal error: message
    - file:line: error: message (no column)
    - error: message (no file location)
    - Clang/GCC specific diagnostics
    """
    errors = []
    seen = set()  # Avoid duplicates

    # Combine stderr and stdout (some compilers output to stdout)
    combined = f"{stderr}\n{stdout}"
    lines = combined.split("\n")

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Skip if already seen
        if line_stripped in seen:
            continue

        # Pattern 1: file:line:col: [fatal] error: message (most common)
        if re.search(r':\d+:.*(?:fatal\s+)?error:', line, re.IGNORECASE):
            errors.append(line_stripped)
            seen.add(line_stripped)
            continue

        # Pattern 2: Just "error:" without file location
        if re.match(r'^error:', line_stripped, re.IGNORECASE):
            errors.append(line_stripped)
            seen.add(line_stripped)
            continue

        # Pattern 3: "N error(s) generated" summary - skip but indicates errors exist
        if re.match(r'^\d+\s+errors?\s+generated', line_stripped, re.IGNORECASE):
            continue

        # Pattern 4: Linker errors (undefined reference, etc.)
        if 'undefined reference' in line.lower() or 'undefined symbol' in line.lower():
            errors.append(line_stripped)
            seen.add(line_stripped)
            continue

        # Pattern 5: ld: errors
        if re.match(r'^ld:', line_stripped) and 'error' in line.lower():
            errors.append(line_stripped)
            seen.add(line_stripped)
            continue

    # Fallback: if compilation failed but no specific errors found
    if not errors and ('error' in combined.lower() or 'fatal' in combined.lower()):
        # Extract any line that looks diagnostic
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped in seen:
                continue
            # Look for diagnostic-like lines
            if any(kw in line.lower() for kw in ['error', 'fatal', 'undefined', 'redefinition', 'undeclared']):
                if len(line_stripped) < 500:  # Reasonable length
                    errors.append(line_stripped)
                    seen.add(line_stripped)
                    if len(errors) >= 10:
                        break

    return errors


def cc_compile(
    driver_path: str,
    include_paths: List[str],
    cc_flags: List[str] = None,
    timeout: int = 60,
) -> CCResult:
    """
    Stage 1: Basic C compilation check using local cc.

    This always runs locally regardless of TIS execution mode.

    Args:
        driver_path: Path to the driver file to compile
        include_paths: List of include paths (-I flags)
        cc_flags: Compiler flags (defaults to strict C11 syntax check)
        timeout: Compilation timeout in seconds

    Returns:
        CCResult with compilation outcome
    """
    if cc_flags is None:
        cc_flags = [
            "-c",
            "-Werror",
            "-Wfatal-errors",
            "-Wno-unknown-attributes",  # Ignore TIS-specific attributes
            "-Wno-visibility",  # Ignore visibility warnings when headers are incomplete
            "-Wno-implicit-function-declaration",  # Allow undeclared functions (may be in missing headers)
            "-std=c11",
            "-fsyntax-only",
        ]

    # Add stubs directory first for TIS-specific headers (tis_builtin.h, etc.)
    include_flags = [f"-I{_STUBS_DIR}"] + [f"-I{p}" for p in include_paths]
    cmd = ["cc"] + cc_flags + include_flags + [driver_path]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        errors = parse_cc_errors(result.stderr, result.stdout) if result.returncode != 0 else []

        return CCResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            errors=errors,
            command=" ".join(cmd),
        )
    except subprocess.TimeoutExpired:
        return CCResult(
            success=False,
            stdout="",
            stderr="Compilation timed out",
            exit_code=-1,
            errors=["Compilation timed out"],
            command=" ".join(cmd),
        )
    except FileNotFoundError:
        return CCResult(
            success=False,
            stdout="",
            stderr="cc compiler not found",
            exit_code=-1,
            errors=["cc compiler not found"],
            command=" ".join(cmd),
        )
