Step: generator
Iteration: 1
Model: gpt-4o-mini
Timestamp: 2025-11-28T11:28:18.126846
================================================================================

=== PROMPT ===

You are an expert C programmer specializing in TrustInSoft Analyzer verification drivers.

## Context

Function to test: json_object_equal

### Include Paths:
- /home/arozovyk/work/json-c

### Source Files:
File: AST Context
```c
## Context for generating test driver for `json_object_equal`

### Target Function

**Documentation:**
```
/** Check if two json_object's are equal
 *
 * If the passed objects are equal 1 will be returned.
 * Equality is defined as follows:
 * - json_objects of different types are never equal
 * - json_objects of the same primitive type are equal if the
 *   c-representation of their value is equal
 * - json-arrays are considered equal if all values at the same
 *   indices are equal (same order)
 * - Complex json_objects are considered equal if all
 *   contained objects referenced by their key are equal,
 *   regardless their order.
 *
 * @param obj1 the first json_object instance
 * @param obj2 the second json_object instance
 * @returns 1 if both objects are equal, 0 otherwise
 */
```

**Signature:**
```c
int json_object_equal(struct json_object *jso1, struct json_object *jso2);
```

**Implementation (for understanding what code paths to exercise):**
```c
int json_object_equal(struct json_object *jso1, struct json_object *jso2)
{
	if (jso1 == jso2)
		return 1;

	if (!jso1 || !jso2)
		return 0;

	if (jso1->o_type != jso2->o_type)
		return 0;

	switch (jso1->o_type)
	{
	case json_type_boolean: return (JC_BOOL(jso1)->c_boolean == JC_BOOL(jso2)->c_boolean);

	case json_type_double: return (JC_DOUBLE(jso1)->c_double == JC_DOUBLE(jso2)->c_double);

	case json_type_int:
	{
		struct json_object_int *int1 = JC_INT(jso1);
		struct json_object_int *int2 = JC_INT(jso2);
		if (int1->cint_type == json_object_int_type_int64)
		{
			if (int2->cint_type == json_object_int_type_int64)
				return (int1->cint.c_int64 == int2->cint.c_int64);
			if (int1->cint.c_int64 < 0)
				return 0;
			return ((uint64_t)int1->cint.c_int64 == int2->cint.c_uint64);
		}c4);
	}

	case json_type_string:
	{
		return (_json_object_get_string_len(JC_STRING(jso1)) ==
		            _json_object_get_string_len(JC_STRING(jso2)) &&
		        memcmp(get_string_component(jso1), get_string_component(jso2),
		               _json_object_get_string_len(JC_STRING(jso1))) == 0);
	}

	case json_type_object: return json_object_all_values_equal(jso1, jso2);

	case json_type_array: return json_array_equal(jso1, jso2);

	case json_type_null: return 1;
	};

	return 0;
}
```

### Object Creation API

**CRITICAL: Use these constructor functions to create objects.**
**DO NOT use `tis_alloc()`, `malloc()`, or manual struct allocation for these types.**

#### Constructors for `json_object` (struct json_object *)

Use one of these functions to create instances:

```c
/* object type methods */
/** Create a new empty object with a reference count of 1.  The caller of
 * this object initially has sole ownership.  Remember, when using
 * json_object_object_add or json_object_array_put_idx, ownership will
 * transfer to the object/array.  Call json_object_get if you want to maintain
...
// From json_object.h:360
json_object *json_object_new_object(void);

/* Array type methods */
/** Create a new empty json_object of type json_type_array
 * with 32 slots allocated.
 * If you know the array size you'll need ahead of time, use
 * json_object_new_array_ext() instead.
...
// From json_object.h:546
json_object *json_object_new_array(void);

/** This method exists only to provide a complementary function
 * along the lines of the other json_object_new_* functions.
 * It always returns NULL, and it is entirely acceptable to simply use NULL directly.
 */
// From json_object.h:1040
json_object *json_object_new_null(void);

/** Create a new empty json_object of type json_type_array
 * with the desired number of slots allocated.
 * @see json_object_array_shrink()
 * @param initial_size the number of slots to allocate
 * @returns a json_object of type json_type_array
...
// From json_object.h:554
json_object *json_object_new_array_ext(int initial_size);

/* json_bool type methods */
/** Create a new empty json_object of type json_type_boolean
 * @param b a json_bool 1 or 0
 * @returns a json_object of type json_type_boolean
 */
// From json_object.h:689
json_object *json_object_new_boolean(json_bool b);

/* int type methods */
/** Create a new empty json_object of type json_type_int
 * Note that values are stored as 64-bit values internally.
 * To ensure the full range is maintained, use json_object_new_int64 instead.
 * @param i the integer
...
// From json_object.h:725
json_object *json_object_new_int(int32_t i);

/** Create a new empty json_object of type json_type_int
 * @param i the integer
 * @returns a json_object of type json_type_int
 */
// From json_object.h:731
json_object *json_object_new_int64(int64_t i);

/** Create a new empty json_object of type json_type_uint
 * @param i the integer
 * @returns a json_object of type json_type_uint
 */
// From json_object.h:737
json_object *json_object_new_uint64(uint64_t i);

/* double type methods */
/** Create a new empty json_object of type json_type_double
 *
 * @see json_object_double_to_json_string() for how to set a custom format string.
 *
...
// From json_object.h:857
json_object *json_object_new_double(double d);

/**
 * Create a new json_object of type json_type_double, using
 * the exact serialized representation of the value.
 *
 * This allows for numbers that would otherwise get displayed
...
// From json_object.h:886
json_object *json_object_new_double_s(double d, const char *ds);

```
*(11 more constructors available)*

#### Constructors for `json_tokener` (struct json_tokener *)

Use one of these functions to create instances:

```c
/**
 * Allocate a new json_tokener.
 * When done using that to parse objects, free it with json_tokener_free().
 * See json_tokener_parse_ex() for usage details.
 */
// From json_tokener.h:205
json_tokener *json_tokener_new(void);

/**
 * Allocate a new json_tokener with a custom max nesting depth.
 * The depth must be at least 1.
 * @see JSON_TOKENER_DEFAULT_DEPTH
 */
// From json_tokener.h:212
json_tokener *json_tokener_new_ex(int depth);

/**
 * Parse a json_object out of the string `str`.
 *
 * If you need more control over how the parsing occurs,
 * see json_tokener_parse_ex().
...
// From json_tokener.h:231
json_object *json_tokener_parse(const char *str);

/**
 * Parse a json_object out of the string `str`, but if it fails
 * return the error in `*error`.
 * @see json_tokener_parse()
 * @see json_tokener_parse_ex()
...
// From json_tokener.h:239
json_object *json_tokener_parse_verbose(const char *str,
                                                           enum json_tokener_error *error);

// From json_tokener.c:130
static int json_tokener_parse_double(const char *buf, int len, double *retval);

```

### Required Extern Declarations

**Copy these declarations into your driver to use the constructor functions:**

```c
// Forward declare opaque types (DO NOT define the struct contents)
struct json_object;
struct json_tokener;

// Required type definitions for constructor parameters
typedef int json_bool;

// Constructor function declarations
extern json_object *json_object_new_object(void);
extern json_object *json_object_new_array(void);
extern json_object *json_object_new_null(void);
extern json_object *json_object_new_array_ext(int initial_size);
extern json_object *json_object_new_boolean(json_bool b);
extern json_tokener *json_tokener_new(void);
extern json_tokener *json_tokener_new_ex(int depth);
extern json_object *json_tokener_parse(const char *str);
extern json_object *json_tokener_parse_verbose(const char *str,
                                                           enum json_tokener_error *error);
```

### Type Information
```c
// struct_ptr: json_object
typedef struct json_object json_object;

// enum: json_type
enum json_type

// enum: json_tokener_error
enum json_tokener_error
{
	json_tokener_success,
	json_tokener_continue,
	json_tokener_error_depth,
	json_tokener_error_parse_eof,
	json_tokener_error_parse_unexpected,
	json_tokener_error_parse_null,
	json_tokener_error_parse_boolean,
	json_tokener_error_parse_number,
	json_tokener_error_parse_array,
	json_tokener_error_parse_object_key_name,
	json_tokener_error_parse_object_key_sep,
	json_tokener_error_parse_object_value_sep,
	json_tokener_error_parse_string,
	json_tokener_error_parse_comment,
	json_tokener_error_parse_utf8_string,
	json_tokener_error_size,   /* A string longer than INT32_MAX was passed as input */
	json_tokener_error_memory  /* Failed to allocate memory */
}

```

### Parameter Initialization Guide

| Parameter | Type | Recommended Approach |
|-----------|------|---------------------|
| `jso1` | `struct json_object` | Use `json_object_new_object()` or similar |
| `jso2` | `struct json_object` | Use `json_object_new_object()` or similar |

```



## Requirements

Write a strictly conformant C11 verification driver for json_object_equal.
The goal is to detect coding errors that may lead to undefined behaviors.

### Driver Structure:
1. Header comment: `// TIS-Analyzer verification driver for function json_object_equal. It has been generated by tis-ai with model unknown.`
2. Include `<tis_builtin.h>`
3. All required type definitions (complete, not just declarations)
4. Function declaration as `extern`
5. Driver function: `__tis_json_object_equal_driver(void)`
6. Main function calling all test functions in order

### TIS Builtin Functions (use ONLY these):
- `void tis_make_unknown(char *addr, unsigned long len)` - Initialize memory with generalized values
- `int tis_interval(int min, int max)` - Generalized integer in range [min, max]
- `void *tis_alloc(size_t size)` - Allocate raw memory ONLY for primitive types/arrays (NOT for complex structs with constructors)
- `void *tis_nondet_ptr(void *p1, void *p2)` - Return either p1 or p2

### Object Creation Rules:
- **If constructor functions are provided in the context (e.g., `foo_new()`, `foo_create()`)**: USE THEM to create objects. Declare them as `extern` in your driver.
- **If NO constructor is provided**: Use `tis_alloc()` with manual field initialization
- **NEVER manually define struct contents when constructors are available** - use opaque forward declarations (`struct foo;`)

### Rules:
- Test NULL pointers using `tis_nondet_ptr(valid_ptr, NULL)` unless documented otherwise
- Array lengths MUST use #define macros, never tis_interval for sizes
- All strings MUST be null-terminated
- Never test function effects, only exercise code paths
- Do not insert code that is not useful to call json_object_equal
- Initialize all struct fields before use
- Use "generalized" not "random" in comments
- In the comment, describe why a line is here, but do not comment on things that are not here

### CRITICAL - Header Includes:
- ONLY include `<tis_builtin.h>` and standard C headers (`<stddef.h>`, `<stdint.h>`, `<string.h>`, etc.)
- NEVER include project-specific headers (e.g., `<json-c/json.h>`, `"myproject.h"`)
- All project types MUST be forward-declared in the driver using the skeleton's declarations
- The driver will be compiled alongside the actual source files, so forward declarations are sufficient

### Output Format:
Return ONLY valid C11 code in a ```c block. No explanations outside code comments.
Do not give your thought process. Write only code in your answer.


================================================================================

=== RESPONSE ===
```c
// TIS-Analyzer verification driver for function json_object_equal. It has been generated by tis-ai with model unknown.

#include <tis_builtin.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

// Forward declare opaque types (DO NOT define the struct contents)
struct json_object;
struct json_tokener;

// Required type definitions for constructor parameters
typedef int json_bool;

// Constructor function declarations
extern struct json_object *json_object_new_object(void);
extern struct json_object *json_object_new_array(void);
extern struct json_object *json_object_new_null(void);
extern struct json_object *json_object_new_boolean(json_bool b);
extern struct json_object *json_object_new_int(int32_t i);
extern struct json_object *json_object_new_double(double d);
extern struct json_object *json_object_new_string(const char *s);

// Function declaration
extern int json_object_equal(struct json_object *jso1, struct json_object *jso2);

// Driver function
void __tis_json_object_equal_driver(void) {
    struct json_object *obj1, *obj2;

    // Test 1: Both objects are NULL
    obj1 = NULL;
    obj2 = NULL;
    if (json_object_equal(obj1, obj2) != 1) {
        // Expect equal
    }

    // Test 2: One object NULL
    obj1 = NULL;
    obj2 = json_object_new_object();
    if (json_object_equal(obj1, obj2) != 0) {
        // Expect not equal
    }
    json_object_new_object(); // Clean up

    // Test 3: Both objects are equal integers
    obj1 = json_object_new_int(42);
    obj2 = json_object_new_int(42);
    if (json_object_equal(obj1, obj2) != 1) {
        // Expect equal
    }

    // Test 4: Both objects are different integers
    obj2 = json_object_new_int(43);
    if (json_object_equal(obj1, obj2) != 0) {
        // Expect not equal
    }
    json_object_new_object(); // Clean up

    // Test 5: Both objects are equal strings
    obj1 = json_object_new_string("hello");
    obj2 = json_object_new_string("hello");
    if (json_object_equal(obj1, obj2) != 1) {
        // Expect equal
    }

    // Test 6: Both objects are different strings
    obj2 = json_object_new_string("world");
    if (json_object_equal(obj1, obj2) != 0) {
        // Expect not equal
    }
    json_object_new_object(); // Clean up

    // Test 7: Both objects are equal booleans
    obj1 = json_object_new_boolean(1);
    obj2 = json_object_new_boolean(1);
    if (json_object_equal(obj1, obj2) != 1) {
        // Expect equal
    }

    // Test 8: Both objects are different booleans
    obj2 = json_object_new_boolean(0);
    if (json_object_equal(obj1, obj2) != 0) {
        // Expect not equal
    }

    // Clean up
    // Assume json_object_free is a valid function to free json_object 
    // json_object_free(obj1);
    // json_object_free(obj2);
}

// Main function to call the driver
int main(void) {
    __tis_json_object_equal_driver();
    return 0;
}
```