"""Abstract base class for TIS runners."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class TISResult:
    """Result of TIS compilation/analysis."""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    errors: List[str]
    command: str


class TISRunnerBase(ABC):
    """Abstract base for TIS execution backends."""

    @abstractmethod
    def tis_compile(
        self,
        driver_path: str,
        source_files: List[str],
        reference_file: str,
        compilation_db: Optional[str] = None,
    ) -> TISResult:
        """Run TIS Analyzer compilation check."""
        pass

    @abstractmethod
    def write_driver(self, driver_code: str, driver_path: str) -> bool:
        """Write driver code to file."""
        pass

    @abstractmethod
    def cleanup(self, driver_path: str) -> None:
        """Clean up temporary files."""
        pass

    def parse_tis_errors(self, output: str) -> List[str]:
        """Extract compilation errors from TIS output (not UB alarms).

        Handles multiple TIS error formats:
        - [kernel] Error EAP124: ... (error codes with multiline context)
        - [kernel] error: ... (simple errors)
        - [kernel] user error: ... (user errors)
        - [kernel] TrustInSoft Kernel aborted: ... (fatal errors)
        - Preprocessing/parsing failures
        """
        errors = []
        lines = output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i]

            # Pattern 1: [kernel] Error CODE: (e.g., Error EAP124:)
            # These are often multiline - capture until next [kernel] or [time] line
            error_code_match = re.match(r'\[kernel\]\s+Error\s+(\w+):\s*(.+)', line, re.IGNORECASE)
            if error_code_match:
                error_code = error_code_match.group(1)
                error_msg = error_code_match.group(2).strip()

                # Collect continuation lines (indented lines that follow)
                context_lines = [f"[{error_code}] {error_msg}"]
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # Stop at next [kernel], [time], or non-indented line
                    if re.match(r'\[(kernel|time|value)\]', next_line):
                        break
                    if next_line.strip() and not next_line.startswith(' '):
                        break
                    if next_line.strip():
                        context_lines.append(next_line.strip())
                    i += 1

                errors.append('\n'.join(context_lines))
                continue

            # Pattern 2: [kernel] error: or [kernel] user error: (simple format)
            simple_error = re.match(r'\[kernel\]\s+(?:user\s+)?error:\s*(.+)', line, re.IGNORECASE)
            if simple_error:
                errors.append(simple_error.group(1).strip())
                i += 1
                continue

            # Pattern 3: [kernel] TrustInSoft Kernel aborted: (fatal error)
            abort_match = re.match(r'\[kernel\]\s+TrustInSoft Kernel aborted:\s*(.+)', line, re.IGNORECASE)
            if abort_match:
                errors.append(f"TIS aborted: {abort_match.group(1).strip()}")
                i += 1
                continue

            # Pattern 4: Preprocessing/syntax errors (file:line:col: error:)
            file_error = re.match(r'(.+?:\d+:\d*:?\s*(?:fatal\s+)?error:\s*.+)', line, re.IGNORECASE)
            if file_error:
                errors.append(file_error.group(1).strip())
                i += 1
                continue

            # Pattern 5: [kernel] failure or [kernel] fatal
            fatal_match = re.match(r'\[kernel\]\s+(failure|fatal):\s*(.+)', line, re.IGNORECASE)
            if fatal_match:
                errors.append(f"{fatal_match.group(1)}: {fatal_match.group(2).strip()}")
                i += 1
                continue

            i += 1

        # Fallback: if no errors found but output suggests failure, extract key info
        if not errors:
            # Check for common failure indicators
            if 'aborted' in output.lower() or 'fatal' in output.lower() or 'error' in output.lower():
                # Try to extract any line with error-like keywords
                for line in lines:
                    line = line.strip()
                    if any(kw in line.lower() for kw in ['error', 'fatal', 'aborted', 'failed', 'failure']):
                        # Skip noise lines
                        if '[time]' in line.lower() or 'performance' in line.lower():
                            continue
                        if line and len(line) < 500:  # Reasonable length
                            errors.append(line)
                            if len(errors) >= 5:  # Limit fallback errors
                                break

        return errors
