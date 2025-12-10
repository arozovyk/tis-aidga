"""List command - list projects or files in a project."""

import sys

from ...utils.project_manager import ProjectManager


def cmd_list(args):
    """List projects or files in a project."""
    pm = ProjectManager()

    if args.project:
        # List files in a project
        if not pm.project_exists(args.project):
            print(f"Error: Project '{args.project}' not found")
            sys.exit(1)

        files = pm.list_files(args.project)
        config = pm.get_project_config(args.project)

        print(f"Project: {args.project}")
        print(f"Remote dir: {config.remote_work_dir}")
        print(f"\nFiles ({len(files)}):")

        for f in files:
            print(f"  {f.name}")
            if args.verbose:
                print(f"    Path: {f.path}")
                if f.includes:
                    print(f"    Includes: {', '.join(f.includes[:3])}")

        # Show index status
        index_stats = pm.get_index_stats(args.project)
        if index_stats:
            print(f"\nAST Index:")
            print(f"  Functions: {index_stats['functions']}")
            print(f"  Types: {index_stats['types']}")
            print(f"  Last indexed: {index_stats.get('last_indexed', 'unknown')}")
        else:
            print(f"\nAST Index: not built")
    else:
        # List all projects
        projects = pm.list_projects()

        if not projects:
            print("No projects found. Use 'tischiron init <compile_commands.json>' to create one.")
            return

        print("Projects:")
        for p in projects:
            config = pm.get_project_config(p)
            files = pm.list_files(p)
            print(f"  {p} ({len(files)} files) - {config.remote_work_dir}")
