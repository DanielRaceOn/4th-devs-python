# -*- coding: utf-8 -*-

#   result.py

"""
### Description:
Minimal Result monad — ok/err discriminated union.

Mirrors src/core/result.ts: Result<T, E> is either
``{"ok": True, "value": T}`` or ``{"ok": False, "error": E}``.

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/core/result.ts

"""

from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


class Ok(Generic[T]):
    """Successful result wrapper."""

    ok: bool = True

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


class Err(Generic[E]):
    """Error result wrapper."""

    ok: bool = False

    def __init__(self, error: E) -> None:
        self.error = error

    def __repr__(self) -> str:
        return f"Err({self.error!r})"


# Union type alias — Result[T, E]
Result = Union[Ok[T], Err[E]]


def ok(value: T) -> Ok[T]:
    """Wrap a success value.

    Args:
        value: The success value.

    Returns:
        An ``Ok`` instance carrying ``value``.
    """
    return Ok(value)


def err(error: E) -> Err[E]:
    """Wrap an error value.

    Args:
        error: The error value.

    Returns:
        An ``Err`` instance carrying ``error``.
    """
    return Err(error)
