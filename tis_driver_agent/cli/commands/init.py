"""Init command - initialize a project from a compilation database."""

import os
import sys

from ...utils.project_manager import ProjectManager


def cmd_init(args):
    """Initialize a project from a compilation database."""
    pm = ProjectManager()

    # Check if compilation database exists
    if not os.path.exists(args.compilation_db):
        print(f"Error: Compilation database not found: {args.compilation_db}")
        sys.exit(1)

    # Initialize project (now includes indexing)
    project_name, index_stats = pm.init_project(
        compilation_db_path=args.compilation_db,
        project_name=args.name,
        ssh_host=args.ssh_host or "",
        ssh_user=args.ssh_user or "",
        tis_env_script=args.tis_env_script or "",
        skip_index=getattr(args, 'no_index', False),
    )

    print(f"Project '{project_name}' initialized successfully!")

    # Show summary
    config = pm.get_project_config(project_name)
    files = pm.list_files(project_name)

    print(f"\nRemote work dir: {config.remote_work_dir}")
    print(f"Files indexed: {len(files)}")

    # Show index stats
    if index_stats.get("functions", 0) > 0:
        print(f"\nAST Index:")
        print(f"  Functions: {index_stats['functions']}")
        print(f"  Types: {index_stats['types']}")
        print(f"  Built in: {index_stats['build_time']:.1f}s")
    elif getattr(args, 'no_index', False):
        print("\nAST Index: skipped (--no-index)")
    elif index_stats.get("files", 0) == 0 and len(files) > 0:
        print("\nAST Index: no files accessible (source files are remote)")
        print("  Run 'tischiron reindex' after syncing files locally")
    else:
        print("\nAST Index: not available")

    if args.verbose:
        print("\nFiles:")
        for f in files[:10]:
            print(f"  - {f.name}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
