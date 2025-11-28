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
    """Get a function by name."""
    row = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE name = ?
        LIMIT 1
    """, (name,)).fetchone()

    return FunctionInfo.from_row(row) if row else None


def find_factories(conn: sqlite3.Connection, type_name: str) -> List[FunctionInfo]:
    """
    Find functions that can create instances of the given type.

    Searches by:
    1. Return type match (normalized)
    2. Naming conventions: *_new*, *_create*, *_from_*, *_parse*
    """
    normalized = normalize_type(type_name)

    # Direct return type match
    rows = conn.execute("""
        SELECT name, return_type, params_json, file_path, line_number, source, doc_comment
        FROM functions
        WHERE return_type_normalized = ?
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
    """, (normalized, normalized, normalized, normalized, normalized, normalized, normalized)).fetchall()

    # Deduplicate by name
    seen = set()
    results = []
    for row in rows + pattern_rows:
        func = FunctionInfo.from_row(row)
        if func.name not in seen:
            seen.add(func.name)
            results.append(func)

    return results


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
