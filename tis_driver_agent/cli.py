"""CLI entry point for TIS Driver Agent."""
# PYTHON_ARGCOMPLETE_OK

import argparse
import os
import sys

import argcomplete
from dotenv import load_dotenv

from .config import AgentConfig, ModelConfig, TISConfig, SSHConfig
from .models.openai_adapter import OpenAIAdapter
from .models.ollama_adapter import OllamaAdapter
from .tis.remote import RemoteTISRunner
from .tis.local import LocalTISRunner

# Known Ollama model prefixes (for auto-detection)
OLLAMA_MODELS = [
    "llama",
    "mistral",
    "gemma",
    "codellama",
    "deepseek",
    "qwen",
    "phi",
    "vicuna",
    "orca",
    "neural-chat",
    "starling",
    "dolphin",
]
from .graph import create_workflow
from .utils.project_manager import ProjectManager
from .utils.context_detector import (
    parse_includes,
    extract_function_signature,
    extract_function,
)
from .workflow_logger import (
    WorkflowLogger,
    StructuredLogger,
    set_logger,
    set_structured_logger,
    get_structured_logger,
)

# Load environment variables from .env file
load_dotenv()


def read_file_local_first(path: str, tis_runner=None, include_paths=None, verbose=False):
    """
    Read a file, trying local first then remote.

    Args:
        path: File path to read
        tis_runner: Optional TIS runner for remote reading
        include_paths: Include paths to search for headers
        verbose: Print debug info

    Returns:
        File content or None if not found
    """
    # Try local first
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception:
            pass

    # If it's a header name (not a full path), search in include paths
    if include_paths and not os.path.isabs(path):
        for inc_path in include_paths:
            full_path = os.path.join(inc_path, path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r") as f:
                        return f.read()
                except Exception:
                    pass

    # Try remote via TIS runner
    if tis_runner:
        content = tis_runner.read_remote_file(path)
        if content:
            return content

        # Try finding header in include paths remotely
        if include_paths and not os.path.isabs(path):
            header_path = tis_runner.find_header_files(include_paths, path)
            if header_path:
                return tis_runner.read_remote_file(header_path)

    return None


# Custom completers for argcomplete
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
        models = [
            # OpenAI - Cheap models (<$0.40/1M input)
            "gpt-4o-mini",      # $0.15 input, $0.60 output - proven, widely used
            "gpt-4.1-mini",     # $0.40 input, $1.60 output - newer, improved
            "gpt-4.1-nano",     # $0.10 input, $0.40 output - very cheap
            "gpt-5-nano",       # $0.05 input, $0.40 output - cheapest
            "gpt-5-mini",       # $0.25 input, $2.00 output - gpt-5 architecture
            # OpenAI - Premium models
            "gpt-4o",
            "gpt-4-turbo",
            # Ollama - Local models (free)
            "llama3.2:latest",
            "llama3.2:1b-instruct-fp16",
            "mistral:7b-instruct",
            "gemma3:12b-it-q4_K_M",
            "codellama:latest",
            "deepseek-coder:latest",
        ]
        return [m for m in models if m.startswith(prefix)]


def is_ollama_model(model: str) -> bool:
    """Check if a model should use Ollama adapter."""
    model_lower = model.lower()
    for prefix in OLLAMA_MODELS:
        if model_lower.startswith(prefix):
            return True
    return False


def create_model_adapter(model: str, api_key: str = None, temperature: float = 0.7, ollama_url: str = None):
    """Create the appropriate model adapter based on model name."""
    if is_ollama_model(model):
        adapter = OllamaAdapter(
            model=model,
            base_url=ollama_url or "http://localhost:11434",
            temperature=temperature,
        )
        # Verify Ollama is available
        if not adapter.is_available():
            print(f"Warning: Ollama model '{model}' may not be available.")
            print("Make sure Ollama is running: `ollama serve`")
            print(f"And the model is pulled: `ollama pull {model}`")
        return adapter
    else:
        return OpenAIAdapter(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )


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


def cmd_gen(args):
    """Generate a driver for a function."""
    pm = ProjectManager()

    # Check project exists
    if not pm.project_exists(args.project):
        print(f"Error: Project '{args.project}' not found")
        sys.exit(1)

    # Get project config
    project_config = pm.get_project_config(args.project)

    # Find the file
    file_info = pm.get_file_info(args.project, args.filename)
    if not file_info:
        print(f"Error: File '{args.filename}' not found in project '{args.project}'")
        print("\nAvailable files:")
        for f in pm.list_files(args.project)[:10]:
            print(f"  - {f.name}")
        sys.exit(1)

    # Resolve SSH settings (priority: CLI args > project config > env vars)
    ssh_host = args.ssh_host or project_config.ssh_host or os.getenv("SSH_HOST", "")
    ssh_user = args.ssh_user or project_config.ssh_user or os.getenv("SSH_USER", "")
    ssh_password = os.getenv("SSH_PASSWORD", "")
    tis_env_script = args.tis_env_script or project_config.tis_env_script or os.getenv("TIS_ENV_SCRIPT", "")

    # Determine mode: local if SSH not configured, otherwise SSH
    use_local_mode = not ssh_host or not ssh_user

    # Build SSH config (may be empty for local mode)
    ssh_config = SSHConfig(
        host=ssh_host,
        user=ssh_user,
        password=ssh_password,
        tis_env_script=tis_env_script,
    )

    # Build agent config
    config = AgentConfig(
        model=ModelConfig(model=args.model),
        tis=TISConfig(
            mode="local" if use_local_mode else "ssh",
            ssh=ssh_config,
            remote_work_dir=project_config.remote_work_dir,
        ),
        max_iterations=args.max_iterations,
    )

    # Validate SSH config only if using SSH mode
    if not use_local_mode:
        if not ssh_config.password:
            print("Error: SSH_PASSWORD environment variable is required for SSH mode.")
            sys.exit(1)

    # Initialize logger if --log is specified
    logger = None
    if args.log:
        logger = WorkflowLogger(args.log)
        set_logger(logger)
        if args.verbose:
            print(f"Logging to: {args.log}")

    # Initialize structured logger if --with-logs is specified
    structured_logger = None
    if args.with_logs:
        from datetime import datetime
        timestamp = datetime.now().strftime("%m_%d-%Hh%M%S")
        logs_dir = f"logs/log_{timestamp}"
        structured_logger = StructuredLogger(logs_dir)
        set_structured_logger(structured_logger)
        if args.verbose:
            print(f"Structured logs directory: {logs_dir}")

    if args.verbose:
        print(f"Generating driver for: {args.function}")
        print(f"Project: {args.project}")
        print(f"File: {file_info.name} ({file_info.path})")
        if use_local_mode:
            print(f"Mode: local")
            print(f"Work dir: {project_config.remote_work_dir}")
        else:
            print(f"Mode: SSH ({ssh_config.user}@{ssh_config.host})")
            print(f"Remote dir: {project_config.remote_work_dir}")
        print(f"Model: {args.model}")
        print("-" * 60)

    # Create TIS runner based on mode
    if use_local_mode:
        tis_runner = LocalTISRunner(
            work_dir=project_config.remote_work_dir,
            tis_env_script=tis_env_script,
        )
    else:
        tis_runner = RemoteTISRunner(
            ssh_config=ssh_config,
            remote_work_dir=project_config.remote_work_dir,
        )

    try:
        tis_runner.connect()

        if args.verbose:
            if use_local_mode:
                print("Running in local mode")
            else:
                print("Connected to remote server")

        # Fetch source file content - prefer local if available
        source_content = read_file_local_first(
            file_info.path,
            tis_runner=tis_runner,
            include_paths=file_info.includes,
            verbose=args.verbose,
        )

        if not source_content:
            print(f"Error: Could not read source file: {file_info.path}")
            print(f"  File does not exist locally and could not be read remotely.")
            sys.exit(1)

        if args.verbose:
            local_exists = os.path.exists(file_info.path)
            print(f"Read source file {'locally' if local_exists else 'remotely'}: {file_info.path}")

        # Build context based on --context mode
        context_files = []

        if args.context == "function":
            # Extract only the target function
            func_code = extract_function(source_content, args.function)
            if func_code:
                context_files.append({"name": f"{args.function}()", "content": func_code})
                if args.verbose:
                    print(f"Context mode: function (extracted {len(func_code)} chars)")
            else:
                # Fallback to full source if extraction fails
                context_files.append({"name": file_info.name, "content": source_content})
                if args.verbose:
                    print(f"Context mode: function (extraction failed, using full source)")

        elif args.context == "source":
            # Full source file only
            context_files.append({"name": file_info.name, "content": source_content})
            if args.verbose:
                print("Context mode: source (full source file)")

        elif args.context == "matching":
            # Source + matching header (foo.c -> foo.h)
            context_files.append({"name": file_info.name, "content": source_content})
            base_name = os.path.splitext(file_info.name)[0]
            matching_header = f"{base_name}.h"

            if args.verbose:
                print(f"Context mode: matching (looking for {matching_header})")

            header_content = read_file_local_first(
                matching_header,
                tis_runner=tis_runner,
                include_paths=file_info.includes,
                verbose=args.verbose,
            )
            if header_content:
                context_files.append({"name": matching_header, "content": header_content})
                if args.verbose:
                    print(f"  Added matching header: {matching_header}")
            elif args.verbose:
                print(f"  No matching header found")

        elif args.context == "full":
            # Full context: source + ALL headers from includes
            context_files.append({"name": file_info.name, "content": source_content})
            includes = parse_includes(source_content)
            if args.verbose:
                print(f"Context mode: full ({len(includes)} includes found)")

            for inc in includes:
                header_content = read_file_local_first(
                    inc,
                    tis_runner=tis_runner,
                    include_paths=file_info.includes,
                    verbose=args.verbose,
                )
                if header_content:
                    context_files.append({"name": inc, "content": header_content})
                    if args.verbose:
                        print(f"  Added header: {inc}")

        elif args.context == "ast":
            # Use AST index to find factory functions and type definitions
            from .context.assembler import assemble_context, get_context_summary

            index_path = pm.get_index_path(args.project)
            if not os.path.exists(index_path):
                print(f"Error: AST index not found. Run 'tischiron reindex {args.project}' first.")
                sys.exit(1)

            ast_context = assemble_context(index_path, args.function)
            if ast_context:
                context_files.append({"name": "AST Context", "content": ast_context})
                if args.verbose:
                    summary = get_context_summary(index_path, args.function)
                    print(f"Context mode: ast")
                    print(f"  Target: {summary.get('target', 'N/A')}")
                    print(f"  Factories: {summary.get('factory_count', 0)}")
                    print(f"  Types: {summary.get('type_count', 0)}")
            else:
                # Fallback to function extraction
                func_code = extract_function(source_content, args.function)
                if func_code:
                    context_files.append({"name": f"{args.function}()", "content": func_code})
                    if args.verbose:
                        print(f"Context mode: ast (no AST context found, using function extraction)")
                else:
                    context_files.append({"name": file_info.name, "content": source_content})
                    if args.verbose:
                        print(f"Context mode: ast (fallback to full source)")

        # Extract function signature
        function_signature = extract_function_signature(source_content, args.function)

        # Create model adapter (auto-detects OpenAI vs Ollama)
        model_adapter = create_model_adapter(
            model=config.model.model,
            api_key=config.model.api_key,
            temperature=config.model.temperature,
            ollama_url=getattr(args, 'ollama_url', None),
        )

        # Create workflow
        app = create_workflow(
            model_adapter=model_adapter,
            tis_runner=tis_runner,
        )

        # Initial state
        initial_state = {
            "function_name": args.function,
            "function_signature": function_signature or "",
            "source_file": file_info.path,
            "context_files": context_files,
            "include_paths": file_info.includes,
            "remote_work_dir": project_config.remote_work_dir,
            "plan": None,
            "skeleton_code": None,
            "current_driver_code": None,
            "iteration": 0,
            "max_iterations": args.max_iterations,
            "cc_result": None,
            "tis_result": None,
            "validation_errors": [],
            "final_driver": None,
            "status": "planning",
            "error_message": None,
            "next_action": None,
        }

        # Log configuration
        if logger:
            logger.log_config(
                function_name=args.function,
                source_file=file_info.path,
                model=args.model,
                max_iterations=args.max_iterations,
                context_file_count=len(context_files),
                include_paths=file_info.includes,
            )

        if args.verbose:
            print(f"\nStarting generation with {len(context_files)} context files")
            print("-" * 60)

        # Run workflow with step callbacks for verbose output
        # Each iteration uses ~4 nodes, so set recursion limit accordingly
        config = {"recursion_limit": args.max_iterations * 5 + 10}

        if args.verbose:
            # Stream through nodes to show progress
            print("\n[Step 1] Planning...", flush=True)
            for step in app.stream(initial_state, config):
                node_name = list(step.keys())[0]
                state = step[node_name]
                status = state.get("status", "unknown")
                iteration = state.get("iteration", 0)

                if node_name == "planner":
                    print(f"[Step 2] Routing...", flush=True)
                elif node_name == "router":
                    action = state.get("next_action", "generate")
                    print(f"[Step 3] Action: {action}", flush=True)
                    if action == "generate":
                        print(f"[Step 4] Calling {args.model} API (this may take 30-60s)...", flush=True)
                    elif action == "refine":
                        print(f"[Refining] Calling {args.model} API for refinement...", flush=True)
                elif node_name == "generator":
                    print(f"         Generated driver code (iteration {iteration})", flush=True)
                elif node_name == "refiner":
                    print(f"         Refined driver code (iteration {iteration})", flush=True)
                elif node_name == "validator":
                    cc_result = state.get("cc_result")
                    tis_result = state.get("tis_result")
                    if cc_result:
                        print(f"[Validate] CC compile: {'OK' if cc_result.get('success') else 'FAILED'}", flush=True)
                    if tis_result:
                        print(f"[Validate] TIS compile: {'OK' if tis_result.get('success') else 'FAILED'}", flush=True)
                    if state.get("validation_errors"):
                        print(f"           Errors found - will refine", flush=True)
                elif node_name == "output_handler":
                    print(f"[Done] Status: {status}", flush=True)

            # Get final state
            result = state
        else:
            result = app.invoke(initial_state, config)

        # Output result
        if result["status"] == "success":
            output_path = args.output or f"Driver_for_{args.function}.c"
            with open(output_path, "w") as f:
                f.write(result["final_driver"])
            print(f"\nSUCCESS: Driver written to {output_path}")
            print(f"Iterations: {result['iteration']}")
            # Log final result
            if logger:
                logger.log_final_result(
                    success=True,
                    iterations=result['iteration'],
                    output_path=output_path,
                )
            # Log structured summary
            struct_logger = get_structured_logger()
            if struct_logger:
                struct_logger.log_summary(
                    success=True,
                    total_iterations=result['iteration'],
                    function_name=args.function,
                    source_file=file_info.path,
                )
        else:
            print(f"\nFAILED after {result['iteration']} iterations")
            if result.get("validation_errors"):
                print("Errors:")
                for err in result["validation_errors"]:
                    for e in err.get("errors", []):
                        print(f"  - {e}")
            # Log final result
            if logger:
                logger.log_final_result(
                    success=False,
                    iterations=result['iteration'],
                )
            # Log structured summary
            struct_logger = get_structured_logger()
            if struct_logger:
                struct_logger.log_summary(
                    success=False,
                    total_iterations=result['iteration'],
                    function_name=args.function,
                    source_file=file_info.path,
                )
            sys.exit(1)

    finally:
        tis_runner.disconnect()
        if args.verbose and not use_local_mode:
            print("Disconnected from remote server")


def cmd_context(args):
    """Show context that would be retrieved for a function."""
    pm = ProjectManager()

    if not pm.project_exists(args.project):
        print(f"Error: Project '{args.project}' not found")
        return 1

    index_path = pm.get_index_path(args.project)

    if not os.path.exists(index_path):
        print(f"Error: No AST index found for '{args.project}'")
        print("Run 'tischiron reindex <project>' to build the index")
        return 1

    try:
        from .context.assembler import assemble_context, get_context_summary

        # Show summary
        summary = get_context_summary(index_path, args.function)
        if not summary:
            print(f"Error: Function '{args.function}' not found in index")
            return 1

        print(f"Function: {summary['function']}")
        print(f"Parameters:")
        for ptype, pname in summary['params']:
            print(f"  - {pname}: {ptype}")

        print(f"\nFactories found:")
        for type_name, factory_names in summary['factories'].items():
            print(f"  {type_name}:")
            for fname in factory_names[:5]:
                print(f"    - {fname}()")
            if len(factory_names) > 5:
                print(f"    ... and {len(factory_names) - 5} more")

        # Show full context if verbose
        if args.verbose:
            print("\n" + "=" * 60)
            print("Full context that would be injected:")
            print("=" * 60 + "\n")

            context = assemble_context(index_path, args.function)
            print(context)

    except ImportError as e:
        print(f"Error: Context module not available ({e})")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def cmd_reindex(args):
    """Rebuild AST index for a project."""
    pm = ProjectManager()

    if not pm.project_exists(args.project):
        print(f"Error: Project '{args.project}' not found")
        return 1

    try:
        from .context.index import build_index
        from .config import FileInfo as ConfigFileInfo
        import time
        import glob

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

        print(f"\nIndex rebuilt successfully!")
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


def main():
    parser = argparse.ArgumentParser(
        prog="tischiron",
        description="AI-powered TIS driver generation",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize project from compilation database"
    )
    init_parser.add_argument(
        "compilation_db", help="Path to compile_commands.json"
    )
    init_parser.add_argument(
        "--name", "-n", help="Project name (default: derived from directory)"
    )
    init_parser.add_argument(
        "--ssh-host", help="SSH host for remote TIS"
    )
    init_parser.add_argument(
        "--ssh-user", help="SSH username"
    )
    init_parser.add_argument(
        "--tis-env-script",
        help="Script to source TIS environment",
    )
    init_parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip building AST index (faster init, no context retrieval)",
    )
    init_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # list command
    list_parser = subparsers.add_parser(
        "list", help="List projects or files"
    )
    list_parser.add_argument(
        "project", nargs="?", help="Project name (omit to list all projects)"
    ).completer = ProjectCompleter()
    list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # gen command
    gen_parser = subparsers.add_parser(
        "gen", help="Generate driver for a function"
    )
    gen_parser.add_argument(
        "project", help="Project name"
    ).completer = ProjectCompleter()
    gen_parser.add_argument(
        "filename", help="Source filename"
    ).completer = FileCompleter()
    gen_parser.add_argument(
        "function", help="Function name"
    )
    gen_parser.add_argument(
        "--output", "-o", help="Output file path"
    )
    gen_parser.add_argument(
        "--model", default="gpt-4o-mini", help="Model to use (default: gpt-4o-mini)"
    ).completer = ModelCompleter()
    gen_parser.add_argument(
        "--max-iterations", type=int, default=5, help="Maximum refinement iterations"
    )
    gen_parser.add_argument("--ssh-host", help=argparse.SUPPRESS)
    gen_parser.add_argument("--ssh-user", help=argparse.SUPPRESS)
    gen_parser.add_argument("--tis-env-script", help=argparse.SUPPRESS)
    gen_parser.add_argument(
        "--log", "-l", help="Path to log file for detailed workflow logging"
    )
    gen_parser.add_argument(
        "--with-logs",
        action="store_true",
        help="Create structured logs in logs/log_<timestamp>/ with separate files for C code, LLM queries, and validation results",
    )
    gen_parser.add_argument(
        "--context",
        choices=["function", "source", "matching", "full", "ast"],
        default="function",
        help="Context mode: function (extracted function only), source (full source file), matching (source + matching header), full (all headers), ast (use AST index for factory functions). Default: function",
    )
    gen_parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )
    gen_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # context command
    context_parser = subparsers.add_parser(
        "context", help="Show context for a function (debug)"
    )
    context_parser.add_argument(
        "project", help="Project name"
    ).completer = ProjectCompleter()
    context_parser.add_argument(
        "function", help="Function name"
    )
    context_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show full context"
    )

    # reindex command
    reindex_parser = subparsers.add_parser(
        "reindex", help="Rebuild AST index for a project"
    )
    reindex_parser.add_argument(
        "project", help="Project name"
    ).completer = ProjectCompleter()

    # Enable argcomplete
    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "gen":
        cmd_gen(args)
    elif args.command == "context":
        cmd_context(args)
    elif args.command == "reindex":
        cmd_reindex(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
