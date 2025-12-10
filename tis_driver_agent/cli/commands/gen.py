"""Gen command - generate a driver for a function."""

import os
import sys
from functools import partial

from ...config import AgentConfig, ModelConfig, TISConfig, SSHConfig
from ...utils.project_manager import ProjectManager
from ...utils.context_builder import ContextBuilder
from ...utils.context_detector import extract_function_signature
from ...models.factory import create_model_adapter
from ...tis.remote import RemoteTISRunner
from ...tis.local import LocalTISRunner
from ...graph import create_workflow
from ...workflow_logger import (
    WorkflowLogger,
    StructuredLogger,
    set_logger,
    set_structured_logger,
    get_structured_logger,
)
from ..helpers import read_file_local_first


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
            print("Mode: local")
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
            print("  File does not exist locally and could not be read remotely.")
            sys.exit(1)

        if args.verbose:
            local_exists = os.path.exists(file_info.path)
            print(f"Read source file {'locally' if local_exists else 'remotely'}: {file_info.path}")

        # Build context using ContextBuilder
        def file_reader(path):
            return read_file_local_first(
                path,
                tis_runner=tis_runner,
                include_paths=file_info.includes,
                verbose=False,
            )

        context_builder = ContextBuilder(
            file_reader=file_reader,
            include_paths=file_info.includes,
            verbose=args.verbose,
        )

        index_path = pm.get_index_path(args.project) if args.context == "ast" else None
        if args.context == "ast" and index_path and not os.path.exists(index_path):
            print(f"Error: AST index not found. Run 'tischiron reindex {args.project}' first.")
            sys.exit(1)

        context_files = context_builder.build(
            mode=args.context,
            source_content=source_content,
            source_filename=file_info.name,
            function_name=args.function,
            index_path=index_path,
        )

        # Extract function signature
        function_signature = extract_function_signature(source_content, args.function)

        # Create model adapter (auto-detects OpenAI vs Ollama vs Anthropic)
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
            "current_driver_code": None,
            "iteration": 0,
            "max_iterations": args.max_iterations,
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
        workflow_config = {"recursion_limit": args.max_iterations * 5 + 10}

        if args.verbose:
            # Stream through nodes to show progress
            print("\n[Step 1] Planning...", flush=True)
            for step in app.stream(initial_state, workflow_config):
                node_name = list(step.keys())[0]
                state = step[node_name]
                status = state.get("status", "unknown")
                iteration = state.get("iteration", 0)

                if node_name == "planner":
                    print("[Step 2] Routing...", flush=True)
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
                    tis_result = state.get("tis_result")
                    if tis_result:
                        print(f"[Validate] TIS compile: {'OK' if tis_result.get('success') else 'FAILED'}", flush=True)
                    if state.get("validation_errors"):
                        print("           Errors found - will refine", flush=True)
                elif node_name == "output_handler":
                    print(f"[Done] Status: {status}", flush=True)

            # Get final state
            result = state
        else:
            result = app.invoke(initial_state, workflow_config)

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
            # Save the last driver code with _xxx suffix if available
            if result.get("final_driver"):
                base_output = args.output or f"Driver_for_{args.function}.c"
                # Insert _xxx before .c extension
                if base_output.endswith(".c"):
                    failed_output = base_output[:-2] + "_xxx.c"
                else:
                    failed_output = base_output + "_xxx"
                with open(failed_output, "w") as f:
                    f.write(result["final_driver"])
                print(f"Last attempt saved to: {failed_output}")
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
