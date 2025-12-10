"""Tree-sitter based C code parsing."""

from typing import List, Optional
import re

try:
    import tree_sitter_c as tsc
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from .models import FunctionInfo, TypeInfo, Param


def get_parser() -> Optional["Parser"]:
    """Get tree-sitter parser for C."""
    if not TREE_SITTER_AVAILABLE:
        return None
    language = Language(tsc.language())
    parser = Parser(language)
    return parser


def extract_leading_comment(node, source_bytes: bytes) -> str:
    """
    Extract doc comment immediately preceding a node.

    Handles // and /* */ style comments.
    Stops if there's a gap of >2 newlines.
    Skips macro-like declarations (e.g., JSON_EXPORT, EXTERN_C).
    """
    comments = []
    current = node
    prev = node.prev_named_sibling

    while prev is not None:
        if prev.type == 'comment':
            comment_text = source_bytes[prev.start_byte:prev.end_byte].decode('utf-8', errors='replace')

            # Check for gap between comment and target
            gap_text = source_bytes[prev.end_byte:current.start_byte].decode('utf-8', errors='replace')
            if gap_text.count('\n') > 2:
                break

            comments.insert(0, comment_text)
            current = prev
            prev = prev.prev_named_sibling
        elif prev.type == 'declaration':
            # Skip macro-like declarations (e.g., JSON_EXPORT, __attribute__)
            # These are typically short declarations with just identifiers
            decl_text = source_bytes[prev.start_byte:prev.end_byte].decode('utf-8', errors='replace').strip()
            # If it looks like a macro (short, no parens with args)
            if len(decl_text) < 50 and '(' not in decl_text:
                current = prev
                prev = prev.prev_named_sibling
                continue
            break
        elif prev.type == 'expression_statement':
            # Also skip expression statements that might be macros
            expr_text = source_bytes[prev.start_byte:prev.end_byte].decode('utf-8', errors='replace').strip()
            if len(expr_text) < 50:
                current = prev
                prev = prev.prev_named_sibling
                continue
            break
        else:
            break

    return '\n'.join(comments) if comments else ''


def _get_node_text(node, source_bytes: bytes) -> str:
    """Get text content of a tree-sitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')


def _find_child_by_type(node, type_name: str):
    """Find first child of a specific type."""
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def _find_children_by_type(node, type_name: str) -> List:
    """Find all children of a specific type."""
    return [child for child in node.children if child.type == type_name]


def _find_descendant_by_type(node, type_name: str):
    """Find first descendant of a specific type (recursive)."""
    for child in node.children:
        if child.type == type_name:
            return child
        result = _find_descendant_by_type(child, type_name)
        if result:
            return result
    return None


def _parse_params(params_node, source_bytes: bytes) -> List[Param]:
    """Parse parameter list into Param objects."""
    params = []

    for child in params_node.children:
        if child.type == 'parameter_declaration':
            # Get the full parameter text
            param_text = _get_node_text(child, source_bytes).strip()

            # Skip void parameters
            if param_text == 'void':
                continue

            # Find the declarator (name)
            name = ""
            type_parts = []

            for part in child.children:
                if part.type == 'identifier':
                    name = _get_node_text(part, source_bytes)
                elif part.type == 'pointer_declarator':
                    # Handle pointer declarators - find the identifier inside
                    ident = _find_descendant_by_type(part, 'identifier')
                    if ident:
                        name = _get_node_text(ident, source_bytes)
                elif part.type == 'array_declarator':
                    # Handle array declarators
                    ident = _find_descendant_by_type(part, 'identifier')
                    if ident:
                        name = _get_node_text(ident, source_bytes)
                else:
                    type_parts.append(_get_node_text(part, source_bytes))

            param_type = ' '.join(type_parts).strip()
            if not param_type:
                # Fallback: extract type by removing name from full text
                if name:
                    param_type = param_text.rsplit(name, 1)[0].strip()
                else:
                    param_type = param_text

            if param_type and param_type != 'void':
                params.append(Param(type=param_type, name=name or f"arg{len(params)}"))

    return params


def _extract_function_info(node, file_path: str, source_bytes: bytes) -> Optional[FunctionInfo]:
    """Extract function info from a function_definition or declaration node."""
    # Find the function declarator and collect type specifiers
    declarator = None
    type_specifiers = []
    pointer_count = 0

    for child in node.children:
        if child.type == 'function_declarator':
            declarator = child
        elif child.type in ('primitive_type', 'type_identifier', 'sized_type_specifier',
                           'struct_specifier', 'enum_specifier'):
            type_specifiers.append(_get_node_text(child, source_bytes))
        elif child.type == 'pointer_declarator':
            # Return type is a pointer - find the function_declarator inside
            inner_declarator = _find_descendant_by_type(child, 'function_declarator')
            if inner_declarator:
                declarator = inner_declarator
                # Count asterisks in the pointer_declarator (excluding nested ones)
                ptr_text = _get_node_text(child, source_bytes)
                # Count only the leading asterisks before the function name
                for c in ptr_text:
                    if c == '*':
                        pointer_count += 1
                    elif c.isalnum() or c == '_':
                        break

    if not declarator:
        return None

    # Get function name
    name_node = _find_child_by_type(declarator, 'identifier')
    if not name_node:
        return None
    name = _get_node_text(name_node, source_bytes)

    # Build return type from type specifiers + pointers
    return_type = ' '.join(type_specifiers)
    if pointer_count > 0:
        return_type += ' ' + '*' * pointer_count

    # Get parameters
    params_node = _find_child_by_type(declarator, 'parameter_list')
    params = _parse_params(params_node, source_bytes) if params_node else []

    # Get full source
    source = _get_node_text(node, source_bytes)

    # Get doc comment
    doc_comment = extract_leading_comment(node, source_bytes)

    return FunctionInfo(
        name=name,
        return_type=return_type.strip(),
        params=params,
        file_path=file_path,
        line_number=node.start_point[0] + 1,
        source=source,
        doc_comment=doc_comment,
    )


def extract_functions(tree, file_path: str, source_bytes: bytes) -> List[FunctionInfo]:
    """Extract all function definitions and declarations from AST."""
    if not TREE_SITTER_AVAILABLE:
        return []

    functions = []
    processed = set()

    def walk_tree(node):
        # Check for function definitions
        if node.type == 'function_definition':
            func_info = _extract_function_info(node, file_path, source_bytes)
            if func_info:
                key = (func_info.name, file_path)
                if key not in processed:
                    processed.add(key)
                    functions.append(func_info)

        # Check for function declarations (prototypes)
        elif node.type == 'declaration':
            # Check if this declaration contains a function_declarator
            func_decl = _find_descendant_by_type(node, 'function_declarator')
            if func_decl:
                func_info = _extract_function_info(node, file_path, source_bytes)
                if func_info:
                    key = (func_info.name, file_path)
                    if key not in processed:
                        processed.add(key)
                        functions.append(func_info)

        # Recurse into children
        for child in node.children:
            walk_tree(child)

    walk_tree(tree.root_node)
    return functions


def _extract_type_info(node, file_path: str, source_bytes: bytes) -> Optional[TypeInfo]:
    """Extract type info from a struct/enum/typedef node."""
    if node.type == 'struct_specifier':
        # Find the name
        name_node = _find_child_by_type(node, 'type_identifier')
        if not name_node:
            return None
        name = _get_node_text(name_node, source_bytes)

        # Check if it has a body (definition vs just declaration)
        body = _find_child_by_type(node, 'field_declaration_list')
        if not body:
            return None  # Just a declaration, not a definition

        return TypeInfo(
            name=name,
            category='struct_ptr',
            file_path=file_path,
            source=_get_node_text(node, source_bytes),
        )

    elif node.type == 'enum_specifier':
        # Find the name
        name_node = _find_child_by_type(node, 'type_identifier')
        if not name_node:
            return None
        name = _get_node_text(name_node, source_bytes)

        # Extract enum values
        enum_values = []
        body = _find_child_by_type(node, 'enumerator_list')
        if body:
            for enumerator in body.children:
                if enumerator.type == 'enumerator':
                    ident = _find_child_by_type(enumerator, 'identifier')
                    if ident:
                        enum_values.append(_get_node_text(ident, source_bytes))

        return TypeInfo(
            name=name,
            category='enum',
            enum_values=enum_values,
            file_path=file_path,
            source=_get_node_text(node, source_bytes),
        )

    elif node.type == 'type_definition':
        # Check for pointer typedef pattern: typedef struct X {} *TypeName;
        # In this case, we have a pointer_declarator containing the typedef name
        pointer_declarator = _find_child_by_type(node, 'pointer_declarator')
        struct_specifier = _find_child_by_type(node, 'struct_specifier')

        if pointer_declarator and struct_specifier:
            # This is a pointer typedef: typedef struct X {} *TypeName;
            typedef_name_node = _find_descendant_by_type(pointer_declarator, 'type_identifier')
            if typedef_name_node:
                typedef_name = _get_node_text(typedef_name_node, source_bytes)

                # Get the underlying struct name
                struct_name_node = _find_child_by_type(struct_specifier, 'type_identifier')
                struct_name = _get_node_text(struct_name_node, source_bytes) if struct_name_node else None

                return TypeInfo(
                    name=typedef_name,
                    category='pointer_typedef',
                    file_path=file_path,
                    source=_get_node_text(node, source_bytes),
                    pointer_to=struct_name,
                )

        # Regular typedef: find the typedef name
        name_node = _find_child_by_type(node, 'type_identifier')
        if not name_node:
            return None
        name = _get_node_text(name_node, source_bytes)

        # Try to find the underlying type
        underlying = ""
        pointer_to = None
        for child in node.children:
            if child.type in ('primitive_type', 'type_identifier', 'sized_type_specifier',
                             'struct_specifier', 'enum_specifier'):
                underlying = _get_node_text(child, source_bytes)
                # If underlying is a struct specifier, extract struct name for pointer_to
                if child.type == 'struct_specifier':
                    struct_name_node = _find_child_by_type(child, 'type_identifier')
                    if struct_name_node:
                        pointer_to = _get_node_text(struct_name_node, source_bytes)
                break

        category = categorize_type(underlying) if underlying else 'primitive'

        return TypeInfo(
            name=name,
            category=category,
            file_path=file_path,
            source=_get_node_text(node, source_bytes),
            pointer_to=pointer_to,
        )

    return None


def extract_types(tree, file_path: str, source_bytes: bytes) -> List[TypeInfo]:
    """Extract struct, enum, and typedef definitions from AST."""
    if not TREE_SITTER_AVAILABLE:
        return []

    types = []
    processed = set()

    def walk_tree(node):
        # Check for type definitions
        if node.type in ('struct_specifier', 'enum_specifier', 'type_definition'):
            type_info = _extract_type_info(node, file_path, source_bytes)
            if type_info and type_info.name not in processed:
                processed.add(type_info.name)
                types.append(type_info)

        # Recurse into children
        for child in node.children:
            walk_tree(child)

    walk_tree(tree.root_node)
    return types


def categorize_type(type_str: str) -> str:
    """Categorize a type string."""
    t = type_str.strip()

    # Check for explicit primitives first
    if re.match(r'^(const\s+)?(unsigned\s+)?(int|long|short|char|float|double|void)\s*$', t):
        return 'primitive'
    # Standard fixed-width integer types
    if re.match(r'^(const\s+)?(u?int\d+_t|size_t|ssize_t|ptrdiff_t|bool|_Bool)\s*$', t):
        return 'primitive'
    if re.match(r'(const\s+)?char\s*\*', t):
        return 'string'
    if re.search(r'\(\s*\*\s*\)', t):
        return 'func_ptr'
    if 'enum' in t:
        return 'enum'
    if '*' in t or 'struct' in t:
        return 'struct_ptr'
    # Types ending with _t that aren't standard primitives are likely typedef'd pointers
    # Examples: TCAesKeySched_t, json_object_t, etc.
    # Remove const qualifier for matching
    bare_type = re.sub(r'\bconst\b', '', t).strip()
    if re.match(r'^[A-Z].*_t$', bare_type):
        # Capitalized type ending in _t - likely a typedef'd pointer (common C convention)
        return 'struct_ptr'
    if re.match(r'^[a-z_]+_t$', bare_type) and bare_type not in ('size_t', 'ssize_t', 'ptrdiff_t'):
        # Lowercase type ending in _t that's not a standard type - might be a typedef'd pointer
        return 'struct_ptr'
    return 'primitive'


def normalize_type(type_str: str) -> str:
    """
    Normalize type for database lookup.

    'struct json_object *' -> 'json_object'
    'const char *'         -> 'char'
    'enum json_type'       -> 'json_type'
    """
    t = type_str.strip()
    t = re.sub(r'\bconst\b', '', t)
    t = re.sub(r'\bstruct\b', '', t)
    t = re.sub(r'\benum\b', '', t)
    t = re.sub(r'\*+$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t
