"""Project management utilities."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from ..config import ProjectConfig, FileInfo
from .compilation_db import (
    parse_compilation_database,
    get_project_remote_dir,
    file_info_to_dict,
    dict_to_file_info,
)


class ProjectManager:
    """Manages tisaidga projects."""

    def __init__(self, projects_dir: str = None):
        """
        Initialize project manager.

        Args:
            projects_dir: Directory to store projects. Defaults to .tisaidga/projects
        """
        self.projects_dir = projects_dir or os.path.join(
            os.getcwd(), ".tisaidga", "projects"
        )

    def _get_project_dir(self, project_name: str) -> str:
        """Get the directory path for a project."""
        return os.path.join(self.projects_dir, project_name)

    def _get_project_config_path(self, project_name: str) -> str:
        """Get the path to project.json."""
        return os.path.join(self._get_project_dir(project_name), "project.json")

    def _get_files_dir(self, project_name: str) -> str:
        """Get the path to files directory."""
        return os.path.join(self._get_project_dir(project_name), "files")

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists."""
        return os.path.exists(self._get_project_config_path(project_name))

    def list_projects(self) -> List[str]:
        """List all projects."""
        if not os.path.exists(self.projects_dir):
            return []

        projects = []
        for name in os.listdir(self.projects_dir):
            project_dir = os.path.join(self.projects_dir, name)
            if os.path.isdir(project_dir) and os.path.exists(
                os.path.join(project_dir, "project.json")
            ):
                projects.append(name)

        return sorted(projects)

    def init_project(
        self,
        compilation_db_path: str,
        project_name: str = None,
        ssh_host: str = "",
        ssh_user: str = "",
        tis_env_script: str = "",
    ) -> str:
        """
        Initialize a new project from a compilation database.

        Args:
            compilation_db_path: Path to compile_commands.json
            project_name: Name for the project (defaults to parent directory name)
            ssh_host: SSH host for remote TIS execution
            ssh_user: SSH username
            tis_env_script: Script to source TIS environment

        Returns:
            Project name
        """
        # Parse compilation database
        with open(compilation_db_path, "r") as f:
            raw_entries = json.load(f)

        # Determine project name from directory if not provided
        if not project_name:
            remote_dir = get_project_remote_dir(raw_entries)
            if remote_dir:
                project_name = Path(remote_dir).name
            else:
                project_name = Path(compilation_db_path).stem

        # Parse file info
        files = parse_compilation_database(compilation_db_path)

        # Get common remote directory
        remote_work_dir = get_project_remote_dir(raw_entries) or ""

        # Collect all unique include paths
        all_includes = set()
        for f in files:
            all_includes.update(f.includes)

        # Create project config
        project_config = ProjectConfig(
            name=project_name,
            remote_work_dir=remote_work_dir,
            compilation_db_path=os.path.abspath(compilation_db_path),
            include_paths=sorted(all_includes),
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            tis_env_script=tis_env_script,
        )

        # Create project directory structure
        files_dir = self._get_files_dir(project_name)
        os.makedirs(files_dir, exist_ok=True)

        # Write project config
        config_path = self._get_project_config_path(project_name)
        with open(config_path, "w") as f:
            json.dump(asdict(project_config), f, indent=2)

        # Write individual file info
        for file_info in files:
            # Use safe filename (replace / with _)
            safe_name = file_info.name.replace("/", "_").replace("\\", "_")
            file_path = os.path.join(files_dir, f"{safe_name}.json")
            with open(file_path, "w") as f:
                json.dump(file_info_to_dict(file_info), f, indent=2)

        return project_name

    def get_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Load project configuration."""
        config_path = self._get_project_config_path(project_name)

        if not os.path.exists(config_path):
            return None

        with open(config_path, "r") as f:
            data = json.load(f)

        return ProjectConfig(
            name=data["name"],
            remote_work_dir=data["remote_work_dir"],
            compilation_db_path=data["compilation_db_path"],
            include_paths=data.get("include_paths", []),
            ssh_host=data.get("ssh_host", ""),
            ssh_user=data.get("ssh_user", ""),
            tis_env_script=data.get("tis_env_script", ""),
        )

    def list_files(self, project_name: str) -> List[FileInfo]:
        """List all files in a project."""
        files_dir = self._get_files_dir(project_name)

        if not os.path.exists(files_dir):
            return []

        files = []
        for filename in os.listdir(files_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(files_dir, filename)
                with open(file_path, "r") as f:
                    data = json.load(f)
                files.append(dict_to_file_info(data))

        return sorted(files, key=lambda x: x.name)

    def get_file_info(self, project_name: str, filename: str) -> Optional[FileInfo]:
        """
        Get file info by filename.

        Args:
            project_name: Project name
            filename: Filename to look up (can be base name or full path)

        Returns:
            FileInfo or None if not found
        """
        files = self.list_files(project_name)

        # Try exact match on name first
        for f in files:
            if f.name == filename:
                return f

        # Try match on path
        for f in files:
            if f.path.endswith(filename):
                return f

        return None

    def delete_project(self, project_name: str) -> bool:
        """Delete a project."""
        import shutil

        project_dir = self._get_project_dir(project_name)

        if not os.path.exists(project_dir):
            return False

        shutil.rmtree(project_dir)
        return True
