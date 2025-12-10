"""AST-based context retrieval for driver generation."""

from .models import FunctionInfo, TypeInfo, Param
from .index import build_index, get_index_stats
from .parser import extract_functions, extract_types, normalize_type, categorize_type
from .lookup import (
    get_connection,
    get_function,
    find_factories,
    find_initializers,
    find_type,
    collect_factories_recursive,
    search_functions,
)
from .assembler import assemble_context, format_context, get_context_summary

__all__ = [
    # Models
    "FunctionInfo",
    "TypeInfo",
    "Param",
    # Index
    "build_index",
    "get_index_stats",
    # Parser
    "extract_functions",
    "extract_types",
    "normalize_type",
    "categorize_type",
    # Lookup
    "get_connection",
    "get_function",
    "find_factories",
    "find_initializers",
    "find_type",
    "collect_factories_recursive",
    "search_functions",
    # Assembler
    "assemble_context",
    "format_context",
    "get_context_summary",
]
