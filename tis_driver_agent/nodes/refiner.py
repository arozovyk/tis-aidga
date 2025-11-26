"""Refiner node - fixes compilation errors."""

from ..state import DriverState
from ..models.openai_adapter import OpenAIAdapter
from ..prompts.templates import build_refiner_prompt
from ..workflow_logger import get_logger


def refiner_node(state: DriverState, model_adapter: OpenAIAdapter) -> DriverState:
    """Refine driver based on compilation errors."""

    iteration = state.get("iteration", 0) + 1
    validation_errors = state.get("validation_errors", [])

    # Log refine context (what errors are being fixed)
    logger = get_logger()
    if logger:
        logger.log_step("REFINER", iteration)
        logger.log_refine_context(validation_errors)

    # Collect all errors
    all_errors = []
    for error_group in validation_errors:
        all_errors.extend(error_group.get("errors", []))

    # Build prompt
    prompt = build_refiner_prompt(
        current_code=state["current_driver_code"],
        errors=all_errors,
        iteration=state.get("iteration", 1),
        max_iterations=state.get("max_iterations", 5),
    )

    # Query model
    response = model_adapter.invoke(prompt)

    # Extract code
    refined_code = model_adapter.extract_code(response)

    # Log refined code
    if logger:
        logger.log_generated_code(refined_code, iteration)

    return {
        **state,
        "current_driver_code": refined_code,
        "iteration": iteration,
        "validation_errors": [],  # Clear for next validation
        "status": "refining",
    }
