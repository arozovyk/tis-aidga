"""Generator node - generates driver code."""

from ..state import DriverState
from ..models.openai_adapter import OpenAIAdapter
from ..prompts.templates import build_generation_prompt


def generator_node(state: DriverState, model_adapter: OpenAIAdapter) -> DriverState:
    """Generate driver code using LLM."""

    # context_files is now a list of dicts with 'name' and 'content'
    prompt = build_generation_prompt(
        function_name=state["function_name"],
        context_contents=state["context_files"],
        include_paths=state.get("include_paths", []),
    )

    # Query model
    response = model_adapter.invoke(prompt)

    # Extract code
    driver_code = model_adapter.extract_code(response)

    return {
        **state,
        "current_driver_code": driver_code,
        "iteration": state.get("iteration", 0) + 1,
        "status": "generating",
    }
