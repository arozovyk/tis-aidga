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

    # Initialize project
    project_name = pm.init_project(
        compilation_db_path=args.compilation_db,
        project_name=args.name,
        ssh_host=args.ssh_host or "",
        ssh_user=args.ssh_user or "",
        tis_env_script=args.tis_env_script or "",
    )

    print(f"Project '{project_name}' initialized successfully!")

    # Show summary
    config = pm.get_project_config(project_name)
    files = pm.list_files(project_name)

    print(f"\nRemote work dir: {config.remote_work_dir}")
    print(f"Files indexed: {len(files)}")

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
    else:
        # List all projects
        projects = pm.list_projects()

        if not projects:
            print("No projects found. Use 'tisaidga init <compile_commands.json>' to create one.")
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

    # Build SSH config
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
            mode="ssh",
            ssh=ssh_config,
            remote_work_dir=project_config.remote_work_dir,
        ),
        max_iterations=args.max_iterations,
    )

    # Validate SSH config
    if not ssh_config.host or not ssh_config.user:
        print("Error: SSH host and user are required.")
        print("Set via --ssh-host/--ssh-user, project config, or SSH_HOST/SSH_USER env vars.")
        sys.exit(1)

    if not ssh_config.password:
        print("Error: SSH_PASSWORD environment variable is required.")
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
        print(f"SSH: {ssh_config.user}@{ssh_config.host}")
        print(f"Remote dir: {project_config.remote_work_dir}")
        print(f"Model: {args.model}")
        print("-" * 60)

    # Create TIS runner and connect
    tis_runner = RemoteTISRunner(
        ssh_config=ssh_config,
        remote_work_dir=project_config.remote_work_dir,
    )

    try:
        tis_runner.connect()

        if args.verbose:
            print("Connected to remote server")

        # Fetch source file content
        source_content = tis_runner.read_remote_file(file_info.path)
        if not source_content:
            print(f"Error: Could not read source file: {file_info.path}")
            sys.exit(1)

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

            header_path = tis_runner.find_header_files(file_info.includes, matching_header)
            if header_path:
                header_content = tis_runner.read_remote_file(header_path)
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
                header_path = tis_runner.find_header_files(file_info.includes, inc)
                if header_path:
                    header_content = tis_runner.read_remote_file(header_path)
                    if header_content:
                        context_files.append({"name": inc, "content": header_content})
                        if args.verbose:
                            print(f"  Added header: {inc}")

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
        if args.verbose:
            print("Disconnected from remote server")


def main():
    parser = argparse.ArgumentParser(
        prog="tisaidga",
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
        choices=["function", "source", "matching", "full"],
        default="function",
        help="Context mode: function (extracted function only), source (full source file), matching (source + matching header), full (all headers). Default: function",
    )
    gen_parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )
    gen_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # Enable argcomplete
    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "gen":
        cmd_gen(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
