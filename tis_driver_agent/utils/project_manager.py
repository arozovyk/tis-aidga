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

    def get_index_path(self, project_name: str) -> str:
        """Get path to context_index.db for a project."""
        project_dir = self._get_project_dir(project_name)
        return os.path.join(project_dir, "context_index.db")

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
        skip_index: bool = False,
    ):
        """
        Initialize a new project from a compilation database.

        Args:
            compilation_db_path: Path to compile_commands.json
            project_name: Name for the project (defaults to parent directory name)
            ssh_host: SSH host for remote TIS execution
            ssh_user: SSH username
            tis_env_script: Script to source TIS environment
            skip_index: Skip building AST index

        Returns:
            Tuple of (project_name, index_stats)
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

        # Build AST index
        index_stats = {"functions": 0, "types": 0, "files": 0, "build_time": 0.0}

        if not skip_index:
            try:
                from ..context.index import build_index
                from ..config import FileInfo as ConfigFileInfo
                import time
                import glob

                index_path = self.get_index_path(project_name)
                start_time = time.time()

                # Collect header files to index (for doxygen comments)
                files_to_index = list(files)
                header_paths_seen = set()

                for f in files:
                    # Find matching header in same directory
                    src_dir = os.path.dirname(f.path)
                    base_name = os.path.splitext(os.path.basename(f.path))[0]

                    # Look for .h files in same dir and include paths
                    search_dirs = [src_dir] + list(all_includes)
                    for search_dir in search_dirs:
                        for ext in ['.h', '_internal.h']:
                            header_path = os.path.join(search_dir, base_name + ext)
                            if header_path not in header_paths_seen and os.path.exists(header_path):
                                header_paths_seen.add(header_path)
                                files_to_index.append(ConfigFileInfo(
                                    name=os.path.basename(header_path),
                                    path=header_path,
                                    directory=search_dir,
                                    includes=[],
                                ))

                    # Also look for any .h files in the source directory
                    for h_file in glob.glob(os.path.join(src_dir, '*.h')):
                        if h_file not in header_paths_seen:
                            header_paths_seen.add(h_file)
                            files_to_index.append(ConfigFileInfo(
                                name=os.path.basename(h_file),
                                path=h_file,
                                directory=src_dir,
                                includes=[],
                            ))

                index_stats = build_index(
                    files=files_to_index,
                    db_path=index_path,
                )
                index_stats["build_time"] = time.time() - start_time

            except ImportError as e:
                # tree-sitter not installed - warn but continue
                print(f"Note: AST indexing skipped ({e})")
            except Exception as e:
                # Index building failed - warn but don't fail init
                import traceback
                print(f"Warning: Failed to build AST index: {e}")
                traceback.print_exc()

        # Check if indexing found any files
        if not skip_index and index_stats.get("files", 0) == 0 and len(files) > 0:
            print(f"Warning: No source files could be read for indexing.")
            print(f"  Files are at remote paths (e.g., {files[0].path})")
            print(f"  AST indexing requires local access to source files.")

        return project_name, index_stats

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

    def get_source_file_paths(
        self, project_name: str, exclude_tests: bool = True
    ) -> List[str]:
        """
        Get all source file paths for a project.

        Args:
            project_name: Project name
            exclude_tests: If True, exclude test files

        Returns:
            List of absolute file paths
        """
        files = self.list_files(project_name)
        paths = []

        for f in files:
            # Optionally exclude test files
            if exclude_tests:
                name_lower = f.name.lower()
                path_lower = f.path.lower()
                # Skip files starting with 'test' or in test directories
                if name_lower.startswith("test"):
                    continue
                if "/tests/" in path_lower or "/test/" in path_lower:
                    continue
            paths.append(f.path)

        return paths

    def get_index_stats(self, project_name: str) -> Optional[dict]:
        """Get statistics about the project's AST index."""
        index_path = self.get_index_path(project_name)

        if not os.path.exists(index_path):
            return None

        try:
            from ..context.index import get_index_stats
            return get_index_stats(index_path)
        except ImportError:
            return None
