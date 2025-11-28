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

enum tis_valid_pointer { TIS_POINTERS_MAY_BE_NULL, TIS_VALID_POINTERS };

#endif /* tis_builtin.h */
