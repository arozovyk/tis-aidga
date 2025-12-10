"""Database lookup functions for factory discovery."""

import sqlite3
from typing import List, Optional, Set
import os

from .models import FunctionInfo, TypeInfo
from .parser import normalize_type, categorize_type


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Index not found: {db_path}")
    return sqlite3.connect(db_path)


def get_function(conn: sqlite3.Connection, name: str) -> Optional[FunctionInfo]:
    """
    Get a function by name.

    Returns the version with body (from .c file), enriched with doc comment
    from header if available.
    """
    # Get all versions
    rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE name = ?
    """, (name,)).fetchall()

    if not rows:
        return None

    # Find version with body and version with doc comment
    with_body = None
    with_doc = None

    for row in rows:
        func = FunctionInfo.from_row(row)
        if '{' in func.source and with_body is None:
            with_body = func
        if func.doc_comment and with_doc is None:
            with_doc = func

    # Prefer version with body, enriched with doc comment
    if with_body:
        if with_doc and not with_body.doc_comment:
            # Merge doc comment from header into the .c version
            with_body = FunctionInfo(
                name=with_body.name,
                return_type=with_body.return_type,
                params=with_body.params,
                file_path=with_body.file_path,
                line_number=with_body.line_number,
                source=with_body.source,
                doc_comment=with_doc.doc_comment,
            )
        return with_body

    # Fall back to version with doc comment
    if with_doc:
        return with_doc

    # Fall back to first version
    return FunctionInfo.from_row(rows[0])


def _is_initializer_pattern(func_name: str) -> bool:
    """
    Check if a function name suggests it's an initializer.

    Initializers are functions that populate/configure pre-allocated memory.
    They take T* as parameter and return int (error code) or void.
    """
    name_lower = func_name.lower()

    # Initializer naming patterns
    initializer_patterns = (
        '_init',      # tc_sha256_init, json_object_init
        '_set_',      # tc_aes128_set_encrypt_key, tc_hmac_set_key
        '_setup',     # ssl_setup
        '_configure', # ctx_configure
        '_begin',     # hash_begin
        '_start',     # session_start
        '_reset',     # state_reset
        '_clear',     # buffer_clear (when used to initialize)
    )

    return any(pat in name_lower for pat in initializer_patterns)


def _is_getter_or_ref_counter(func: FunctionInfo, target_type_normalized: str) -> bool:
    """
    Check if a function is likely a getter/ref-counter rather than a constructor/initializer.

    Signs of a getter/ref-counter:
    - Takes the type as a parameter AND returns the same type
    - Name contains 'get', 'iter', 'peek', 'ref', 'unref'

    Exception: Initializer functions that take the type are NOT getters.
    """
    name_lower = func.name.lower()

    # EXCEPTION: Initializers that take the type are NOT getters
    # They're functions that populate pre-allocated memory
    if _is_initializer_pattern(func.name):
        return False

    # Check if name suggests getter/ref behavior
    getter_patterns = ('_get', '_peek', '_iter', '_ref', '_unref', '_put')
    if any(pat in name_lower for pat in getter_patterns):
        return True

    # Check if it takes the target type as input AND returns it (signature of getter)
    # Note: initializers take the type but return int/void, so they pass through
    if func.params:
        return_normalized = normalize_type(func.return_type)
        for param in func.params:
            param_normalized = normalize_type(param.type)
            if param_normalized == target_type_normalized:
                # Only mark as getter if it ALSO returns the same type
                # Initializers return int/void, so they won't match here
                if return_normalized == target_type_normalized:
                    return True

    return False


def _score_factory(func: FunctionInfo) -> int:
    """
    Score a factory function by how likely it is to be a true constructor.

    Higher score = more likely to be a constructor.
    """
    name = func.name.lower()
    score = 0

    # Naming patterns (higher = better constructor)
    if '_new_' in name or name.endswith('_new'):
        score += 100  # Best: foo_new, foo_new_bar
    elif '_new' in name:
        score += 90
    elif '_create' in name:
        score += 80
    elif '_alloc' in name:
        score += 70
    elif '_parse' in name or '_from_' in name:
        score += 60  # Parsers/converters
    elif '_init' in name:
        score += 50

    # Penalize functions with many required params (harder to use)
    if len(func.params) == 0:
        score += 20  # No params = easy to call
    elif len(func.params) <= 2:
        score += 10

    # Bonus for documented functions
    if func.doc_comment:
        score += 5

    return score


def _is_semantically_opposite(factory_name: str, target_name: str) -> bool:
    """
    Check if a factory function is semantically opposite to the target function.

    For example:
    - Target is *_to_string* (serialization) → exclude *_parse* (deserialization)
    - Target is *_get_* (getter) → exclude *_set_* (setter)
    - Target is *_read* → exclude *_write*
    - Target is *_encode* → exclude *_decode*
    """
    if not target_name:
        return False

    factory_lower = factory_name.lower()
    target_lower = target_name.lower()

    # Define opposite pairs: (target_pattern, factory_pattern_to_exclude)
    opposite_pairs = [
        # Serialization vs deserialization
        ('_to_string', '_parse'),
        ('_to_json', '_parse'),
        ('_serialize', '_parse'),
        ('_serialize', '_deserialize'),
        ('_encode', '_decode'),
        ('_stringify', '_parse'),
        # Getters vs setters (for factories, we usually want constructors not setters)
        ('_get_', '_set_'),
        # Read vs write
        ('_read', '_write'),
        ('_load', '_save'),
        # Pack vs unpack
        ('_pack', '_unpack'),
    ]

    for target_pattern, factory_pattern in opposite_pairs:
        if target_pattern in target_lower and factory_pattern in factory_lower:
            return True

    return False


def find_factories(
    conn: sqlite3.Connection,
    type_name: str,
    target_function_name: str = None,
) -> List[FunctionInfo]:
    """
    Find functions that can create instances of the given type.

    Args:
        conn: Database connection
        type_name: Type to find factories for
        target_function_name: Optional name of target function for semantic filtering

    Searches by:
    1. Return type match (normalized)
    2. Naming conventions: *_new*, *_create*, *_from_*, *_parse*
    3. Output parameter pattern: functions with T** param (error-code + output)

    Filters out:
    - Getter/ref-counter functions (take and return same type)
    - Semantically opposite factories (e.g., *_parse* when target is *_to_string*)

    When the same function exists in both header and source,
    prefers the one with documentation.
    """
    normalized = normalize_type(type_name)

    # Direct return type match - order by doc_comment DESC to get documented version first
    rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE return_type_normalized = ?
        ORDER BY (doc_comment IS NOT NULL AND doc_comment != '') DESC
    """, (normalized,)).fetchall()

    # Also match naming patterns
    pattern_rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE (name LIKE ? || '_new%'
           OR name LIKE ? || '_create%'
           OR name LIKE ? || '_from_%'
           OR name LIKE ? || '_parse%'
           OR name LIKE ? || '_alloc%'
           OR name LIKE ? || '_init%')
          AND name NOT IN (SELECT name FROM functions WHERE return_type_normalized = ?)
        ORDER BY (doc_comment IS NOT NULL AND doc_comment != '') DESC
    """, (normalized, normalized, normalized, normalized, normalized, normalized, normalized)).fetchall()

    # Find functions with T** output parameter (error-code pattern)
    # e.g., int foo_create(foo_t **out) returns error code, writes to output param
    double_ptr_pattern = f'%{normalized}%**%'
    output_param_rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE params_json LIKE ?
          AND (return_type IN ('int', 'void') OR return_type LIKE '%error%' OR return_type LIKE '%status%')
          AND (name LIKE '%_create%' OR name LIKE '%_new%' OR name LIKE '%_init%' OR name LIKE '%_alloc%' OR name LIKE '%_open%')
        ORDER BY (doc_comment IS NOT NULL AND doc_comment != '') DESC
    """, (double_ptr_pattern,)).fetchall()

    # Deduplicate by name - keep first occurrence (which has doc_comment if available)
    seen = set()
    candidates = []
    for row in rows + pattern_rows + output_param_rows:
        func = FunctionInfo.from_row(row)
        if func.name not in seen:
            seen.add(func.name)
            candidates.append(func)

    # Filter out getters/ref-counters, semantically opposite, and score remaining
    results = []
    for func in candidates:
        if _is_getter_or_ref_counter(func, normalized):
            continue
        if _is_semantically_opposite(func.name, target_function_name):
            continue
        results.append((func, _score_factory(func)))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)

    return [func for func, _ in results]


def find_type(conn: sqlite3.Connection, type_name: str) -> Optional[TypeInfo]:
    """Find a type definition by name."""
    normalized = normalize_type(type_name)

    row = conn.execute("""
        SELECT name, category, enum_values_json, file_path, source, pointer_to
        FROM types
        WHERE name = ? OR name = ?
        LIMIT 1
    """, (type_name, normalized)).fetchone()

    return TypeInfo.from_row(row) if row else None


def find_types_by_category(conn: sqlite3.Connection, category: str) -> List[TypeInfo]:
    """Find all types of a given category."""
    rows = conn.execute("""
        SELECT name, category, enum_values_json, file_path, source, pointer_to
        FROM types
        WHERE category = ?
    """, (category,)).fetchall()

    return [TypeInfo.from_row(row) for row in rows]


def _is_destructor(func_name: str) -> bool:
    """Check if a function name suggests it's a destructor/cleanup function."""
    name_lower = func_name.lower()
    destructor_patterns = (
        '_free', '_destroy', '_release', '_cleanup', '_close',
        '_finish', '_final', '_done', '_end', '_deinit',
    )
    return any(pat in name_lower for pat in destructor_patterns)


def _is_update_function(func_name: str) -> bool:
    """Check if a function name suggests it's an update/process function (needs initialized state)."""
    name_lower = func_name.lower()
    update_patterns = ('_update', '_process', '_step', '_feed', '_write', '_read')
    return any(pat in name_lower for pat in update_patterns)


def _score_initializer(func: FunctionInfo) -> int:
    """
    Score an initializer function by how likely it is to be the primary initializer.

    Higher score = more likely to be used first.
    """
    name = func.name.lower()
    score = 0

    # Naming patterns (higher = better for initialization)
    if '_init' in name and '_deinit' not in name:
        score += 100  # Best: foo_init
    elif '_set_' in name and 'key' in name:
        score += 95   # tc_aes128_set_encrypt_key
    elif '_set_' in name:
        score += 80   # General setters
    elif '_setup' in name:
        score += 75
    elif '_configure' in name:
        score += 70
    elif '_begin' in name or '_start' in name:
        score += 60
    elif '_reset' in name:
        score += 40   # Reset might be re-initialization
    elif '_clear' in name:
        score += 30

    # Prefer functions with fewer required params (easier to call)
    if len(func.params) <= 2:
        score += 20
    elif len(func.params) <= 4:
        score += 10

    # Bonus for documented functions
    if func.doc_comment:
        score += 5

    return score


def find_initializers(
    conn: sqlite3.Connection,
    type_name: str,
    target_function_name: str = None,
) -> List[FunctionInfo]:
    """
    Find functions that initialize pre-allocated instances of the given type.

    Unlike factories (which allocate and return T*), initializers:
    - Take T* as an early parameter (typically first)
    - Return int (error code) or void
    - Have names containing: _init, _set_, _setup, _configure, _begin

    Args:
        conn: Database connection
        type_name: Type to find initializers for
        target_function_name: Optional name of target function for semantic filtering

    Returns:
        List of FunctionInfo sorted by initializer score
    """
    normalized = normalize_type(type_name)

    # Strategy 1: Find functions that take this type as a parameter
    # and have initializer-like names
    # Search for the type name in params_json
    type_pattern = f'%{normalized}%'

    rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE params_json LIKE ?
          AND (return_type IN ('int', 'void') OR return_type LIKE '%error%' OR return_type LIKE '%status%')
        ORDER BY (doc_comment IS NOT NULL AND doc_comment != '') DESC
    """, (type_pattern,)).fetchall()

    # Deduplicate and filter
    seen = set()
    candidates = []

    for row in rows:
        func = FunctionInfo.from_row(row)

        if func.name in seen:
            continue
        seen.add(func.name)

        # Skip if it's a destructor
        if _is_destructor(func.name):
            continue

        # Skip update/process functions (they need initialized state, not create it)
        if _is_update_function(func.name):
            continue

        # Skip semantically opposite functions
        if _is_semantically_opposite(func.name, target_function_name):
            continue

        # Must have initializer-like name pattern
        if not _is_initializer_pattern(func.name):
            continue

        # Verify this function actually takes the type as a parameter
        has_type_param = False
        for param in func.params:
            param_normalized = normalize_type(param.type)
            if param_normalized == normalized:
                has_type_param = True
                break

        if not has_type_param:
            continue

        candidates.append((func, _score_initializer(func)))

    # Sort by score descending
    candidates.sort(key=lambda x: x[1], reverse=True)

    return [func for func, _ in candidates]


def collect_factories_recursive(
    conn: sqlite3.Connection,
    type_name: str,
    factories: dict,
    visited: Set[str],
    depth: int = 0,
    max_depth: int = 1,
    target_function_name: str = None,
) -> None:
    """
    Recursively collect factory functions for a type and its dependencies.

    Args:
        conn: Database connection
        type_name: Type to find factories for
        factories: Dict to populate {type_name: [FunctionInfo, ...]}
        visited: Set of already-visited types
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        target_function_name: Name of target function for semantic filtering
    """
    normalized = normalize_type(type_name)

    if normalized in visited or depth > max_depth:
        return

    visited.add(normalized)

    type_factories = find_factories(conn, type_name, target_function_name)
    if type_factories:
        factories[normalized] = type_factories

        # Recurse into factory parameters (for struct pointers)
        for factory in type_factories:
            for param in factory.params:
                param_category = categorize_type(param.type)
                if param_category == 'struct_ptr':
                    collect_factories_recursive(
                        conn,
                        param.type,
                        factories,
                        visited,
                        depth + 1,
                        max_depth,
                        target_function_name,
                    )


def get_all_functions(conn: sqlite3.Connection, limit: int = 1000) -> List[FunctionInfo]:
    """Get all indexed functions (for debugging)."""
    rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        ORDER BY name
        LIMIT ?
    """, (limit,)).fetchall()

    return [FunctionInfo.from_row(row) for row in rows]


def search_functions(conn: sqlite3.Connection, pattern: str) -> List[FunctionInfo]:
    """Search functions by name pattern (SQL LIKE)."""
    rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE name LIKE ?
        ORDER BY name
        LIMIT 100
    """, (f"%{pattern}%",)).fetchall()

    return [FunctionInfo.from_row(row) for row in rows]
