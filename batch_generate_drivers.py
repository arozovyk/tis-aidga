#!/usr/bin/env python3
"""
Batch driver generation script for json-c library.
Runs multiple tischiron gen commands in parallel using a worker pool.
"""

import argparse
import os
import subprocess
import sys
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from queue import Queue


def load_env_file(env_path: Path = None):
    """Load environment variables from .env file."""
    if env_path is None:
        env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        return False

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    return True


# Auto-load .env file on import
_env_loaded = load_env_file()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Functions to generate drivers for, organized by source file
FUNCTIONS_TO_TEST = [
    # json_object.c - Core object functions
    ("json_object.c", "json_object_get_int"),
    ("json_object.c", "json_object_get_int64"),
    ("json_object.c", "json_object_get_uint64"),
    ("json_object.c", "json_object_get_double"),
    ("json_object.c", "json_object_int_inc"),
    ("json_object.c", "json_object_array_put_idx"),
    ("json_object.c", "json_object_array_insert_idx"),
    ("json_object.c", "json_object_array_del_idx"),
    ("json_object.c", "json_object_array_add"),
    ("json_object.c", "json_object_object_add"),
    ("json_object.c", "json_object_object_add_ex"),
    ("json_object.c", "json_object_object_get_ex"),
    ("json_object.c", "json_object_object_del"),
    ("json_object.c", "json_object_new_string_len"),
    ("json_object.c", "json_object_set_string_len"),
    ("json_object.c", "json_object_deep_copy"),
    ("json_object.c", "json_object_equal"),
    ("json_object.c", "json_object_to_json_string_ext"),
    # json_tokener.c - Parsing functions
    ("json_tokener.c", "json_tokener_parse"),
    ("json_tokener.c", "json_tokener_parse_ex"),
    ("json_tokener.c", "json_tokener_new_ex"),
    # json_pointer.c - JSON Pointer (RFC 6901)
    ("json_pointer.c", "json_pointer_get"),
    ("json_pointer.c", "json_pointer_set"),
    # json_visit.c - Tree traversal
    ("json_visit.c", "json_c_visit"),
    # json_util.c - Utilities
    ("json_util.c", "json_parse_int64"),
    ("json_util.c", "json_parse_uint64"),
]


@dataclass
class TaskResult:
    """Result of a single driver generation task."""
    source_file: str
    function_name: str
    success: bool
    duration_seconds: float
    output_file: str
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    return_code: int = -1


class StaggeredExecutor:
    """Executor that staggers task starts to avoid timestamp collisions."""

    def __init__(self, max_workers: int, stagger_seconds: float = 2.0):
        self.max_workers = max_workers
        self.stagger_seconds = stagger_seconds
        self.start_lock = threading.Lock()
        self.last_start_time = 0.0

    def wait_for_slot(self):
        """Wait until enough time has passed since the last task start."""
        with self.start_lock:
            now = time.time()
            time_since_last = now - self.last_start_time
            if time_since_last < self.stagger_seconds:
                wait_time = self.stagger_seconds - time_since_last
                time.sleep(wait_time)
            self.last_start_time = time.time()


# Global staggered executor instance
staggered_executor: Optional[StaggeredExecutor] = None


def generate_driver(
    source_file: str,
    function_name: str,
    model: str,
    max_iterations: int,
    output_dir: Path,
    verbose: bool,
    max_retries: int = 3,
) -> TaskResult:
    """
    Generate a driver for a single function using tischiron.
    Includes retry logic for rate limit errors.
    """
    global staggered_executor

    # Wait for staggered start slot
    if staggered_executor:
        staggered_executor.wait_for_slot()

    start_time = time.time()
    output_file = output_dir / f"{function_name}_driver.c"

    cmd = [
        sys.executable, "-m", "tis_driver_agent.cli", "gen",
        "json-c",
        source_file,
        function_name,
        "--with-logs",
        "--context", "ast",
        "--output", str(output_file),
        "--model", model,
        "--max-iterations", str(max_iterations),
    ]

    if verbose:
        cmd.append("-v")

    cmd_str = " ".join(cmd)
    logger.info(f"[START] {function_name}")
    logger.debug(f"Command: {cmd_str}")

    last_result = None
    last_error = None

    # Ensure environment variables are passed to subprocess
    env = os.environ.copy()

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per function
                env=env,
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            # Check for rate limit error
            is_rate_limit = "RateLimitError" in (result.stderr or "") or "rate_limit" in (result.stderr or "")

            if success:
                logger.info(f"[OK] {function_name} ({duration:.1f}s)")
                return TaskResult(
                    source_file=source_file,
                    function_name=function_name,
                    success=True,
                    duration_seconds=duration,
                    output_file=str(output_file),
                    command=cmd_str,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode,
                )
            elif is_rate_limit and attempt < max_retries - 1:
                # Rate limited - wait and retry
                wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                logger.warning(f"[RATE_LIMIT] {function_name} - waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                time.sleep(wait_time)
                continue
            else:
                # Other error or final retry - extract error message
                error_lines = result.stderr.strip().split('\n') if result.stderr else []
                error_summary = "Unknown error"
                for line in reversed(error_lines):
                    line = line.strip()
                    if line and not line.startswith('File "') and not line.startswith('Traceback'):
                        error_summary = line[:100]
                        break

                if error_summary == "Unknown error" and result.stdout:
                    stdout_lines = result.stdout.strip().split('\n')
                    for line in reversed(stdout_lines):
                        if 'error' in line.lower() or 'failed' in line.lower():
                            error_summary = line[:100]
                            break

                if is_rate_limit:
                    logger.error(f"[RATE_LIMIT_FAIL] {function_name} ({duration:.1f}s) - exhausted retries")
                else:
                    logger.warning(f"[FAIL] {function_name} ({duration:.1f}s) - {error_summary}")

                return TaskResult(
                    source_file=source_file,
                    function_name=function_name,
                    success=False,
                    duration_seconds=duration,
                    output_file=str(output_file),
                    command=cmd_str,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    error_message=result.stderr,
                    return_code=result.returncode,
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"[TIMEOUT] {function_name} (>{duration:.1f}s)")
            return TaskResult(
                source_file=source_file,
                function_name=function_name,
                success=False,
                duration_seconds=duration,
                output_file=str(output_file),
                command=cmd_str,
                error_message="Process timed out after 5 minutes",
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[ERROR] {function_name} - {e}")
            return TaskResult(
                source_file=source_file,
                function_name=function_name,
                success=False,
                duration_seconds=duration,
                output_file=str(output_file),
                command=cmd_str,
                error_message=str(e),
            )

    # Should not reach here, but just in case
    duration = time.time() - start_time
    return TaskResult(
        source_file=source_file,
        function_name=function_name,
        success=False,
        duration_seconds=duration,
        output_file=str(output_file),
        command=cmd_str,
        error_message="Exhausted all retries",
    )


def worker_task(args: tuple) -> TaskResult:
    """Worker function for thread pool."""
    source_file, function_name, model, max_iterations, output_dir, verbose = args
    return generate_driver(
        source_file, function_name, model, max_iterations, output_dir, verbose
    )


def extract_error_summary(result: TaskResult) -> str:
    """Extract a meaningful error summary from the result."""
    # Check both stderr and stdout for errors
    all_output = ""
    if result.error_message:
        all_output += result.error_message + "\n"
    if result.stdout:
        all_output += result.stdout

    if not all_output.strip():
        return "Unknown error (no output)"

    # Priority 0: Check for rate limit errors specifically
    if "RateLimitError" in all_output or "rate_limit_error" in all_output:
        return "RATE_LIMIT: API rate limit exceeded - try fewer workers or longer stagger"

    lines = all_output.strip().split('\n')

    # Priority 1: Look for "Error: X" pattern (common in CLI tools)
    for line in lines:
        line = line.strip()
        if line.startswith('Error:') or line.startswith('error:'):
            return line[:150]

    # Priority 2: Look for exception type lines like "ValueError: something"
    exception_line = None
    error_msg = None

    for line in lines:
        line = line.strip()
        if ': ' in line and not line.startswith('File '):
            parts = line.split(': ', 1)
            if len(parts) == 2:
                first_part = parts[0].strip()
                # Check if it looks like an exception name
                if first_part and first_part[0].isupper() and first_part.replace('_', '').isalnum():
                    exception_line = line
        # Look for explicit error messages
        if 'error' in line.lower() and not line.startswith('File '):
            error_msg = line

    if exception_line:
        return exception_line[:150]
    if error_msg:
        return error_msg[:150]

    # Priority 3: Return last non-empty, non-traceback line
    for line in reversed(lines):
        line = line.strip()
        if line and not line.startswith('File "') and not line.startswith('Traceback'):
            return line[:150]

    return "See full error log"


def print_stats(results: list[TaskResult], total_duration: float, output_dir: Path):
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("GENERATION SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\nTotal functions:  {len(results)}")
    print(f"Successful:       {len(successful)} ({100*len(successful)/len(results):.1f}%)")
    print(f"Failed:           {len(failed)} ({100*len(failed)/len(results):.1f}%)")
    print(f"Total time:       {total_duration:.1f}s")

    if results:
        avg_time = sum(r.duration_seconds for r in results) / len(results)
        print(f"Avg time/func:    {avg_time:.1f}s")

    # Successful functions
    if successful:
        print("\n" + "-" * 80)
        print("SUCCESSFUL DRIVERS:")
        print("-" * 80)
        for r in sorted(successful, key=lambda x: x.duration_seconds):
            print(f"  {r.function_name:45} {r.duration_seconds:6.1f}s")
        print(f"\n  Output directory: {output_dir}")

    # Failed functions with better error info
    if failed:
        print("\n" + "-" * 80)
        print("FAILED FUNCTIONS:")
        print("-" * 80)
        for r in sorted(failed, key=lambda x: x.function_name):
            error_summary = extract_error_summary(r)
            print(f"\n  {r.function_name}")
            print(f"    Error: {error_summary}")
            print(f"    Return code: {r.return_code}")

    # By source file breakdown
    print("\n" + "-" * 80)
    print("BY SOURCE FILE:")
    print("-" * 80)
    source_files = {}
    for r in results:
        if r.source_file not in source_files:
            source_files[r.source_file] = {"success": 0, "failed": 0}
        if r.success:
            source_files[r.source_file]["success"] += 1
        else:
            source_files[r.source_file]["failed"] += 1

    for sf, counts in sorted(source_files.items()):
        total = counts["success"] + counts["failed"]
        pct = 100 * counts["success"] / total if total > 0 else 0
        print(f"  {sf:35} {counts['success']:2}/{total:2} ({pct:5.1f}%)")

    print("\n" + "=" * 80)

    # Write detailed error log
    if failed:
        error_log_path = output_dir / "errors.log"
        with open(error_log_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("DETAILED ERROR LOG\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            for r in sorted(failed, key=lambda x: x.function_name):
                f.write("-" * 80 + "\n")
                f.write(f"FUNCTION: {r.function_name}\n")
                f.write(f"SOURCE:   {r.source_file}\n")
                f.write(f"COMMAND:  {r.command}\n")
                f.write(f"DURATION: {r.duration_seconds:.1f}s\n")
                f.write(f"RETURN:   {r.return_code}\n")
                f.write("-" * 80 + "\n")

                if r.stdout:
                    f.write("\n--- STDOUT ---\n")
                    f.write(r.stdout)
                    f.write("\n")

                if r.stderr:
                    f.write("\n--- STDERR ---\n")
                    f.write(r.stderr)
                    f.write("\n")

                f.write("\n\n")

        print(f"\nDetailed error log written to: {error_log_path}")


def main():
    global staggered_executor

    parser = argparse.ArgumentParser(
        description="Batch generate TIS-Analyzer drivers for json-c functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model claude-haiku-4-5
  %(prog)s --model gpt-4o-mini --workers 5 --max-iterations 5
  %(prog)s --model claude-sonnet-4 --verbose --dry-run
  %(prog)s --model claude-haiku-4-5 --stagger 3  # 3 second delay between starts
        """,
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        help="LLM model to use for generation (e.g., claude-haiku-4-5, gpt-4o-mini)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=3,
        help="Number of parallel workers (default: 3 - conservative for API rate limits)",
    )
    parser.add_argument(
        "--stagger", "-s",
        type=float,
        default=5.0,
        help="Seconds to wait between starting each task (default: 5.0 - helps avoid rate limits)",
    )
    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        default=3,
        help="Maximum refinement iterations per function (default: 3)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("drivers/batch"),
        help="Output directory for generated drivers (default: drivers/batch)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be run without executing",
    )
    parser.add_argument(
        "--functions", "-f",
        nargs="+",
        help="Only generate drivers for specific functions (space-separated)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (shows commands, full errors)",
    )

    args = parser.parse_args()

    # Set log level
    if args.debug or args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Filter functions if specified
    functions = FUNCTIONS_TO_TEST
    if args.functions:
        functions = [
            (sf, fn) for sf, fn in FUNCTIONS_TO_TEST
            if fn in args.functions
        ]
        if not functions:
            logger.error(f"No matching functions found for: {args.functions}")
            logger.info(f"Available functions: {[fn for _, fn in FUNCTIONS_TO_TEST]}")
            sys.exit(1)

    print("=" * 80)
    print("TIS-CHIRON BATCH DRIVER GENERATION")
    print("=" * 80)
    print(f"Model:            {args.model}")
    print(f"Workers:          {args.workers}")
    print(f"Stagger delay:    {args.stagger}s")
    print(f"Max iterations:   {args.max_iterations}")
    print(f"Output directory: {args.output_dir}")
    print(f"Functions:        {len(functions)}")

    # Check for API keys
    env_status = []
    if _env_loaded:
        env_status.append(".env loaded")
    if os.environ.get("ANTHROPIC_API_KEY"):
        env_status.append("ANTHROPIC_API_KEY set")
    if os.environ.get("OPENAI_API_KEY"):
        env_status.append("OPENAI_API_KEY set")
    print(f"Environment:      {', '.join(env_status) if env_status else 'No API keys found!'}")
    print("=" * 80)

    if args.dry_run:
        print("\nDRY RUN - Commands that would be executed:\n")
        for i, (source_file, function_name) in enumerate(functions):
            output_file = args.output_dir / f"{function_name}_driver.c"
            cmd = (
                f"tischiron gen json-c {source_file} {function_name} "
                f"--with-logs --context ast --output {output_file} "
                f"--model {args.model} --max-iterations {args.max_iterations}"
            )
            if args.verbose:
                cmd += " -v"
            delay = i * args.stagger
            print(f"  [+{delay:5.1f}s] {cmd}")

        estimated_time = len(functions) * args.stagger
        print(f"\nTotal: {len(functions)} commands")
        print(f"Estimated minimum start time spread: {estimated_time:.1f}s")
        return

    # Initialize staggered executor
    staggered_executor = StaggeredExecutor(args.workers, args.stagger)

    # Prepare task arguments
    tasks = [
        (sf, fn, args.model, args.max_iterations, args.output_dir, args.verbose)
        for sf, fn in functions
    ]

    # Run tasks in parallel with thread pool (better for I/O bound tasks)
    start_time = time.time()
    results = []

    logger.info(f"Starting {len(tasks)} tasks with {args.workers} workers (stagger: {args.stagger}s)...")
    print()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_task = {
            executor.submit(worker_task, task): task
            for task in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)

                # Debug: print full error immediately if debug mode
                if args.debug and not result.success and result.stderr:
                    print(f"\n--- DEBUG: Full error for {result.function_name} ---")
                    print(result.stderr[:1000])
                    print("---\n")

            except Exception as e:
                logger.error(f"Task failed unexpectedly: {task[1]} - {e}")
                import traceback
                if args.debug:
                    traceback.print_exc()
                results.append(TaskResult(
                    source_file=task[0],
                    function_name=task[1],
                    success=False,
                    duration_seconds=0,
                    output_file="",
                    command="",
                    error_message=f"{type(e).__name__}: {e}",
                ))

    total_duration = time.time() - start_time

    # Print statistics
    print_stats(results, total_duration, args.output_dir)

    # Exit with error code if any failures
    failed_count = sum(1 for r in results if not r.success)
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
