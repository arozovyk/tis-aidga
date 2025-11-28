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


def _is_getter_or_ref_counter(func: FunctionInfo, target_type_normalized: str) -> bool:
    """
    Check if a function is likely a getter/ref-counter rather than a true constructor.

    Signs of a getter/ref-counter:
    - Takes the type as a parameter AND returns the same type
    - Name contains 'get', 'iter', 'peek', 'ref', 'unref'
    """
    # Check if name suggests getter/ref behavior
    getter_patterns = ('_get', '_peek', '_iter', '_ref', '_unref', '_put')
    name_lower = func.name.lower()
    if any(pat in name_lower for pat in getter_patterns):
        return True

    # Check if it takes the target type as input AND returns it (signature of getter)
    if func.params:
        for param in func.params:
            param_normalized = normalize_type(param.type)
            if param_normalized == target_type_normalized:
                # This function takes the type as input - likely a getter/transformer
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


def find_factories(conn: sqlite3.Connection, type_name: str) -> List[FunctionInfo]:
    """
    Find functions that can create instances of the given type.

    Searches by:
    1. Return type match (normalized)
    2. Naming conventions: *_new*, *_create*, *_from_*, *_parse*

    Filters out:
    - Getter/ref-counter functions (take and return same type)

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

    # Deduplicate by name - keep first occurrence (which has doc_comment if available)
    seen = set()
    candidates = []
    for row in rows + pattern_rows:
        func = FunctionInfo.from_row(row)
        if func.name not in seen:
            seen.add(func.name)
            candidates.append(func)

    # Filter out getters/ref-counters and score remaining
    results = []
    for func in candidates:
        if not _is_getter_or_ref_counter(func, normalized):
            results.append((func, _score_factory(func)))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)

    return [func for func, _ in results]


def find_type(conn: sqlite3.Connection, type_name: str) -> Optional[TypeInfo]:
    """Find a type definition by name."""
    normalized = normalize_type(type_name)

    row = conn.execute("""
        SELECT name, category, enum_values_json, file_path, source
        FROM types
        WHERE name = ? OR name = ?
        LIMIT 1
    """, (type_name, normalized)).fetchone()

    return TypeInfo.from_row(row) if row else None


def find_types_by_category(conn: sqlite3.Connection, category: str) -> List[TypeInfo]:
    """Find all types of a given category."""
    rows = conn.execute("""
        SELECT name, category, enum_values_json, file_path, source
        FROM types
        WHERE category = ?
    """, (category,)).fetchall()

    return [TypeInfo.from_row(row) for row in rows]


def collect_factories_recursive(
    conn: sqlite3.Connection,
    type_name: str,
    factories: dict,
    visited: Set[str],
    depth: int = 0,
    max_depth: int = 2,
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
    """
    normalized = normalize_type(type_name)

    if normalized in visited or depth > max_depth:
        return

    visited.add(normalized)

    type_factories = find_factories(conn, type_name)
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
