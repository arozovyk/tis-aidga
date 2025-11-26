"""Refiner node - fixes compilation errors."""

from ..state import DriverState
from ..models.openai_adapter import OpenAIAdapter
from ..prompts.templates import build_refiner_prompt


def refiner_node(state: DriverState, model_adapter: OpenAIAdapter) -> DriverState:
    """Refine driver based on compilation errors."""

    # Collect all errors
    all_errors = []
    for error_group in state.get("validation_errors", []):
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

    return {
        **state,
        "current_driver_code": refined_code,
        "iteration": state.get("iteration", 0) + 1,
        "validation_errors": [],  # Clear for next validation
        "status": "refining",
    }
