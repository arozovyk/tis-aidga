"""Assemble context for LLM prompt injection."""

import os
import re
from typing import Dict, List, Optional, Set

from .models import FunctionInfo, TypeInfo
from .lookup import (
    get_connection,
    get_function,
    collect_factories_recursive,
    find_type,
)
from .parser import normalize_type, categorize_type


def extract_type_identifiers(signatures: List[str]) -> Set[str]:
    """
    Extract all type identifiers from function signatures.

    Looks for potential typedef/enum names that aren't standard C types.
    """
    all_text = ' '.join(signatures)

    # Standard C types we don't need to define
    standard_types = {
        'void', 'int', 'char', 'short', 'long', 'float', 'double',
        'unsigned', 'signed', 'const', 'volatile', 'static', 'extern',
        'struct', 'enum', 'union', 'typedef',
        'size_t', 'ssize_t', 'ptrdiff_t',
        'int8_t', 'int16_t', 'int32_t', 'int64_t',
        'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
        'bool', '_Bool', 'FILE',
    }

    # Find all identifiers (words that could be type names)
    # Pattern: word characters that aren't preceded by 'struct ' or 'enum '
    identifiers = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', all_text))

    # Filter out standard types and common keywords
    custom_types = identifiers - standard_types

    # Filter out things that are clearly not types (function names, param names)
    # Type names typically end with _t, _type, _bool, etc. or are used in specific contexts
    potential_types = set()
    for ident in custom_types:
        # Skip if it looks like a function name (starts with project prefix and has verb)
        if re.match(r'^(json_object_|json_tokener_)\w+$', ident):
            continue
        # Keep if it looks like a type (ends with common type suffixes)
        if re.search(r'(_t|_type|_bool|_error|_state|_flags)$', ident):
            potential_types.add(ident)
        # Also keep short identifiers that appear before a parameter name
        elif re.search(rf'\b{ident}\s+\w+[,)]', all_text):
            potential_types.add(ident)

    return potential_types


def resolve_type_definitions(conn, type_names: Set[str]) -> Dict[str, str]:
    """
    Look up type definitions from the index.

    Returns dict of {type_name: definition_source}
    """
    definitions = {}

    for type_name in type_names:
        type_info = find_type(conn, type_name)
        if type_info and type_info.source:
            definitions[type_name] = type_info.source

    return definitions


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

        # 3. Collect factories for each type (with semantic filtering)
        factories: Dict[str, List[FunctionInfo]] = {}
        visited = set()

        for ptype in param_types:
            collect_factories_recursive(
                conn, ptype, factories, visited,
                depth=0, max_depth=1,
                target_function_name=function_name,
            )

        # 4. Get type definitions
        type_defs: Dict[str, TypeInfo] = {}
        if include_types:
            for ptype in param_types:
                type_info = find_type(conn, ptype)
                if type_info:
                    type_defs[normalize_type(ptype)] = type_info

            # Also get enum types used in top factories (limit to top 3 per type)
            for _, funcs in factories.items():
                for func in funcs[:3]:  # Only top 3 to avoid noise from low-ranked factories
                    for param in func.params:
                        if categorize_type(param.type) == 'enum':
                            enum_info = find_type(conn, param.type)
                            if enum_info:
                                type_defs[normalize_type(param.type)] = enum_info

        # 5. Collect factory signatures and resolve type dependencies
        factory_signatures = []
        for funcs in factories.values():
            for func in funcs[:5]:  # Top 5 per type
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if 'static ' not in sig:
                    factory_signatures.append(sig)

        # Extract and resolve type dependencies from signatures
        required_type_names = extract_type_identifiers(factory_signatures)
        required_type_defs = resolve_type_definitions(conn, required_type_names)

        # 6. Format context (pass target param types for forward declarations)
        target_param_types = set(normalize_type(pt) for pt in param_types)
        return format_context(target, factories, type_defs, required_type_defs, target_param_types)

    finally:
        conn.close()


def format_context(
    target: FunctionInfo,
    factories: Dict[str, List[FunctionInfo]],
    type_defs: Dict[str, TypeInfo],
    required_type_defs: Optional[Dict[str, str]] = None,
    target_param_types: Optional[Set[str]] = None,
) -> str:
    """
    Format collected context as markdown for LLM prompt.

    Args:
        target: Target function info
        factories: Dict of type_name -> list of factory functions
        type_defs: Dict of type definitions
        required_type_defs: Dict of required type definitions from factory signatures
        target_param_types: Set of normalized type names that the target function needs
                           (only these get forward declarations)

    Includes doc comments when available.
    """
    lines = []

    # Header
    lines.append(f"## Context for generating test driver for `{target.name}`")
    lines.append("")

    # Target function signature and documentation
    lines.append("### Target Function")
    if target.doc_comment:
        lines.append("")
        lines.append("**Documentation:**")
        lines.append("```")
        lines.append(target.doc_comment)
        lines.append("```")
    lines.append("")
    lines.append("**Signature:**")
    lines.append("```c")
    # Extract just the signature (before the body)
    sig = target.source.split('{')[0].strip() if '{' in target.source else target.source.strip()
    if not sig.endswith(';'):
        sig += ';'
    lines.append(sig)
    lines.append("```")
    lines.append("")

    # Include function body for context (helps LLM understand what to test)
    if '{' in target.source:
        lines.append("**Implementation (for understanding what code paths to exercise):**")
        lines.append("```c")
        # Truncate very long bodies
        body_lines = target.source.split('\n')
        if len(body_lines) > 80:
            lines.append('\n'.join(body_lines[:80]))
            lines.append('// ... (truncated)')
        else:
            lines.append(target.source)
        lines.append("```")
        lines.append("")

    # Object creation API - only show factories for types the target function needs
    relevant_factories = {
        k: v for k, v in factories.items()
        if not target_param_types or k in target_param_types
    }

    if relevant_factories:
        lines.append("### Object Creation API")
        lines.append("")
        lines.append("**CRITICAL: Use these constructor functions to create objects.**")
        lines.append("**DO NOT use `tis_alloc()`, `malloc()`, or manual struct allocation for these types.**")
        lines.append("")

        for type_name, funcs in relevant_factories.items():
            # Limit to top 10 most relevant factories per type
            top_funcs = funcs[:10]

            lines.append(f"#### Constructors for `{type_name}` (struct {type_name} *)")
            lines.append("")
            lines.append("Use one of these functions to create instances:")
            lines.append("")
            lines.append("```c")

            for func in top_funcs:
                # Include doc comment if present (truncated if too long)
                if func.doc_comment:
                    doc_lines = func.doc_comment.strip().split('\n')
                    if len(doc_lines) > 5:
                        doc_lines = doc_lines[:5] + ['...']
                    lines.append('\n'.join(doc_lines))

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

            if len(funcs) > 10:
                lines.append(f"*({len(funcs) - 10} more constructors available)*")
            lines.append("")

        # Add extern declarations section that the LLM can copy
        lines.append("### Required Extern Declarations")
        lines.append("")
        lines.append("**Copy these declarations into your driver to use the constructor functions:**")
        lines.append("")
        lines.append("```c")
        lines.append("// Forward declare opaque types (DO NOT define the struct contents)")
        # Only forward-declare types that the target function actually needs,
        # not types that appear as factory parameters (e.g., json_tokener)
        types_to_declare = target_param_types if target_param_types else set(factories.keys())
        for type_name in types_to_declare:
            lines.append(f"struct {type_name};")
        lines.append("")

        # Include required type definitions (typedefs, enums used in signatures)
        if required_type_defs:
            lines.append("// Required type definitions for constructor parameters")
            for type_name, type_source in required_type_defs.items():
                # Clean up the source - just include the typedef/enum definition
                source = type_source.strip()
                if not source.endswith(';'):
                    source += ';'
                lines.append(source)
            lines.append("")

        # Collect all signatures (only from relevant factories)
        signatures = []
        for type_name, funcs in relevant_factories.items():
            for func in funcs[:5]:  # Top 5 per type
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if not sig.endswith(';'):
                    sig += ';'
                if 'static ' in sig:
                    continue
                if not sig.startswith('extern'):
                    sig = 'extern ' + sig
                signatures.append(sig)

        lines.append("// Constructor function declarations")
        for sig in signatures:
            lines.append(sig)
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
                collect_factories_recursive(
                    conn, param.type, factories, visited,
                    depth=0, max_depth=1,
                    target_function_name=function_name,
                )

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
