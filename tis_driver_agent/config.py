"""Configuration for TIS Driver Agent."""

from dataclasses import dataclass, field
from typing import List, Optional
import os


@dataclass
class ModelConfig:
    """LLM model configuration."""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )


@dataclass
class SSHConfig:
    """SSH connection configuration."""

    host: str = ""
    user: str = ""
    password: str = field(default_factory=lambda: os.getenv("SSH_PASSWORD", ""))
    port: int = 22
    tis_env_script: str = ""  # Script to source TIS environment


@dataclass
class TISConfig:
    """TIS Analyzer configuration."""

    mode: str = "ssh"  # "local" or "ssh"

    # Local mode settings
    tis_path: str = "tis-analyzer"

    # SSH mode settings
    ssh: SSHConfig = field(default_factory=SSHConfig)
    remote_work_dir: str = ""

    # TIS settings
    machdep: str = "gcc_x86_64"


@dataclass
class ProjectConfig:
    """Project-level configuration stored in project.json."""

    name: str
    remote_work_dir: str  # Remote directory on SSH host where project lives
    compilation_db_path: str  # Original path to compile_commands.json
    include_paths: List[str] = field(default_factory=list)

    # SSH settings (can override global)
    ssh_host: str = ""
    ssh_user: str = ""
    tis_env_script: str = ""


@dataclass
class FileInfo:
    """Information about a source file extracted from compilation database."""

    name: str  # Base filename (e.g., "json_object.c")
    path: str  # Full path on remote (e.g., "/home/user/work/json-c/json_object.c")
    directory: str  # Working directory for compilation
    includes: List[str] = field(default_factory=list)  # Include paths (-I flags)
    defines: List[str] = field(default_factory=list)  # Preprocessor defines (-D flags)


@dataclass
class AgentConfig:
    """Main agent configuration."""

    model: ModelConfig = field(default_factory=ModelConfig)
    tis: TISConfig = field(default_factory=TISConfig)
    max_iterations: int = 5
    projects_dir: str = field(
        default_factory=lambda: os.path.join(os.getcwd(), ".tischiron", "projects")
    )
