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

#endif /* tis_builtin.h */

