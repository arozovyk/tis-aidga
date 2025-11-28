"""SQLite index for AST metadata."""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from .models import FunctionInfo, TypeInfo, Param
from .parser import (
    get_parser,
    extract_functions,
    extract_types,
    normalize_type,
    TREE_SITTER_AVAILABLE,
)


SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS functions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    return_type TEXT NOT NULL,
    return_type_normalized TEXT NOT NULL,
    params_json TEXT,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    source TEXT,
    doc_comment TEXT,
    UNIQUE(name, file_path)
);

CREATE INDEX IF NOT EXISTS idx_return_type ON functions(return_type_normalized);
CREATE INDEX IF NOT EXISTS idx_name ON functions(name);

CREATE TABLE IF NOT EXISTS types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    enum_values_json TEXT,
    file_path TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_type_name ON types(name);
CREATE INDEX IF NOT EXISTS idx_type_category ON types(category);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema."""
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),)
    )
    conn.commit()


def build_index(
    files: List[Any],  # List of FileInfo from compilation_db
    db_path: str,
    tis_runner=None,
    progress_callback=None,
) -> Dict[str, int]:
    """
    Build AST index from source files.

    Args:
        files: List of FileInfo objects with .path attribute
        db_path: Path to SQLite database
        tis_runner: Optional TIS runner for remote file access
        progress_callback: Optional callback(current, total, file_path)

    Returns:
        Dict with stats: {"functions": N, "types": N, "files": N}
    """
    if not TREE_SITTER_AVAILABLE:
        raise ImportError(
            "tree-sitter and tree-sitter-c are required. "
            "Install with: pip install tree-sitter tree-sitter-c"
        )

    parser = get_parser()
    if not parser:
        raise RuntimeError("Failed to create tree-sitter parser")

    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    _create_schema(conn)

    stats = {"functions": 0, "types": 0, "files": 0}
    total_files = len(files)

    for i, file_info in enumerate(files):
        file_path = file_info.path if hasattr(file_info, 'path') else str(file_info)

        if progress_callback:
            progress_callback(i + 1, total_files, file_path)

        # Read file content
        try:
            if tis_runner and hasattr(tis_runner, 'read_remote_file'):
                content = tis_runner.read_remote_file(file_path)
                if isinstance(content, str):
                    content = content.encode('utf-8')
            else:
                with open(file_path, 'rb') as f:
                    content = f.read()
        except Exception as e:
            # Skip files we can't read
            continue

        if not content:
            continue

        # Parse with tree-sitter
        tree = parser.parse(content)

        # Extract and store functions
        for func in extract_functions(tree, file_path, content):
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO functions
                    (name, return_type, return_type_normalized, params_json,
                     file_path, line_number, source, doc_comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    func.name,
                    func.return_type,
                    normalize_type(func.return_type),
                    json.dumps([asdict(p) for p in func.params]),
                    func.file_path,
                    func.line_number,
                    func.source,
                    func.doc_comment,
                ))
                stats["functions"] += 1
            except sqlite3.IntegrityError:
                pass  # Duplicate, skip

        # Extract and store types
        for type_info in extract_types(tree, file_path, content):
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO types
                    (name, category, enum_values_json, file_path, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    type_info.name,
                    type_info.category,
                    json.dumps(type_info.enum_values),
                    type_info.file_path,
                    type_info.source,
                ))
                stats["types"] += 1
            except sqlite3.IntegrityError:
                pass

        stats["files"] += 1

    # Store metadata
    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('last_indexed', ?)",
        (datetime.now().isoformat(),)
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('file_count', ?)",
        (str(stats["files"]),)
    )

    conn.commit()
    conn.close()

    return stats


def get_index_stats(db_path: str) -> Optional[Dict[str, Any]]:
    """Get statistics about an existing index."""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)

    try:
        func_count = conn.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        type_count = conn.execute("SELECT COUNT(*) FROM types").fetchone()[0]

        meta = {}
        for row in conn.execute("SELECT key, value FROM meta"):
            meta[row[0]] = row[1]

        return {
            "functions": func_count,
            "types": type_count,
            "last_indexed": meta.get("last_indexed"),
            "file_count": int(meta.get("file_count", 0)),
            "schema_version": int(meta.get("schema_version", 0)),
        }
    finally:
        conn.close()
