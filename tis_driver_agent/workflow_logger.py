"""Workflow logger - logs detailed workflow steps to file."""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class StructuredLogger:
    """Logs workflow artifacts to separate files in a logs directory."""

    def __init__(self, logs_dir: str):
        """
        Initialize structured logger.

        Args:
            logs_dir: Directory to store log files
        """
        self.logs_dir = logs_dir
        self._step_counter = 0
        self._ensure_dir()

    def _ensure_dir(self):
        """Create logs directory if it doesn't exist."""
        os.makedirs(self.logs_dir, exist_ok=True)

    def _next_index(self) -> int:
        """Get next step index."""
        self._step_counter += 1
        return self._step_counter

    def log_driver_code(self, code: str, step: str, iteration: int) -> str:
        """
        Log generated C code to a file.

        Args:
            code: The C code content
            step: Step name (generator, refiner)
            iteration: Current iteration number

        Returns:
            Path to the created file
        """
        idx = self._next_index()
        filename = f"{idx:03d}_{step}_iter{iteration}_driver.c"
        filepath = os.path.join(self.logs_dir, filename)

        with open(filepath, "w") as f:
            f.write(f"// Step: {step}\n")
            f.write(f"// Iteration: {iteration}\n")
            f.write(f"// Timestamp: {datetime.now().isoformat()}\n")
            f.write("// " + "=" * 60 + "\n\n")
            f.write(code)

        return filepath

    def log_llm_query(
        self,
        prompt: str,
        response: str,
        step: str,
        iteration: int,
        model: str = "",
    ) -> str:
        """
        Log LLM query and response to a file.

        Args:
            prompt: The prompt sent to the LLM
            response: The LLM response
            step: Step name (generator, refiner)
            iteration: Current iteration number
            model: Model name

        Returns:
            Path to the created file
        """
        idx = self._next_index()
        filename = f"{idx:03d}_{step}_iter{iteration}_query.txt"
        filepath = os.path.join(self.logs_dir, filename)

        with open(filepath, "w") as f:
            f.write(f"Step: {step}\n")
            f.write(f"Iteration: {iteration}\n")
            f.write(f"Model: {model}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            f.write("=== PROMPT ===\n")
            f.write(prompt)
            f.write("\n\n" + "=" * 80 + "\n\n")
            f.write("=== RESPONSE ===\n")
            f.write(response)

        return filepath

    def log_validation(
        self,
        iteration: int,
        cc_result: Optional[Dict[str, Any]],
        tis_result: Optional[Dict[str, Any]],
        is_valid: bool,
    ) -> str:
        """
        Log validation results to a JSON file.

        Args:
            iteration: Current iteration number
            cc_result: CC compilation result dict
            tis_result: TIS compilation result dict
            is_valid: Whether validation passed

        Returns:
            Path to the created file
        """
        idx = self._next_index()
        filename = f"{idx:03d}_validation_iter{iteration}.json"
        filepath = os.path.join(self.logs_dir, filename)

        data = {
            "step": "validation",
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "is_valid": is_valid,
            "cc_compile": cc_result,
            "tis_compile": tis_result,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    def log_summary(
        self,
        success: bool,
        total_iterations: int,
        function_name: str,
        source_file: str,
    ) -> str:
        """
        Log final summary.

        Args:
            success: Whether generation succeeded
            total_iterations: Total iterations performed
            function_name: Target function name
            source_file: Source file path

        Returns:
            Path to the created file
        """
        idx = self._next_index()
        filename = f"{idx:03d}_summary.json"
        filepath = os.path.join(self.logs_dir, filename)

        data = {
            "step": "summary",
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "total_iterations": total_iterations,
            "function_name": function_name,
            "source_file": source_file,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath


class WorkflowLogger:
    """Logs workflow execution details to a file."""

    def __init__(self, log_path: Optional[str] = None):
        """
        Initialize logger.

        Args:
            log_path: Path to log file. If None, logging is disabled.
        """
        self.log_path = log_path
        self._initialized = False

    def _ensure_initialized(self):
        """Create log file with header on first write."""
        if self._initialized or not self.log_path:
            return

        # Ensure directory exists
        log_dir = os.path.dirname(self.log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Write header
        with open(self.log_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("TIS DRIVER AGENT - WORKFLOW LOG\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

        self._initialized = True

    def _write(self, text: str):
        """Write text to log file."""
        if not self.log_path:
            return
        self._ensure_initialized()
        with open(self.log_path, "a") as f:
            f.write(text)

    def log_config(
        self,
        function_name: str,
        source_file: str,
        model: str,
        max_iterations: int,
        context_file_count: int,
        include_paths: List[str],
    ):
        """Log initial configuration."""
        self._write(f"CONFIGURATION\n")
        self._write(f"-" * 40 + "\n")
        self._write(f"Function: {function_name}\n")
        self._write(f"Source file: {source_file}\n")
        self._write(f"Model: {model}\n")
        self._write(f"Max iterations: {max_iterations}\n")
        self._write(f"Context files: {context_file_count}\n")
        self._write(f"Include paths ({len(include_paths)}):\n")
        for path in include_paths[:10]:
            self._write(f"  - {path}\n")
        if len(include_paths) > 10:
            self._write(f"  ... and {len(include_paths) - 10} more\n")
        self._write("\n")

    def log_step(self, step_name: str, iteration: int = 0):
        """Log a workflow step."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._write(f"\n{'=' * 80}\n")
        self._write(f"[{timestamp}] STEP: {step_name}")
        if iteration > 0:
            self._write(f" (iteration {iteration})")
        self._write("\n")
        self._write("=" * 80 + "\n\n")

    def log_generated_code(self, code: str, iteration: int):
        """Log generated driver code."""
        self._write(f"GENERATED CODE (iteration {iteration})\n")
        self._write("-" * 40 + "\n")
        self._write("```c\n")
        self._write(code)
        self._write("\n```\n\n")

    def log_cc_result(
        self,
        success: bool,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        errors: List[str],
    ):
        """Log CC compilation result."""
        self._write(f"CC COMPILATION: {'SUCCESS' if success else 'FAILED'}\n")
        self._write("-" * 40 + "\n")
        self._write(f"Command: {command}\n")
        self._write(f"Exit code: {exit_code}\n")

        if stdout.strip():
            self._write(f"\nStdout:\n{stdout}\n")

        if stderr.strip():
            self._write(f"\nStderr:\n{stderr}\n")

        if errors:
            self._write(f"\nParsed errors ({len(errors)}):\n")
            for err in errors:
                self._write(f"  - {err}\n")

        self._write("\n")

    def log_tis_result(
        self,
        success: bool,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        errors: List[str],
    ):
        """Log TIS compilation result."""
        self._write(f"TIS COMPILATION: {'SUCCESS' if success else 'FAILED'}\n")
        self._write("-" * 40 + "\n")
        self._write(f"Command: {command}\n")
        self._write(f"Exit code: {exit_code}\n")

        if stdout.strip():
            self._write(f"\nStdout:\n{stdout}\n")

        if stderr.strip():
            self._write(f"\nStderr:\n{stderr}\n")

        if errors:
            self._write(f"\nParsed errors ({len(errors)}):\n")
            for err in errors:
                self._write(f"  - {err}\n")

        self._write("\n")

    def log_validation_decision(
        self,
        is_valid: bool,
        cc_success: bool,
        tis_success: bool,
        error_summary: str,
    ):
        """Log validation decision and reasoning."""
        self._write(f"VALIDATION DECISION: {'PASS' if is_valid else 'FAIL'}\n")
        self._write("-" * 40 + "\n")
        self._write(f"CC compile passed: {cc_success}\n")
        self._write(f"TIS compile passed: {tis_success}\n")
        if error_summary:
            self._write(f"Error summary: {error_summary}\n")
        self._write("\n")

    def log_refine_context(self, errors: List[Dict[str, Any]]):
        """Log context being sent to refiner."""
        self._write(f"REFINE CONTEXT\n")
        self._write("-" * 40 + "\n")
        self._write(f"Errors to fix ({len(errors)}):\n")
        for i, err_dict in enumerate(errors, 1):
            stage = err_dict.get("stage", "unknown")
            err_list = err_dict.get("errors", [])
            self._write(f"\n  [{i}] Stage: {stage}\n")
            for e in err_list:
                self._write(f"      - {e}\n")
        self._write("\n")

    def log_final_result(
        self,
        success: bool,
        iterations: int,
        output_path: Optional[str] = None,
    ):
        """Log final result."""
        self._write("\n" + "=" * 80 + "\n")
        self._write("FINAL RESULT\n")
        self._write("=" * 80 + "\n")
        self._write(f"Status: {'SUCCESS' if success else 'FAILED'}\n")
        self._write(f"Total iterations: {iterations}\n")
        if output_path:
            self._write(f"Output file: {output_path}\n")
        self._write(f"Completed: {datetime.now().isoformat()}\n")

    def log_error(self, message: str):
        """Log an error message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._write(f"[{timestamp}] ERROR: {message}\n")


# Global logger instances - set by CLI
_logger: Optional[WorkflowLogger] = None
_structured_logger: Optional[StructuredLogger] = None


def get_logger() -> Optional[WorkflowLogger]:
    """Get the global workflow logger instance."""
    return _logger


def set_logger(logger: WorkflowLogger):
    """Set the global workflow logger instance."""
    global _logger
    _logger = logger


def get_structured_logger() -> Optional[StructuredLogger]:
    """Get the global structured logger instance."""
    return _structured_logger


def set_structured_logger(logger: StructuredLogger):
    """Set the global structured logger instance."""
    global _structured_logger
    _structured_logger = logger
