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
        """Extract compilation errors from TIS output (not UB alarms)."""
        errors = []
        # Only match [kernel] error: lines, not warnings/alarms
        pattern = r"\[kernel\] (?:user )?error: (.+)"
        matches = re.findall(pattern, output)
        errors.extend(matches)
        return errors
