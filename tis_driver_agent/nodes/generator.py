"""Generator node - generates driver code."""

from ..state import DriverState
from ..models.openai_adapter import OpenAIAdapter
from ..prompts.templates import build_generation_prompt
from ..workflow_logger import get_logger, get_structured_logger


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

    iteration = state.get("iteration", 0) + 1

    # Log generated code (workflow logger)
    logger = get_logger()
    if logger:
        logger.log_step("GENERATOR", iteration)
        logger.log_generated_code(driver_code, iteration)

    # Log to structured logger (separate files)
    structured_logger = get_structured_logger()
    if structured_logger:
        structured_logger.log_llm_query(
            prompt=prompt,
            response=response,
            step="generator",
            iteration=iteration,
            model=model_adapter.model,
        )
        structured_logger.log_driver_code(
            code=driver_code,
            step="generator",
            iteration=iteration,
        )

    return {
        **state,
        "current_driver_code": driver_code,
        "iteration": iteration,
        "status": "generating",
    }
