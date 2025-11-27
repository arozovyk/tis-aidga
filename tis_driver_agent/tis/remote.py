"""Remote TIS runner - connects via SSH."""

from typing import List, Optional

try:
    import paramiko
except ImportError:
    paramiko = None

from .base import TISRunnerBase, TISResult
from ..config import SSHConfig


class RemoteTISRunner(TISRunnerBase):
    """Runs TIS Analyzer on a remote server via SSH."""

    def __init__(
        self,
        ssh_config: SSHConfig,
        remote_work_dir: str,
        machdep: str = "gcc_x86_64",
        timeout: int = 120,
    ):
        if paramiko is None:
            raise ImportError(
                "paramiko is required for SSH mode. Install with: pip install paramiko"
            )

        self.ssh_config = ssh_config
        self.remote_work_dir = remote_work_dir
        self.machdep = machdep
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        """Establish SSH connection."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.ssh_config.host,
            port=self.ssh_config.port,
            username=self.ssh_config.user,
            password=self.ssh_config.password,
        )

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None

    def _run_command(self, command: str, with_tis_env: bool = False) -> tuple:
        """Run a command on remote server."""
        if not self.client:
            self.connect()

        if with_tis_env and self.ssh_config.tis_env_script:
            escaped_cmd = command.replace("'", "'\\''")
            command = f"bash -c '{self.ssh_config.tis_env_script} && {escaped_cmd}'"

        _, stdout, stderr = self.client.exec_command(command, timeout=self.timeout)
        exit_code = stdout.channel.recv_exit_status()

        return stdout.read().decode("utf-8"), stderr.read().decode("utf-8"), exit_code

    def read_remote_file(self, remote_path: str) -> Optional[str]:
        """Read a file from the remote server."""
        command = f"cat {remote_path}"
        stdout, stderr, exit_code = self._run_command(command)

        if exit_code != 0:
            return None

        return stdout

    def find_header_files(self, include_paths: List[str], header_name: str) -> Optional[str]:
        """Find a header file in the given include paths on remote."""
        for inc_path in include_paths:
            full_path = f"{inc_path}/{header_name}"
            # Check if file exists
            stdout, _, exit_code = self._run_command(f"test -f {full_path} && echo exists")
            if exit_code == 0 and "exists" in stdout:
                return full_path
        return None

    def tis_compile(
        self,
        driver_path: str,
        source_files: List[str],
        reference_file: str,
        compilation_db: Optional[str] = None,
    ) -> TISResult:
        """Run TIS Analyzer compilation check on remote."""
        cpp_compile_like = f"{driver_path}:{reference_file}"
        sources = " ".join(source_files)

        cmd_parts = [f"cd {self.remote_work_dir} && tis-analyzer"]

        if compilation_db:
            cmd_parts.append(f"-compilation-database {compilation_db}")

        cmd_parts.extend(
            [
                f"-cpp-compile-like {cpp_compile_like}",
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

            return TISResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                errors=errors,
                command=cmd,
            )
        except Exception as e:
            return TISResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                errors=[str(e)],
                command=cmd,
            )

    def write_driver(self, driver_code: str, driver_path: str) -> bool:
        """Write driver code to remote file."""
        try:
            if not self.client:
                self.connect()

            sftp = self.client.open_sftp()
            full_path = f"{self.remote_work_dir}/{driver_path}"

            with sftp.file(full_path, "w") as f:
                f.write(driver_code)

            sftp.close()
            return True
        except Exception:
            return False

    def cleanup(self, driver_path: str) -> None:
        """Remove temporary driver file on remote."""
        try:
            cmd = f"rm -f {self.remote_work_dir}/{driver_path}"
            self._run_command(cmd)
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
        cmd_parts = [f"cd {self.remote_work_dir} && tis-analyzer"]

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

            # The skeleton is printed to stdout
            return stdout.strip()

        except Exception:
            return None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
