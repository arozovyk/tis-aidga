"""Planner node - analyzes function and creates basic plan."""

from ..state import DriverState


def planner_node(state: DriverState) -> DriverState:
    """
    Basic planner - just passes through for Phase 1.
    In later phases, this will create a structured plan.
    """
    # For Phase 1, we skip detailed planning
    # Just mark as ready to generate
    return {
        **state,
        "plan": f"Generate driver for {state['function_name']}",
        "status": "planning",
    }
