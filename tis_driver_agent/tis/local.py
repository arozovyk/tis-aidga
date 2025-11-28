"""Local TIS runner - assumes tis-analyzer is in PATH."""

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from .base import TISRunnerBase, TISResult


class LocalTISRunner(TISRunnerBase):
    """Runs TIS Analyzer locally."""

    def __init__(
        self,
        work_dir: str = ".",
        tis_path: str = "tis-analyzer",
        tis_env_script: str = "",
        machdep: str = "gcc_x86_64",
        timeout: int = 120,
    ):
        self.work_dir = os.path.abspath(work_dir)
        self.tis_path = tis_path
        self.tis_env_script = tis_env_script
        self.machdep = machdep
        self.timeout = timeout

    def connect(self) -> None:
        """No-op for local runner (maintains interface compatibility)."""
        pass

    def disconnect(self) -> None:
        """No-op for local runner (maintains interface compatibility)."""
        pass

    def _run_command(self, command: str, with_tis_env: bool = False) -> tuple:
        """Run a command locally."""
        if with_tis_env and self.tis_env_script:
            command = f"bash -c '{self.tis_env_script} && {command}'"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.work_dir,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1
        except Exception as e:
            return "", str(e), -1

    def read_remote_file(self, file_path: str) -> Optional[str]:
        """Read a local file (named for interface compatibility)."""
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception:
            return None

    def find_header_files(self, include_paths: List[str], header_name: str) -> Optional[str]:
        """Find a header file in the given include paths."""
        for inc_path in include_paths:
            full_path = os.path.join(inc_path, header_name)
            if os.path.isfile(full_path):
                return full_path
        return None

    def tis_compile(
        self,
        driver_path: str,
        source_files: List[str],
        reference_file: str,
        compilation_db: Optional[str] = None,
        function_name: Optional[str] = None,
    ) -> TISResult:
        """Run TIS Analyzer value analysis locally."""
        sources = " ".join(source_files)
        info_json_file = "tis_info_results.json"

        # Derive driver entry point from function name or driver path
        if function_name:
            main_entry = f"__tis_{function_name}_driver"
        else:
            match = re.search(r'__tis_driver_(\w+)\.c', driver_path)
            if match:
                main_entry = f"__tis_{match.group(1)}_driver"
            else:
                main_entry = "main"

        cmd_parts = [self.tis_path]

        cmd_parts.extend(
            [
                driver_path,
                sources,
                f"-machdep {self.machdep}",
            ]
        )

        cmd = " ".join(cmd_parts)

        try:
            stdout, stderr, exit_code = self._run_command(cmd, with_tis_env=True)

            output = stdout + stderr
            errors = self.parse_tis_errors(output)
            success = exit_code == 0 and len(errors) == 0

            # Try to fetch and parse the JSON results file
            info_json = self._fetch_info_json(info_json_file)

            return TISResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                errors=errors,
                command=cmd,
                info_json=info_json,
            )
        except Exception as e:
            return TISResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                errors=[str(e)],
                command=cmd,
                info_json=None,
            )

    def _fetch_info_json(self, json_filename: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse the TIS info JSON results file."""
        try:
            json_path = os.path.join(self.work_dir, json_filename)
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    content = f.read()
                # Clean up the file after reading
                os.remove(json_path)
                return json.loads(content)
        except (json.JSONDecodeError, Exception):
            pass
        return None

    def write_driver(self, driver_code: str, driver_path: str) -> bool:
        """Write driver code to local file."""
        try:
            full_path = os.path.join(self.work_dir, driver_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(driver_code)
            return True
        except Exception:
            return False

    def cleanup(self, driver_path: str) -> None:
        """Remove temporary driver file."""
        try:
            full_path = os.path.join(self.work_dir, driver_path)
            if os.path.exists(full_path):
                os.unlink(full_path)
        except Exception:
            pass

    def generate_skeleton(
        self,
        function_name: str,
        source_files: List[str],
        include_paths: List[str],
        compilation_db: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate driver skeleton using tis-analyzer -drivergen-skeleton.

        Args:
            function_name: Name of the function to generate skeleton for
            source_files: List of source files
            include_paths: List of include paths
            compilation_db: Optional path to compilation database

        Returns:
            Generated skeleton code or None if failed
        """
        sources = " ".join(source_files)
        cmd_parts = [self.tis_path]

        if compilation_db:
            cmd_parts.append(f"-compilation-database {compilation_db}")

        cmd_parts.extend(
            [
                sources,
                f"-drivergen-skeleton {function_name}",
                f"-machdep {self.machdep}",
            ]
        )

        cmd = " ".join(cmd_parts)

        try:
            stdout, stderr, exit_code = self._run_command(cmd, with_tis_env=True)

            if exit_code != 0:
                return None

            return self._parse_skeleton_output(stdout)

        except Exception:
            return None

    def _parse_skeleton_output(self, output: str) -> Optional[str]:
        """
        Parse TIS skeleton output to extract only the generated code.

        The output format is:
        [kernel] ... parsing info ...
        [codegen] <code here with indentation>
        [time] ... performance info ...

        Returns:
            Extracted code or None if parsing fails
        """
        lines = output.split('\n')
        code_lines = []
        in_codegen = False

        for line in lines:
            # Start capturing after [codegen]
            if line.startswith('[codegen]'):
                in_codegen = True
                # Extract code from the [codegen] line itself (after the tag)
                code_part = line[len('[codegen]'):].strip()
                if code_part:
                    code_lines.append(code_part)
                continue

            # Stop at [time] or other tags
            if line.startswith('[time]') or line.startswith('[kernel]'):
                if in_codegen:
                    break
                continue

            # Capture indented code lines (TIS indents with spaces)
            if in_codegen:
                # Remove the leading indentation (TIS uses consistent indentation)
                if line.startswith('          '):  # 10 spaces TIS prefix
                    code_lines.append(line[10:])
                elif line.strip() == '':
                    code_lines.append('')  # Preserve empty lines
                else:
                    code_lines.append(line)

        if not code_lines:
            return None

        # Remove trailing empty lines
        while code_lines and not code_lines[-1].strip():
            code_lines.pop()

        return '\n'.join(code_lines)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
