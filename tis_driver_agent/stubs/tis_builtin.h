/**************************************************************************/
/*                                                                        */
/*  This file is part of TrustInSoft Kernel.                              */
/*                                                                        */
/*    Copyright (C) 2016-2025 TrustInSoft                                 */
/*                                                                        */
/*  TrustInSoft Kernel is released under GPLv2                            */
/*                                                                        */
/**************************************************************************/

#ifndef __TIS_BUILTIN_H
#define __TIS_BUILTIN_H

/* We do not want to include __fc_features.h in order to be fully
   independent of the C standard library.
   For the same reason, the following prototypes do not depend on size_t
   but on unsigned long.
*/
#ifdef __cplusplus
# define __BEGIN_DECLS extern "C" {
# define __END_DECLS }
# define __TIS_THROW throw ()
#else
# define __BEGIN_DECLS
# define __END_DECLS
# define __TIS_THROW __attribute__ ((nothrow))
#endif

__BEGIN_DECLS

extern _Thread_local int tis_entropy_source __attribute__((__TIS_MODEL__));

extern _Thread_local int __TIS_errno;

/**
 * Construct an abstract value representing any `int` value between `__min`
 * and `__max` (inclusive).
 *
 * Alias: tis_int_interval
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `int` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
int tis_interval(int __min, int __max) __TIS_THROW;

/**
 * Populate an area of memory starting at address `__p` of size `__l` with
 * abstract values representing unknown contents.
 *
 * @param __p pointer to an area of memory to populate
 * @param __l size of the area of memory being populated (in bytes)
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-make-unknown
 */
/*@ requires valid_buffer: UB: \valid(__p + (0 .. __l-1));
    assigns __p[0 .. __l-1] \from tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \initialized(__p + (0 .. __l-1));
*/
void tis_make_unknown(char *__p, unsigned long __l) __TIS_THROW;

/**
 * Construct an abstract value representing a nondeterministic choice between
 * two signed integer values.
 *
 * @param __a a possible value
 * @param __b a possible value
 * @returns an abstract value representing a set or interval of possible
 *         `int` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet
 */
/*@ assigns \result \from __a, __b, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \subset(\result, __a) || \subset(\result, __b);
 */
int tis_nondet(int __a, int __b) __TIS_THROW;

/**
 * Construct an abstract value representing a nondeterministic choice between
 * three signed integer values.
 *
 * @param __a a possible value
 * @param __b a possible value
 * @param __c a possible value
 * @returns an abstract value representing a set or interval of possible
 *         `int` values
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet3
 */
/*@ assigns \result \from __a, __b, __c, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \subset(\result, __a) || \subset(\result, __b) || \subset(\result, __c);
*/
int tis_nondet3(int __a, int __b, int __c) __TIS_THROW;

/**
 * Construct an abstract value representing a nondeterministic choice between
 * four signed integer values.
 *
 * @param __a a possible value
 * @param __b a possible value
 * @param __c a possible value
 * @param __d a possible value
 * @returns an abstract value representing a set or interval of possible
 *         `int` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet4
 */
/*@ assigns \result \from __a, __b, __c, __d, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \subset(\result, __a) || \subset(\result, __b) ||
            \subset(\result, __c) || \subset(\result, __d);
 */
int tis_nondet4(int __a, int __b, int __c, int __d) __TIS_THROW;

/**
 * Construct an abstract value representing a nondeterministic choice between
 * five signed integer values.
 *
 * @param __a a possible value
 * @param __b a possible value
 * @param __c a possible value
 * @param __d a possible value
 * @param __e a possible value
 * @returns an abstract value representing a set or interval of possible
 *         `int` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet5
 */
/*@ assigns \result \from __a, __b, __c, __d, __e, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \subset(\result, __a) || \subset(\result, __b) ||
            \subset(\result, __c) || \subset(\result, __d) ||
            \subset(\result, __e);
 */
int tis_nondet5(int __a, int __b, int __c, int __d, int __e) __TIS_THROW;

/**
 * Construct an abstract value representing a nondeterministic choice between
 * two pointers.
 *
 * @param __a a pointer to a memory address
 * @param __b a pointer to a memory address
 * @returns an abstract value representing a set or interval of possible
 *         pointers to memory addresses
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet-ptr
 */
/*@ assigns \result \from __a, __b, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \result == __a || \result == __b;
 */
#ifdef __cplusplus
static inline void *tis_nondet_ptr(void *__a, void *__b) __TIS_THROW
#else
static inline __TIS_THROW void *tis_nondet_ptr(void *__a, void *__b)
#endif
{
    return tis_nondet(0, 1) ? __a : __b;
}

/**
 * Construct an abstract value representing a nondeterministic choice between
 * three pointers.
 *
 * @param __a a pointer to a memory address
 * @param __b a pointer to a memory address
 * @param __c a pointer to a memory address
 * @returns an abstract value representing a set or interval of possible
 *         pointers to memory addresses
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet3-ptr
 */
/*@ assigns \result \from __a, __b, __c, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \result == __a || \result == __b || \result == __c;
 */
#ifdef __cplusplus
static inline void *tis_nondet3_ptr(void *__a, void *__b, void *__c) __TIS_THROW
#else
static inline __TIS_THROW void *tis_nondet3_ptr(void *__a, void *__b, void *__c)
#endif
{
    void *res;
    switch(tis_interval(0, 2)) {
      case 0: res = __a; break;
      case 1: res = __b; break;
      default: res = __c;
    }
    return res;
}

/**
 * Construct an abstract value representing a nondeterministic choice between
 * four pointers.
 *
 * @param __a a pointer to a memory address
 * @param __b a pointer to a memory address
 * @param __c a pointer to a memory address
 * @param __d a pointer to a memory address
 * @returns an abstract value representing a set or interval of possible
 *         pointers to memory addresses
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet4-ptr
 */
/*@ assigns \result \from __a, __b, __c, __d, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \result == __a || \result == __b || \result == __c
    || \result == __d;
 */
#ifdef __cplusplus
static inline void *tis_nondet4_ptr(void *__a, void *__b, void *__c, void *__d)
    __TIS_THROW
#else
static inline __TIS_THROW void *tis_nondet4_ptr(void *__a, void *__b, void *__c,
                                            void *__d)
#endif
{
    void *res;
    switch(tis_interval(0, 3)) {
      case 0: res = __a; break;
      case 1: res = __b; break;
      case 2: res = __c; break;
      default: res = __d;
    }
    return res;
}

/**
 * Construct an abstract value representing a nondeterministic choice between
 * five pointers.
 *
 * @param __a a pointer to a memory address
 * @param __b a pointer to a memory address
 * @param __c a pointer to a memory address
 * @param __d a pointer to a memory address
 * @param __e a pointer to a memory address
 * @returns an abstract value representing a set or interval of possible
 *         pointers to memory addresses
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-nondet5-ptr
 */
/*@ assigns \result \from __a, __b, __c, __d, __e, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \result == __a || \result == __b || \result == __c
    || \result == __d || \result == __e;
 */
#ifdef __cplusplus
static inline void *tis_nondet5_ptr(void *__a, void *__b, void *__c,
                                    void *__d, void *__e) __TIS_THROW
#else
static inline __TIS_THROW void *tis_nondet5_ptr(void *__a, void *__b,
                                            void *__c, void *__d, void *__e)
#endif
{
    void *res;
    switch(tis_interval(0, 4)) {
      case 0: res = __a; break;
      case 1: res = __b; break;
      case 2: res = __c; break;
      case 3: res = __d; break;
      default: res = __e;
    }
    return res;
}

/**
 * Make an area of memory starting at address `__p` of size `__l`
 * uninitialized.
 *
 * @param __p pointer to an area of memory to make uninitialized
 * @param __l size of the area of memory being uninitialized (in bytes)
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-make-uninitialized
 */
/*@ requires \valid(__p + (0 .. __l-1));
    assigns __p[0 .. __l-1] \from \nothing;
*/
void tis_make_uninitialized(char *__p, unsigned long __l) __TIS_THROW;

/**
 * Construct an abstract value representing any `int` value between `__min`
 * and `__max` (inclusive) and place each resulting value in a separate state.
 * Equivalent to `tis_interval` followed by `tis_variable_split`.
 *
 * @param __min lowest value in returned interval
 * @param __max highest value in returned interval
 * @return an abstract value representing an interval of possible `int` values
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-interval-split
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
int tis_interval_split(int __min, int __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `unsigned char` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         unsigned char values
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-unsigned-char-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
unsigned char tis_unsigned_char_interval(unsigned char __min,
                                         unsigned char __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `char` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         char values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-char-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
char tis_char_interval(char __min, char __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `unsigned short` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `unsigned short` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-unsigned-short-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
unsigned short tis_unsigned_short_interval(unsigned short __min,
                                           unsigned short __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `short` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `short` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-short-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
short tis_short_interval(short __min, short __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `unsigned int` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `unsigned int` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-unsigned-int-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
unsigned int tis_unsigned_int_interval(unsigned int __min,
                                       unsigned int __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `int` value between `__min`
 * and `__max` (inclusive).
 *
 * Alias: tis_interval
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `int` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-int-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
int tis_int_interval(int __min, int __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `unsigned long` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `unsigned long` values
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-unsigned-long-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
unsigned long tis_unsigned_long_interval(unsigned long __min,
                                         unsigned long __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `long` value between `__min`
 * and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `long` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-long-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
long tis_long_interval(long __min, long __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `long long` value between
 * `__min` and `__max` (inclusive) and place each resulting value in a separate
 * state. Equivalent to `tis_long_long_interval` followed by
 * `tis_variable_split`.
 *
 * @param __min lowest value in returned interval
 * @param __max highest value in returned interval
 * @return an abstract value representing an interval of possible
 *         `long long` values
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-long-long-interval-split
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
long long tis_long_long_interval_split(long long __min, long long __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `unsigned long long` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `unsigned long long` values
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-unsigned-long-long-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
unsigned long long tis_unsigned_long_long_interval
     (unsigned long long __min, unsigned long long __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `long long` value between
 * `__min` and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `long long` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-long-long-interval
 */
/*@ requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures __min <= \result <= __max;
 */
long long tis_long_long_interval(long long __min, long long __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `float` value between `__min`
 * and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible `long
 *         long` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-float-interval
 */
/*@ requires valid_bounds: \is_finite(__min) && \is_finite(__max);
    requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \is_finite(\result) && __min <= \result <= __max;
 */
float tis_float_interval(float __min, float __max) __TIS_THROW;

/**
 * Construct an abstract value representing any `double` value between `__min`
 * and `__max` (inclusive).
 *
 * @param __min lowest value in returned interval or set
 * @param __max highest value in returned interval or set
 * @return an abstract value representing an interval or set of possible
 *         `double` values
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-double-interval
 */
/*@ requires valid_bounds: \is_finite(__min) && \is_finite(__max);
    requires valid_interval: __min <= __max;
    assigns \result \from __min, __max, tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \is_finite(\result) && __min <= \result <= __max;
 */
double tis_double_interval(double __min, double __max) __TIS_THROW;

/**
 * Construct an abstract `float` value.
 *
 * @param __nmin lower bound of the negative interval. Must be finite.
 * @param __nmax upper bound of the negative interval. Must be finite.
 * @param __pmin lower bound of the positive interval. Must be finite.
 * @param __pmax upper bound of the positive interval. Must be finite.
 * @param __nzero if nonzero, the abstract value will contain -0.
 * @param __pzero if nonzero, the abstract value will contain +0.
 * @param __ninf if nonzero, the abstract value will contain -inf.
 * @param __pinf if nonzero, the abstract value will contain +inf.
 * @param __nan if nonzero, the abstract value will contain NaN.
 * @return the constructed abstract value
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-abstract-float
 */
/*@ requires valid_bounds:
      \is_finite(__nmin) && \is_finite(__nmax) &&
    \is_finite(__pmin) && \is_finite(__pmax);
    requires not_bottom:
           __nmin <= __nmax || __pmin <= __pmax ||
     __nzero != 0 || __pzero != 0 || __ninf != 0 || __pinf != 0 || __nan != 0;
    assigns \result \from __nmin, __nmax, __pmin, __pmax, __nzero,
                          __pzero, __ninf, __pinf, __nan, tis_entropy_source;
*/
float tis_abstract_float(float __nmin, float __nmax, float __pmin, float __pmax,
                         int __nzero, int __pzero, int __ninf, int __pinf, int __nan)
                         __TIS_THROW;

/**
 * Construct an abstract `double` value.
 *
 * @param __nmin lower bound of the negative interval. Must be finite.
 * @param __nmax upper bound of the negative interval. Must be finite.
 * @param __pmin lower bound of the positive interval. Must be finite.
 * @param __pmax upper bound of the positive interval. Must be finite.
 * @param __nzero if nonzero, the abstract value will contain -0.
 * @param __pzero if nonzero, the abstract value will contain +0.
 * @param __ninf if nonzero, the abstract value will contain -inf.
 * @param __pinf if nonzero, the abstract value will contain +inf.
 * @param __nan if nonzero, the abstract value will contain NaN.
 * @return the constructed abstract value
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-abstract-double
 */
/*@ requires valid_bounds:
      \is_finite(__nmin) && \is_finite(__nmax) &&
    \is_finite(__pmin) && \is_finite(__pmax);
    requires not_bottom:
           __nmin <= __nmax || __pmin <= __pmax ||
    __nzero != 0 || __pzero != 0 || __ninf != 0 || __pinf != 0 || __nan != 0;
    assigns \result \from __nmin, __nmax, __pmin, __pmax, __nzero,
                          __pzero, __ninf, __pinf, __nan, tis_entropy_source;
*/
double tis_abstract_double(double __nmin, double __nmax, double __pmin, double __pmax,
                         int __nzero, int __pzero, int __ninf, int __pinf, int __nan)
                         __TIS_THROW;

/**
 * Retrieve a pointer to variable `__name` from file `__file`.
 *
 * @param __name a string literal specifying the name of a variable in `__file`
 * @param __file a string literal specifying a name (not path) of a source file
 * @return a pointer to a variable
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-find-variable
 */
/*@ // obtains a pointer to a variable, even if the variable is static.
  requires \valid_read(__name); // in fact only string literals are supported
  requires \valid_read(__file); // in fact only string literals are supported
  assigns \nothing;
*/
void *tis_find_variable(const char *__name, const char *__file);

/**
 * Generic function pointer.
 */
typedef void (*tis_funptr)(void);

/**
 * Retrieve a pointer to function `__name` from file `__file`.
 *
 * @param __name a string literal specifying the name of a function in `__file`
 * @param __file a string literal specifying a name (not path) of a source file
 * @return a pointer to a function
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-find-function
 */
/*@ // obtains a pointer to a function, even if the function is static.
  requires \valid_read(__name); // in fact only string literals are supported
  requires \valid_read(__file); // in fact only string literals are supported
  assigns \nothing;
*/
tis_funptr tis_find_function(const char *__name, const char *__file);

/**
 * Emit an alarm with message `__msg` if `__test` is zero.
 *
 * @param __msg message to print
 * @param __test integer to test
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-ub
 */
/*@ assigns \nothing; */
void tis_ub(const char* __msg, int __test) __TIS_THROW;

/**
 * Set up a watchpoint that checks the number of possible values at a memory
 * location.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __maximal_cardinal max allowed values at memory location.
 * @param __n the number of statements during which the condition may remain
 *              true before the analysis is stopped (`-1` not to stop at all).
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-watch-cardinal
 */
/*@ assigns \nothing; */
void tis_watch_cardinal(void *__p, unsigned long __s,
                        unsigned long long __maximal_cardinal, int __n) __TIS_THROW;

/**
 * Set up a watchpoint that checks possible values at a memory location.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __forbidden_value checked value.
 * @param __n the number of statements during which the condition may remain
 *              true before the analysis is stopped (`-1` not to stop at all).
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-watch-value
 */
/*@ assigns \nothing; */
void tis_watch_value(void *__p, unsigned long __s, int __forbidden_value,
                     int __n) __TIS_THROW;

/**
 * Set up a watchpoint that checks whether value at a memory location is an
 * address.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __n the number of statements during which the condition may remain
 *              true before the analysis is stopped (`-1` not to stop at all).
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-watch-address
 */
/*@ assigns \nothing; */
void tis_watch_address(void *__p, unsigned long __s, int __n) __TIS_THROW;

/**
 * Set up a watchpoint that checks whether value at a memory location is a
 * garbled mix.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __n the number of statements during which the condition may remain
 *              true before the analysis is stopped (`-1` not to stop at all).
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-watch-garbled
 *
 * @since 1.14
 */
/*@ assigns \nothing; */
void tis_watch_garbled(void *__p, unsigned long __s, int __n) __TIS_THROW;

/**
 * Set up a watchpoint that checks that all accesses to a given memory location
 * are protected by the given mutex.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __lock pointer to the mutex.
 *
 * @see
 * https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-watch-shared-variable
 *
 * @since 2025.04
 */
/*@ assigns \nothing; */
void tis_watch_shared_variable(void *__p, unsigned long __s, void *__lock) __TIS_THROW;

/**
 * Set up a watchpoint that checks whether expressions involving a pointer
 * yield imprecise pointers.
 *
 * @param __p pointer to checked memory location.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-detect-imprecise-pointer
 */
/*@ assigns \nothing; */
void tis_detect_imprecise_pointer(void *__p) __TIS_THROW;

/**
 * Check the number of possible values at a memory location.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __maximal_cardinal max allowed values at memory location.
 * @return `1` if the condition is true, or `0` otherwise.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-check-cardinal
 *
 * @since 1.46
 */
/*@ assigns \result \from __p, __s, __maximal_cardinal, ((char*)__p)[0..]; */
int tis_check_cardinal(void *__p, unsigned long __s,
                        unsigned long long __maximal_cardinal) __TIS_THROW;

/**
 * Check possible values at a memory location.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @param __forbidden_value checked value.
 * @return `1` if the condition is true, or `0` otherwise.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-check-value
 *
 * @since 1.46
 */
/*@ assigns \result \from __p, __s, __forbidden_value, ((char*)__p)[0..]; */
int tis_check_value(void *__p, unsigned long __s, int __forbidden_value) __TIS_THROW;

/**
 * Check whether value at a memory location is an address.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @return `1` if the condition is true, or `0` otherwise.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-check-address
 *
 * @since 1.46
 */
/*@ assigns \result \from __p, __s, ((char*)__p)[0..]; */
int tis_check_address(void *__p, unsigned long __s) __TIS_THROW;

/**
 * Check whether value at a memory location is a garbled mix.
 *
 * @param __p pointer to checked memory location.
 * @param __s size of checked memory location.
 * @return `1` if the condition is true, or `0` otherwise.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-check-garbled
 *
 * @since 1.46
 */
/*@ assigns \result \from __p, __s, ((char*)__p)[0..]; */
int tis_check_garbled(void *__p, unsigned long __s) __TIS_THROW;

/**
 * Check whether a pointer is imprecise.
 *
 * @param __p pointer to checked memory location.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-check-for-imprecise-pointer
 *
 * @since 1.46
 */
/*@ assigns \nothing; */
void tis_check_for_imprecise_pointer(void *__p) __TIS_THROW;

extern int __fc_heap_status __attribute__((__TIS_MODEL__));

/**
 * Allocate `__size` bytes and return a pointer to the allocated memory,
 * allocating a fresh base of size `__size` for each call.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc-size
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
    assigns __TIS_errno \from __size, __fc_heap_status;
*/
void *tis_alloc_size(unsigned long __size) __TIS_THROW;

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory,
 * allocating a fresh weak base of size `__size` for each call.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc-size-weak
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
    assigns __TIS_errno \from __size, __fc_heap_status;
*/
void *tis_alloc_size_weak(unsigned long __size) __TIS_THROW;

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
    assigns __TIS_errno \from __size, __fc_heap_status;
*/
void *tis_alloc(unsigned long __size) __TIS_THROW;

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory,
 * allocating a fresh base of size `__size` for each call. Never return `NULL`.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory (never `NULL`).
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc-safe
 */
/*@
   allocates \result;
   assigns \result \from __size, __fc_heap_status;
   assigns __fc_heap_status \from __size, __fc_heap_status;
   ensures \fresh(\result, __size);
*/
void *tis_alloc_safe(unsigned long __size) __TIS_THROW;

/**
 * Allocate `__size` bytes and return a pointer to the allocated memory whose
 * value is within the specified range of addresses.
 *
 * @param __size size of the allocated memory in bytes.
 * @param __min
 * @param __max
 * @param __rem
 * @param __modu
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc-with-address
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __min, __max, __rem, __modu,
    __fc_heap_status;
    assigns \result \from __size, __min, __max, __rem, __modu,
    __fc_heap_status;
    assigns __TIS_errno \from __size, __fc_heap_status;
*/
void *tis_alloc_with_address (unsigned long __size,
                              unsigned long __min,
                              unsigned long __max,
                              unsigned long __rem,
                              unsigned long __modu) __TIS_THROW;

/**
 * Allocate `__size` bytes and return a pointer to the allocated memory, allocating
 * a fresh weak base for each callstack.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc-weak
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
    assigns __TIS_errno \from __size, __fc_heap_status;
*/
void *tis_alloc_weak(unsigned long __size) __TIS_THROW;

/**
 * Allocate `__size` bytes and returns a pointer to the allocated memory.
 * Never return `NULL`.
 *
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory (never `NULL`).
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-alloc_non_null
 *
 * @since 2025.04
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
    assigns __TIS_errno \from __size, __fc_heap_status;
*/
void *tis_alloc_non_null(unsigned long __size) __TIS_THROW;

/**
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-calloc
 */
/*@ allocates \result;
  assigns __fc_heap_status \from __size, __nmemb, __fc_heap_status;
  assigns \result \from __size, __nmemb, __fc_heap_status;
  assigns __TIS_errno \from __size, __nmemb, __fc_heap_status;
*/
void *tis_calloc(unsigned long __nmemb, unsigned long __size) __TIS_THROW;

/**
 * Return the size of a block in bytes.
 * 
 * @param __p a pointer to a block.
 * @return size of the block in bytes.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-block-size
 */
/*@ assigns \result \from indirect:__p; */
__typeof__(sizeof(int)) tis_block_size(const void *__p) __TIS_THROW;

/**
 * Free a block allocated by any `tis_alloc*` function.
 *
 * @param __p a pointer to a memory area allocated with any `tis_alloc*`
 *            function.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-free
 */
/*@ assigns __fc_heap_status \from indirect:__p, __fc_heap_status;
*/
void tis_free(const void *__p) __TIS_THROW;

/**
 * Allocate `__size` bytes and return a pointer to the allocated memory. The
 * allocated block can only be freed with `tis_delete`.
 * 
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-new
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
*/
void *tis_new(unsigned long __size) __TIS_THROW;

/**
 * Allocate `__size` bytes and return a pointer to the allocated memory. The
 * allocated block can only be freed with `tis_delete_array`.
 * 
 * @param __size size of the allocated memory in bytes.
 * @return pointer to an allocated area of memory or `NULL`.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-new-array
 */
/*@ allocates \result;
    assigns __fc_heap_status \from __size, __fc_heap_status;
    assigns \result \from __size, __fc_heap_status;
*/
void *tis_new_array(unsigned long __size) __TIS_THROW;

/**
 * Free a block allocated by the `tis_new` function.
 * 
 * @param __p a pointer to a memory area allocated with `tis_new`.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-delete
 */
/*@ assigns __fc_heap_status \from indirect:__p, __fc_heap_status;
*/
void tis_delete(const void *__p) __TIS_THROW;

/**
 * Free a block allocated by the `tis_new_array` function.
 * 
 * @param __p a pointer to a memory area allocated with `tis_new_array`.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-delete-array
 */
/*@ assigns __fc_heap_status \from indirect:__p, __fc_heap_status;
*/
void tis_delete_array(const void *__p) __TIS_THROW;

/**
 * Split the state of the analyzer so that each possible value contained at
 * memory location of size `__s` at address `__p` is placed in a separate state
 * (up to `__limit` states).
 *
 * @param __p pointer to an area of memory by which to split the state
 * @param __s size of the area of memory by which to split the state
 * @param __limit upper bound on the number of created states
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-variable-split
 */
/*@ assigns \nothing; */
void tis_variable_split(void *__p, unsigned long __s, int __limit) __TIS_THROW;

/*@ assigns \result \from __p;
    ensures \result == (void *)\base_addr(__p);
*/
void *tis_base_addr(void *__p) __TIS_THROW;

/*@ requires valid_length: __n != 0;
    requires valid_src1: \valid_read((char *)__src1 + (0 .. __n - 1));
    requires valid_src2: \valid_read((char *)__src2 + (0 .. __n - 1));
    assigns \nothing;
*/
void tis_check_included(const void *__src1, unsigned long __n,
                        const void *__src2) __TIS_THROW;

/*@ assigns \nothing; */
void tis_print_subexps(const char *__description, ...) __TIS_THROW;

/*@ assigns \result \from __p, __start, __end; */
int tis_ptr_is_within(const void *__p, const void *__start,
                      const void *__end) __TIS_THROW;

/*@ assigns \result \from __p1, __p2; */
int tis_ptr_is_less_than(const void *__p1, const void *__p2) __TIS_THROW;

/*@ assigns \result \from __p, __n; */
int tis_valid_read(const void* __p, unsigned long __n) __TIS_THROW;

/*@ assigns \result \from __p, __n; */
int tis_valid(const void* __p, unsigned long __n) __TIS_THROW;

/*@ assigns \nothing; */
void tis_deps_show_deps(void) __TIS_THROW;

/*@ assigns \nothing; */
void tis_deps_show_pathdeps(void) __TIS_THROW;

/*@ assigns \nothing; */
void tis_deps_show_open_pathdeps(void) __TIS_THROW;

/*@ assigns \nothing; */
void tis_deps_show_file_generalizable_bytes(void) __TIS_THROW;

/**
 * Print a list of allocated blocks.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-show-allocated
 */
/*@ assigns \nothing; */
void tis_show_allocated(void) __TIS_THROW;

/**
 * Return a different number in each state it is called in.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-id
 */
/*@ assigns \nothing; */
unsigned long long tis_id(void) __TIS_THROW;

/**
 * Pretty-print the message in `__msg`, the value of each of the following
 * arguments, and a list of allocated blocks.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-show-allocated-and-id
 */
/*@ assigns \nothing; */
void tis_show_allocated_and_id(const char * __msg, ...) __TIS_THROW;

/*@ assigns \nothing; */
void tis_sa_show_each(const char * __msg, ...) __TIS_THROW;

/*@ assigns \nothing; */
void tis_sa_dump_each(void) __TIS_THROW;

/**
 * Pretty-print the message in `__msg` and the value of each of the following
 * arguments.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-show-each
 */
/*@ assigns \nothing; */
void tis_show_each(const char * __msg, ...);

/*@ assigns \nothing; */
void tis_show_recursively_each(const void * __P);

/**
 * Pretty-print the whole state at the program point where it is called.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-dump-each
 */
/*@ assigns \nothing; */
void tis_dump_each(void) __TIS_THROW;

/**
 * Pretty-print the whole state at the program point where it is called as a
 * list of constraints.
 *
 * @warning This function does not have utility for users performing analyses.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-dump-assert-each
 */
/*@ assigns \nothing; */
void tis_dump_assert_each(void) __TIS_THROW;

/**
 * Pretty-print the whole state at the program point where it is called as a
 * list of C assignments.
 *
 * @warning This function does not have utility for users performing analyses.
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-dump-assignments-each
 */
/*@ assigns \nothing; */
void tis_dump_assignments_each(void) __TIS_THROW;

/**
 * Output the whole state at the program point where it is called into a file.
 *
 * @warning This function does not have utility for users performing analyses.
 *
 * @param __name a string literal specifying the name of the output file
 *
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-dump-each-file
 */
/*@ assigns \nothing; */
void tis_dump_each_file(char *__name, ...) __TIS_THROW;

// see code and specifications in tis_mem_bounded.c
void * tis_memset_bounded(void *__dst, int __c, unsigned long __n,
                          void *__dst_bound) __TIS_THROW;
void * tis_memcpy_bounded(void *__dst, const void *__src, unsigned long __n,
                          void *__dst_bound, const void *__src_bound) __TIS_THROW;
void * tis_memmove_bounded(void *__dst, const void *__src, unsigned long __n,
                           void *__dst_bound, const void *__src_bound) __TIS_THROW;

/**
 * Pretty-print the value pointed to by `__p` with the
 * help of a corresponding user-defined C function when the value pointed
 * to by `__p` has `tis_pretty` attribute.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-pretty
 */
/*@ assigns \nothing; */
void tis_pretty(const void *__p, ...) __TIS_THROW;

/**
 * Load the contents of a file from the host filesystem.
 *
 * @param[in] __filename a string literal specifying the name of the input
 *                       file
 * @param[out] __size the size of the loaded file, must point to a unique
 *                    valid object
 * @return an object containing the data from the loaded file
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-inject-file
 */
/*@ assigns \result, *__size \from __filename[0..]; */
char *tis_inject_file (const char *__filename, unsigned long *__size) __TIS_THROW;

/**
 * Print the list of allocated memory blocks that are not referenced by any
 * other memory block anymore.
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-check-leak
 */
/*@ assigns \nothing; */
void tis_check_leak (void) __TIS_THROW;

enum tis_valid_pointer { TIS_POINTERS_MAY_BE_NULL, TIS_VALID_POINTERS };

/**
 * Construct an abstract value and make the pointer `*__ptr` point to it.
 *
 * @param[in] __type string representing the type of `*__ptr`
 * @param[out] __ptr the pointer being initialized
 * @param __depth depth of the structure to allocate
 * @param __width width of the array to allocate
 * @param __valid_pointers whether to allow null pointers in the structure to allocate
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-init-type
 */
/*@
  assigns ((char*)__ptr)[0..] \from __fc_heap_status, __type[0..], __depth,
  __width, __valid_pointers;
*/
void tis_init_type(const char * __type, void * __ptr, unsigned long __depth,
                   unsigned long __width, enum tis_valid_pointer __valid_pointers) __TIS_THROW;

/**
 * Pretty-print the message `__msg` and the *ival* representation of each of
 * the following arguments.
 *
 * @param[in] __msg message to print
 * @param ... arguments whose ival representation to print
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-show-ival-representation
 */
/*@ assigns \nothing; */
void tis_show_ival_representation(const char * __msg, ...) __TIS_THROW;

/**
 * Return the *ival* representation of the argument.
 *
 * @param __value argument
 * @return ival representation of the argument
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/c.html#builtin-tis-force-ival-representation
 */
/*@ assigns \result \from __value; */
unsigned long tis_force_ival_representation(unsigned long __value) __TIS_THROW;

/*@ allocates \result;
    assigns __fc_heap_status \from __alignment, __size, __fc_heap_status;
    assigns \result \from __alignment, __size, __fc_heap_status;
    assigns __TIS_errno \from __alignment, __size, __fc_heap_status;
*/
void *tis_aligned_alloc(unsigned long __alignment,
                        unsigned long __size) __TIS_THROW;
                        

/*@ assigns ((char*)__dst)[0..__n-1];*/
void *tis_memcpy(void *__dst, const void *__src, unsigned long __n) __TIS_THROW;
void tis__exit(int) __TIS_THROW;
double tis_acos(double) __TIS_THROW;
double tis_asin(double) __TIS_THROW;
int tis_asprintf_interpreter(char **, const char *, ...) __TIS_THROW;
double tis_atan(double) __TIS_THROW;
double tis_atan2(double, double) __TIS_THROW;
double tis_atof_interpreter(const char *) __TIS_THROW;
int tis_atoi_interpreter(const char *) __TIS_THROW;
long tis_atol_interpreter(const char *) __TIS_THROW;
long long tis_atoll_interpreter(const char *) __TIS_THROW;
double tis_ceil(double) __TIS_THROW;
float tis_ceilf(float) __TIS_THROW;
double tis_cos(double) __TIS_THROW;
double tis_cos_precise(double) __TIS_THROW;
double tis_cosh(double) __TIS_THROW;
int tis_degenerate_or_inject(void) __TIS_THROW;
double tis_exp(double) __TIS_THROW;
float tis_expf(float) __TIS_THROW;
double tis_floor(double) __TIS_THROW;
float tis_floorf(float) __TIS_THROW;
double tis_fma(double, double, double) __TIS_THROW;
float tis_fmaf(float, float, float) __TIS_THROW;
double tis_fmax(double, double) __TIS_THROW;
double tis_fmin(double, double) __TIS_THROW;
double tis_fmod(double, double) __TIS_THROW;
int tis_fprintf(/* FILE */void *, const char *, ...) __TIS_THROW;
double tis_hypot(double, double) __TIS_THROW;
double tis_log(double) __TIS_THROW;
double tis_log10(double) __TIS_THROW;
float tis_log10f(float) __TIS_THROW;
float tis_logf(float) __TIS_THROW;
void *tis_memchr(const void *, int, unsigned long) __TIS_THROW;
int tis_memcmp(const void *, const void *, unsigned long) __TIS_THROW;
void *tis_memcpy(void *, const void *, unsigned long) __TIS_THROW;
void *tis_memmove(void *, const void *, unsigned long) __TIS_THROW;
void *tis_memset(void *, int, unsigned long);
double tis_nan(const char *) __TIS_THROW;
float tis_nanf(const char *) __TIS_THROW;
double tis_nextafter(double, double) __TIS_THROW;
float tis_nextafterf(float, float) __TIS_THROW;
double tis_pow(double, double) __TIS_THROW;
float tis_powf(float, float) __TIS_THROW;
int tis_printf(const char *, ...) __TIS_THROW;
void *tis_realloc(void *, unsigned long) __TIS_THROW;
void *tis_realloc_multiple(void *, unsigned long) __TIS_THROW;
double tis_round(double) __TIS_THROW;
float tis_roundf(float) __TIS_THROW;
int tis_scanf_interpreter(const char *, ...) __TIS_THROW;
double tis_sin(double) __TIS_THROW;
double tis_sin_precise(double) __TIS_THROW;
double tis_sinh(double) __TIS_THROW;
int tis_sprintf(char *, const char *, ...) __TIS_THROW;
int tis_snprintf(char *, unsigned long, const char *, ...) __TIS_THROW;
double tis_sqrt(double) __TIS_THROW;
float tis_sqrtf(float) __TIS_THROW;
int tis_sscanf_interpreter(const char *, const char *, ...) __TIS_THROW;
char *tis_strcat(char *, const char *) __TIS_THROW;
char *tis_strchr(const char *, int) __TIS_THROW;
int tis_strcmp(const char *, const char *) __TIS_THROW;
int tis_strcasecmp(const char *, const char *) __TIS_THROW;
char *tis_strcpy(char *, const char *) __TIS_THROW;
__typeof__(sizeof(int)) tis_strlen(const char *) __TIS_THROW;
char *tis_strncat(char *, const char *, unsigned long) __TIS_THROW;
int tis_strncmp(const char *, const char *, unsigned long) __TIS_THROW;
int tis_strncasecmp(const char *, const char *, unsigned long) __TIS_THROW;
char *tis_strncpy(char *, const char *, unsigned long) __TIS_THROW;
__typeof__(sizeof(int)) tis_strnlen(const char *, unsigned long) __TIS_THROW;
double tis_strtod_interpreter(const char *, char **) __TIS_THROW;
float tis_strtof_interpreter(const char *, char **) __TIS_THROW;
long int tis_strtol_interpreter(const char *, char **, int) __TIS_THROW;
long double tis_strtold_interpreter(const char *, char **) __TIS_THROW;
long long int tis_strtoll_interpreter(const char *, char **, int) __TIS_THROW;
unsigned long int tis_strtoul_interpreter(const char *, char **, int) __TIS_THROW;
unsigned long long int tis_strtoull_interpreter(const char *, char **, int) __TIS_THROW;
//int tis_swprintf(wchar_t *, unsigned long long, const wchar_t *, ...) __TIS_THROW;
double tis_tan(double) __TIS_THROW;
double tis_tanh(double) __TIS_THROW;
double tis_trunc(double) __TIS_THROW;
float tis_truncf(float) __TIS_THROW;

// also  used for normalization (see __fc_builtin_for_normalization.i)
void tis_bzero(unsigned char* dest,  __typeof__(sizeof(int))/*size_t*/ n);

// All the others rely on va_list of wchar_t
// int tis_vasprintf_interpreter(char **strp, const char *fmt, va_list ap) __TIS_THROW;
// int tis_vfprintf(FILE *stream, const char *format, va_list ap) __TIS_THROW;
// int tis_vprintf(const char *format, va_list ap) __TIS_THROW;
// int tis_vsnprintf(char *str, unsigned long long size, const char *format, va_list ap) __TIS_THROW;
// int tis_vsprintf(char *str, const char *format, va_list ap) __TIS_THROW;
// int tis_vwprintf(const wchar_t *format, va_list args) __TIS_THROW;
// wchar_t *tis_wcscat(wchar_t *dest, const wchar_t *src) __TIS_THROW;
// tis_wcschr, tis_wcscmp, tis_wcscpy, tis_wcslen, tis_wcsncat, tis_wcsncmp
// tis_wcsncpy, tis_wcsnlen, tis_wmemcpy, tis_wmemmove, tis_wprintf

__END_DECLS

#ifdef __cplusplus
/* C++-specific builtins.*/
/**
 * Populate an area of memory starting at address `__p` of size `__l` with
 * abstract values representing unknown contents.
 *
 * @param __p pointer to an area of memory to populate
 * @param __l size of the area of memory being populated (in bytes)
 * 
 * @see https://man.trust-in-soft.com/ref/builtins/cpp.html#builtin-tis-make-unknown
 */
/*@ requires valid_buffer: \valid(((char *)__p) + (0 .. __l-1));
    assigns ((char *)__p)[0 .. __l-1] \from tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
    ensures \initialized(((char *)__p) + (0 .. __l-1));
*/
void tis_make_unknown(void *__p, unsigned long __l) __TIS_THROW;

/**
 * @see https://man.trust-in-soft.com/ref/builtins/cpp.html#builtin-tis-make-unknown-t
 */
template <typename T>
/*@ requires valid_buffer: \valid(__object);
    assigns *__object \from tis_entropy_source;
    assigns tis_entropy_source \from tis_entropy_source;
*/
void tis_make_unknown(T *__object) __TIS_THROW;

/* This builtin is used to access the direct field [fieldName] of type
   [FieldType] from an object [obj] of type [ClassType]. No conversion is done
   on [FieldType]. */
template <typename FieldType, typename ClassType>
FieldType *tis_get_direct_field(ClassType *obj, const char *fieldName);

#endif

#undef __TIS_THROW

#endif /* tis_builtin.h */
