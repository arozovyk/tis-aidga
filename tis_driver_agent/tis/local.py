"""Local TIS runner - assumes tis-analyzer is in PATH."""

import subprocess
import os
from typing import List, Optional

from .base import TISRunnerBase, TISResult


class LocalTISRunner(TISRunnerBase):
    """Runs TIS Analyzer locally."""

    def __init__(
        self,
        tis_path: str = "tis-analyzer",
        machdep: str = "gcc_x86_64",
        timeout: int = 60,
    ):
        self.tis_path = tis_path
        self.machdep = machdep
        self.timeout = timeout

    def tis_compile(
        self,
        driver_path: str,
        source_files: List[str],
        reference_file: str,
        compilation_db: Optional[str] = None,
    ) -> TISResult:
        """Stage 2: TIS Analyzer compilation check."""
        # Build -cpp-compile-like argument
        cpp_compile_like = f"{driver_path}:{reference_file}"

        cmd = [self.tis_path]

        if compilation_db:
            cmd.extend(["-compilation-database", compilation_db])

        cmd.extend(
            [
                "-cpp-compile-like",
                cpp_compile_like,
                driver_path,
                *source_files,
                "-machdep",
                self.machdep,
            ]
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout
            )

            output = result.stdout + result.stderr
            errors = self.parse_tis_errors(output)

            # Success = no compilation errors (UB alarms are OK)
            success = result.returncode == 0 and len(errors) == 0

            return TISResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                errors=errors,
                command=" ".join(cmd),
            )
        except subprocess.TimeoutExpired:
            return TISResult(
                success=False,
                stdout="",
                stderr="TIS analysis timed out",
                exit_code=-1,
                errors=["TIS analysis timed out"],
                command=" ".join(cmd),
            )
        except FileNotFoundError:
            return TISResult(
                success=False,
                stdout="",
                stderr=f"tis-analyzer not found at {self.tis_path}",
                exit_code=-1,
                errors=[f"tis-analyzer not found at {self.tis_path}"],
                command=" ".join(cmd),
            )

    def write_driver(self, driver_code: str, driver_path: str) -> bool:
        """Write driver code to local file."""
        try:
            os.makedirs(os.path.dirname(driver_path), exist_ok=True)
            with open(driver_path, "w") as f:
                f.write(driver_code)
            return True
        except Exception:
            return False

    def cleanup(self, driver_path: str) -> None:
        """Remove temporary driver file."""
        try:
            if os.path.exists(driver_path):
                os.unlink(driver_path)
        except Exception:
            pass
