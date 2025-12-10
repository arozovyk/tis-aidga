"""Context builder - assembles context files based on selected mode."""

import os
from typing import List, Dict, Optional, Callable

from .context_detector import parse_includes, extract_function


class ContextBuilder:
    """
    Builds context files based on selected mode.

    Modes:
        - function: Extract only the target function
        - source: Full source file only
        - matching: Source + matching header (foo.c -> foo.h)
        - full: Source + all headers from #include directives
        - ast: Use AST index for factory functions and type definitions
    """

    def __init__(
        self,
        file_reader: Callable[[str], Optional[str]],
        include_paths: List[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize context builder.

        Args:
            file_reader: Function to read file contents (handles local/remote)
            include_paths: Include paths to search for headers
            verbose: Print debug info
        """
        self.file_reader = file_reader
        self.include_paths = include_paths or []
        self.verbose = verbose

    def build(
        self,
        mode: str,
        source_content: str,
        source_filename: str,
        function_name: str,
        index_path: str = None,
    ) -> List[Dict[str, str]]:
        """
        Build context files based on mode.

        Args:
            mode: Context mode ("function", "source", "matching", "full", "ast")
            source_content: Content of the source file
            source_filename: Name of the source file
            function_name: Target function name
            index_path: Path to AST index (required for "ast" mode)

        Returns:
            List of dicts with 'name' and 'content' keys
        """
        if mode == "function":
            return self._build_function_context(source_content, source_filename, function_name)
        elif mode == "source":
            return self._build_source_context(source_content, source_filename)
        elif mode == "matching":
            return self._build_matching_context(source_content, source_filename)
        elif mode == "full":
            return self._build_full_context(source_content, source_filename)
        elif mode == "ast":
            return self._build_ast_context(source_content, source_filename, function_name, index_path)
        else:
            raise ValueError(f"Unknown context mode: {mode}")

    def _build_function_context(
        self,
        source_content: str,
        source_filename: str,
        function_name: str,
    ) -> List[Dict[str, str]]:
        """Extract only the target function."""
        func_code = extract_function(source_content, function_name)
        if func_code:
            if self.verbose:
                print(f"Context mode: function (extracted {len(func_code)} chars)")
            return [{"name": f"{function_name}()", "content": func_code}]
        else:
            # Fallback to full source if extraction fails
            if self.verbose:
                print("Context mode: function (extraction failed, using full source)")
            return [{"name": source_filename, "content": source_content}]

    def _build_source_context(
        self,
        source_content: str,
        source_filename: str,
    ) -> List[Dict[str, str]]:
        """Full source file only."""
        if self.verbose:
            print("Context mode: source (full source file)")
        return [{"name": source_filename, "content": source_content}]

    def _build_matching_context(
        self,
        source_content: str,
        source_filename: str,
    ) -> List[Dict[str, str]]:
        """Source + matching header (foo.c -> foo.h)."""
        context_files = [{"name": source_filename, "content": source_content}]

        base_name = os.path.splitext(source_filename)[0]
        matching_header = f"{base_name}.h"

        if self.verbose:
            print(f"Context mode: matching (looking for {matching_header})")

        header_content = self.file_reader(matching_header)
        if header_content:
            context_files.append({"name": matching_header, "content": header_content})
            if self.verbose:
                print(f"  Added matching header: {matching_header}")
        elif self.verbose:
            print("  No matching header found")

        return context_files

    def _build_full_context(
        self,
        source_content: str,
        source_filename: str,
    ) -> List[Dict[str, str]]:
        """Full context: source + ALL headers from includes."""
        context_files = [{"name": source_filename, "content": source_content}]
        includes = parse_includes(source_content)

        if self.verbose:
            print(f"Context mode: full ({len(includes)} includes found)")

        for inc in includes:
            header_content = self.file_reader(inc)
            if header_content:
                context_files.append({"name": inc, "content": header_content})
                if self.verbose:
                    print(f"  Added header: {inc}")

        return context_files

    def _build_ast_context(
        self,
        source_content: str,
        source_filename: str,
        function_name: str,
        index_path: str,
    ) -> List[Dict[str, str]]:
        """Use AST index to find factory functions and type definitions."""
        if not index_path or not os.path.exists(index_path):
            if self.verbose:
                print("Context mode: ast (index not found, falling back to function extraction)")
            return self._build_function_context(source_content, source_filename, function_name)

        try:
            from ..context.assembler import assemble_context, get_context_summary

            ast_context = assemble_context(index_path, function_name)
            if ast_context:
                if self.verbose:
                    summary = get_context_summary(index_path, function_name)
                    print("Context mode: ast")
                    print(f"  Target: {summary.get('function', 'N/A')}")
                    factories = summary.get('factories', {})
                    factory_count = sum(len(v) for v in factories.values())
                    print(f"  Factories: {factory_count}")
                    print(f"  Types: {len(factories)}")
                return [{"name": "AST Context", "content": ast_context}]
            else:
                # Fallback to function extraction
                if self.verbose:
                    print("Context mode: ast (no AST context found, using function extraction)")
                return self._build_function_context(source_content, source_filename, function_name)

        except ImportError:
            if self.verbose:
                print("Context mode: ast (assembler not available, using function extraction)")
            return self._build_function_context(source_content, source_filename, function_name)
