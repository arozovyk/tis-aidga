"""Context command - show context that would be retrieved for a function."""

import os

from ...utils.project_manager import ProjectManager


def cmd_context(args):
    """Show context that would be retrieved for a function."""
    pm = ProjectManager()

    if not pm.project_exists(args.project):
        print(f"Error: Project '{args.project}' not found")
        return 1

    index_path = pm.get_index_path(args.project)

    if not os.path.exists(index_path):
        print(f"Error: No AST index found for '{args.project}'")
        print("Run 'tischiron reindex <project>' to build the index")
        return 1

    try:
        from ...context.assembler import assemble_context, get_context_summary

        # Show summary
        summary = get_context_summary(index_path, args.function)
        if not summary:
            print(f"Error: Function '{args.function}' not found in index")
            return 1

        print(f"Function: {summary['function']}")
        print("Parameters:")
        for ptype, pname in summary['params']:
            print(f"  - {pname}: {ptype}")

        print("\nFactories found:")
        if summary['factories']:
            for type_name, factory_names in summary['factories'].items():
                print(f"  {type_name}:")
                for fname in factory_names[:5]:
                    print(f"    - {fname}()")
                if len(factory_names) > 5:
                    print(f"    ... and {len(factory_names) - 5} more")
        else:
            print("  (none)")

        print("\nInitializers found:")
        if summary.get('initializers'):
            for type_name, init_names in summary['initializers'].items():
                print(f"  {type_name}:")
                for fname in init_names[:5]:
                    print(f"    - {fname}()")
                if len(init_names) > 5:
                    print(f"    ... and {len(init_names) - 5} more")
        else:
            print("  (none)")

        # Show full context if verbose
        if args.verbose:
            print("\n" + "=" * 60)
            print("Full context that would be injected:")
            print("=" * 60 + "\n")

            context = assemble_context(index_path, args.function)
            print(context)

    except ImportError as e:
        print(f"Error: Context module not available ({e})")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0
