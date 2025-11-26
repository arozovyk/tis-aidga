"""CLI entry point for TIS Driver Agent."""

import argparse
import os
import sys

from dotenv import load_dotenv

from .config import AgentConfig, ModelConfig, TISConfig, SSHConfig
from .models.openai_adapter import OpenAIAdapter
from .tis.remote import RemoteTISRunner
from .graph import create_workflow
from .utils.project_manager import ProjectManager
from .utils.context_detector import (
    parse_includes,
    extract_function_signature,
)

# Load environment variables from .env file
load_dotenv()


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
    tis_env_script = args.tis_env_script or project_config.tis_env_script or ""

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

        # Build context: source file + headers
        context_files = [{"name": file_info.name, "content": source_content}]

        # Parse includes from source and fetch headers
        includes = parse_includes(source_content)
        if args.verbose:
            print(f"Found {len(includes)} includes in source")

        for inc in includes:
            # Try to find and read header
            header_path = tis_runner.find_header_files(file_info.includes, inc)
            if header_path:
                header_content = tis_runner.read_remote_file(header_path)
                if header_content:
                    context_files.append({"name": inc, "content": header_content})
                    if args.verbose:
                        print(f"  Added header: {inc}")

        # Extract function signature
        function_signature = extract_function_signature(source_content, args.function)

        # Create model adapter
        model_adapter = OpenAIAdapter(
            model=config.model.model,
            api_key=config.model.api_key,
            temperature=config.model.temperature,
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

        if args.verbose:
            print(f"\nStarting generation with {len(context_files)} context files")
            print("-" * 60)

        # Run workflow
        result = app.invoke(initial_state)

        # Output result
        if result["status"] == "success":
            output_path = args.output or f"Driver_for_{args.function}.c"
            with open(output_path, "w") as f:
                f.write(result["final_driver"])
            print(f"\nSUCCESS: Driver written to {output_path}")
            print(f"Iterations: {result['iteration']}")
        else:
            print(f"\nFAILED after {result['iteration']} iterations")
            if result.get("validation_errors"):
                print("Errors:")
                for err in result["validation_errors"]:
                    for e in err.get("errors", []):
                        print(f"  - {e}")
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
    )
    list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # gen command
    gen_parser = subparsers.add_parser(
        "gen", help="Generate driver for a function"
    )
    gen_parser.add_argument(
        "project", help="Project name"
    )
    gen_parser.add_argument(
        "filename", help="Source filename"
    )
    gen_parser.add_argument(
        "function", help="Function name"
    )
    gen_parser.add_argument(
        "--output", "-o", help="Output file path"
    )
    gen_parser.add_argument(
        "--model", default="gpt-4o-mini", help="Model to use (default: gpt-4o-mini)"
    )
    gen_parser.add_argument(
        "--max-iterations", type=int, default=5, help="Maximum refinement iterations"
    )
    gen_parser.add_argument(
        "--ssh-host", help="SSH host (override project config)"
    )
    gen_parser.add_argument(
        "--ssh-user", help="SSH username (override project config)"
    )
    gen_parser.add_argument(
        "--tis-env-script", help="TIS environment script (override project config)"
    )
    gen_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

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
