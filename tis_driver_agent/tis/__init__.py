"""TIS Runner factory."""

from .base import TISRunnerBase, TISResult
from .local import LocalTISRunner
from .remote import RemoteTISRunner
from ..config import SSHConfig


def create_tis_runner(config) -> TISRunnerBase:
    """Create appropriate TIS runner based on config."""
    if config.tis.mode == "ssh":
        return RemoteTISRunner(
            ssh_config=config.tis.ssh,
            remote_work_dir=config.tis.remote_work_dir,
            machdep=config.tis.machdep,
        )
    else:
        return LocalTISRunner(
            tis_path=config.tis.tis_path,
            machdep=config.tis.machdep,
        )


__all__ = [
    "TISRunnerBase",
    "TISResult",
    "LocalTISRunner",
    "RemoteTISRunner",
    "SSHConfig",
    "create_tis_runner",
]
