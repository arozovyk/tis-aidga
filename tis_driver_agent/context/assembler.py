"""Assemble context for LLM prompt injection."""

import os
from typing import Dict, List, Optional

from .models import FunctionInfo, TypeInfo
from .lookup import (
    get_connection,
    get_function,
    collect_factories_recursive,
    find_type,
)
from .parser import normalize_type, categorize_type


def assemble_context(
    index_path: str,
    function_name: str,
    max_depth: int = 2,
    include_types: bool = True,
) -> str:
    """
    Assemble context for generating a test driver.

    Args:
        index_path: Path to context_index.db
        function_name: Name of the target function
        max_depth: Max recursion depth for factory dependencies
        include_types: Whether to include type definitions

    Returns:
        Formatted markdown context for prompt injection
    """
    conn = get_connection(index_path)

    try:
        # 1. Get target function
        target = get_function(conn, function_name)
        if not target:
            return f"<!-- Function '{function_name}' not found in index -->"

        # 2. Extract parameter types
        param_types = []
        for param in target.params:
            category = categorize_type(param.type)
            if category == 'struct_ptr':
                param_types.append(param.type)

        # 3. Collect factories for each type (with transitive deps)
        factories: Dict[str, List[FunctionInfo]] = {}
        visited = set()

        for ptype in param_types:
            collect_factories_recursive(conn, ptype, factories, visited, 0, max_depth)

        # 4. Get type definitions
        type_defs: Dict[str, TypeInfo] = {}
        if include_types:
            for ptype in param_types:
                type_info = find_type(conn, ptype)
                if type_info:
                    type_defs[normalize_type(ptype)] = type_info

            # Also get enum types used in factories
            for type_name, funcs in factories.items():
                for func in funcs:
                    for param in func.params:
                        if categorize_type(param.type) == 'enum':
                            enum_info = find_type(conn, param.type)
                            if enum_info:
                                type_defs[normalize_type(param.type)] = enum_info

        # 5. Format context
        return format_context(target, factories, type_defs)

    finally:
        conn.close()


def format_context(
    target: FunctionInfo,
    factories: Dict[str, List[FunctionInfo]],
    type_defs: Dict[str, TypeInfo],
) -> str:
    """
    Format collected context as markdown for LLM prompt.

    Includes doc comments when available.
    """
    lines = []

    # Header
    lines.append(f"## Context for generating test driver for `{target.name}`")
    lines.append("")

    # Target function signature
    lines.append("### Target Function Signature")
    lines.append("```c")
    # Extract just the signature (before the body)
    sig = target.source.split('{')[0].strip() if '{' in target.source else target.source.strip()
    if not sig.endswith(';'):
        sig += ';'
    lines.append(sig)
    lines.append("```")
    lines.append("")

    # Object creation API
    if factories:
        lines.append("### Object Creation API")
        lines.append("")
        lines.append("**Use these functions to create objects. DO NOT use `tis_alloc()` to allocate structs directly.**")
        lines.append("")

        for type_name, funcs in factories.items():
            lines.append(f"#### For `{type_name}` (or `struct {type_name} *`)")
            lines.append("```c")

            for func in funcs:
                # Include doc comment if present
                if func.doc_comment:
                    lines.append(func.doc_comment)

                # Location comment
                basename = os.path.basename(func.file_path)
                lines.append(f"// From {basename}:{func.line_number}")

                # Function signature only (not full body)
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if not sig.endswith(';'):
                    sig += ';'
                lines.append(sig)
                lines.append("")

            lines.append("```")
            lines.append("")

    # Type information
    if type_defs:
        lines.append("### Type Information")
        lines.append("```c")

        for type_name, type_info in type_defs.items():
            if type_info.source:
                lines.append(f"// {type_info.category}: {type_name}")
                lines.append(type_info.source)
                lines.append("")

        lines.append("```")
        lines.append("")

    # Parameter handling guide
    if target.params:
        lines.append("### Parameter Initialization Guide")
        lines.append("")
        lines.append("| Parameter | Type | Recommended Approach |")
        lines.append("|-----------|------|---------------------|")

        for param in target.params:
            category = categorize_type(param.type)
            normalized = normalize_type(param.type)

            if category == 'struct_ptr' and normalized in factories:
                factory_names = [f.name for f in factories[normalized][:3]]
                approach = f"Use `{factory_names[0]}()`" + (f" or similar" if len(factory_names) > 1 else "")
            elif category == 'string':
                approach = "`malloc()` + `tis_make_unknown()` + null-terminate"
            elif category == 'enum':
                approach = "`tis_interval()` over enum range"
            elif category == 'primitive':
                approach = "`tis_int_interval()` or specific value"
            elif category == 'func_ptr':
                approach = "`NULL` or stub function"
            else:
                approach = "See type definition"

            lines.append(f"| `{param.name}` | `{param.type}` | {approach} |")

        lines.append("")

    return '\n'.join(lines)


def get_context_summary(index_path: str, function_name: str) -> Optional[Dict]:
    """
    Get a summary of available context for a function.

    Useful for debugging/CLI output.
    """
    conn = get_connection(index_path)

    try:
        target = get_function(conn, function_name)
        if not target:
            return None

        # Collect factories
        factories: Dict[str, List[FunctionInfo]] = {}
        visited = set()

        for param in target.params:
            if categorize_type(param.type) == 'struct_ptr':
                collect_factories_recursive(conn, param.type, factories, visited, 0, 2)

        return {
            "function": target.name,
            "params": [(p.type, p.name) for p in target.params],
            "factories": {
                type_name: [f.name for f in funcs]
                for type_name, funcs in factories.items()
            },
        }

    finally:
        conn.close()
