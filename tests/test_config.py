"""Tests for config module."""

import os
from tis_driver_agent.config import (
    ModelConfig,
    SSHConfig,
    TISConfig,
    ProjectConfig,
    FileInfo,
    AgentConfig,
)


def test_model_config_defaults():
    config = ModelConfig()
    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.temperature == 0.7


def test_ssh_config_defaults():
    config = SSHConfig()
    assert config.host == ""
    assert config.user == ""
    assert config.port == 22


def test_tis_config_defaults():
    config = TISConfig()
    assert config.mode == "ssh"
    assert config.tis_path == "tis-analyzer"
    assert config.machdep == "gcc_x86_64"
    assert isinstance(config.ssh, SSHConfig)


def test_project_config():
    config = ProjectConfig(
        name="test-project",
        remote_work_dir="/home/user/test",
        compilation_db_path="/path/to/compile_commands.json",
    )
    assert config.name == "test-project"
    assert config.include_paths == []
    assert config.ssh_host == ""


def test_file_info():
    info = FileInfo(
        name="test.c",
        path="/home/user/test.c",
        directory="/home/user",
        includes=["/usr/include"],
        defines=["DEBUG"],
    )
    assert info.name == "test.c"
    assert len(info.includes) == 1
    assert len(info.defines) == 1


def test_agent_config_defaults():
    config = AgentConfig()
    assert config.max_iterations == 5
    assert isinstance(config.model, ModelConfig)
    assert isinstance(config.tis, TISConfig)
