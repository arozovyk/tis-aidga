"""Tests for CC compiler module."""

import tempfile
import os
from tis_driver_agent.cc import cc_compile, parse_cc_errors, CCResult


def test_parse_cc_errors_extracts_errors():
    stderr = """
test.c:10:5: error: expected ';' before 'return'
test.c:15:1: error: unknown type name 'foo'
test.c:20:10: warning: unused variable
"""
    errors = parse_cc_errors(stderr)
    assert len(errors) == 2
    assert "expected ';'" in errors[0]
    assert "unknown type name" in errors[1]


def test_parse_cc_errors_empty():
    errors = parse_cc_errors("")
    assert errors == []


def test_cc_compile_valid_c():
    # Create a valid C file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write("int main(void) { return 0; }\n")
        temp_path = f.name

    try:
        result = cc_compile(temp_path, include_paths=[])
        assert isinstance(result, CCResult)
        assert result.success is True
        assert result.exit_code == 0
        assert result.errors == []
    finally:
        os.unlink(temp_path)


def test_cc_compile_invalid_c():
    # Create an invalid C file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write("int main(void) { return }\n")  # missing value
        temp_path = f.name

    try:
        result = cc_compile(temp_path, include_paths=[])
        assert result.success is False
        assert result.exit_code != 0
        assert len(result.errors) > 0
    finally:
        os.unlink(temp_path)


def test_cc_compile_nonexistent_file():
    result = cc_compile("/nonexistent/file.c", include_paths=[])
    assert result.success is False


def test_cc_compile_with_includes():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write("int x = 1;\n")
        temp_path = f.name

    try:
        result = cc_compile(temp_path, include_paths=["/usr/include"])
        assert "-I/usr/include" in result.command
    finally:
        os.unlink(temp_path)
