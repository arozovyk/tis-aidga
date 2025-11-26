"""Validator node - two-step compilation validation."""

import tempfile
import os

from ..state import DriverState
from ..cc import cc_compile
from ..tis import TISRunnerBase
from ..workflow_logger import get_logger, get_structured_logger


def validator_node(
    state: DriverState,
    tis_runner: TISRunnerBase,
) -> DriverState:
    """
    Two-step validation:
    1. Basic C compilation (cc) - always runs locally
    2. TIS Analyzer compilation - runs via tis_runner (local or remote)
    """
    iteration = state.get("iteration", 0)
    logger = get_logger()
    if logger:
        logger.log_step("VALIDATOR", iteration)

    errors = []
    include_paths = state.get("include_paths", [])
    source_file = state["source_file"]

    # Driver filename
    driver_filename = f"__tis_driver_{state['function_name']}.c"

    # Stage 1: CC compile locally
    # Write driver to temp file for local cc check
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.c', delete=False
        ) as tmp:
            tmp.write(state["current_driver_code"])
            local_driver_path = tmp.name

        cc_result = cc_compile(local_driver_path, include_paths)

        # Log CC result
        if logger:
            logger.log_cc_result(
                success=cc_result.success,
                command=cc_result.command,
                exit_code=cc_result.exit_code,
                stdout=cc_result.stdout,
                stderr=cc_result.stderr,
                errors=cc_result.errors,
            )

        if not cc_result.success:
            errors.append(
                {
                    "stage": "cc_compile",
                    "errors": cc_result.errors,
                    "stderr": cc_result.stderr,
                }
            )
            # Log validation decision for CC failure
            if logger:
                logger.log_validation_decision(
                    is_valid=False,
                    cc_success=False,
                    tis_success=False,
                    error_summary=f"CC failed with {len(cc_result.errors)} errors (TIS not attempted)",
                )
            # Log to structured logger (CC failed, TIS not attempted)
            structured_logger = get_structured_logger()
            if structured_logger:
                structured_logger.log_validation(
                    iteration=iteration,
                    cc_result={
                        "success": cc_result.success,
                        "command": cc_result.command,
                        "exit_code": cc_result.exit_code,
                        "errors": cc_result.errors,
                        "stdout": cc_result.stdout,
                        "stderr": cc_result.stderr,
                    },
                    tis_result=None,
                    is_valid=False,
                )
            return {
                **state,
                "cc_result": {
                    "success": cc_result.success,
                    "errors": cc_result.errors,
                    "command": cc_result.command,
                },
                "tis_result": None,
                "validation_errors": errors,
                "status": "validating",
            }
    finally:
        # Cleanup local temp file
        if os.path.exists(local_driver_path):
            os.unlink(local_driver_path)

    # Stage 2: TIS compile (via runner - local or remote)
    # Write driver to runner's location
    if not tis_runner.write_driver(state["current_driver_code"], driver_filename):
        return {
            **state,
            "cc_result": {
                "success": cc_result.success,
                "errors": cc_result.errors,
                "command": cc_result.command,
            },
            "tis_result": None,
            "validation_errors": [{"stage": "write", "errors": ["Failed to write driver"]}],
            "status": "validating",
        }

    try:
        tis_result = tis_runner.tis_compile(
            driver_path=driver_filename,
            source_files=[source_file],
            reference_file=source_file,
            compilation_db=None,  # Use include paths instead
        )

        # Log TIS result
        if logger:
            logger.log_tis_result(
                success=tis_result.success,
                command=tis_result.command,
                exit_code=tis_result.exit_code,
                stdout=tis_result.stdout,
                stderr=tis_result.stderr,
                errors=tis_result.errors,
            )

        if not tis_result.success:
            errors.append(
                {
                    "stage": "tis_compile",
                    "errors": tis_result.errors,
                    "stderr": tis_result.stderr,
                }
            )

        # Log validation decision
        is_valid = cc_result.success and tis_result.success
        if logger:
            error_summary = ""
            if not cc_result.success:
                error_summary = f"CC failed with {len(cc_result.errors)} errors"
            elif not tis_result.success:
                error_summary = f"TIS failed with {len(tis_result.errors)} errors"
            logger.log_validation_decision(
                is_valid=is_valid,
                cc_success=cc_result.success,
                tis_success=tis_result.success,
                error_summary=error_summary,
            )

        # Log to structured logger (separate files)
        structured_logger = get_structured_logger()
        if structured_logger:
            structured_logger.log_validation(
                iteration=iteration,
                cc_result={
                    "success": cc_result.success,
                    "command": cc_result.command,
                    "exit_code": cc_result.exit_code,
                    "errors": cc_result.errors,
                    "stdout": cc_result.stdout,
                    "stderr": cc_result.stderr,
                },
                tis_result={
                    "success": tis_result.success,
                    "command": tis_result.command,
                    "exit_code": tis_result.exit_code,
                    "errors": tis_result.errors,
                    "stdout": tis_result.stdout,
                    "stderr": tis_result.stderr,
                },
                is_valid=is_valid,
            )

        return {
            **state,
            "cc_result": {
                "success": cc_result.success,
                "errors": cc_result.errors,
                "command": cc_result.command,
            },
            "tis_result": {
                "success": tis_result.success,
                "errors": tis_result.errors,
                "command": tis_result.command,
            },
            "validation_errors": errors,
            "status": "validating",
        }

    finally:
        # Cleanup driver file on runner
        tis_runner.cleanup(driver_filename)
