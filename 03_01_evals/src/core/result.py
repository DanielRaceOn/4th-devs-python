# -*- coding: utf-8 -*-

#   result.py

"""
### Description:
Minimal Result monad — mirrors src/core/result.ts.

Provides ``Ok[T]`` / ``Err[E]`` discriminated union types and the
``ok()`` / ``err()`` constructors used throughout the codebase.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/result.ts

"""

from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


class Ok(Generic[T]):
    """Successful result wrapper."""

    ok: bool = True

    def __init__(self, value: T) -> None:
        self.value = value


class Err(Generic[E]):
    """Error result wrapper."""

    ok: bool = False

    def __init__(self, error: E) -> None:
        self.error = error


# Union type alias used in type hints throughout the codebase
Result = Ok[T] | Err[E]


def ok(value: T) -> Ok[T]:
    """Wrap a success value.

    Args:
        value: The success value.

    Returns:
        An ``Ok`` wrapping the value.
    """
    return Ok(value)


def err(error: E) -> Err[E]:
    """Wrap an error value.

    Args:
        error: The error value.

    Returns:
        An ``Err`` wrapping the error.
    """
    return Err(error)
