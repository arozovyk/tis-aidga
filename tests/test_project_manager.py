"""Tests for ProjectManager."""

import json
import tempfile
import os
import shutil
import pytest
from tis_driver_agent.utils import ProjectManager


@pytest.fixture
def temp_projects_dir():
    """Create a temporary directory for projects."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_compile_commands(temp_projects_dir):
    """Create a sample compile_commands.json."""
    db_path = os.path.join(temp_projects_dir, "compile_commands.json")
    entries = [
        {
            "directory": "/home/user/myproject",
            "command": "gcc -I/home/user/myproject/include -DDEBUG -c src/main.c",
            "file": "/home/user/myproject/src/main.c",
        },
        {
            "directory": "/home/user/myproject",
            "command": "gcc -I/home/user/myproject/include -c src/utils.c",
            "file": "/home/user/myproject/src/utils.c",
        },
    ]
    with open(db_path, "w") as f:
        json.dump(entries, f)
    return db_path


class TestProjectManager:
    def test_init_default_path(self):
        pm = ProjectManager()
        assert ".tisaidga/projects" in pm.projects_dir

    def test_init_custom_path(self, temp_projects_dir):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        assert pm.projects_dir == temp_projects_dir

    def test_list_projects_empty(self, temp_projects_dir):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        projects = pm.list_projects()
        assert projects == []

    def test_init_project(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        name = pm.init_project(
            compilation_db_path=sample_compile_commands,
            project_name="test-project",
            ssh_host="192.168.1.1",
            ssh_user="testuser",
        )

        assert name == "test-project"
        assert pm.project_exists("test-project")

    def test_list_projects_after_init(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        pm.init_project(sample_compile_commands, project_name="proj1")
        pm.init_project(sample_compile_commands, project_name="proj2")

        projects = pm.list_projects()
        assert "proj1" in projects
        assert "proj2" in projects

    def test_get_project_config(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        pm.init_project(
            sample_compile_commands,
            project_name="myproj",
            ssh_host="host.example.com",
            ssh_user="user",
        )

        config = pm.get_project_config("myproj")
        assert config is not None
        assert config.name == "myproj"
        assert config.ssh_host == "host.example.com"
        assert config.ssh_user == "user"
        assert config.remote_work_dir == "/home/user/myproject"

    def test_get_project_config_nonexistent(self, temp_projects_dir):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        config = pm.get_project_config("nonexistent")
        assert config is None

    def test_list_files(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        pm.init_project(sample_compile_commands, project_name="filetest")

        files = pm.list_files("filetest")
        assert len(files) == 2
        names = [f.name for f in files]
        assert "main.c" in names
        assert "utils.c" in names

    def test_get_file_info_by_name(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        pm.init_project(sample_compile_commands, project_name="fileinfo")

        info = pm.get_file_info("fileinfo", "main.c")
        assert info is not None
        assert info.name == "main.c"
        assert "/home/user/myproject/include" in info.includes

    def test_get_file_info_nonexistent(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        pm.init_project(sample_compile_commands, project_name="test")

        info = pm.get_file_info("test", "nonexistent.c")
        assert info is None

    def test_delete_project(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        pm.init_project(sample_compile_commands, project_name="todelete")

        assert pm.project_exists("todelete")
        result = pm.delete_project("todelete")
        assert result is True
        assert not pm.project_exists("todelete")

    def test_delete_nonexistent_project(self, temp_projects_dir):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        result = pm.delete_project("nonexistent")
        assert result is False

    def test_auto_project_name(self, temp_projects_dir, sample_compile_commands):
        pm = ProjectManager(projects_dir=temp_projects_dir)
        name = pm.init_project(sample_compile_commands)
        # Should derive name from directory: /home/user/myproject -> myproject
        assert name == "myproject"
