"""Argcomplete completers for CLI."""

from ..utils.project_manager import ProjectManager
from ..models.registry import get_model_names


class ProjectCompleter:
    """Completer for project names."""

    def __call__(self, prefix, parsed_args, **kwargs):
        pm = ProjectManager()
        projects = pm.list_projects()
        return [p for p in projects if p.startswith(prefix)]


class FileCompleter:
    """Completer for filenames within a project."""

    def __call__(self, prefix, parsed_args, **kwargs):
        if not hasattr(parsed_args, 'project') or not parsed_args.project:
            return []
        pm = ProjectManager()
        if not pm.project_exists(parsed_args.project):
            return []
        files = pm.list_files(parsed_args.project)
        return [f.name for f in files if f.name.startswith(prefix)]


class ModelCompleter:
    """Completer for model names."""

    def __call__(self, prefix, parsed_args, **kwargs):
        models = get_model_names()
        return [m for m in models if m.startswith(prefix)]
