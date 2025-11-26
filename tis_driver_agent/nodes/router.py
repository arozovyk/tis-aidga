"""Router node - decides next action."""

from ..state import DriverState


def router_node(state: DriverState) -> DriverState:
    """Route to appropriate next node based on state."""

    # First time: generate
    if state.get("current_driver_code") is None:
        return {**state, "next_action": "generate"}

    # Check iteration limit
    if state.get("iteration", 0) >= state.get("max_iterations", 5):
        return {**state, "next_action": "output", "status": "failed"}

    # Has errors: refine
    if state.get("validation_errors"):
        return {**state, "next_action": "refine"}

    # Success
    return {**state, "next_action": "output"}


def route_decision(state: DriverState) -> str:
    """Return the routing decision."""
    return state.get("next_action", "generate")
