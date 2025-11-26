"""Tests for utils module."""

import json
import tempfile
import os
from tis_driver_agent.utils import (
    parse_includes,
    extract_function_signature,
    detect_context_files_from_content,
    parse_includes_from_command,
    parse_defines_from_command,
    get_project_remote_dir,
    file_info_to_dict,
    dict_to_file_info,
)
from tis_driver_agent.config import FileInfo


class TestContextDetector:
    def test_parse_includes_quoted(self):
        content = '#include "myheader.h"\n#include "other.h"'
        includes = parse_includes(content)
        assert includes == ["myheader.h", "other.h"]

    def test_parse_includes_angle_brackets(self):
        content = '#include <stdio.h>\n#include <stdlib.h>'
        includes = parse_includes(content)
        assert includes == ["stdio.h", "stdlib.h"]

    def test_parse_includes_mixed(self):
        content = '#include <stdio.h>\n#include "local.h"'
        includes = parse_includes(content)
        assert includes == ["stdio.h", "local.h"]

    def test_parse_includes_empty(self):
        content = "int main() { return 0; }"
        includes = parse_includes(content)
        assert includes == []

    def test_extract_function_signature_simple(self):
        content = "int foo(int x, int y) { return x + y; }"
        sig = extract_function_signature(content, "foo")
        assert sig == "int foo(int x, int y)"

    def test_extract_function_signature_pointer_return(self):
        content = "char *get_name(void) { return NULL; }"
        sig = extract_function_signature(content, "get_name")
        assert "get_name" in sig
        assert "void" in sig

    def test_extract_function_signature_not_found(self):
        content = "int bar(void) { return 0; }"
        sig = extract_function_signature(content, "foo")
        assert sig is None

    def test_detect_context_files(self):
        content = '#include "json_object.h"\nint test() {}'
        files = detect_context_files_from_content(content, "test")
        assert "json_object.h" in files


class TestCompilationDb:
    def test_parse_includes_from_command_basic(self):
        cmd = "gcc -I/usr/include -I/home/user/proj file.c"
        includes = parse_includes_from_command(cmd)
        assert includes == ["/usr/include", "/home/user/proj"]

    def test_parse_includes_from_command_attached(self):
        cmd = "gcc -I/path1 -I/path2 file.c"
        includes = parse_includes_from_command(cmd)
        assert includes == ["/path1", "/path2"]

    def test_parse_includes_from_command_empty(self):
        cmd = "gcc file.c"
        includes = parse_includes_from_command(cmd)
        assert includes == []

    def test_parse_defines_from_command_basic(self):
        cmd = "gcc -DFOO=1 -DBAR -D DEBUG file.c"
        defines = parse_defines_from_command(cmd)
        assert "FOO=1" in defines
        assert "BAR" in defines
        assert "DEBUG" in defines

    def test_parse_defines_from_command_empty(self):
        cmd = "gcc file.c"
        defines = parse_defines_from_command(cmd)
        assert defines == []

    def test_get_project_remote_dir_common(self):
        entries = [
            {"directory": "/home/user/project/src"},
            {"directory": "/home/user/project/lib"},
            {"directory": "/home/user/project"},
        ]
        common = get_project_remote_dir(entries)
        assert common == "/home/user/project"

    def test_get_project_remote_dir_empty(self):
        result = get_project_remote_dir([])
        assert result is None

    def test_file_info_roundtrip(self):
        original = FileInfo(
            name="test.c",
            path="/home/user/test.c",
            directory="/home/user",
            includes=["/usr/include"],
            defines=["DEBUG"],
        )
        as_dict = file_info_to_dict(original)
        restored = dict_to_file_info(as_dict)

        assert restored.name == original.name
        assert restored.path == original.path
        assert restored.directory == original.directory
        assert restored.includes == original.includes
        assert restored.defines == original.defines
