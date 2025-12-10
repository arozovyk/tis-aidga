"""Reindex command - rebuild AST index for a project."""

import os
import glob
import time

from ...utils.project_manager import ProjectManager
from ...config import FileInfo as ConfigFileInfo


def cmd_reindex(args):
    """Rebuild AST index for a project."""
    pm = ProjectManager()

    if not pm.project_exists(args.project):
        print(f"Error: Project '{args.project}' not found")
        return 1

    try:
        from ...context.index import build_index

        # Get files from project
        files = pm.list_files(args.project)
        config = pm.get_project_config(args.project)
        index_path = pm.get_index_path(args.project)

        # Collect header files to index (for doxygen comments)
        files_to_index = list(files)
        header_paths_seen = set()

        for f in files:
            src_dir = os.path.dirname(f.path)

            # Look for any .h files in the source directory
            for h_file in glob.glob(os.path.join(src_dir, '*.h')):
                if h_file not in header_paths_seen and os.path.exists(h_file):
                    header_paths_seen.add(h_file)
                    files_to_index.append(ConfigFileInfo(
                        name=os.path.basename(h_file),
                        path=h_file,
                        directory=src_dir,
                        includes=[],
                    ))

        print(f"Reindexing {len(files_to_index)} files ({len(files)} sources + {len(header_paths_seen)} headers)...")
        start_time = time.time()

        stats = build_index(
            files=files_to_index,
            db_path=index_path,
        )

        elapsed = time.time() - start_time

        print("\nIndex rebuilt successfully!")
        print(f"  Functions: {stats['functions']}")
        print(f"  Types: {stats['types']}")
        print(f"  Time: {elapsed:.1f}s")

    except ImportError as e:
        print(f"Error: tree-sitter not available ({e})")
        print("Install with: pip install tree-sitter tree-sitter-c")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0
