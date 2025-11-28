"""Prompt templates for driver generation."""

from typing import List, Dict

TIS_BUILTIN_HEADER = """
/**************************************************************************/
/*                                                                        */
/*  This file is part of TrustInSoft Kernel.                              */
/*                                                                        */
/*    Copyright (C) 2016-2025 TrustInSoft                                 */
/*                                                                        */
/*  TrustInSoft Kernel is released under GPLv2                            */
/*                                                                        */
/**************************************************************************/

#ifndef __TIS_DRIVERGEN_BUILTIN_H
#define __TIS_DRIVERGEN_BUILTIN_H

__BEGIN_DECLS

extern _Thread_local int tis_entropy_source __attribute__((__TIS_MODEL__));

/**
 * Construct an abstract value representing any `int` value between `__min`
 * and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `int` values
 */
int tis_interval(int __min, int __max);

/**
 * Populate an area of memory starting at address `__p` of size `__l` with
 * abstract values representing unknown contents.
 *
 * @param __p pointer to an area of memory to populate
 * @param __l size of the area of memory being populated (in bytes)
 */
void tis_make_unknown(char *__p, unsigned long __l);

/**
 * Construct an abstract value representing a nondeterministic choice between
 * two signed integer values.
 *
 * @param __a a possible value
 * @param __b a possible value
 * @returns an abstract value representing a set or interval of possible
 *         `int` values
 */
int tis_nondet(int __a, int __b);

/**
 * Construct an abstract value representing a nondeterministic choice between
 * two pointers.
 *
 * @param __a a pointer to a memory address
 * @param __b a pointer to a memory address
 * @returns an abstract value representing a set or interval of possible
 *         pointers to memory addresses
 */
void *tis_nondet_ptr(void *__a, void *__b);

/**
 * Make an area of memory starting at address `__p` of size `__l`
 * uninitialized.
 *
 * @param __p pointer to an area of memory to make uninitialized
 * @param __l size of the area of memory being uninitialized (in bytes)
 */
void tis_make_uninitialized(char *__p, unsigned long __l);

/**
 * Construct an abstract value representing any `int` value between `__min`
 * and `__max` (inclusive) and place each resulting value in a separate state.
 * Equivalent to `tis_interval` followed by `tis_variable_split`.
 *
 * @param __min lowest value in returned interval
 * @param __max highest value in returned interval
 * @return an abstract value representing an interval of possible `int` values
 */
int tis_interval_split(int __min, int __max);

/**
 * Construct an abstract value representing any `unsigned char` value between
 * `__min` and `__max` (inclusive).
 */
unsigned char tis_unsigned_char_interval(unsigned char __min, unsigned char __max);

/**
 * Construct an abstract value representing any `char` value between
 * `__min` and `__max` (inclusive).
 */
char tis_char_interval(char __min, char __max);

/**
 * Construct an abstract value representing any `unsigned short` value between
 * `__min` and `__max` (inclusive).
 */
unsigned short tis_unsigned_short_interval(unsigned short __min, unsigned short __max);

/**
 * Construct an abstract value representing any `short` value between
 * `__min` and `__max` (inclusive).
 */
short tis_short_interval(short __min, short __max);

/**
 * Construct an abstract value representing any `unsigned int` value between
 * `__min` and `__max` (inclusive).
 */
unsigned int tis_unsigned_int_interval(unsigned int __min, unsigned int __max);

/**
 * Construct an abstract value representing any `int` value between `__min`
 * and `__max` (inclusive). Alias: tis_interval
 */
int tis_int_interval(int __min, int __max);

/**
 * Construct an abstract value representing any `unsigned long` value between
 * `__min` and `__max` (inclusive).
 */
unsigned long tis_unsigned_long_interval(unsigned long __min, unsigned long __max);

/**
 * Construct an abstract value representing any `long` value between `__min`
 * and `__max` (inclusive).
 */
long tis_long_interval(long __min, long __max);

/**
 * Construct an abstract value representing any `unsigned long long` value between
 * `__min` and `__max` (inclusive).
 */
unsigned long long tis_unsigned_long_long_interval(unsigned long long __min, unsigned long long __max);

/**
 * Construct an abstract value representing any `long long` value between
 * `__min` and `__max` (inclusive).
 */
long long tis_long_long_interval(long long __min, long long __max);

/**
 * Construct an abstract value representing any `float` value between `__min`
 * and `__max` (inclusive).
 */
float tis_float_interval(float __min, float __max);

/**
 * Construct an abstract value representing any `double` value between `__min`
 * and `__max` (inclusive).
 */
double tis_double_interval(double __min, double __max);

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 */
void *tis_alloc(unsigned long __size);

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory.
 * Never return `NULL`.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory (never `NULL`).
 */
void *tis_alloc_safe(unsigned long __size);

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory.
 * Never return `NULL`.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory (never `NULL`).
 */
void *tis_alloc_non_null(unsigned long __size);

/**
 * Allocate zeroed memory for an array.
 *
 * @param __nmemb number of elements
 * @param __size size of each element in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 */
void *tis_calloc(unsigned long __nmemb, unsigned long __size);

/**
 * Split the state of the analyzer so that each possible value contained at
 * memory location of size `__s` at address `__p` is placed in a separate state
 * (up to `__limit` states).
 *
 * @param __p pointer to an area of memory by which to split the state
 * @param __s size of the area of memory by which to split the state
 * @param __limit upper bound on the number of created states
 */
void tis_variable_split(void *__p, unsigned long __s, int __limit);

__END_DECLS

#endif /* tis_builtin.h */
"""

DRIVER_GENERATION_TEMPLATE = """
You are an expert C programmer specializing in writing randomized unit tests.

## Context

Function to test: {function_name}

### Include Paths:
{include_paths}

### Source Files:
{context}

{skeleton_section}

## Requirements

Write a C11 verification driver for {function_name}.
The goal is to detect coding errors that may lead to undefined behaviors.

### Driver Structure:
1. Header comment: `// TIS-Analyzer verification driver for function {function_name}. It has been generated by tis-ai with model {model}.`
2. Include `<tis_builtin.h>`
3. Function declaration as `extern`
4. Driver function: `__tis_{function_name}_driver(void)`
5. Main function calling all driver functions in order

### TIS Builtin Functions:

A "generalized" value means a random value within a specified range. For example, a generalized value between 0 and 10 represents any random value in the range [0, 10].

Here is the full `tis_builtin.h` header with all available functions:

```c
{tis_builtin_header}
```

### Object Creation:
- You can create objects on the stack, with `tis_alloc()`, or using constructor functions from the API
- If constructor functions are provided in the context (e.g., `foo_new()`, `foo_create()`), prefer using them. Declare them as `extern` in your driver
- When using constructors, use opaque forward declarations (`struct foo;`) instead of defining struct contents

### Rules:
- Test NULL pointers using `tis_nondet_ptr(valid_ptr, NULL)` unless documented otherwise
- Array lengths should use #define macros instead of tis_interval for sizes
- All strings must be null-terminated
- Focus on exercising code paths rather than testing function effects
- Initialize all struct fields before use
- Use "generalized" instead of "random" in comments

### Header Includes:
- Include `<tis_builtin.h>` and standard C headers as needed (`<stddef.h>`, `<stdint.h>`, `<string.h>`, etc.)
- You may include project headers if they are provided in the context
- Alternatively, use forward declarations for types you don't need to access internals of

### Output Format:
Return ONLY C11 code in a ```c block. No explanations outside code comments.
"""

REFINER_TEMPLATE = """
You are fixing a TIS-Analyzer verification driver that failed compilation.

## Current Driver Code:
```c
{current_code}
```

## Compilation Errors:
{errors}

## Common Fixes:
- "incomplete type": Provide full struct definition with all fields, not just forward declaration
- "undeclared identifier": Add missing forward declaration (do NOT add project header includes)
- "variable-sized object": Use #define macros for array sizes
- "unbound function tis_*": Include <tis_builtin.h>
- "Incompatible declaration" / "not isomorphic": Your type definitions conflict with the actual source. Use opaque pointers (`struct X;`) instead of redefining structs, or ensure your definitions exactly match the source

## CRITICAL Rules:
- NEVER add project-specific headers (e.g., `<json-c/json.h>`, `"myproject.h"`)
- ONLY use `<tis_builtin.h>` and standard C headers
- Use forward declarations (`struct X;`) for types you don't need to access internals of
- The driver is compiled with the actual source files, so forward declarations are sufficient

## Instructions:
Fix the compilation errors while maintaining the driver's purpose.
Return the complete corrected driver in a ```c block.

Iteration: {iteration}/{max_iterations}
"""


def format_context_from_contents(context_contents: List[Dict[str, str]]) -> str:
    """
    Format context files for prompt injection.

    Args:
        context_contents: List of dicts with 'name' and 'content' keys

    Returns:
        Formatted string with all context files
    """
    formatted = []
    for ctx in context_contents:
        name = ctx.get("name", "unknown")
        content = ctx.get("content", "")
        formatted.append(f"File: {name}\n```c\n{content}\n```")

    return "\n\n".join(formatted)


def format_include_paths(include_paths: List[str]) -> str:
    """Format include paths for prompt."""
    if not include_paths:
        return "(none specified)"
    return "\n".join(f"- {path}" for path in include_paths)


def build_generation_prompt(
    function_name: str,
    context_contents: List[Dict[str, str]],
    include_paths: List[str] = None,
    model: str = "unknown",
    skeleton_code: str = None,
) -> str:
    """
    Build the driver generation prompt.

    Args:
        function_name: Name of the function to generate driver for
        context_contents: List of dicts with 'name' and 'content' keys
        include_paths: List of include paths from compilation database
        model: Model name used to generate the driver
        skeleton_code: Optional skeleton generated by tis-analyzer -drivergen-skeleton

    Returns:
        Formatted prompt string
    """
    context = format_context_from_contents(context_contents)
    includes = format_include_paths(include_paths or [])

    # Add skeleton section if available
    # NOTE: Skeleton is currently disabled - it provides full struct definitions
    # which causes LLM to use tis_alloc() instead of factory functions
    skeleton_section = ""
    # if skeleton_code:
    #     skeleton_section = f"""### Driver Skeleton:
    #
    # The following skeleton has been automatically generated using `tis-analyzer -drivergen-skeleton {function_name}`.
    # It contains all necessary type definitions and forward declarations.
    #
    # **CRITICAL**:
    # - Use this skeleton as the basis for your driver
    # - The skeleton provides all necessary forward declarations - do NOT add project header includes
    # - Fill in the body of the `__tis_{function_name}_driver(void)` function with parameter initialization and function calls
    # - Do not redefine types that are already forward-declared in the skeleton
    #
    # ```c
    # {skeleton_code}
    # ```
    # """

    return DRIVER_GENERATION_TEMPLATE.format(
        function_name=function_name,
        context=context,
        include_paths=includes,
        model=model,
        skeleton_section=skeleton_section,
        tis_builtin_header=TIS_BUILTIN_HEADER,
    )


def build_refiner_prompt(
    current_code: str, errors: list, iteration: int, max_iterations: int
) -> str:
    """Build the refinement prompt."""
    if errors:
        error_text = "\n".join(errors)
    else:
        error_text = (
            "Compilation failed but no specific error messages were captured. "
            "Common issues to check:\n"
            "- Incompatible type declarations between driver and source\n"
            "- Missing or incorrect struct definitions\n"
            "- Function signature mismatches\n"
            "- Missing #include directives"
        )
    return REFINER_TEMPLATE.format(
        current_code=current_code,
        errors=error_text,
        iteration=iteration,
        max_iterations=max_iterations,
    )
