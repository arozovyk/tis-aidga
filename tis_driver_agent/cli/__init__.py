"""CLI entry point for TIS Driver Agent."""
# PYTHON_ARGCOMPLETE_OK

import argparse
import sys

import argcomplete

from .helpers import load_env_files
from .completers import ProjectCompleter, FileCompleter, ModelCompleter
from .commands import cmd_init, cmd_list, cmd_gen, cmd_context, cmd_reindex, cmd_models

# Load environment variables from .env file(s)
load_env_files()


def main():
    parser = argparse.ArgumentParser(
        prog="tischiron",
        description="AI-powered TIS driver generation",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize project from compilation database"
    )
    init_parser.add_argument(
        "compilation_db", help="Path to compile_commands.json"
    )
    init_parser.add_argument(
        "--name", "-n", help="Project name (default: derived from directory)"
    )
    init_parser.add_argument(
        "--ssh-host", help="SSH host for remote TIS"
    )
    init_parser.add_argument(
        "--ssh-user", help="SSH username"
    )
    init_parser.add_argument(
        "--tis-env-script",
        help="Script to source TIS environment",
    )
    init_parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip building AST index (faster init, no context retrieval)",
    )
    init_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # list command
    list_parser = subparsers.add_parser(
        "list", help="List projects or files"
    )
    list_parser.add_argument(
        "project", nargs="?", help="Project name (omit to list all projects)"
    ).completer = ProjectCompleter()
    list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # gen command
    gen_parser = subparsers.add_parser(
        "gen", help="Generate driver for a function"
    )
    gen_parser.add_argument(
        "project", help="Project name"
    ).completer = ProjectCompleter()
    gen_parser.add_argument(
        "filename", help="Source filename"
    ).completer = FileCompleter()
    gen_parser.add_argument(
        "function", help="Function name"
    )
    gen_parser.add_argument(
        "--output", "-o", help="Output file path"
    )
    gen_parser.add_argument(
        "--model", default="gpt-4o-mini",
        help="""Model to use. Auto-detected by prefix:
  claude-*  -> Anthropic (needs ANTHROPIC_API_KEY)
  llama-*, mistral-*, etc -> Ollama (local)
  gpt-*, o1-*, etc -> OpenAI (needs OPENAI_API_KEY)
Default: gpt-4o-mini. Use 'tischiron models' for full list."""
    ).completer = ModelCompleter()
    gen_parser.add_argument(
        "--max-iterations", type=int, default=5, help="Maximum refinement iterations"
    )
    gen_parser.add_argument("--ssh-host", help=argparse.SUPPRESS)
    gen_parser.add_argument("--ssh-user", help=argparse.SUPPRESS)
    gen_parser.add_argument("--tis-env-script", help=argparse.SUPPRESS)
    gen_parser.add_argument(
        "--log", "-l", help="Path to log file for detailed workflow logging"
    )
    gen_parser.add_argument(
        "--with-logs",
        action="store_true",
        help="Create structured logs in logs/log_<timestamp>/ with separate files for C code, LLM queries, and validation results",
    )
    gen_parser.add_argument(
        "--context",
        choices=["function", "source", "matching", "full", "ast"],
        default="function",
        help="Context mode: function (extracted function only), source (full source file), matching (source + matching header), full (all headers), ast (use AST index for factory functions). Default: function",
    )
    gen_parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )
    gen_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # context command
    context_parser = subparsers.add_parser(
        "context", help="Show context for a function (debug)"
    )
    context_parser.add_argument(
        "project", help="Project name"
    ).completer = ProjectCompleter()
    context_parser.add_argument(
        "function", help="Function name"
    )
    context_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show full context"
    )

    # reindex command
    reindex_parser = subparsers.add_parser(
        "reindex", help="Rebuild AST index for a project"
    )
    reindex_parser.add_argument(
        "project", help="Project name"
    ).completer = ProjectCompleter()

    # models command
    subparsers.add_parser(
        "models", help="List available models and their requirements"
    )

    # Enable argcomplete
    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "gen":
        cmd_gen(args)
    elif args.command == "context":
        cmd_context(args)
    elif args.command == "reindex":
        cmd_reindex(args)
    elif args.command == "models":
        cmd_models(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
