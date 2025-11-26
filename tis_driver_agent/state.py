"""State schema for LangGraph workflow."""

from typing import TypedDict, List, Optional, Literal


class DriverState(TypedDict):
    """State passed between nodes."""

    # Input (from project)
    function_name: str
    function_signature: str
    source_file: str  # Path to source file on remote
    context_files: List[dict]  # List of dicts with 'name' and 'content' keys
    include_paths: List[str]  # Include paths for compilation
    remote_work_dir: str  # Remote working directory

    # Processing
    plan: Optional[str]
    current_driver_code: Optional[str]
    iteration: int
    max_iterations: int

    # Validation
    cc_result: Optional[dict]
    tis_result: Optional[dict]
    validation_errors: List[dict]

    # Output
    final_driver: Optional[str]
    status: Literal[
        "planning", "generating", "validating", "refining", "success", "failed"
    ]
    error_message: Optional[str]

    # Routing
    next_action: Optional[str]
