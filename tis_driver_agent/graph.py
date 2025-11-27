"""LangGraph workflow definition."""

from langgraph.graph import StateGraph, END
from functools import partial

from .state import DriverState
from .nodes.planner import planner_node
from .nodes.skeleton import skeleton_node
from .nodes.router import router_node, route_decision
from .nodes.generator import generator_node
from .nodes.validator import validator_node
from .nodes.refiner import refiner_node


def create_workflow(
    model_adapter,
    tis_runner,
):
    """
    Create the LangGraph workflow.

    Args:
        model_adapter: OpenAI adapter for LLM calls
        tis_runner: TIS runner for validation

    Returns:
        Compiled LangGraph workflow
    """

    workflow = StateGraph(DriverState)

    # Bind dependencies to nodes
    bound_skeleton = partial(skeleton_node, tis_runner=tis_runner)
    bound_generator = partial(generator_node, model_adapter=model_adapter)
    bound_validator = partial(validator_node, tis_runner=tis_runner)
    bound_refiner = partial(refiner_node, model_adapter=model_adapter)

    # Output handler
    def output_handler(state: DriverState) -> DriverState:
        if not state.get("validation_errors"):
            return {
                **state,
                "final_driver": state["current_driver_code"],
                "status": "success",
            }
        return {**state, "status": "failed"}

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("skeleton", bound_skeleton)
    workflow.add_node("router", router_node)
    workflow.add_node("generator", bound_generator)
    workflow.add_node("validator", bound_validator)
    workflow.add_node("refiner", bound_refiner)
    workflow.add_node("output_handler", output_handler)

    # Define edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "skeleton")
    workflow.add_edge("skeleton", "router")
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {"generate": "generator", "refine": "refiner", "output": "output_handler"},
    )
    workflow.add_edge("generator", "validator")
    workflow.add_edge("refiner", "validator")
    workflow.add_conditional_edges(
        "validator",
        lambda s: "success" if not s.get("validation_errors") else "retry",
        {"success": "output_handler", "retry": "router"},
    )
    workflow.add_edge("output_handler", END)

    return workflow.compile()
