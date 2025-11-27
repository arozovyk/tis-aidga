"""Skeleton node - generates function skeleton using tis-analyzer."""

from ..state import DriverState
from ..workflow_logger import get_logger, get_structured_logger


def skeleton_node(state: DriverState, tis_runner) -> DriverState:
    """
    Generate driver skeleton using tis-analyzer -drivergen-skeleton.

    This provides the LLM with type definitions and function signatures
    without the parameter initialization logic.
    """
    function_name = state["function_name"]

    logger = get_logger()
    if logger:
        logger.log_step("SKELETON", state.get("iteration", 0))

    structured_logger = get_structured_logger()

    try:
        # Run tis-analyzer -drivergen-skeleton
        skeleton_code = tis_runner.generate_skeleton(
            function_name=function_name,
            source_files=[state["source_file"]],
            include_paths=state.get("include_paths", []),
        )

        if not skeleton_code:
            # Failed to generate skeleton - log and continue without it
            error_msg = f"Failed to generate skeleton for {function_name}"
            if logger:
                logger.log_message(f"⚠️  {error_msg}")
            if structured_logger:
                structured_logger.log_error(f"[skeleton] {error_msg}")

            return {
                **state,
                "skeleton_code": None,
                "status": "planning",
            }

        # Log the generated skeleton
        if logger:
            logger.log_message(f"✓ Generated skeleton ({len(skeleton_code)} chars)")

        if structured_logger:
            structured_logger.log_driver_code(
                code=skeleton_code,
                step="skeleton",
                iteration=state.get("iteration", 0),
            )

        return {
            **state,
            "skeleton_code": skeleton_code,
            "status": "planning",
        }

    except Exception as e:
        # If skeleton generation fails, log and continue without it
        error_msg = f"Skeleton generation failed: {str(e)}"
        if logger:
            logger.log_message(f"⚠️  {error_msg}")
        if structured_logger:
            structured_logger.log_error(f"[skeleton] {error_msg}")

        return {
            **state,
            "skeleton_code": None,
            "status": "planning",
        }
