"""Assemble context for LLM prompt injection."""

import os
import re
from typing import Dict, List, Optional, Set

from .models import FunctionInfo, TypeInfo
from .lookup import (
    get_connection,
    get_function,
    collect_factories_recursive,
    find_initializers,
    find_type,
)
from .parser import normalize_type, categorize_type


def add_struct_keyword_to_signature(sig: str, opaque_types: Set[str]) -> str:
    """
    Ensure opaque type names in a signature use the 'struct' keyword.

    In C, when using forward-declared types (e.g., `struct json_object;`),
    you must use `struct json_object *` not just `json_object *`.
    This function transforms signatures to use the correct form.

    Args:
        sig: Function signature string
        opaque_types: Set of type names that are forward-declared as opaque structs

    Returns:
        Signature with struct keywords added where needed
    """
    result = sig
    for opaque_type in opaque_types:
        # Match the type name followed by optional whitespace and *
        # but not already preceded by 'struct '
        # Use word boundary to avoid partial matches
        pattern = rf'(?<!\bstruct\s)(?<!\bstruct)\b({re.escape(opaque_type)})\s*\*'
        replacement = rf'struct \1 *'
        result = re.sub(pattern, replacement, result)
    return result


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

        # 4. Collect initializers for each type (for types without factories)
        initializers: Dict[str, List[FunctionInfo]] = {}
        for ptype in param_types:
            normalized = normalize_type(ptype)
            # Find initializers for this type
            type_initializers = find_initializers(conn, ptype, function_name)
            if type_initializers:
                initializers[normalized] = type_initializers

        # 5. Get type definitions
        type_defs: Dict[str, TypeInfo] = {}
        if include_types:
            for ptype in param_types:
                type_info = find_type(conn, ptype)
                if type_info:
                    type_defs[normalize_type(ptype)] = type_info

            # Also get enum types used in top factories/initializers
            all_funcs = []
            for funcs in factories.values():
                all_funcs.extend(funcs[:3])
            for funcs in initializers.values():
                all_funcs.extend(funcs[:3])

            for func in all_funcs:
                for param in func.params:
                    if categorize_type(param.type) == 'enum':
                        enum_info = find_type(conn, param.type)
                        if enum_info:
                            type_defs[normalize_type(param.type)] = enum_info

        # 6. Collect function signatures and resolve type dependencies
        all_signatures = []
        for funcs in factories.values():
            for func in funcs[:5]:
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if 'static ' not in sig:
                    all_signatures.append(sig)
        for funcs in initializers.values():
            for func in funcs[:5]:
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if 'static ' not in sig:
                    all_signatures.append(sig)

        # Extract and resolve type dependencies from signatures
        required_type_names = extract_type_identifiers(all_signatures)
        required_type_defs = resolve_type_definitions(conn, required_type_names)

        # 7. Format context (pass target param types for forward declarations)
        target_param_types = set(normalize_type(pt) for pt in param_types)
        return format_context(
            target, factories, initializers, type_defs,
            required_type_defs, target_param_types
        )

    finally:
        conn.close()


def format_context(
    target: FunctionInfo,
    factories: Dict[str, List[FunctionInfo]],
    initializers: Dict[str, List[FunctionInfo]],
    type_defs: Dict[str, TypeInfo],
    required_type_defs: Optional[Dict[str, str]] = None,
    target_param_types: Optional[Set[str]] = None,
) -> str:
    """
    Format collected context as markdown for LLM prompt.

    Args:
        target: Target function info
        factories: Dict of type_name -> list of factory functions
        initializers: Dict of type_name -> list of initializer functions
        type_defs: Dict of type definitions
        required_type_defs: Dict of required type definitions from signatures
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

    # Filter to relevant types only
    relevant_factories = {
        k: v for k, v in factories.items()
        if not target_param_types or k in target_param_types
    }
    relevant_initializers = {
        k: v for k, v in initializers.items()
        if not target_param_types or k in target_param_types
    }

    # Types to declare (for extern declarations)
    types_to_declare = target_param_types if target_param_types else set()
    types_to_declare = types_to_declare | set(factories.keys()) | set(initializers.keys())

    # ========== FACTORY PATTERN (allocate + return) ==========
    if relevant_factories:
        lines.append("### Object Creation API (Factory Pattern)")
        lines.append("")
        lines.append("**CRITICAL: Use these constructor functions to create objects.**")
        lines.append("**DO NOT use `tis_alloc()`, `malloc()`, or manual struct allocation for these types.**")
        lines.append("")

        for type_name, funcs in relevant_factories.items():
            top_funcs = funcs[:10]

            lines.append(f"#### Constructors for `{type_name}` (struct {type_name} *)")
            lines.append("")
            lines.append("Use one of these functions to create instances:")
            lines.append("")
            lines.append("```c")

            for func in top_funcs:
                if func.doc_comment:
                    doc_lines = func.doc_comment.strip().split('\n')
                    if len(doc_lines) > 5:
                        doc_lines = doc_lines[:5] + ['...']
                    lines.append('\n'.join(doc_lines))

                basename = os.path.basename(func.file_path)
                lines.append(f"// From {basename}:{func.line_number}")

                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if not sig.endswith(';'):
                    sig += ';'
                lines.append(sig)
                lines.append("")

            lines.append("```")

            if len(funcs) > 10:
                lines.append(f"*({len(funcs) - 10} more constructors available)*")
            lines.append("")

    # ========== INITIALIZER PATTERN (caller allocates, function initializes) ==========
    if relevant_initializers:
        lines.append("### Object Initialization API (Initializer Pattern)")
        lines.append("")
        lines.append("**These types use the INITIALIZER pattern:** allocate the struct yourself, then call an initializer.")
        lines.append("")

        for type_name, funcs in relevant_initializers.items():
            top_funcs = funcs[:10]

            # Get type info to check if it's a pointer typedef
            type_info = type_defs.get(type_name)
            underlying_struct = type_info.pointer_to if type_info and type_info.pointer_to else type_name

            lines.append(f"#### Initializers for `{type_name}`")
            lines.append("")

            # Show usage pattern
            if type_info and type_info.pointer_to:
                lines.append(f"**Note:** `{type_name}` is a pointer typedef to `struct {underlying_struct}`.")
                lines.append("")
            lines.append("**Usage pattern:**")
            lines.append("```c")
            lines.append(f"// 1. Allocate the struct on the stack")
            lines.append(f"struct {underlying_struct} obj;")
            lines.append("")
            lines.append(f"// 2. Initialize using one of the functions below")
            if top_funcs:
                # Show first initializer as example
                first_init = top_funcs[0]
                lines.append(f"// {first_init.name}(&obj, ...);")
            lines.append("")
            lines.append(f"// 3. Pass to target function")
            lines.append(f"// {target.name}(..., &obj, ...);")
            lines.append("```")
            lines.append("")

            lines.append("**Available initializer functions:**")
            lines.append("")
            lines.append("```c")

            for func in top_funcs:
                if func.doc_comment:
                    doc_lines = func.doc_comment.strip().split('\n')
                    if len(doc_lines) > 5:
                        doc_lines = doc_lines[:5] + ['...']
                    lines.append('\n'.join(doc_lines))

                basename = os.path.basename(func.file_path)
                lines.append(f"// From {basename}:{func.line_number}")

                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if not sig.endswith(';'):
                    sig += ';'
                lines.append(sig)
                lines.append("")

            lines.append("```")

            if len(funcs) > 10:
                lines.append(f"*({len(funcs) - 10} more initializers available)*")
            lines.append("")

    # ========== EXTERN DECLARATIONS ==========
    if relevant_factories or relevant_initializers:
        lines.append("### Required Extern Declarations")
        lines.append("")
        lines.append("**Copy these declarations into your driver:**")
        lines.append("")
        lines.append("```c")

        # Forward declare struct types
        # For pointer typedefs, declare the underlying struct
        declared_structs = set()
        for type_name in types_to_declare:
            type_info = type_defs.get(type_name)
            if type_info and type_info.pointer_to:
                struct_name = type_info.pointer_to
            else:
                struct_name = type_name
            if struct_name not in declared_structs:
                lines.append(f"struct {struct_name};")
                declared_structs.add(struct_name)
        lines.append("")

        # Include required type definitions (typedefs, enums used in signatures)
        if required_type_defs:
            lines.append("// Required type definitions")
            for type_name, type_source in required_type_defs.items():
                source = type_source.strip()
                if not source.endswith(';'):
                    source += ';'
                lines.append(source)
            lines.append("")

        # Collect all function signatures
        signatures = []

        # Factory signatures
        for type_name, funcs in relevant_factories.items():
            for func in funcs[:5]:
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if not sig.endswith(';'):
                    sig += ';'
                if 'static ' in sig:
                    continue
                sig = add_struct_keyword_to_signature(sig, declared_structs)
                if not sig.startswith('extern'):
                    sig = 'extern ' + sig
                if sig not in signatures:
                    signatures.append(sig)

        # Initializer signatures
        for type_name, funcs in relevant_initializers.items():
            for func in funcs[:5]:
                sig = func.source.split('{')[0].strip() if '{' in func.source else func.source.strip()
                if not sig.endswith(';'):
                    sig += ';'
                if 'static ' in sig:
                    continue
                sig = add_struct_keyword_to_signature(sig, declared_structs)
                if not sig.startswith('extern'):
                    sig = 'extern ' + sig
                if sig not in signatures:
                    signatures.append(sig)

        if signatures:
            lines.append("// Function declarations")
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
                category_str = type_info.category
                if type_info.pointer_to:
                    category_str += f" (pointer to struct {type_info.pointer_to})"
                lines.append(f"// {category_str}: {type_name}")
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
            elif category == 'struct_ptr' and normalized in initializers:
                init_names = [f.name for f in initializers[normalized][:3]]
                type_info = type_defs.get(normalized)
                underlying = type_info.pointer_to if type_info and type_info.pointer_to else normalized
                approach = f"Stack-allocate `struct {underlying}`, then `{init_names[0]}()`"
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

        # Collect initializers
        initializers: Dict[str, List[FunctionInfo]] = {}
        for param in target.params:
            if categorize_type(param.type) == 'struct_ptr':
                normalized = normalize_type(param.type)
                type_initializers = find_initializers(conn, param.type, function_name)
                if type_initializers:
                    initializers[normalized] = type_initializers

        return {
            "function": target.name,
            "params": [(p.type, p.name) for p in target.params],
            "factories": {
                type_name: [f.name for f in funcs]
                for type_name, funcs in factories.items()
            },
            "initializers": {
                type_name: [f.name for f in funcs]
                for type_name, funcs in initializers.items()
            },
        }

    finally:
        conn.close()
