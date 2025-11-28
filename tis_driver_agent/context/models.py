"""Data models for AST context retrieval."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json


@dataclass
class Param:
    """Function parameter."""
    type: str
    name: str


@dataclass
class FunctionInfo:
    """Extracted function information."""
    name: str
    return_type: str
    params: List[Param]
    file_path: str
    line_number: int
    source: str
    doc_comment: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "return_type": self.return_type,
            "params": [asdict(p) for p in self.params],
            "file_path": self.file_path,
            "line_number": self.line_number,
            "source": self.source,
            "doc_comment": self.doc_comment,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "FunctionInfo":
        """Create from SQLite row."""
        name, return_type, params_json, file_path, line_number, source, doc_comment = row
        params = [Param(**p) for p in json.loads(params_json)] if params_json else []
        return cls(
            name=name,
            return_type=return_type,
            params=params,
            file_path=file_path,
            line_number=line_number,
            source=source or "",
            doc_comment=doc_comment or "",
        )


@dataclass
class TypeInfo:
    """Extracted type information."""
    name: str
    category: str  # "struct_ptr" | "primitive" | "string" | "func_ptr" | "enum"
    enum_values: List[str] = field(default_factory=list)
    file_path: str = ""
    source: str = ""

    @classmethod
    def from_row(cls, row: tuple) -> "TypeInfo":
        """Create from SQLite row."""
        name, category, enum_values_json, file_path, source = row
        enum_values = json.loads(enum_values_json) if enum_values_json else []
        return cls(
            name=name,
            category=category,
            enum_values=enum_values,
            file_path=file_path or "",
            source=source or "",
        )
