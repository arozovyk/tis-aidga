#!/usr/bin/env python3
"""Benchmark script for testing TIS driver generation across multiple models."""

import subprocess
import json
import csv
import os
import time
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class RunResult:
    """Result of a single benchmark run."""
    model: str
    run_number: int
    success: bool
    iterations: int
    total_time_seconds: float
    log_dir: str

    # Coverage metrics (from info_json)
    function_coverage: Optional[str] = None
    total_statements_coverage: Optional[str] = None
    semantic_statements_coverage: Optional[str] = None

    # Analysis metrics
    alarm_count: int = 0
    non_terminating_count: int = 0

    # Error info
    error_type: Optional[str] = None
    error_file: Optional[str] = None

    # TIS timing
    tis_parsing_time: Optional[str] = None
    tis_value_analysis_time: Optional[str] = None


def find_latest_log_dir(base_dir: str = "logs") -> Optional[str]:
    """Find the most recently created log directory."""
    log_path = Path(base_dir)
    if not log_path.exists():
        return None

    dirs = [d for d in log_path.iterdir() if d.is_dir() and d.name.startswith("log_")]
    if not dirs:
        return None

    return str(max(dirs, key=lambda d: d.stat().st_mtime))


def parse_log_dir(log_dir: str) -> Dict[str, Any]:
    """Parse a log directory to extract stats."""
    result = {
        "success": False,
        "iterations": 0,
        "function_coverage": None,
        "total_statements_coverage": None,
        "semantic_statements_coverage": None,
        "alarm_count": 0,
        "non_terminating_count": 0,
        "error_type": None,
        "error_file": None,
        "tis_parsing_time": None,
        "tis_value_analysis_time": None,
    }

    log_path = Path(log_dir)
    if not log_path.exists():
        return result

    # Find validation files (they contain the final results)
    validation_files = sorted(log_path.glob("*_validation_iter*.json"))

    last_validation = None
    for vf in validation_files:
        try:
            with open(vf) as f:
                data = json.load(f)
                last_validation = data
                result["iterations"] = data.get("iteration", 0)

                # Check if this iteration was valid (success)
                if data.get("is_valid", False):
                    result["success"] = True

                # Extract info_json if available
                tis_compile = data.get("tis_compile", {})
                info_json = tis_compile.get("info_json", {})

                if info_json:
                    # Coverage
                    coverage = info_json.get("coverage", {})
                    result["function_coverage"] = coverage.get("function_coverage")
                    result["total_statements_coverage"] = coverage.get("total_statements_coverage")
                    result["semantic_statements_coverage"] = coverage.get("semantic_statements_coverage")

                    # Alarms
                    alarms = info_json.get("alarms", {})
                    alarm_list = alarms.get("list", [])
                    result["alarm_count"] = len(alarm_list)

                    # Non-terminating
                    non_term = info_json.get("non_terminating", {})
                    non_term_list = non_term.get("list", [])
                    result["non_terminating_count"] = len(non_term_list)

                    # TIS timing
                    tis_time = info_json.get("time", {})
                    result["tis_parsing_time"] = tis_time.get("parsing_time")
                    result["tis_value_analysis_time"] = tis_time.get("value_analysis_time")

        except (json.JSONDecodeError, IOError):
            continue

    # Find error files if not successful
    if not result["success"]:
        error_files = sorted(log_path.glob("*_error.txt"))
        if error_files:
            result["error_file"] = str(error_files[-1])
            # Try to determine error type from filename or content
            try:
                with open(error_files[-1]) as f:
                    content = f.read()
                    if "file not found" in content.lower():
                        result["error_type"] = "header_not_found"
                    elif "incompatible declaration" in content.lower() or "not isomorphic" in content.lower():
                        result["error_type"] = "type_mismatch"
                    elif "undefined" in content.lower():
                        result["error_type"] = "undefined_reference"
                    else:
                        result["error_type"] = "compilation_error"
            except IOError:
                result["error_type"] = "unknown"

    return result


def run_benchmark(
    model: str,
    run_number: int,
    project: str = "json-c",
    filename: str = "json_object.c",
    function: str = "json_object_equal",
    max_iterations: int = 3,
    context: str = "function",
) -> RunResult:
    """Run a single benchmark iteration."""

    output_file = f"drivers/benchmark_{model}_{run_number}.c"

    # Ensure drivers directory exists
    os.makedirs("drivers", exist_ok=True)

    cmd = [
        "tisaidga",
        "gen",
        project,
        filename,
        function,
        "--with-logs",
        "--context", context,
        "--output", output_file,
        "--model", model,
        "--max-iterations", str(max_iterations),
        "-v",
    ]

    print(f"\n{'='*60}")
    print(f"Running: {model} - Run {run_number + 1}/10")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        success = False
        print(f"TIMEOUT after 300 seconds")
    except Exception as e:
        success = False
        print(f"ERROR: {e}")

    end_time = time.time()
    total_time = end_time - start_time

    # Find the log directory that was just created
    log_dir = find_latest_log_dir()

    # Parse the log directory for stats
    stats = parse_log_dir(log_dir) if log_dir else {}

    run_result = RunResult(
        model=model,
        run_number=run_number,
        success=stats.get("success", success),
        iterations=stats.get("iterations", 0),
        total_time_seconds=round(total_time, 2),
        log_dir=log_dir or "",
        function_coverage=stats.get("function_coverage"),
        total_statements_coverage=stats.get("total_statements_coverage"),
        semantic_statements_coverage=stats.get("semantic_statements_coverage"),
        alarm_count=stats.get("alarm_count", 0),
        non_terminating_count=stats.get("non_terminating_count", 0),
        error_type=stats.get("error_type"),
        error_file=stats.get("error_file"),
        tis_parsing_time=stats.get("tis_parsing_time"),
        tis_value_analysis_time=stats.get("tis_value_analysis_time"),
    )

    # Print summary
    status = "SUCCESS" if run_result.success else "FAILED"
    print(f"Result: {status} in {total_time:.2f}s ({run_result.iterations} iterations)")
    if run_result.function_coverage:
        print(f"Coverage: func={run_result.function_coverage}, stmt={run_result.total_statements_coverage}, semantic={run_result.semantic_statements_coverage}")
    if run_result.error_type:
        print(f"Error: {run_result.error_type}")

    return run_result


def write_csv(results: List[RunResult], model: str, output_dir: str = "benchmark_results"):
    """Write results to CSV file."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/benchmark_{model}_{timestamp}.csv"

    # Define CSV columns
    fieldnames = [
        "run_number",
        "success",
        "iterations",
        "total_time_seconds",
        "function_coverage",
        "total_statements_coverage",
        "semantic_statements_coverage",
        "alarm_count",
        "non_terminating_count",
        "error_type",
        "error_file",
        "tis_parsing_time",
        "tis_value_analysis_time",
        "log_dir",
    ]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            row = asdict(r)
            del row["model"]  # Already in filename
            writer.writerow(row)

    print(f"\nCSV written to: {filename}")
    return filename


def write_summary(all_results: Dict[str, List[RunResult]], output_dir: str = "benchmark_results"):
    """Write a summary CSV comparing all models."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/benchmark_summary_{timestamp}.csv"

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "model",
            "total_runs",
            "successes",
            "failures",
            "success_rate",
            "avg_time_seconds",
            "avg_iterations",
            "avg_alarm_count",
            "avg_function_coverage",
            "avg_stmt_coverage",
            "avg_semantic_coverage",
        ])

        for model, results in all_results.items():
            successes = sum(1 for r in results if r.success)
            failures = len(results) - successes
            success_rate = f"{(successes / len(results) * 100):.1f}%"
            avg_time = sum(r.total_time_seconds for r in results) / len(results)
            avg_iterations = sum(r.iterations for r in results) / len(results)
            avg_alarms = sum(r.alarm_count for r in results) / len(results)

            # Coverage averages (only for successful runs with coverage data)
            successful_with_coverage = [r for r in results if r.success and r.function_coverage]
            if successful_with_coverage:
                avg_func_cov = sum(float(r.function_coverage.rstrip('%')) for r in successful_with_coverage) / len(successful_with_coverage)
                avg_stmt_cov = sum(float(r.total_statements_coverage.rstrip('%')) for r in successful_with_coverage) / len(successful_with_coverage)
                avg_sem_cov = sum(float(r.semantic_statements_coverage.rstrip('%')) for r in successful_with_coverage) / len(successful_with_coverage)
                avg_func_cov = f"{avg_func_cov:.1f}%"
                avg_stmt_cov = f"{avg_stmt_cov:.1f}%"
                avg_sem_cov = f"{avg_sem_cov:.1f}%"
            else:
                avg_func_cov = avg_stmt_cov = avg_sem_cov = "N/A"

            writer.writerow([
                model,
                len(results),
                successes,
                failures,
                success_rate,
                f"{avg_time:.2f}",
                f"{avg_iterations:.2f}",
                f"{avg_alarms:.2f}",
                avg_func_cov,
                avg_stmt_cov,
                avg_sem_cov,
            ])

    print(f"\nSummary CSV written to: {filename}")
    return filename


def main():
    """Run the full benchmark."""
    models = [
        "gpt-4o-mini",      # $0.15 input, $0.60 output - proven, widely used
        "gpt-4.1-mini",     # $0.40 input, $1.60 output - newer, improved
        "gpt-4.1-nano",     # $0.10 input, $0.40 output - very cheap
        "gpt-5-nano",       # $0.05 input, $0.40 output - cheapest
        "gpt-5-mini",       # $0.25 input, $2.00 output - gpt-5 architecture
    ]

    runs_per_model = 10
    max_iterations = 3

    all_results: Dict[str, List[RunResult]] = {}

    print("="*60)
    print("TIS Driver Generation Benchmark")
    print("="*60)
    print(f"Models: {', '.join(models)}")
    print(f"Runs per model: {runs_per_model}")
    print(f"Max iterations per run: {max_iterations}")
    print(f"Function: json_object_equal")
    print("="*60)

    for model in models:
        print(f"\n{'#'*60}")
        print(f"# Benchmarking model: {model}")
        print(f"{'#'*60}")

        results = []
        for run_num in range(runs_per_model):
            result = run_benchmark(
                model=model,
                run_number=run_num,
                max_iterations=max_iterations,
            )
            results.append(result)

            # Small delay between runs to avoid rate limiting
            time.sleep(2)

        all_results[model] = results

        # Write CSV for this model
        write_csv(results, model)

    # Write summary CSV
    write_summary(all_results)

    # Print final summary
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)

    for model, results in all_results.items():
        successes = sum(1 for r in results if r.success)
        avg_time = sum(r.total_time_seconds for r in results) / len(results)
        print(f"\n{model}:")
        print(f"  Success rate: {successes}/{len(results)} ({successes/len(results)*100:.1f}%)")
        print(f"  Avg time: {avg_time:.2f}s")


if __name__ == "__main__":
    main()
