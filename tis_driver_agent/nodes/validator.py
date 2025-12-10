"""Validator node - TIS compilation validation."""

from ..state import DriverState
from ..tis import TISRunnerBase
from ..workflow_logger import get_logger, get_structured_logger


def validator_node(
    state: DriverState,
    tis_runner: TISRunnerBase,
) -> DriverState:
    """
    Validate driver code using TIS Analyzer compilation.
    """
    iteration = state.get("iteration", 0)
    logger = get_logger()
    if logger:
        logger.log_step("VALIDATOR", iteration)

    errors = []
    source_file = state["source_file"]

    # Driver filename
    driver_filename = f"__tis_driver_{state['function_name']}.c"

    # Write driver to runner's location
    if not tis_runner.write_driver(state["current_driver_code"], driver_filename):
        structured_logger = get_structured_logger()
        if structured_logger:
            try:
                structured_logger.log_validation(
                    iteration=iteration,
                    tis_result={
                        "success": False,
                        "command": "(write_driver failed)",
                        "exit_code": -1,
                        "errors": ["Failed to write driver to remote"],
                        "stdout": "",
                        "stderr": "",
                        "info_json": None,
                    },
                    is_valid=False,
                )
            except Exception:
                pass  # Ignore logging failures

        return {
            **state,
            "tis_result": None,
            "validation_errors": [{"stage": "write", "errors": ["Failed to write driver"]}],
            "status": "validating",
        }

    try:
        tis_result = tis_runner.tis_compile(
            driver_path=driver_filename,
            source_files=[source_file],
            reference_file=source_file,
            compilation_db=None,
            function_name=state["function_name"],
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
        is_valid = tis_result.success
        if logger:
            error_summary = ""
            if not tis_result.success:
                error_summary = f"TIS failed with {len(tis_result.errors)} errors"
            logger.log_validation_decision(
                is_valid=is_valid,
                tis_success=tis_result.success,
                error_summary=error_summary,
            )

        # Log to structured logger
        structured_logger = get_structured_logger()
        if structured_logger:
            try:
                structured_logger.log_validation(
                    iteration=iteration,
                    tis_result={
                        "success": tis_result.success,
                        "command": tis_result.command,
                        "exit_code": tis_result.exit_code,
                        "errors": list(tis_result.errors),
                        "stdout": tis_result.stdout,
                        "stderr": tis_result.stderr,
                        "info_json": tis_result.info_json,
                    },
                    is_valid=is_valid,
                )
            except Exception:
                pass  # Ignore logging failures

        return {
            **state,
            "tis_result": {
                "success": tis_result.success,
                "errors": tis_result.errors,
                "command": tis_result.command,
                "info_json": tis_result.info_json,
            },
            "validation_errors": errors,
            "status": "validating",
        }

    finally:
        # Cleanup driver file on runner
        tis_runner.cleanup(driver_filename)
