"""Local C compiler validation - always runs locally."""

import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class CCResult:
    """Result of CC compilation check."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    errors: List[str]
    command: str


def parse_cc_errors(stderr: str) -> List[str]:
    """Extract error messages from cc output."""
    errors = []
    for line in stderr.split("\n"):
        if "error:" in line.lower():
            errors.append(line.strip())
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
            "-std=c11",
            "-fsyntax-only",
        ]

    include_flags = [f"-I{p}" for p in include_paths]
    cmd = ["cc"] + cc_flags + include_flags + [driver_path]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        errors = parse_cc_errors(result.stderr) if result.returncode != 0 else []

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
